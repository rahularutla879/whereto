"""Isolated Task 52B model evaluation. Never imported by application runtime.

Offline: python -m scripts.cloud_model52 inspect
Live dispatch intentionally requires a separately completed account-readiness review.
No SDK, implicit credentials, automatic retries, fallback or arbitrary prompt input.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime
import fcntl
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time
from unittest.mock import patch

from backend.ai import Interpretation, parse_interpretation
from backend.ai.ollama import EXAMPLES, SYSTEM_PROMPT
from backend.interpretation import InterpretationInput, activity_category, interpret_request
from backend.journey import LIMITATION

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'docs/task52-evaluation-corpus.json'
CORPUS_SHA = '5c7be9828fd6690f5b11ef38bee019eff5a9962adaccef13ee572fca2ac8549f'
STATE = ROOT / 'backend/.local/task52-model-evaluation'
PROMPT_VERSION = '52b-v2-unchanged-instructions-reviewed-wire-settings'
INPUT_CAP, OUTPUT_CAP = 12000, 2000
TOTAL_CAP, PROVIDER_CAP, SPEND_CAP = 594, 198, 12_000_000_000  # nanodollars
# Noncached standard text rates in nanodollars/token. No tools, cache writes,
# batch, fast mode, region premium or subscription may be enabled implicitly.
CANDIDATES = {
    'openai': {'model': 'gpt-6-luna', 'rates': [125, 500],
               'blockers': ['Live requires hash-bound readiness and token admission']},
    'google': {'model': 'gemini-3.8-flash', 'rates': [750, 3750],
               'blockers': ['Live requires hash-bound readiness and token admission', 'Introductory global pricing expires 2026-12-31']},
    'anthropic': {'model': 'claude-haiku-5-5', 'rates': [100, 500],
                  'blockers': ['Live requires hash-bound readiness and token admission']},
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def corpus():
    raw = CORPUS.read_bytes()
    if hashlib.sha256(raw).hexdigest() != CORPUS_SHA:
        raise ValueError('Authoritative corpus changed; explicit review required')
    data = json.loads(raw)
    cases = data['cases']
    if len(cases) != 66 or data['caseCount'] != 66 or len({c['id'] for c in cases}) != 66:
        raise ValueError('Corpus count/identity mismatch')
    for name, expected in data['sourceSha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Reference source changed; review required: ' + name)
    return data


def schema():
    """Same clock-free schema projection as local adapter, then explicit defaults.

    All object properties required for strict output; defaults stripped only from
    provider schema. Shared Pydantic contract and source validation are unchanged.
    """
    result = Interpretation.model_json_schema()
    for key in ('start_time', 'end_time'):
        result['properties'].pop(key)
    result['properties']['journey'] = {'$ref': '#/$defs/Journey'}
    result['$defs']['Journey']['properties'].pop('order_conflict')
    result['$defs']['Deadline']['properties'].pop('minute')
    def strict(node):
        if isinstance(node, dict):
            node.pop('default', None)
            if node.get('type') == 'object':
                node['required'] = list(node.get('properties', {}))
                node['additionalProperties'] = False
            for value in list(node.values()):
                strict(value)
        elif isinstance(node, list):
            for value in node:
                strict(value)
    strict(result)
    return result


def wire_schema(provider):
    """Provider dialect only; original constraints remain enforced offline."""
    canonical = schema()
    if provider == 'openai':
        return canonical
    def project(node):
        if not isinstance(node, dict):
            return node
        if provider == 'google' and '$ref' in node:
            return project(canonical['$defs'][node['$ref'].split('/')[-1]])
        node = dict(node)
        if provider == 'google' and 'anyOf' in node:
            alternatives = node['anyOf']
            nonnull = [b for b in alternatives if b.get('type') != 'null']
            if len(nonnull) == 1 and len(alternatives) != len(nonnull):
                return {**project(nonnull[0]), 'nullable': True}
        moved = {}
        unsupported = {'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum',
                       'multipleOf', 'minLength', 'maxLength', 'pattern', 'minItems', 'maxItems'} if provider == 'anthropic' else {
                           'title', 'additionalProperties', 'minLength', 'maxLength',
                           'pattern', 'exclusiveMinimum', 'exclusiveMaximum', 'multipleOf'}
        for key in unsupported:
            if key in node:
                moved[key] = node.pop(key)
        if moved:
            node['description'] = (node.get('description', '') + ' Validation constraints: ' + json.dumps(moved, sort_keys=True)).strip()
        for key in ('properties', '$defs'):
            if key in node:
                node[key] = {name: project(value) for name, value in node[key].items()}
        if 'items' in node:
            node['items'] = project(node['items'])
        if 'anyOf' in node:
            node['anyOf'] = [project(value) for value in node['anyOf']]
        if provider == 'google':
            node.pop('$defs', None)
            if 'const' in node:
                node['enum'] = [node.pop('const')]
            if 'type' in node:
                node['type'] = node['type'].upper()
        return node
    return project(canonical)


def messages(text):
    return [{'role': 'system', 'content': SYSTEM_PROMPT}] + [
        message for example, reply in EXAMPLES for message in (
            {'role': 'user', 'content': example},
            {'role': 'assistant', 'content': json.dumps(reply, separators=(',', ':'))})
    ] + [{'role': 'user', 'content': text}]


def metadata():
    data = corpus()
    return {'experiment': 'task52b-phase1', 'corpusHash': CORPUS_SHA,
            'promptVersion': PROMPT_VERSION, 'promptHash': digest(messages('')),
            'schemaHash': digest(schema()),
            'wireSchemaHashes': {p: digest(wire_schema(p)) for p in CANDIDATES}, 'referenceTime': data['referenceTime'],
            'candidates': CANDIDATES, 'inputCap': INPUT_CAP, 'outputCap': OUTPUT_CAP,
            'attemptCap': TOTAL_CAP, 'providerCap': PROVIDER_CAP,
            'spendCapNanodollars': SPEND_CAP, 'concurrency': 1, 'retries': 0,
            'timezonePolicy': 'Explicit America/New_York or Asia/Kolkata for named synthetic destinations; unknown remains unknown',
            'sampling': {'openai': 'temperature 0; reasoning none', 'google': 'temperature 0; thinking low', 'anthropic': 'temperature omitted; thinking disabled; effort low'},
            'tools': False, 'inferenceRegion': 'standard global; synthetic non-personal evaluation only',
            'transportVersion': '52b-single-http-v1', 'timeoutSeconds': 120,
            'googleService': 'Gemini Developer API; separate paid Default Gemini Project'}


class Adapter:
    """Mechanical provider wire mapping; transport must make exactly one call.

    Endpoint/authentication is deliberately not implemented until Stage B passes.
    An injected transport receives a body only, never credentials in artifacts.
    """
    def __init__(self, provider, transport):
        self.provider, self.transport = provider, transport

    def payload(self, text):
        common = messages(text)
        model = CANDIDATES[self.provider]['model']
        if self.provider == 'openai':
            return {'model': model, 'messages': common, 'temperature': 0, 'reasoning_effort': 'none', 'service_tier': 'default',
                    'max_completion_tokens': OUTPUT_CAP, 'store': False,
                    'response_format': {'type': 'json_schema', 'json_schema': {
                        'name': 'outing_interpretation', 'strict': True, 'schema': wire_schema(self.provider)}}}
        if self.provider == 'anthropic':
            return {'model': model, 'system': SYSTEM_PROMPT, 'messages': common[1:],
                    'max_tokens': OUTPUT_CAP, 'thinking': {'type': 'disabled'},
                    'output_config': {'effort': 'low', 'format': {'type': 'json_schema', 'schema': wire_schema(self.provider)}}}
        return {'systemInstruction': {'parts': [{'text': SYSTEM_PROMPT}]},
                'contents': [{'role': 'model' if m['role'] == 'assistant' else 'user',
                              'parts': [{'text': m['content']}]} for m in common[1:]],
                'generationConfig': {'temperature': 0, 'maxOutputTokens': OUTPUT_CAP, 'thinkingConfig': {'thinkingLevel': 'low'},
                                     'responseMimeType': 'application/json', 'responseSchema': wire_schema(self.provider)}}

    def decode(self, response):
        """Return content, complete billed usage, and safe stop classification."""
        if 'error' in response:
            return None, None, 'provider_error'
        if self.provider == 'openai':
            choice = response['choices'][0]
            usage = response.get('usage', {})
            status = ('refusal' if choice['message'].get('refusal') else
                      'complete' if choice['finish_reason'] == 'stop' else 'incomplete')
            return choice['message'].get('content'), (usage.get('prompt_tokens'), usage.get('completion_tokens')), status
        if self.provider == 'anthropic':
            usage = response.get('usage', {})
            # Sum every billed input class conservatively; no caching is requested.
            inputs = usage.get('input_tokens')
            if inputs is not None:
                inputs += usage.get('cache_creation_input_tokens', 0) + usage.get('cache_read_input_tokens', 0)
            status = 'complete' if response['stop_reason'] == 'end_turn' else response['stop_reason']
            return ''.join(b['text'] for b in response.get('content', []) if b['type'] == 'text'), (inputs, usage.get('output_tokens')), status
        usage = response.get('usageMetadata', {})
        inputs, total = usage.get('promptTokenCount'), usage.get('totalTokenCount')
        # Total minus prompt includes reasoning, unlike candidatesTokenCount alone.
        output = total - inputs if type(total) is int and type(inputs) is int else None
        candidates = response.get('candidates', [])
        if not candidates:
            return None, (inputs, output), 'refusal'
        candidate = candidates[0]
        return ''.join(p.get('text', '') for p in candidate.get('content', {}).get('parts', []) if not p.get('thought')), (inputs, output), ('complete' if candidate.get('finishReason') == 'STOP' else 'incomplete')


class AdmissionError(RuntimeError):
    pass


class Ledger:
    """One durable journal for all candidates, repetitions and configurations.

    Caller holds process lock across complete operation. FULL sync commits before
    dispatch. Reserved/uncertain rows are terminal: never retry on resumption.
    """
    def __init__(self, path, config):
        self.directory = Path(path).parent
        Path(path).touch(mode=0o600, exist_ok=True)
        Path(path).chmod(0o600)
        self.db = sqlite3.connect(path)
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('CREATE TABLE IF NOT EXISTS metadata (id INTEGER PRIMARY KEY CHECK(id=1), config TEXT NOT NULL); CREATE TABLE IF NOT EXISTS attempts (provider TEXT, case_id TEXT, repetition INTEGER, status TEXT NOT NULL, charge INTEGER NOT NULL, record TEXT, PRIMARY KEY(provider,case_id,repetition));')
        encoded = json.dumps(config, sort_keys=True)
        self.db.execute('INSERT OR IGNORE INTO metadata VALUES (1,?)', (encoded,))
        self.db.commit()
        if self.db.execute('SELECT config FROM metadata').fetchone()[0] != encoded:
            self.db.close()
            raise AdmissionError('Configuration changed; cannot reset or fork paid allowance')

    def reserve(self, provider, case_id, repetition):
        if provider not in CANDIDATES or case_id not in {c['id'] for c in corpus()['cases']} or type(repetition) is not int or repetition not in (1, 2, 3):
            raise AdmissionError('Not an authorized corpus/repetition/provider slot')
        if self.db.execute("SELECT 1 FROM attempts WHERE status='recorded_halted'").fetchone():
            raise AdmissionError('Experiment halted; owner review required')
        rates = CANDIDATES[provider]['rates']
        reservation = INPUT_CAP * rates[0] + OUTPUT_CAP * rates[1]
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            if self.db.execute('SELECT 1 FROM attempts WHERE provider=? AND case_id=? AND repetition=?', (provider, case_id, repetition)).fetchone():
                return False
            total, charge = self.db.execute('SELECT count(*),coalesce(sum(charge),0) FROM attempts').fetchone()
            count = self.db.execute('SELECT count(*) FROM attempts WHERE provider=?', (provider,)).fetchone()[0]
            if total >= TOTAL_CAP or count >= PROVIDER_CAP or charge + reservation > SPEND_CAP:
                raise AdmissionError('Attempt/spend ceiling refuses dispatch')
            self.db.execute('INSERT INTO attempts VALUES (?,?,?,?,?,NULL)', (provider, case_id, repetition, 'reserved_uncertain', reservation))
        return True

    def finish(self, provider, case_id, repetition, record, usage):
        rates = CANDIDATES[provider]['rates']
        row = self.db.execute('SELECT status,charge FROM attempts WHERE provider=? AND case_id=? AND repetition=?', (provider, case_id, repetition)).fetchone()
        if row is None or row[0] != 'reserved_uncertain':
            raise AdmissionError('Missing or already completed reservation')
        charge = row[1]
        if usage and len(usage) == 2 and all(type(n) is int and n >= 0 for n in usage):
            if usage[0] > INPUT_CAP or usage[1] > OUTPUT_CAP:
                # Record the observed liability; stop the experiment, never hide it.
                record['capViolation'] = True
                charge = max(charge, sum(n * r for n, r in zip(usage, rates)))
            else:
                charge = sum(n * r for n, r in zip(usage, rates))
        record['accountedNanodollars'] = charge
        with self.db:
            self.db.execute('UPDATE attempts SET status=?,charge=?,record=? WHERE provider=? AND case_id=? AND repetition=?',
                            ('recorded_halted' if record.get('capViolation') or record.get('reviewHalt') else 'recorded', charge, json.dumps(record), provider, case_id, repetition))
        if record.get('capViolation'):
            raise AdmissionError('Provider usage exceeded caps; all further dispatch stopped')

    def close(self):
        self.db.close()


@contextmanager
def exclusive(directory):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (directory / 'experiment.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def timezone_for(case):
    text = case['text'].casefold()
    if any(x in text for x in ('hyderabad', 'kothapet')):
        return 'Asia/Kolkata'
    if any(x in text for x in ('jersey city', 'manhattan', 'brooklyn', 'baltimore', 'washington', 'penn station', 'suny')):
        return 'America/New_York'
    return None


def validate(case, content):
    ai = parse_interpretation(content)  # duplicate, unknown, missing required/type checks
    class Recorded:
        def interpret(self, _):
            return ai
    with patch('requests.sessions.Session.send', side_effect=AssertionError('No network in scoring')), patch('socket.create_connection', side_effect=AssertionError('No network in scoring')):
        result = interpret_request(InterpretationInput(text=case['text'], calendarTimezone=timezone_for(case)), Recorded(), now=datetime.fromisoformat(corpus()['referenceTime'].replace('Z', '+00:00')))
    return ai, result


def score(case, content):
    row = {'structuredValid': False, 'validatedAccepted': False,
           'fullyCorrect': None, 'reviewRequired': True}
    try:
        ai, result = validate(case, content)
        missing = missing_properties(json.loads(content), schema())
        unknown = missing_properties(json.loads(content), schema(), unknown=True)
        row['missingRequiredProperties'] = missing
        row['unknownProperties'] = unknown
        advanced_handoff = (result.executionStatus == 'advanced_unavailable'
                            and result.issues == [LIMITATION] and result.unsupported == [LIMITATION]
                            and result.context is not None and result.interpretation.journey is not None)
        ordinary_accepted = not result.issues and not result.unsupported and not result.questions
        row.update(structuredValid=not missing and not unknown,
                   groundedAdvancedHandoff=advanced_handoff,
                   validatedAccepted=not missing and not unknown and (ordinary_accepted or advanced_handoff),
                   questions=[q.field for q in result.questions], issues=result.issues,
                   unsupported=result.unsupported, validated=result.model_dump(mode='json'))
        # Partial mechanical assertions never stand in for semantic adjudication.
        checks = {}
        expected = case.get('expectedChecks')
        if expected:
            checks['activityCategories'] = [activity_category(x) for x in ai.activities] == expected['activities']
            checks['location'] = ai.location == expected['location']
            if 'clarify' in expected:
                checks['clarification'] = expected['clarify'] in row['questions']
            req = result.request
            for key, field in [('first', 'firstTravel'), ('between', 'betweenTravel'), ('geography', 'geography'), ('wheelchair', 'requireWheelchairAccess'), ('budget', 'budget'), ('date', 'date')]:
                if key in expected:
                    got = getattr(req, field) if req else None
                    want = expected[key]
                    checks[key] = (all(getattr(got, k, None) == v for k, v in want.items()) if isinstance(want, dict) else str(got) == str(want)) if got is not None else False
        if 'expectedExtraction' in case:
            target = Interpretation.model_validate(case['expectedExtraction'])
            checks['activities'] = ai.activities == target.activities
            checks['journeySemantics'] = semantic_journey(result.interpretation.journey) == semantic_journey(target.journey)
        row['automatedChecks'] = checks
        row['automatedFailures'] = [key for key, ok in checks.items() if not ok]
    except (ValueError, TypeError, KeyError) as error:
        row['failureType'] = type(error).__name__
    return row


def missing_properties(value, node, path='$', *, unknown=False):
    """Required-property audit layered on existing strict type/unknown validator."""
    if '$ref' in node:
        node = schema()['$defs'][node['$ref'].split('/')[-1]]
    if 'anyOf' in node:
        branches = node['anyOf']
        if value is None and any(b.get('type') == 'null' for b in branches):
            return []
        branches = [b for b in branches if b.get('type') != 'null']
        return min((missing_properties(value, b, path, unknown=unknown) for b in branches), key=len)
    missing = []
    if isinstance(value, dict) and node.get('type') == 'object':
        missing += ([path + '.' + key for key in value if key not in node.get('properties', {})] if unknown else
                    [path + '.' + key for key in node.get('required', []) if key not in value])
        for key, item in value.items():
            if key in node.get('properties', {}):
                missing += missing_properties(item, node['properties'][key], path + '.' + key, unknown=unknown)
    elif isinstance(value, list) and 'items' in node:
        for index, item in enumerate(value):
            missing += missing_properties(item, node['items'], path + '[' + str(index) + ']', unknown=unknown)
    return missing


def semantic_journey(journey):
    if journey is None:
        return None
    data = journey.model_dump(mode='json')
    def strip(node):
        if isinstance(node, dict):
            return {k: strip(v) for k, v in node.items() if k not in ('source', 'minute')}
        if isinstance(node, list):
            return [strip(v) for v in node]
        return node
    return strip(data)


def _run_one(ledger, adapter, case, repetition, input_upper_bound):
    """Internal orchestration; readiness/token verification precedes this call.

    Unknown tokenization must refuse dispatch. Bound includes schema, examples,
    request framing and provider overhead, not merely user text length.
    """
    if type(input_upper_bound) is not int or not 0 < input_upper_bound <= INPUT_CAP:
        raise AdmissionError('Verified complete input token bound unavailable or over cap')
    if case not in corpus()['cases']:
        raise AdmissionError('Only unchanged authoritative corpus entries are admitted')
    payload = adapter.payload(case['text'])
    if not ledger.reserve(adapter.provider, case['id'], repetition):
        return None
    started = time.perf_counter()
    usage = None
    response = None
    latency = None
    try:
        response = adapter.transport(payload)
        latency = (time.perf_counter() - started) * 1000
        content, usage, status = adapter.decode(response)
        record = {'latencyMs': latency, 'status': status, 'response': response,
                  'usage': usage, 'outputCharacters': len(content) if isinstance(content, str) else 0,
                  'scoring': score(case, content) if status == 'complete' and isinstance(content, str) else None}
    except Exception as error:
        record = {'latencyMs': latency if latency is not None else (time.perf_counter() - started) * 1000,
                  'status': 'uncertain_failure', 'errorType': type(error).__name__}
        if response is not None:
            record['response'] = response
    record.update(provider=adapter.provider, model=CANDIDATES[adapter.provider]['model'],
                  caseId=case['id'], repetition=repetition,
                  inputUpperBound=input_upper_bound, payloadHash=digest(payload),
                  recordedAt=datetime.now().astimezone().isoformat())
    scoring = record.get('scoring') or {}
    if scoring.get('validatedAccepted') and scoring.get('automatedFailures'):
        record['reviewHalt'] = True
    ledger.finish(adapter.provider, case['id'], repetition, record, usage)
    return record


def run_one(ledger, adapter, case, repetition, input_upper_bound):
    # Own the sole in-flight operation through response reading/scoring/journaling.
    with exclusive(ledger.directory):
        return _run_one(ledger, adapter, case, repetition, input_upper_bound)


def run_matrix(ledger, adapters, token_bound):
    """Resume the fixed matrix. Internal injected-transport API, no live CLI.

    Stage B must supply a reviewed complete-payload bound; no count-token API
    calls or extra warmups occur here. Failed/uncertain slots remain consumed.
    """
    if len({a.provider for a in adapters}) != len(adapters):
        raise AdmissionError('Duplicate provider adapters')
    for adapter in adapters:
        for repetition in (1, 2, 3):
            for case in corpus()['cases']:
                payload = adapter.payload(case['text'])
                record = run_one(ledger, adapter, case, repetition, token_bound(adapter.provider, payload))
                scoring = (record or {}).get('scoring') or {}
                if scoring.get('validatedAccepted') and scoring.get('automatedFailures'):
                    return {'stopped': 'accepted semantic mismatch requires review',
                            'provider': adapter.provider, 'case': case['id'], 'repetition': repetition}
    return {'stopped': 'matrix consumed; offline semantic review required'}


SEMANTIC_FIELDS = (
    'required_stops', 'optional_stops', 'venue_identity', 'ordering',
    'return_to_origin', 'final_destination', 'total_duration', 'travel_only_limits',
    'strict_flexible', 'visit_duration', 'duration_relation', 'relative_date_time',
    'clarification', 'unsupported', 'contradiction', 'unicode', 'grounding', 'injection',
)
OUTCOMES = ('correct_extraction', 'correct_clarification', 'safe_failure', 'incorrect_extraction', 'refusal')


def review_template(records):
    return {'configurationHash': digest(metadata()), 'reviews': [
        {'caseId': r['caseId'], 'repetition': r['repetition'], 'responseHash': digest(r),
         'outcome': None, 'criticalAcceptedFailures': [],
         'fields': {field: {'applicable': None, 'correct': None} for field in SEMANTIC_FIELDS}}
        for r in records]}


def adjudicate(records, review):
    """Aggregate explicit offline human judgments; never use an AI as gold.

    The operator reviews original corpus expectations, raw output AND trusted
    validation. Templates are not judgments. Every field needs an applicability
    decision; stale/duplicate/incomplete reviews fail instead of inflating scores.
    """
    if review.get('configurationHash') != digest(metadata()):
        raise ValueError('Stale review configuration')
    indexed = {(r['caseId'], r['repetition']): r for r in records}
    seen = set()
    metrics = {field: {'correct': 0, 'applicable': 0} for field in SEMANTIC_FIELDS}
    outcomes = Counter()
    critical = []
    correct = set()
    for judgment in review['reviews']:
        slot = (judgment['caseId'], judgment['repetition'])
        if slot in seen or slot not in indexed:
            raise ValueError('Unknown or duplicate review slot')
        seen.add(slot)
        record = indexed[slot]
        if judgment['responseHash'] != digest(record):
            raise ValueError('Stale response review')
        outcome = judgment['outcome']
        if outcome not in OUTCOMES or set(judgment['fields']) != set(SEMANTIC_FIELDS):
            raise ValueError('Incomplete review outcome/fields')
        scoring = record.get('scoring') or {}
        if outcome in ('correct_extraction', 'correct_clarification') and not scoring.get('structuredValid'):
            raise ValueError('Invalid structured output cannot count as correct interpretation')
        if outcome == 'correct_extraction' and not scoring.get('validatedAccepted'):
            raise ValueError('Rejected output cannot count as accepted extraction')
        if judgment['fields']['grounding'].get('applicable') is not True:
            raise ValueError('Source grounding must be reviewed for every output')
        all_correct = True
        for field, decision in judgment['fields'].items():
            applicable, passed = decision['applicable'], decision['correct']
            if type(applicable) is not bool or (type(passed) is not bool if applicable else passed is not None):
                raise ValueError('Every field needs reviewed applicability and correctness')
            if applicable:
                metrics[field]['applicable'] += 1
                metrics[field]['correct'] += passed
                all_correct = all_correct and passed
        failures = judgment['criticalAcceptedFailures']
        if not isinstance(failures, list) or any(f not in SEMANTIC_FIELDS for f in failures) or len(failures) != len(set(failures)):
            raise ValueError('Invalid critical failure classifications')
        if failures and outcome in ('correct_extraction', 'correct_clarification'):
            raise ValueError('Critical failure cannot be fully correct')
        critical += [{'caseId': slot[0], 'repetition': slot[1], 'constraint': failure} for failure in failures]
        outcomes[outcome] += 1
        if outcome in ('correct_extraction', 'correct_clarification') and all_correct and not failures:
            correct.add(slot)
    all_repeats = sum(all((case['id'], repeat) in correct for repeat in (1, 2, 3)) for case in corpus()['cases'])
    return {'reviewedAttempts': len(seen), 'recordedAttempts': len(records),
            'plannedAttemptDenominator': PROVIDER_CAP, 'plannedCaseDenominator': 66,
            'fullyCorrectReviewedAttempts': len(correct), 'casesCorrectAllThreeRepetitions': all_repeats,
            'fieldMetrics': metrics, 'outcomes': dict(outcomes), 'criticalFailures': critical,
            'expandedCorpus98PercentGate': 'not established by this 66-case screen',
            'qualification': 'not production qualified; owner review and expanded validation required'}


def summarize(records):
    latencies = sorted(r['latencyMs'] for r in records)
    def percentile(p):
        return latencies[math.ceil(p * len(latencies)) - 1] if latencies else None
    measured_usage = [r['usage'] for r in records if r.get('usage') and len(r['usage']) == 2 and all(type(n) is int and n >= 0 for n in r['usage'])]
    return {'reportedUsageRecords': len(measured_usage),
            'inputTokensWithReportedUsage': sum(u[0] for u in measured_usage),
            'outputTokensWithReportedUsage': sum(u[1] for u in measured_usage),
            'validatedAccepted': sum(bool((r.get('scoring') or {}).get('validatedAccepted')) for r in records),
            'criticalFailures': None, 'safeClarifications': None,
            'attemptRecords': len(records), 'p50Ms': percentile(.5), 'p90Ms': percentile(.9),
            'p95Ms': percentile(.95), 'maxMs': max(latencies) if latencies else None,
            'structuredValid': sum(bool((r.get('scoring') or {}).get('structuredValid')) for r in records),
            'statusCounts': dict(Counter(r['status'] for r in records)),
            'fullyCorrect': None, 'qualification': 'not qualified; semantic review required'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['inspect', 'report', 'export', 'review', 'live'])
    args = parser.parse_args()
    config = metadata()
    if args.command == 'live':
        # Credentials alone cannot clear processing/account/payment/token gates.
        raise SystemExit('Live blocked. See docs/task52-cloud-model-benchmark.md for provider-specific prerequisites. No requests sent.')
    if args.command in ('report', 'export', 'review'):
        path = STATE / 'journal.sqlite'
        if not path.exists():
            raise SystemExit('No paid journal exists; all provider metrics unavailable, calls 0, spend $0.')
        with exclusive(STATE):
            ledger = Ledger(path, config)
            try:
                reports = {}
                for provider in CANDIDATES:
                    rows = ledger.db.execute('SELECT status,charge,record FROM attempts WHERE provider=?', (provider,)).fetchall()
                    records = [json.loads(row[2]) for row in rows if row[2]]
                    if args.command == 'export':
                        destination = STATE / (provider + '-responses.json')
                        destination.touch(mode=0o600, exist_ok=True)
                        destination.chmod(0o600)
                        destination.write_text(json.dumps({'metadata': config, 'provider': provider, 'records': records}, indent=2) + '\n')
                        template_path = STATE / (provider + '-review.json')
                        if not template_path.exists():
                            with template_path.open('x') as template_file:
                                template_path.chmod(0o600)
                                json.dump(review_template(records), template_file, indent=2)
                    review_path = STATE / (provider + '-review.json')
                    reviewed = None
                    if review_path.exists() and args.command == 'review':
                        reviewed = adjudicate(records, json.loads(review_path.read_text()))
                    reports[provider] = {**summarize(records), 'semanticReview': reviewed, 'attemptsIncludingUncertain': len(rows),
                                         'unresolvedReservations': sum(row[0] == 'reserved_uncertain' for row in rows),
                                         'accountedNanodollars': sum(row[1] for row in rows)}
                print(json.dumps(reports, indent=2))
            finally:
                ledger.close()
        return
    print(json.dumps({'metadata': config, 'caseCounts': dict(Counter(c['source'] for c in corpus()['cases'])),
                      'schemaBytes': len(json.dumps(schema()).encode()),
                      'maxMessageBytes': max(len(json.dumps(messages(c['text'])).encode()) for c in corpus()['cases']),
                      'paidRequestsByThisCommand': 0}, indent=2))


if __name__ == '__main__':
    main()
