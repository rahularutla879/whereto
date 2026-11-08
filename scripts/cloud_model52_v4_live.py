"""Fixed, owner-approved v4 continuation; one inference per explicit invocation.

No CLI loop, retries, runtime integration, replacement journal or refunds. The
seven original rows and root stay immutable. A missing/uncertain result or review
blocks continuation, including after a crash. Agent review is not human signoff.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import time

from scripts import cloud_model52 as e
from scripts import cloud_model52_audit as audit
from scripts import cloud_model52_live as transport
from scripts import cloud_model52_offline as scorer
from scripts import cloud_model52_v4 as v
from backend.ai import parse_interpretation
from backend.interpretation import activity_category
from backend.journey import validate_journey

CONFIG = '6c14d470f27ac95152d1c12eec6b48adbeba869901bd49b5548e4447499056e3'
RUN = e.STATE / 'v4-approved-five-c549287'
RESERVATION = 2500000
EXTRA_CAP = 12500000


def now():
    return datetime.now(timezone.utc)


def code_hashes():
    return {name: hashlib.sha256((e.ROOT / 'scripts' / name).read_bytes()).hexdigest()
            for name in ('cloud_model52.py', 'cloud_model52_offline.py',
                         'cloud_model52_v4.py', 'cloud_model52_v4_live.py',
                         'cloud_model52_live.py', 'cloud_model52_audit.py',
                         'cloud_model52_semantics.py', 'cloud_model52_proposal.py')}


def fresh(stamp):
    try:
        age = (now() - datetime.fromisoformat(stamp)).total_seconds()
        if not 0 <= age <= 86400:
            raise ValueError()
    except (ValueError, TypeError):
        raise e.AdmissionError('Readiness expired or timestamp invalid') from None


def check_readiness(value):
    fresh(value['preparedAtUTC'])
    if value['reviewDateUTC'] != now().date().isoformat():
        raise e.AdmissionError('Daily model/pricing/processing/account review expired')
    if value['configurationHash'] != CONFIG or e.digest(v.configuration()) != CONFIG:
        raise e.AdmissionError('Approved v4 configuration mismatch')
    account = value['accountReview']
    if (type(account['creditsUSD']) not in (int, float) or account['creditsUSD'] < .0125
            or account['autoReload'] is not False
            or any(account.get(k) is not True for k in ('sharingDisabled',
                'globalSyntheticOnly', 'responsesWriteVerified', 'modelAvailable',
                'pricingUnchanged', 'processingUnchanged', 'freeCountingVerified'))
            or type(account['rpm']) is not int or account['rpm'] < 5
            or type(account['tpm']) is not int or account['tpm'] < 45945):
        raise e.AdmissionError('Account/model/terms/limits readiness incomplete')
    cases = e.corpus()['cases']
    if set(value['counts']) != {c['id'] for c in cases}:
        raise e.AdmissionError('All 66 complete-input counts required')
    for case in cases:
        row = value['counts'][case['id']]
        fresh(row['observedAtUTC'])
        count = row['inputTokens']
        if (type(count) is not int or not 0 < count <= e.INPUT_CAP - 2048
                or row['httpStatus'] != 200 or row['configurationHash'] != CONFIG
                or row['payloadHash'] != e.digest(v.payload(case['id'], 'openai'))
                or row['countBodyHash'] != e.digest(v.count_body(case['id'], 'openai')[1])):
            raise e.AdmissionError('Complete-input count/payload/cap mismatch')
    if (e.INPUT_CAP, e.OUTPUT_CAP, e.CANDIDATES['openai']['rates']) != (12000, 2000, [125, 500]):
        raise e.AdmissionError('Original caps/conservative pricing changed')


class ExistingLedger(e.Ledger):
    """Open existing database only; no DDL, touch, chmod or root replacement."""
    def __init__(self, path):
        self.directory = Path(path).parent
        self.db = sqlite3.connect(f'file:{path}?mode=rw', uri=True)
        self.db.execute('PRAGMA synchronous=FULL')


def rows_and_root(db):
    if db.execute('pragma integrity_check').fetchone() != ('ok',):
        raise e.AdmissionError('Paid journal integrity failure')
    return (db.execute('select * from attempts order by rowid').fetchall(),
            db.execute('select config from metadata').fetchone()[0])


def approval(readiness, directory=None):
    """Append the exact owner approval once, while original journal is intact."""
    directory = Path(directory or RUN)
    with e.exclusive(e.STATE):
        check_readiness(readiness)
        baseline = v.journal_snapshot()  # Pins entire original seven-row file.
        reviewed = json.loads((e.ROOT / 'docs/task52-v4-openai-test-plan.json').read_text())
        if reviewed['journal'] != baseline or reviewed['configurationHash'] != CONFIG:
            raise e.AdmissionError('Reviewed original plan/baseline mismatch')
        if reviewed['slots'] != [['openai', case, 1] for case in v.SLOTS]:
            raise e.AdmissionError('Owner-approved sequence mismatch')
        db = sqlite3.connect(f'file:{e.STATE}/journal.sqlite?mode=ro', uri=True)
        try:
            rows, root = rows_and_root(db)
            # The historical decoder correction must still verify, without
            # turning the historical journey-07 rejection into a success.
            for row in rows:
                if row[0] == 'openai':
                    audit.effective_record(row, e.STATE / 'corrections')
            if len(rows) + 5 > e.TOTAL_CAP or baseline['counts']['openai'] + 5 > e.PROVIDER_CAP or sum(r[4] for r in rows) + EXTRA_CAP > e.SPEND_CAP:
                raise e.AdmissionError('Five full reservations cannot fit original limits')
            historical = {str(p.relative_to(e.STATE)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in e.STATE.rglob('*.json') if directory not in p.parents}
            value = {'kind': 'owner-approved-v4-five-slots-v1', 'configurationHash': CONFIG,
                'promptVersion': v.VERSION, 'scorer': scorer.VERSION,
                'slots': reviewed['slots'], 'coverage': reviewed['coverage'],
                'baseline': baseline, 'baselineRoot': root, 'historicalEvidenceHashes': historical,
                'reviewedPlanHash': e.digest(reviewed), 'codeHashes': code_hashes(),
                'maxNewAttempts': 5, 'maxAdditionalReservationNanodollars': EXTRA_CAP,
                'reservationPerAttemptNanodollars': RESERVATION, 'concurrency': 1, 'retries': 0,
                'approval': 'Owner explicitly approved exactly these five original slots in order, v4 configuration '+CONFIG+', at most five attempts and $0.0125 full reservations; stop on any provider, source, semantic or unresolved-review failure. No other inference authorized.',
                'historicalHaltAcknowledgment': 'V3 stopped screen and journey-07 source rejection remain failures; journey-01 decoder correction retained, no retry/refund/record rewrite.',
                'readiness': readiness}
            audit.append_json(directory / 'approval.json', value)
            audit.append_json(directory / 'approval.seal.json', {'hash': e.digest(value)})
            return value
        finally:
            db.close()


def load_approval(directory):
    value = json.loads((directory / 'approval.json').read_text())
    if json.loads((directory / 'approval.seal.json').read_text()) != {'hash': e.digest(value)}:
        raise e.AdmissionError('Append-only approval seal mismatch')
    if (value['configurationHash'] != CONFIG or value['scorer'] != scorer.VERSION
            or value['slots'] != [['openai', case, 1] for case in v.SLOTS]
            or value['maxNewAttempts'] != 5 or value['maxAdditionalReservationNanodollars'] != EXTRA_CAP
            or value['reservationPerAttemptNanodollars'] != RESERVATION
            or value['concurrency'] != 1 or value['retries'] != 0
            or value['codeHashes'] != code_hashes()
            or value['reviewedPlanHash'] != e.digest(json.loads((e.ROOT / 'docs/task52-v4-openai-test-plan.json').read_text()))):
        raise e.AdmissionError('Owner scope/configuration/code changed')
    check_readiness(value['readiness'])
    for case in v.SLOTS:
        corpus_case = next(c for c in e.corpus()['cases'] if c['id'] == case)
        if (value['coverage'][case]['text'] != corpus_case['text']
                or value['coverage'][case]['payloadHash'] != e.digest(v.payload(case, 'openai'))):
            raise e.AdmissionError('Approved source/payload mismatch')
    for name, expected in value['historicalEvidenceHashes'].items():
        path = e.STATE / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise e.AdmissionError('Historical evidence changed/missing')
    return value


def verify_review(record, review):
    if (review.get('recordHash') != e.digest(record) or review.get('configurationHash') != CONFIG
            or review.get('approvalHash') != record['approvalHash']
            or review.get('reviewerKind') != 'agent' or review.get('independentHumanSignoff') is not False
            or review.get('outcome') not in ('correct_extraction', 'correct_clarification')
            or review.get('criticalFailures') != [] or not review.get('evidenceNotes')
            or set(review.get('fields', {})) != set(e.SEMANTIC_FIELDS)):
        raise e.AdmissionError('Complete explicit agent rubric required; no human signoff implied')
    accepted = record.get('scoring', {}).get('validatedAccepted')
    if review['outcome'] != ('correct_extraction' if accepted else 'correct_clarification'):
        raise e.AdmissionError('Clarification cannot be counted as accepted extraction')
    for judgment in review['fields'].values():
        if type(judgment.get('applicable')) is not bool or judgment.get('correct') is not (True if judgment['applicable'] else None):
            raise e.AdmissionError('Unresolved or failed semantic field')


def verify_record_evidence(record, directory):
    row_id = str(record['rowid'])
    operation = json.loads((directory / ('operation-' + row_id + '.json')).read_text())
    evidence = json.loads((directory / ('response-' + row_id + '.json')).read_text())
    if (json.loads((directory / ('record-' + row_id + '.json')).read_text()) != record
            or e.digest(operation) != record['operationHash']
            or e.digest(evidence) != record['responseEvidenceHash']
            or e.digest(evidence['response']) != record['responseHash']
            or evidence['response'] != record['response']
            or record['configurationHash'] != CONFIG or record['promptVersion'] != v.VERSION
            or record['evaluatorVersion'] != scorer.VERSION
            or record['payloadHash'] != e.digest(v.payload(record['caseId'], 'openai'))):
        raise e.AdmissionError('Immutable operation/response/record evidence mismatch')


def approved_extension_checks(case, content):
    """Additional owner-plan checks, not a replacement/version change to scorer.

    Prose-gold cases still need all-field agent review. These assertions prevent
    partial automated activity checks from being reported as full correctness.
    """
    if case['id'] not in ('extension-partial', 'extension-repeated'):
        return {}
    ai = parse_interpretation(content)
    j = ai.journey
    if j is None:
        return {'journeyPresent': False}
    partial = case['id'] == 'extension-partial'
    expected = ['pharmacy', 'bank', 'coffee'] if partial else ['coffee', 'museum', 'coffee']
    checks = {
        'requiredDistinctOccurrences': len(j.stops) == 3 and len(ai.activities) == 3
            and [activity_category(s.source) for s in j.stops] == [activity_category(s) for s in expected]
            and [activity_category(s) for s in ai.activities] == [activity_category(s) for s in expected]
            and all(s.requirement == 'required' and s.kind == 'activity' for s in j.stops),
        'occurrenceProvenance': scorer.occurrences(case['text'], j.stops) is not None,
        'partialOrderOnly': {(x.before, x.after) for x in j.order} == ({(0, 1)} if partial else {(1, 2)}),
        'destinationDate': ai.location == 'Jersey City' and ai.date in (None, '2026-11-06')
            and ai.date_expressions == ['tomorrow'],
        'noInventedScalarRequirements': all(getattr(ai, f) is None for f in
            ('people', 'budget_per_person', 'budget_group', 'currency', 'travel_total_minutes',
             'travel_leg_minutes', 'transport', 'cost', 'start_time', 'end_time'))
            and not ai.preferences and not ai.time_expressions and not ai.suggested_activities,
        'noInventedJourneyRequirements': not j.deadline and not j.shared_place
            and not j.clarification and not j.order_conflict and all(s.duration is None for s in j.stops),
        'endpoint': j.endpoint is None if partial else j.endpoint is not None and j.endpoint.kind == 'origin',
        'wholeTripBudget': j.total_duration is None if partial else j.total_duration is not None
            and j.total_duration.minutes == 180 and j.total_duration.relation == 'maximum',
    }
    return checks


def expected_endpoint_clarification(case, content, scoring):
    """Only the reviewed unresolved-home case; never a grounding rejection pass.

    Strict substantive/reference checks must pass first. The validator must ask
    its canonical home question and retain home as distinct from the origin.
    """
    if case['id'] != 'journey-12' or scoring.get('automatedFailures') or not scoring['structuredValid']:
        return False
    ai = parse_interpretation(content)
    explanation, needs_answer = validate_journey(case['text'], ai)
    return (needs_answer and explanation == "Where should the outing end? Please name home in your request or say ‘return to my starting point’ if that is what you mean."
            and scoring.get('questions') == ['endpoint'] and ai.journey is not None
            and ai.journey.endpoint is not None and ai.journey.endpoint.kind == 'home'
            and ai.journey.total_duration is not None
            and ai.journey.total_duration.minutes == 45 and ai.journey.total_duration.relation == 'maximum')


def verified_rows(db, plan, directory):
    rows, root = rows_and_root(db)
    old = plan['baseline']['rows']
    if root != plan['baselineRoot'] or len(rows) < 7:
        raise e.AdmissionError('Original journal root/rows changed')
    for row, expected in zip(rows[:7], old):
        if list(row[:3]) != expected['slot'] or e.digest(row) != expected['rowHash']:
            raise e.AdmissionError('Original paid record changed')
    added = rows[7:]
    if len(added) > 5 or len(added) * RESERVATION > EXTRA_CAP:
        raise e.AdmissionError('Additional attempt/reservation limit')
    for i, row in enumerate(added):
        if list(row[:3]) != plan['slots'][i] or row[3] != 'recorded' or row[5] is None:
            raise e.AdmissionError('Unexpected/uncertain/halted attempt; never retry')
        record = json.loads(row[5])
        if record.get('reviewHalt') or record.get('approvalHash') != e.digest(plan) or row[4] != RESERVATION:
            raise e.AdmissionError('Continuation halted/accounting mismatch')
        verify_record_evidence(record, directory)
        review_path = directory / ('review-' + e.digest(record) + '.json')
        if not review_path.exists():
            raise e.AdmissionError('Previous response needs complete semantic review')
        verify_review(record, json.loads(review_path.read_text()))
    if (directory / 'halt.json').exists():
        raise e.AdmissionError('Persistent reviewed halt; no further inference')
    return rows, added


def run_next(directory=None, http=None):
    """Exactly zero or one send. Call again only after explicit offline review."""
    directory = Path(directory or RUN)
    with e.exclusive(e.STATE):
        plan = load_approval(directory)
        ledger = ExistingLedger(e.STATE / 'journal.sqlite')
        try:
            _, added = verified_rows(ledger.db, plan, directory)
            if len(added) == 5:
                return None
            slot = plan['slots'][len(added)]
            _, case_id, repetition = slot
            case = next(c for c in e.corpus()['cases'] if c['id'] == case_id)
            body = v.payload(case_id, 'openai')
            # Full request equality is bound by coverage and all66 counts above.
            if body['max_output_tokens'] != 2000 or body['store'] is not False or body['reasoning'] != {'effort': 'none'} or body.get('tools'):
                raise e.AdmissionError('Exact output/state/reasoning/tools settings changed')
            http = http if http is not None else transport.HTTP('openai', transport.credentials()['openai'])
            if not ledger.reserve(*slot):
                raise e.AdmissionError('Consumed original slot; no retries')
            row_id = ledger.db.execute('select rowid from attempts where provider=? and case_id=? and repetition=?', slot).fetchone()[0]
            operation = {'slot': slot, 'rowid': row_id, 'approvalHash': e.digest(plan),
                'configurationHash': CONFIG, 'sourceHash': e.digest(case['text']),
                'payloadHash': e.digest(body), 'reservationNanodollars': RESERVATION}
            op_hash = e.digest(operation)
            audit.append_json(directory / ('operation-' + str(row_id) + '.json'), operation)
            started = time.perf_counter()
            response = None
            failure = None
            try:
                response = http(body)  # Full body consumed; transport retries=0.
            except Exception as error:
                failure = type(error).__name__  # No arbitrary exception text.
            latency = (time.perf_counter() - started) * 1000
            evidence = {'operationHash': op_hash, 'response': response, 'failureType': failure,
                        'latencyMs': latency, 'completedAtUTC': now().isoformat()}
            audit.append_json(directory / ('response-' + str(row_id) + '.json'), evidence)
            content, usage, status = (None, None, 'transport_error')
            scoring = None
            plan_checks = {}
            try:
                if response is not None:
                    content, usage, status = e.Adapter('openai', None).decode(response)
                if status == 'complete':
                    scoring = scorer.score(case, content)
                    plan_checks = approved_extension_checks(case, content)
            except (ValueError, TypeError, KeyError):
                status = 'decode_error'
            stop = None
            if status != 'complete': stop = status
            elif not scoring or not scoring['structuredValid']: stop = 'invalid_structure'
            elif scoring.get('automatedFailures'): stop = 'automated_semantic_failure'
            elif not all(plan_checks.values()): stop = 'approved_prose_semantics_failure_or_unresolved'
            elif not scoring['validatedAccepted'] and not expected_endpoint_clarification(case, content, scoring):
                stop = 'trusted_rejection_or_clarification_requires_review'
            usage_valid = usage is not None and len(usage) == 2 and all(type(n) is int and n >= 0 for n in usage)
            if not usage_valid:
                stop = stop or 'missing_usage'
            elif usage[0] > 12000 or usage[1] > 2000:
                stop = 'token_cap_violation'
            record = {**operation, 'operationHash': op_hash, 'responseHash': e.digest(response),
                'responseEvidenceHash': e.digest(evidence), 'response': response,
                'provider': 'openai', 'caseId': case_id, 'repetition': repetition,
                'model': 'gpt-6-luna', 'promptVersion': v.VERSION, 'promptHash': v.PROMPT_HASH,
                'schemaHash': v.configuration()['schemaHash'], 'corpusHash': e.CORPUS_SHA,
                'wireSchemaHash': v.configuration()['wireSchemaHashes']['openai'],
                'evaluatorVersion': scorer.VERSION, 'scorerCodeHash': plan['codeHashes']['cloud_model52_offline.py'],
                'status': status, 'latencyMs': latency, 'usage': list(usage) if usage else None, 'content': content,
                'outputHash': e.digest(content), 'scoring': scoring,
                'approvedPlanChecks': plan_checks,
                'usageEstimatedNanodollars': sum(n*r for n, r in zip(usage, [125, 500])) if usage_valid else None,
                'reviewHalt': stop is not None, 'stopReason': stop,
                'fullyCorrect': None, 'independentHumanSignoff': False}
            # Keep the FULL reservation even on successful usage reports. No
            # uncertain failure is refunded. Observed over-cap liability wins.
            ledger.finish(*slot, record, usage if stop == 'token_cap_violation' else None)
            audit.append_json(directory / ('record-' + str(row_id) + '.json'), record)
            return record
        finally:
            ledger.close()


def record_review(record, review, directory=None):
    directory = Path(directory or RUN)
    with e.exclusive(e.STATE):
        if record.get('reviewHalt'):
            raise e.AdmissionError('Historical/current halt cannot be cleared by review')
        verify_record_evidence(record, directory)
        verify_review(record, review)
        audit.append_json(directory / ('review-' + e.digest(record) + '.json'), review)


def halt_after_review(record, reason, directory=None):
    directory = Path(directory or RUN)
    with e.exclusive(e.STATE):
        audit.append_json(directory / 'halt.json', {'recordHash': e.digest(record),
            'approvalHash': record['approvalHash'], 'reason': reason,
            'reviewerKind': 'agent', 'independentHumanSignoff': False})
