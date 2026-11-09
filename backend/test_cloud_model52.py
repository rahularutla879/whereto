"""Task52 evaluation-only fake provider checks; no inference/network/owner state."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import json

from backend.ai import AISettings, create_provider, Interpretation
from scripts import cloud_model52 as e


def output(case):
    value = Interpretation.model_validate(case['expectedExtraction']).model_dump(mode='json')
    for key in ('start_time', 'end_time'):
        value.pop(key)
    value['journey'].pop('order_conflict')
    if value['journey']['deadline']:
        value['journey']['deadline'].pop('minute')
    return json.dumps(value)


def response(provider, content):
    if provider == 'openai':
        return {'status':'completed', 'output':[{'content':[{'type':'output_text','text':content}]}], 'usage':{'input_tokens':100,'output_tokens':20}}
    if provider == 'anthropic':
        return {'content': [{'type': 'text', 'text': content}], 'stop_reason': 'end_turn', 'usage': {'input_tokens': 100, 'output_tokens': 20}}
    return {'candidates': [{'content': {'parts': [{'text': content}]}, 'finishReason': 'STOP'}], 'usageMetadata': {'promptTokenCount': 100, 'totalTokenCount': 120, 'candidatesTokenCount': 15, 'thoughtsTokenCount': 5}}


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'journal.sqlite'
        self.ledger = e.Ledger(self.path, e.metadata())
        self.case = e.corpus()['cases'][0]
        self.content = output(self.case)
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(self.ledger.close)

    def test_exact_corpus_and_hashes(self):
        cases = e.corpus()['cases']
        self.assertEqual(len(cases), 66)
        self.assertEqual(sum('expectedExtraction' in c for c in cases), 25)
        self.assertEqual(sum('expectedChecks' in c for c in cases), 26)
        self.assertEqual(sum('expectedSemanticReview' in c for c in cases), 15)
        for case in cases[:25]:
            Interpretation.model_validate(case['expectedExtraction'])

    def test_runtime_defaults_unchanged(self):
        self.assertEqual(AISettings().model, 'qwen3:4b')
        self.assertEqual(type(create_provider(AISettings())).__name__, 'OllamaProvider')
        with self.assertRaises(Exception):
            create_provider(AISettings(provider='openai'))

    def test_all_adapters_same_semantics_schema_and_usage(self):
        for provider in e.CANDIDATES:
            with self.subTest(provider=provider):
                replies = []
                adapter = e.Adapter(provider, lambda body: replies.append(body) or response(provider, self.content))
                result = e.run_one(self.ledger, adapter, self.case, 1, 1000)
                self.assertEqual(result['status'], 'complete')
                self.assertEqual(result['usage'], (100, 20))
                self.assertTrue(result['scoring']['structuredValid'])
                self.assertIsNone(result['scoring']['fullyCorrect'])
                self.assertEqual(len(replies), 1)
                payload = replies[0]
                if provider == 'openai':
                    self.assertEqual(payload['input'], e.messages(self.case['text']))
                    self.assertEqual(payload['text']['format']['schema'], e.wire_schema(provider))
                elif provider == 'anthropic':
                    self.assertEqual(payload['system'], e.SYSTEM_PROMPT)
                    self.assertEqual(payload['messages'], e.messages(self.case['text'])[1:])
                    self.assertEqual(payload['output_config']['format']['schema'], e.wire_schema(provider))
                else:
                    self.assertEqual(payload['systemInstruction']['parts'][0]['text'], e.SYSTEM_PROMPT)
                    self.assertEqual([m['parts'][0]['text'] for m in payload['contents']], [m['content'] for m in e.messages(self.case['text'])[1:]])
                    self.assertEqual(payload['generationConfig']['responseFormat']['text']['schema'], e.wire_schema(provider))

    def test_provider_schema_projection_preserves_constraints_in_descriptions(self):
        anthropic = e.wire_schema('anthropic')
        self.assertNotIn('maxItems', anthropic['properties']['activities'])
        self.assertIn('maxItems', anthropic['properties']['activities']['description'])
        google = e.wire_schema('google')
        self.assertIn('$defs', google)
        self.assertEqual(google['type'], 'object')
        self.assertIn({'type':'null'}, google['properties']['budget_per_person']['anyOf'])
        self.assertFalse(google['additionalProperties'])
        self.assertEqual(google['required'], e.schema()['required'])

    def test_three_explicit_examples_replay_historical_qwen_only(self):
        examples = {
            'Go to SUNY College of Optometry first, then get coffee, and return within 3 hours tomorrow.': (2, 180),
            "Tomorrow in Jersey City, buy groceries and stop at a pharmacy, and maybe grab coffee if there's time. Return to where I started within 90 minutes.": (3, 90),
            'Generate a grocery → pharmacy → return-to-start outing.': (2, None),
        }
        found = set()
        for name in ('repair_extractions', 'return_phrase_extractions', 'unicode_extractions'):
            for row in json.loads((e.ROOT / 'backend' / (name + '.json')).read_text()):
                if row['text'] not in examples:
                    continue
                with self.subTest(text=row['text']):
                    found.add(row['text'])
                    _, result = e.validate({'text': row['text']}, json.dumps(row['raw']))
                    journey = result.interpretation.journey
                    count, duration = examples[row['text']]
                    self.assertEqual(len(journey.stops), count)
                    self.assertEqual(journey.endpoint.kind, 'origin')
                    self.assertEqual(journey.total_duration.minutes if journey.total_duration else None, duration)
                    if duration:
                        self.assertEqual(journey.total_duration.relation, 'maximum')
                    if count == 3:
                        self.assertEqual([s.requirement for s in journey.stops], ['required', 'required', 'optional'])
                    else:
                        self.assertEqual([(x.before, x.after) for x in journey.order], [(0,1)])
                    if 'SUNY' in row['text']:
                        self.assertEqual(journey.stops[0].source, 'SUNY College of Optometry')
                        self.assertIn('endpoint', [q.field for q in result.questions])
                    self.assertIsNone(result.request)  # no ordinary partial itinerary
        self.assertEqual(found, set(examples))

    def test_grounded_advanced_handoff_is_not_a_rejected_extraction(self):
        case = next(c for c in e.corpus()['cases'] if c['text'] == 'Go to SUNY College of Optometry.')
        row = e.score(case, output(case))
        self.assertTrue(row['structuredValid'])
        self.assertTrue(row['groundedAdvancedHandoff'])
        self.assertTrue(row['validatedAccepted'])
        self.assertIsNone(row['fullyCorrect'])
        self.assertIsNone(row['validated']['request'])
        self.assertIsNone(row['validated']['advancedToken'])

    def test_missing_unknown_duplicate_and_invalid_json(self):
        for content in ['{}', 'not json', self.content[:-1] + ',"surprise":1}', self.content[:-1] + ',"activities":[]}']:
            self.assertFalse(e.score(self.case, content)['structuredValid'])
        value = json.loads(self.content)
        del value['budget_group']  # shared parser default is insufficient for wire schema
        scored = e.score(self.case, json.dumps(value))
        self.assertFalse(scored['structuredValid'])
        self.assertIn('$.budget_group', scored['missingRequiredProperties'])
        self.assertFalse(scored['validatedAccepted'])
        value = json.loads(self.content)
        value['start_time'] = None
        scored = e.score(self.case, json.dumps(value))
        self.assertFalse(scored['structuredValid'])
        self.assertIn('$.start_time', scored['unknownProperties'])

    def test_hallucination_never_semantic_success(self):
        value = json.loads(self.content)
        value['activities'] = ['bowling']
        value['journey']['stops'] = [value['journey']['stops'][0]]
        value['journey']['stops'][0]['source'] = 'bowling'
        row = e.score(self.case, json.dumps(value))
        self.assertFalse(row['validatedAccepted'])
        self.assertIn('activities', row['automatedFailures'])
        self.assertIsNone(row['fullyCorrect'])

    def test_recovery_skips_reserved_and_completed(self):
        self.assertTrue(self.ledger.reserve('google', self.case['id'], 1))
        reopened = e.Ledger(self.path, e.metadata())
        self.addCleanup(reopened.close)
        sends = []
        adapter = e.Adapter('google', lambda body: sends.append(body) or response('google', self.content))
        self.assertIsNone(e.run_one(reopened, adapter, self.case, 1, 1000))
        e.run_one(reopened, adapter, self.case, 2, 1000)
        self.assertIsNone(e.run_one(reopened, adapter, self.case, 2, 1000))
        self.assertEqual(len(sends), 1)
        self.assertEqual(reopened.db.execute('SELECT charge FROM attempts WHERE repetition=1').fetchone()[0], 16500000)

    def test_timeout_and_exception_no_retry_no_secret(self):
        for error in (TimeoutError('credential-secret'), ConnectionError('credential-secret')):
            def fail(_):
                raise error
            result = e.run_one(self.ledger, e.Adapter('anthropic', fail), self.case, 1 if isinstance(error, TimeoutError) else 2, 1000)
            self.assertEqual(result['status'], 'uncertain_failure')
            self.assertEqual(result['accountedNanodollars'], 2200000)
            self.assertNotIn('credential-secret', json.dumps(result))

    def test_malformed_refused_truncated_and_error_keep_reservation_without_usage(self):
        for index, raw in enumerate([{}, {'error': {'type': 'rate_limit_error'}}, {'content': [], 'stop_reason': 'refusal'}], 1):
            row = e.run_one(self.ledger, e.Adapter('anthropic', lambda body: raw), self.case, index, 1000)
            self.assertNotEqual(row['status'], 'complete')
            self.assertEqual(row['accountedNanodollars'], 2200000)
        raw = response('openai', self.content)
        raw['status'] = 'incomplete'
        row = e.run_one(self.ledger, e.Adapter('openai', lambda body: raw), self.case, 1, 1000)
        self.assertEqual(row['status'], 'incomplete')
        self.assertIsNone(row['scoring'])

    def test_spend_reservation_before_dispatch(self):
        self.ledger.db.execute('INSERT INTO attempts VALUES (?,?,?,?,?,NULL)', ('google', 'prior', 1, 'reserved_uncertain', e.SPEND_CAP - 1))
        self.ledger.db.commit()
        sends = []
        with self.assertRaises(e.AdmissionError):
            e.run_one(self.ledger, e.Adapter('google', lambda body: sends.append(body)), self.case, 1, 1000)
        self.assertEqual(sends, [])

    def test_provider_and_global_attempt_caps(self):
        for provider in e.CANDIDATES:
            for case in e.corpus()['cases']:
                for repeat in (1, 2, 3):
                    self.assertTrue(self.ledger.reserve(provider, case['id'], repeat))
        self.assertEqual(self.ledger.db.execute('SELECT count(*) FROM attempts').fetchone()[0], 594)
        self.assertEqual(self.ledger.db.execute('SELECT sum(charge) FROM attempts').fetchone()[0], 4197600000)
        with patch.object(e, 'PROVIDER_CAP', 0), self.assertRaises(e.AdmissionError):
            # Exercise independent provider ceiling using a fresh ledger.
            other = e.Ledger(Path(self.tmp.name) / 'other.sqlite', {})
            try:
                other.reserve('google', self.case['id'], 1)
            finally:
                other.close()
        with patch.object(e, 'TOTAL_CAP', 0), self.assertRaises(e.AdmissionError):
            other = e.Ledger(Path(self.tmp.name) / 'third.sqlite', {})
            try:
                other.reserve('google', self.case['id'], 1)
            finally:
                other.close()

    def test_unapproved_slots_config_prompts_and_token_bounds(self):
        for provider, case, repeat in [('other',self.case['id'],1), ('google','private',1), ('google',self.case['id'],4)]:
            with self.assertRaises(e.AdmissionError):
                self.ledger.reserve(provider, case, repeat)
        config = e.metadata()
        config['promptVersion'] = 'changed'
        with self.assertRaises(e.AdmissionError):
            e.Ledger(self.path, config)
        adapter = e.Adapter('google', lambda body: self.fail('No send'))
        for bound in (None, 0, 12001, -1, True):
            with self.assertRaises(e.AdmissionError):
                e.run_one(self.ledger, adapter, self.case, 1, bound)
        altered = {**self.case, 'text': 'private prompt'}
        with self.assertRaises(e.AdmissionError):
            e.run_one(self.ledger, adapter, altered, 1, 1000)

    def test_entire_fake_matrix_resumes_without_additional_sends(self):
        sends = []
        adapters = [e.Adapter(provider, lambda body, provider=provider: sends.append(provider) or {'error': {'type': 'synthetic_refusal'}}) for provider in e.CANDIDATES]
        result = e.run_matrix(self.ledger, adapters, lambda provider, payload: 1000)
        self.assertIn('matrix consumed', result['stopped'])
        self.assertEqual(len(sends), 594)
        for provider in e.CANDIDATES:
            self.assertEqual(sends.count(provider), 198)
        e.run_matrix(self.ledger, adapters, lambda provider, payload: 1000)
        self.assertEqual(len(sends), 594)
        self.assertEqual(self.ledger.db.execute('SELECT sum(charge) FROM attempts').fetchone()[0], 4197600000)

    def test_interrupt_retains_reservation_and_prevents_second_send(self):
        sends = []
        def interrupted(body):
            sends.append(body)
            raise KeyboardInterrupt()
        adapter = e.Adapter('google', interrupted)
        with self.assertRaises(KeyboardInterrupt):
            e.run_one(self.ledger, adapter, self.case, 1, 1000)
        self.assertIsNone(e.run_one(self.ledger, adapter, self.case, 1, 1000))
        self.assertEqual(len(sends), 1)
        self.assertEqual(self.ledger.db.execute('SELECT status,charge FROM attempts').fetchone(), ('reserved_uncertain',16500000))

    def test_usage_cap_violation_halts_after_restart(self):
        raw = response('openai', self.content)
        raw['usage']['input_tokens'] = 12001
        with self.assertRaises(e.AdmissionError):
            e.run_one(self.ledger, e.Adapter('openai', lambda body: raw), self.case, 1, 1000)
        restarted = e.Ledger(self.path, e.metadata())
        self.addCleanup(restarted.close)
        with self.assertRaises(e.AdmissionError):
            restarted.reserve('google', self.case['id'], 1)

    def test_accepted_automated_mismatch_persists_review_halt(self):
        adapter = e.Adapter('google', lambda body: response('google', self.content))
        with patch.object(e, 'score', return_value={'validatedAccepted': True, 'automatedFailures': ['simulated_required_stop_mismatch']}):
            record = e.run_one(self.ledger, adapter, self.case, 1, 1000)
        self.assertTrue(record['reviewHalt'])
        reopened = e.Ledger(self.path, e.metadata())
        self.addCleanup(reopened.close)
        with self.assertRaises(e.AdmissionError):
            e.run_one(reopened, adapter, self.case, 2, 1000)

    def test_lock_rejects_second_runner(self):
        directory = Path(self.tmp.name) / 'locked'
        with e.exclusive(directory):
            with self.assertRaises(BlockingIOError):
                with e.exclusive(directory):
                    self.fail('Second runner acquired lock')

    def test_semantic_review_denominators_stale_and_invalid_rejection(self):
        record = e.run_one(self.ledger, e.Adapter('google', lambda body: response('google', self.content)), self.case, 1, 1000)
        template = e.review_template([record])
        judgment = template['reviews'][0]
        with self.assertRaises(ValueError):
            e.adjudicate([record], template)  # an untouched template is not a pass
        judgment['outcome'] = 'correct_extraction'
        for field in e.SEMANTIC_FIELDS:
            judgment['fields'][field] = {'applicable': field in ('required_stops','ordering','grounding'), 'correct': True if field in ('required_stops','ordering','grounding') else None}
        result = e.adjudicate([record], template)
        self.assertEqual(result['fullyCorrectReviewedAttempts'], 1)
        self.assertEqual(result['fieldMetrics']['required_stops'], {'correct':1,'applicable':1})
        self.assertEqual(result['fieldMetrics']['venue_identity']['applicable'], 0)
        self.assertEqual(result['plannedAttemptDenominator'], 198)
        self.assertEqual(result['casesCorrectAllThreeRepetitions'], 0)
        judgment['responseHash'] = 'stale'
        with self.assertRaises(ValueError):
            e.adjudicate([record], template)
        record['scoring']['structuredValid'] = False
        judgment['responseHash'] = e.digest(record)
        with self.assertRaises(ValueError):
            e.adjudicate([record], template)

    def test_scoring_error_preserves_complete_response_latency_and_body(self):
        raw = response('google', self.content)
        adapter = e.Adapter('google', lambda body: raw)
        with patch.object(e.time, 'perf_counter', side_effect=[1.0, 2.0, 100.0]), patch.object(e, 'score', side_effect=RuntimeError('offline scoring failed')):
            record = e.run_one(self.ledger, adapter, self.case, 1, 1000)
        self.assertEqual(record['latencyMs'], 1000)
        self.assertEqual(record['response'], raw)
        self.assertEqual(record['status'], 'uncertain_failure')

    def test_failure_latency_is_reported_separately_from_inference(self):
        result = e.summarize([{'latencyMs': x, 'status': 'uncertain_failure'} for x in range(1, 21)])
        self.assertEqual([result[k] for k in ('p50OperationMs','p90OperationMs','p95OperationMs','maxOperationLatencyMs')], [10,18,19,20])
        self.assertEqual([result[k] for k in ('p50Ms','p90Ms','p95Ms','maxMs')], [None]*4)
        self.assertIsNone(e.summarize([])['p50Ms'])



# Offline fake fixtures only; the unmodified paid source gate rejects B2.
def load_tests(loader, tests, pattern):
    from scripts.task52_b2_test_fixture import OfflineUnitSuite
    return OfflineUnitSuite(tests)


if __name__ == '__main__':
    unittest.main()
