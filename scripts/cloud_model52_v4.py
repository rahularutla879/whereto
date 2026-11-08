"""Task52B v4 readiness only. No inference endpoint, journal mutation or retries.

The v3 adapter/configuration/audit remains intact. This module binds a separate
configuration to the reviewed common addition and source-bound offline scorer.
"""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
import sqlite3

from scripts import cloud_model52 as e
from scripts import cloud_model52_audit as audit
from scripts import cloud_model52_live as old
from scripts import cloud_model52_offline as scorer
from scripts import cloud_model52_proposal as proposal

VERSION = '52b-v4-order-edge-quotes'
BASE_HASH = '1c2352a7ec2b0bf826567de22b36ff2265bcd957e979d5b307cface7b5e0ee4e'
PROMPT_HASH = '1614adf1a72843e987b5d5ebdbf33099ce94a0740c4efb9def07125da6ee84c8'
JOURNAL_SHA = 'd13b585b4821be465be1c635792471072f11f38258f87e2e94126481835e9a45'
SLOTS = ('journey-04', 'extension-partial', 'extension-repeated', 'journey-12', 'journey-06')
COUNT_PATHS = {'openai': '/responses/input_tokens',
    'google': '/models/gemini-3.8-flash:countTokens', 'anthropic': '/messages/count_tokens'}
FREE_COUNT_SOURCES = {
    'openai': 'https://help.openai.com/en/articles/4936856-understanding-and-counting-tokens',
    'anthropic': 'https://platform.claude.com/docs/en/build-with-claude/token-counting',
    'google': 'https://discuss.ai.google.dev/t/direct-gemini-developer-api-counttokens-free-tier-billing-and-quota-clarification/190706'}


def configuration():
    if e.digest(e.metadata()) != BASE_HASH or len(proposal.ADDITION.encode()) != 370:
        raise e.AdmissionError('Reviewed base configuration/addition changed')
    if e.digest(proposal.messages('')) != PROMPT_HASH:
        raise e.AdmissionError('Exact reviewed v4 instructions/examples changed')
    return {**e.metadata(), 'promptVersion': VERSION,
            'promptHash': PROMPT_HASH, 'evaluatorVersion': scorer.VERSION}


def payload(case_id, provider):
    if provider not in e.CANDIDATES:
        raise e.AdmissionError('Unknown provider; no substitution')
    configuration()
    case = next((c for c in e.corpus()['cases'] if c['id'] == case_id), None)
    if case is None:
        raise e.AdmissionError('Only original synthetic corpus allowed')
    return proposal.payload(provider, case['text'])


def journal_snapshot():
    path = e.STATE / 'journal.sqlite'
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != JOURNAL_SHA:
        raise e.AdmissionError('Original seven-attempt journal changed/missing')
    db = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
    try:
        rows = db.execute('select * from attempts order by rowid').fetchall()
        if db.execute('pragma integrity_check').fetchone() != ('ok',):
            raise e.AdmissionError('Journal integrity failed')
        if len(rows) != 7 or sum(r[4] for r in rows) != 39866625:
            raise e.AdmissionError('Original attempts/reservations changed')
        for row in rows:
            if row[0] == 'openai': audit.effective_record(row, e.STATE / 'corrections')
        return {'sha256': JOURNAL_SHA, 'rootHash': e.digest(db.execute('select config from metadata').fetchone()[0]),
            'rows': [{'slot': list(r[:3]), 'rowHash': e.digest(r)} for r in rows],
            'counts': {p: sum(r[0] == p for r in rows) for p in e.CANDIDATES},
            'accountedNanodollars': sum(r[4] for r in rows), 'integrity': 'ok'}
    finally:
        db.close()


def future_plan():
    snapshot = journal_snapshot()
    consumed = {tuple(r['slot']) for r in snapshot['rows']}
    slots = [['openai', case, 1] for case in SLOTS]
    if any(tuple(slot) in consumed for slot in slots):
        raise e.AdmissionError('Proposed slot already consumed; never retry')
    return {'status': 'PROPOSED; owner approval required; no dispatch implementation',
        'configurationHash': e.digest(configuration()), 'evaluatorVersion': scorer.VERSION,
        'journal': snapshot, 'slots': slots, 'maxFutureAttempts': 5, 'authorizedInferenceRequests': 0,
        'maxFutureReservationNanodollars': 12500000, 'concurrency': 1, 'retries': 0,
        'stopConditions': ['provider/schema/permission error', 'cap/spend admission failure',
            'unsafe accepted hallucination', 'critical stop/order/return/time mismatch',
            'missing or unresolved semantic review', 'persistent halt', 'readiness/pricing expiry'],
        'review': 'All fields per response; extension cases have prose gold and require explicit review. Agent review is not independent human signoff.'}


def count_body(case_id, provider):
    full = payload(case_id, provider)
    if provider == 'openai':
        # Include the same reasoning representation, instructions/examples and
        # strict text.format schema. No previous responses, files or tools.
        body = {k: full[k] for k in ('model', 'input', 'text', 'reasoning')}
    elif provider == 'anthropic':
        body = {k: v for k, v in full.items() if k != 'max_tokens'}
    else:
        # Developer API counting does not certify generationConfig injection.
        # Count schema-as-text too, but never label this a complete format count.
        body = {'generateContentRequest': {'model': 'models/gemini-3.8-flash',
            'systemInstruction': full['systemInstruction'],
            'contents': full['contents'] + [{'role': 'user', 'parts': [
                {'text': json.dumps(e.wire_schema(provider), ensure_ascii=False)}]}]}}
    return COUNT_PATHS[provider], body


