"""Fake HTTP/temporary paid journals only; never reads owner credentials/state."""
import copy
from datetime import timedelta
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts import cloud_model52 as e
from scripts import cloud_model52_v4 as v
from scripts import cloud_model52_v4_live as live
from scripts import cloud_model52_audit as audit
from backend.test_cloud_model52_semantics import reference_wire


def readiness():
    stamp = live.now().isoformat()
    return {'preparedAtUTC': stamp, 'reviewDateUTC': live.now().date().isoformat(),
        'configurationHash': live.CONFIG, 'accountReview': {'creditsUSD': 4.93,
            'autoReload': False, 'sharingDisabled': True, 'globalSyntheticOnly': True,
            'responsesWriteVerified': True, 'modelAvailable': True, 'pricingUnchanged': True,
            'processingUnchanged': True, 'freeCountingVerified': True, 'rpm': 5000, 'tpm': 2000000},
        'counts': {c['id']: {'observedAtUTC': stamp, 'inputTokens': 5130, 'httpStatus': 200,
            'configurationHash': live.CONFIG, 'payloadHash': e.digest(v.payload(c['id'], 'openai')),
            'countBodyHash': e.digest(v.count_body(c['id'], 'openai')[1])} for c in e.corpus()['cases']}}


def review(record):
    return {'recordHash': e.digest(record), 'configurationHash': live.CONFIG,
        'approvalHash': record['approvalHash'], 'reviewerKind': 'agent',
        'independentHumanSignoff': False, 'outcome': 'correct_extraction',
        'criticalFailures': [], 'evidenceNotes': 'Fake full rubric; not model qualification',
        'fields': {f: {'applicable': True, 'correct': True} for f in e.SEMANTIC_FIELDS}}


class ContinuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Build real immutable payload/count fixtures once. Admission tests
        # compare their hashes repeatedly; schema construction has separate tests.
        cls.payloads = {c['id']: v.payload(c['id'], 'openai') for c in e.corpus()['cases']}
        cls.bodies = {c['id']: v.count_body(c['id'], 'openai') for c in e.corpus()['cases']}

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state = Path(self.temp.name)
        self.run = self.state / 'approved'
        # Entirely fictional baseline rows; production snapshot remains pinned.
        plan = json.loads((e.ROOT / 'docs/task52-v4-openai-test-plan.json').read_text())
        db = sqlite3.connect(self.state / 'journal.sqlite')
        db.executescript('create table metadata(id integer primary key, config text); create table attempts(provider text,case_id text,repetition integer,status text,charge integer,record text,primary key(provider,case_id,repetition));')
        db.execute('insert into metadata values(1,?)', ('original root',))
        self.old = []
        for i, original in enumerate(plan['journal']['rows']):
            row = (*original['slot'], 'recorded', [16500000,16500000,2200000,2500000,720250,715375,731000][i], json.dumps({'historical': i}))
            db.execute('insert into attempts values(?,?,?,?,?,?)', row)
            self.old.append(row)
        db.commit(); db.close()
        self.baseline = {**plan['journal'], 'rows': [{'slot': list(r[:3]), 'rowHash': e.digest(r)} for r in self.old]}
        self.patchers = [patch.object(e, 'STATE', self.state), patch.object(v, 'journal_snapshot', return_value=self.baseline),
            patch.object(audit, 'effective_record', return_value={}),
            patch.object(v, 'payload', side_effect=lambda case, provider: copy.deepcopy(self.payloads[case])),
            patch.object(v, 'count_body', side_effect=lambda case, provider: copy.deepcopy(self.bodies[case]))]
        for p in self.patchers: p.start()
        self.ready = readiness()
        # Approval compares the real reviewed baseline; fake tests replace only
        # that single document read, never production baseline checks.
        self.real_read = Path.read_text
        def read(path, *args, **kwargs):
            if path == e.ROOT / 'docs/task52-v4-openai-test-plan.json':
                return json.dumps({**plan, 'journal': self.baseline})
            return self.real_read(path, *args, **kwargs)
        self.reader = patch.object(Path, 'read_text', read); self.reader.start()
        self.plan = live.approval(self.ready, self.run)

    def tearDown(self):
        self.reader.stop()
        for p in reversed(self.patchers): p.stop()
        self.temp.cleanup()

    def dbrows(self):
        db = sqlite3.connect(self.state / 'journal.sqlite')
        try: return db.execute('select * from attempts order by rowid').fetchall()
        finally: db.close()

    def success(self, body):
        case = next(c for c in e.corpus()['cases'] if c['id'] == 'journey-04')
        return {'_http_status': 200, 'status': 'completed', 'error': None,
            'model': 'gpt-6-luna', 'usage': {'input_tokens': 5130, 'output_tokens': 400,
                'output_tokens_details': {'reasoning_tokens': 0}},
            'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(reference_wire(case))}]}]}

    def test_one_send_durable_reserve_original_rows_root_unchanged_and_review_gate(self):
        def send(body):
            rows = self.dbrows()
            self.assertEqual(rows[:7], self.old)
            self.assertEqual(rows[7][3:5], ('reserved_uncertain', live.RESERVATION))
            self.assertEqual(body, v.payload('journey-04', 'openai'))
            return self.success(body)
        http = Mock(side_effect=send)
        record = live.run_next(self.run, http)
        self.assertEqual(http.call_count, 1)
        self.assertFalse(record['reviewHalt'], record)
        self.assertEqual(self.dbrows()[7][4], 2500000)
        self.assertEqual(record['rowid'], 8)
        self.assertEqual(self.dbrows()[:7], self.old)
        with self.assertRaisesRegex(e.AdmissionError, 'review'): live.run_next(self.run, http)
        self.assertEqual(http.call_count, 1)
        live.record_review(record, review(record), self.run)
        self.assertEqual(len(self.dbrows()), 8)

    def test_provider_error_halts_no_retry(self):
        http = Mock(return_value={'_http_status': 400, 'error': {'type': 'invalid_request_error'}})
        record = live.run_next(self.run, http)
        self.assertTrue(record['reviewHalt'])
        self.assertEqual(self.dbrows()[7][3:5], ('recorded_halted',2500000))
        with self.assertRaises(e.AdmissionError): live.run_next(self.run, http)
        self.assertEqual(http.call_count, 1)
        with self.assertRaises(e.AdmissionError): live.record_review(record, review(record), self.run)

    def test_timeout_retains_full_reservation_and_exception_text_not_stored(self):
        record = live.run_next(self.run, Mock(side_effect=TimeoutError('private-secret')))
        self.assertEqual(record['status'], 'transport_error')
        self.assertNotIn('private-secret', json.dumps(record))
        self.assertEqual(self.dbrows()[7][4], 2500000)

    def test_invalid_json(self):
        response = self.success({}); response['output'][0]['content'][0]['text'] = '{'
        record = live.run_next(self.run, Mock(return_value=response))
        self.assertTrue(record['reviewHalt'])

    def test_truncation_is_not_success_or_retryable(self):
        response = self.success({}); response['status'] = 'incomplete'
        record = live.run_next(self.run, Mock(return_value=response))
        self.assertTrue(record['reviewHalt'])
        self.assertEqual(self.dbrows()[7][4],2500000)

    def test_missing_usage_retains_full_liability_and_halts(self):
        response = self.success({}); response.pop('usage')
        record = live.run_next(self.run, Mock(return_value=response))
        self.assertTrue(record['reviewHalt'])
        self.assertEqual(self.dbrows()[7][4],2500000)

    def test_changed_source_or_code_even_with_matching_seal_refuses(self):
        for field in ('coverage', 'codeHashes'):
            value = copy.deepcopy(self.plan)
            if field == 'coverage': value[field]['journey-04']['text'] = 'Unapproved prompt'
            else: value[field]['cloud_model52_offline.py'] = 'wrong'
            (self.run/'approval.json').write_text(json.dumps(value))
            (self.run/'approval.seal.json').write_text(json.dumps({'hash':e.digest(value)}))
            http = Mock()
            with self.assertRaises(e.AdmissionError): live.run_next(self.run,http)
            http.assert_not_called()
        self.assertEqual(len(self.dbrows()),7)

    def test_source_rejection_and_wrong_order_halt(self):
        response = self.success({})
        value = json.loads(response['output'][0]['content'][0]['text'])
        value['journey']['order'][0]['source'] = 'then'
        response['output'][0]['content'][0]['text'] = json.dumps(value)
        record = live.run_next(self.run, Mock(return_value=response))
        self.assertTrue(record['reviewHalt'])
        self.assertFalse(record['scoring']['validatedAccepted'])

    def test_crash_before_send_is_consumed_uncertain_never_retried(self):
        http = Mock()
        with patch.object(audit, 'append_json', side_effect=RuntimeError('crash')):
            with self.assertRaises(RuntimeError): live.run_next(self.run, http)
        self.assertEqual(self.dbrows()[7][3], 'reserved_uncertain')
        http.assert_not_called()
        with self.assertRaises(e.AdmissionError): live.run_next(self.run, http)
        http.assert_not_called()

    def test_crash_after_send_preserves_evidence_uncertain_and_no_retry(self):
        http = Mock(side_effect=self.success)
        with patch.object(live.ExistingLedger, 'finish', side_effect=RuntimeError('crash')):
            with self.assertRaises(RuntimeError): live.run_next(self.run, http)
        self.assertTrue((self.run / 'response-8.json').exists())
        self.assertEqual(self.dbrows()[7][3], 'reserved_uncertain')
        with self.assertRaises(e.AdmissionError): live.run_next(self.run, http)
        self.assertEqual(http.call_count, 1)

    def test_approval_seal_code_source_payload_and_historical_tampering(self):
        path = self.run / 'approval.json'
        plan = json.loads(path.read_text()); plan['slots'].reverse()
        path.write_text(json.dumps(plan))
        http = Mock()
        with self.assertRaises(e.AdmissionError): live.run_next(self.run, http)
        http.assert_not_called()
        self.assertEqual(len(self.dbrows()), 7)

    def test_original_row_and_root_mutation_blocks_before_send(self):
        db = sqlite3.connect(self.state / 'journal.sqlite')
        db.execute('update attempts set charge=0 where rowid=1'); db.commit(); db.close()
        http = Mock()
        with self.assertRaises(e.AdmissionError): live.run_next(self.run, http)
        http.assert_not_called()

    def test_expired_daily_count_credit_and_scope_readiness(self):
        for mutation in ('count', 'day', 'prepared', 'credits', 'reload', 'rpm', 'hash', 'payload', 'cap'):
            value = copy.deepcopy(self.ready)
            expired = (live.now()-timedelta(days=2)).isoformat()
            if mutation == 'count': value['counts']['journey-04']['observedAtUTC'] = expired
            elif mutation == 'day': value['reviewDateUTC'] = '2000-01-01'
            elif mutation == 'prepared': value['preparedAtUTC'] = expired
            elif mutation == 'credits': value['accountReview']['creditsUSD'] = .001
            elif mutation == 'reload': value['accountReview']['autoReload'] = True
            elif mutation == 'rpm': value['accountReview']['rpm'] = 0
            elif mutation == 'hash': value['configurationHash'] = 'wrong'
            elif mutation == 'payload': value['counts']['journey-04']['payloadHash'] = 'wrong'
            elif mutation == 'cap': value['counts']['journey-04']['inputTokens'] = 12001
            with self.subTest(mutation=mutation), self.assertRaises(e.AdmissionError): live.check_readiness(value)

    def test_concurrent_process_lock_refuses_no_send(self):
        http = Mock()
        with e.exclusive(self.state), self.assertRaises(BlockingIOError): live.run_next(self.run, http)
        http.assert_not_called()

    def test_output_cap_and_observed_liability_stop(self):
        response = self.success({}); response['usage']['output_tokens'] = 2001
        with self.assertRaises(e.AdmissionError): live.run_next(self.run, Mock(return_value=response))
        self.assertEqual(self.dbrows()[7][3], 'recorded_halted')

    def test_aggregate_and_provider_and_global_ceilings(self):
        for name, value in [('SPEND_CAP', 39866625), ('PROVIDER_CAP', 4), ('TOTAL_CAP', 7)]:
            http = Mock()
            with patch.object(e, name, value), self.assertRaises(e.AdmissionError): live.run_next(self.run, http)
            http.assert_not_called()
        self.assertEqual(len(self.dbrows()), 7)

    def test_five_original_slots_in_order_full_gross_reservation_no_sixth(self):
        http = Mock(return_value=self.success({}))
        # Only isolate semantics for this admission test; real semantic/source
        # tests below and the existing suites never use this fake pass.
        with patch.object(live.scorer, 'score', return_value={'structuredValid': True, 'validatedAccepted': True, 'automatedFailures': []}), patch.object(live, 'approved_extension_checks', return_value={}):
            for i, case_id in enumerate(v.SLOTS):
                record = live.run_next(self.run, http)
                self.assertEqual(record['caseId'], case_id)
                self.assertEqual(record['rowid'], i+8)
                live.record_review(record, review(record), self.run)
            self.assertIsNone(live.run_next(self.run, http))
        self.assertEqual(http.call_count, 5)
        self.assertEqual(sum(r[4] for r in self.dbrows()[7:]),12500000)
        self.assertEqual(self.dbrows()[:7], self.old)

    def test_review_cannot_claim_human_or_leave_fields_unresolved(self):
        record = {'approvalHash': 'fake'}
        for change in ('human', 'missing', 'wrong', 'null'):
            value = review(record)
            if change == 'human': value['independentHumanSignoff'] = True
            elif change == 'missing': value['fields'].pop('ordering')
            elif change == 'wrong': value['fields']['ordering']['correct'] = False
            elif change == 'null': value['fields']['ordering']['correct'] = None
            with self.assertRaises(e.AdmissionError): live.verify_review(record,value)

    def test_existing_only_no_database_creation(self):
        with self.assertRaises(sqlite3.OperationalError): live.ExistingLedger(self.state/'missing.sqlite')
        self.assertFalse((self.state/'missing.sqlite').exists())

    def test_prose_gold_partial_repeated_return_budget_and_negative_requirements(self):
        from backend.ai import Interpretation
        for case_id in ('extension-partial', 'extension-repeated'):
            case = next(c for c in e.corpus()['cases'] if c['id'] == case_id)
            partial = case_id == 'extension-partial'
            stops = ['pharmacy', 'bank', 'coffee'] if partial else ['Coffee', 'museum', 'coffee']
            raw = Interpretation(activities=stops, budget_per_person=None, date=None,
                location='Jersey City', preferences=[], date_expressions=['tomorrow'],
                journey={'stops': [{'source': s} for s in stops],
                    'order': [{'before': 0 if partial else 1, 'after': 1 if partial else 2,
                        'source': 'pharmacy before the bank' if partial else 'museum, then coffee'}],
                    'ordering': 'constrained',
                    'endpoint': None if partial else {'kind': 'origin', 'source': 'return to the starting point'},
                    'total_duration': None if partial else {'minutes': 180, 'relation': 'maximum', 'source': 'within three hours'}}).model_dump(mode='json')
            checks = live.approved_extension_checks(case,json.dumps(raw))
            self.assertTrue(all(checks.values()), checks)
            if not partial:
                # Reproduce the consumed v4 response's failure without model
                # I/O. A real quote can contain both names and a trailing cue
                # while attaching that cue to the wrong relationship.
                wrong = copy.deepcopy(raw)
                wrong['journey']['order'].insert(0, {'before':0, 'after':1,
                    'source':'Coffee, museum, then'})
                wire = reference_wire({'expectedExtraction': wrong})
                canonical = live.scorer.score(case,json.dumps(wire))
                self.assertTrue(canonical['structuredValid'])
                self.assertTrue(canonical['validatedAccepted'])  # Known bounded-validator limitation.
                self.assertFalse(canonical['automatedFailures'])  # Prose gold is not fully compared here.
                self.assertFalse(live.approved_extension_checks(case,json.dumps(wire))['partialOrderOnly'])
            mutations = [lambda x: x['journey']['stops'].pop(),
                lambda x: x['journey']['stops'][2].update(requirement='optional'),
                lambda x: x['journey']['order'].append({'before': 0,'after': 2,'source': case['text']}),
                lambda x: x.update(location='New York'),
                lambda x: x.update(travel_total_minutes=180),
                lambda x: x['journey']['stops'][0].update(source='Eiffel Tower')]
            if not partial:
                mutations += [lambda x: x['journey']['endpoint'].update(kind='home'),
                    lambda x: x['journey']['total_duration'].update(relation='under')]
            for change in mutations:
                bad = copy.deepcopy(raw); change(bad)
                try: checked = live.approved_extension_checks(case,json.dumps(bad))
                except ValueError: continue
                self.assertFalse(all(checked.values()), bad)

    def test_only_source_valid_reviewed_home_clarification_is_permitted(self):
        case = next(c for c in e.corpus()['cases'] if c['id']=='journey-12')
        raw = reference_wire(case); content = json.dumps(raw)
        scored = live.scorer.score(case,content)
        self.assertFalse(scored['validatedAccepted'])
        self.assertTrue(live.expected_endpoint_clarification(case,content,scored))
        for change in (lambda x: x['journey']['endpoint'].update(kind='origin'),
                lambda x: x['journey']['total_duration'].update(relation='under'),
                lambda x: x['journey']['stops'][0].update(source='Eiffel Tower')):
            bad = copy.deepcopy(raw); change(bad); content = json.dumps(bad)
            self.assertFalse(live.expected_endpoint_clarification(case,content,live.scorer.score(case,content)))


if __name__ == '__main__': unittest.main()