class CountingHTTP:
    """Narrower boundary than the historical transport: generation is forbidden."""
    def __init__(self, provider, key):
        self.provider = provider
        self._http = old.HTTP(provider, key)

    def request(self, method, path, body=None):
        model_path = '/models/' + e.CANDIDATES[self.provider]['model']
        if not ((method == 'POST' and path == COUNT_PATHS[self.provider]) or
                (method == 'GET' and self.provider != 'openai' and path == model_path)):
            raise e.AdmissionError('Readiness transport forbids inference/other endpoints')
        return self._http.request(method, path, body)


def prepare(provider, directory, http=None):
    """At most66 free count operations/provider, checkpoints, no automatic retry.

    Caller first verifies current fee/privacy/account terms. Existing completed
    checkpoints are validated and reused; a failed/uncertain checkpoint stops.
    No old readiness/configuration/paid journal file is overwritten.
    """
    before = journal_snapshot()
    directory = Path(directory)
    config = configuration(); identity = e.digest(config)
    audit.append_json(directory / 'configuration.json', {'hash': identity, 'configuration': config})
    audit.append_json(directory / 'journal-before.json', before)
    http = http if http is not None else CountingHTTP(provider, old.credentials()[provider])
    results = []
    for case in e.corpus()['cases']:
        path, body = count_body(case['id'], provider)
        destination = directory / (provider + '-' + case['id'] + '.json')
        binding = {'configurationHash': identity, 'provider': provider, 'caseId': case['id'],
                   'payloadHash': e.digest(payload(case['id'], provider)), 'countBodyHash': e.digest(body)}
        if destination.exists():
            row = json.loads(destination.read_text())
            if any(row.get(k) != v for k, v in binding.items()):
                raise e.AdmissionError('Counting checkpoint drift')
        else:
            # Commit an uncertainty marker BEFORE I/O, never retry it implicitly.
            marker = destination.with_suffix('.started.json')
            if marker.exists():
                raise e.AdmissionError('Interrupted count requires review; no automatic retry')
            audit.append_json(marker, binding)
            try:
                counted = http.request('POST', path, body)
                count = counted.get('totalTokens') if provider == 'google' else counted.get('input_tokens')
                if provider == 'openai' and counted.get('object') != 'response.input_tokens':
                    count = None
                row = {**binding, 'httpStatus': counted.get('_http_status'),
                       'inputTokens': count if type(count) is int and count > 0 else None,
                       'observedAtUTC': datetime.now(timezone.utc).isoformat()}
            except Exception as error:
                row = {**binding, 'inputTokens': None, 'failureType': type(error).__name__,
                       'observedAtUTC': datetime.now(timezone.utc).isoformat()}
            audit.append_json(destination, row)
        if row.get('httpStatus') != 200 or type(row.get('inputTokens')) is not int or row['inputTokens'] <= 0:
            raise e.AdmissionError('Counting failed/uncertain; inspect sanitized checkpoint, no retry')
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(row['observedAtUTC'])).total_seconds()
        except (ValueError, TypeError, KeyError):
            raise e.AdmissionError('Invalid counting timestamp') from None
        if not 0 <= age <= 86400:
            raise e.AdmissionError('Counting evidence expired; explicit refresh in a new readiness artifact required')
        results.append(row)
    if journal_snapshot() != before:
        raise e.AdmissionError('Readiness must never change paid journal')
    margin = 512 if provider == 'anthropic' else 2048
    maximum = max(r['inputTokens'] for r in results)
    return {'configurationHash': identity, 'provider': provider, 'casesCounted': len(results),
            'minCounted': min(r['inputTokens'] for r in results), 'maxCounted': maximum,
            'margin': margin, 'admissionBound': maximum + margin,
            'capPass': maximum + margin <= e.INPUT_CAP,
            'completeStructuredInputCount': provider != 'google',
            'countCoverage': 'Full input with output_config/schema injection' if provider == 'anthropic' else
                'Complete Responses input/text.format/reasoning' if provider == 'openai' else
                'Messages/system plus schema-as-text; actual structured-format overhead unverified',
            'outputCap': e.OUTPUT_CAP, 'inferenceRequests': 0, 'countFeeUSD': 0,
            'paidDispatchAuthorized': False, 'counts': results}


def anthropic_grammar_proposal():
    """Factor shared nullable Duration, not a semantic/canonical field change.

    A repeated union's syntactic duplication is reduced. Its expanded logical
    branches remain identical; remote grammar benefit is unproven. Not activated.
    """
    schema = copy.deepcopy(e.wire_schema('anthropic'))
    nullable = {'anyOf': [{'$ref': '#/$defs/Duration'}, {'type': 'null'}]}
    count = 0
    def walk(node):
        nonlocal count
        if isinstance(node, dict):
            if node == nullable:
                count += 1
                return {'$ref': '#/$defs/NullableDuration'}
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list): return [walk(v) for v in node]
        return node
    factored = walk(schema)
    if count != 2:
        raise e.AdmissionError('Reviewed repeated nullable Duration structure changed')
    factored['$defs']['NullableDuration'] = nullable
    return factored
