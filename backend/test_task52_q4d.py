"""Q4D real read-only inspection; all mutations use NEW fictional databases."""
from copy import deepcopy
from contextlib import closing
import json
import multiprocessing
from pathlib import Path
from types import SimpleNamespace
import sqlite3
import unittest
from unittest.mock import patch

from backend import test_task52_v51_evaluator as fixtures
from scripts import task52_q1 as q1
from scripts import task52_q4d as q
from scripts import task52_q4d_identity as identity
from scripts import task52_q4b as reader

NOW = fixtures.NOW


def crash_child(continuation, permission, response):
    with patch('socket.socket.connect', side_effect=AssertionError('No network')):
        continuation.simulate_one(permission, fixtures.base.FakeTransport(response), NOW, crash_at='after_outcome')


class Q4DTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = q1.private_hashes()
        cls.original = q.inspect_original()
        cls.keys = fixtures.SyntheticKeys()
        cls.responses = fixtures.fake_responses()

    @classmethod
    def tearDownClass(cls):
        cls.keys.close()
        assert q1.private_hashes() == cls.before
        assert q.inspect_original() == cls.original

    def fixture(self, active=True):
        c = q.FictionalContinuation(self.keys.trust)
        self.addCleanup(c.close)
        binding = SimpleNamespace(**c.fixture_binding())
        scope = fixtures.scope(self.keys, binding)
        if active:
            c.activate_synthetic_scope(scope, NOW)
        return c, binding, scope

    def reach(self, index):
        c, b, s = self.fixture()
        previous = fixtures.a.ZERO
        for i in range(index):
            o = c.simulate_one(fixtures.execute(self.keys, b, s, i, previous), fixtures.base.FakeTransport(self.responses[i]), NOW)
            c.record_review(fixtures.review(self.keys, b, o), NOW)
            previous = c._engine.state()[1][-1]['hash']
        return c, b, s, previous

    def test_original_exact_ro_connection_and_sanitized_compatibility(self):
        connect = sqlite3.connect
        seen = []
        def readonly(database, *args, **kwargs):
            self.assertEqual(database, reader.READ_URI)
            self.assertIs(kwargs.get('uri'), True)
            seen.append(database)
            return connect(database, *args, **kwargs)
        with patch.object(reader.sqlite3, 'connect', readonly):
            report = q.inspect_original()
        self.assertTrue(seen)
        self.assertTrue(report['schemaCompatible'])
        self.assertFalse(report['realWritableAdapter'])
        self.assertFalse(report['executionAuthorized'])
        self.assertEqual(report['original']['attempts'], 10)
        self.assertEqual(report['original']['accountedNanodollars'], 47366625)
        self.assertNotIn('metadata', report['original'])
        self.assertNotIn('rows', report['original'])

    def test_wrong_root_prefix_amount_halt_corrections_and_evidence_refuse(self):
        for key, value in [('rootHash', '0'*64), ('rowHashes', []), ('counts', {}),
                           ('accountedNanodollars', 0), ('persistentHistoricalHalt', False),
                           ('correctionsUnchanged', False), ('privateFilesUnchanged', 323),
                           ('executionAuthorized', True), ('continuationReady', True)]:
            bad = deepcopy(self.original['original']); bad[key] = value
            with self.subTest(key=key), self.assertRaises(q.Denied):
                q.compatibility(bad)
        with (patch.object(q.reader, 'inspect_original', side_effect=reader.Incompatible('bad')),
                patch.object(q.protocol, 'SyntheticJournal', side_effect=AssertionError('No write before compatibility'))):
            with self.assertRaises(reader.Incompatible):
                q.FictionalContinuation(self.keys.trust)

    def test_factory_no_arbitrary_path_live_switch_or_real_writer(self):
        with self.assertRaises(TypeError):
            q.FictionalContinuation(self.keys.trust, directory=reader.STATE)
        with self.assertRaises(q.Denied):
            q.protocol.Engine(reader.STATE, self.keys.trust)
        for grant in (None, {}, {'force': True}, {'resume': True}, self.original):
            with self.assertRaises(fixtures.base.Refused):
                q.live_dispatch(grant)
        c, _, _ = self.fixture(False)
        self.assertNotEqual(c._fixture.directory, reader.STATE)
        self.assertEqual(c._fixture.directory.stat().st_mode & 0o777, 0o700)
        self.assertNotIn(str(c._fixture.directory), str(self.original))

    def test_exact_schema_prefix_full_charge_halt_and_shared_lock_contract(self):
        c, b, s = self.fixture()
        rows_before = c._engine.state()[0]
        o = c.simulate_one(fixtures.execute(self.keys, b, s), fixtures.base.FakeTransport(self.responses[0]), NOW)
        with closing(c._engine.db()) as db:
            self.assertEqual(dict(db.execute("SELECT name,sql FROM sqlite_master WHERE type='table'")), reader.DDL)
        rows = c._engine.state()[0]
        self.assertEqual(rows[:10], rows_before)
        self.assertEqual(rows[-1][4:6], ('reserved_uncertain', 2500000))
        self.assertEqual(c.report()['childExposureNanodollars'], 2500000)
        self.assertTrue(c.report()['historicalHaltPreserved'])
        self.assertFalse(o['data']['assessment']['planningAuthorized'])
        with c._engine.lock(), self.assertRaises(q.Denied):
            c.simulate_one(fixtures.execute(self.keys, b, s), fixtures.base.FakeTransport(self.responses[0]), NOW)

    def test_known_loss_halts_without_altering_correct_raw_and_blocks_review_next(self):
        c, b, s, previous = self.reach(3)
        o = c.simulate_one(fixtures.execute(self.keys, b, s, 3, previous), fixtures.base.FakeTransport(self.responses[3]), NOW)
        a = o['data']['assessment']
        self.assertEqual(a['raw']['extractionFailures'], [])
        self.assertEqual(a['guarded']['disposition'], q.LOSS)
        self.assertEqual(a['responseHash'], q1.digest(self.responses[3]))
        self.assertFalse(a['planningAuthorized'])
        report = c.report()
        self.assertTrue(report['childHalted']); self.assertTrue(report['legacyOrderLoss'])
        self.assertEqual(report['childAttempts'], 4)
        self.assertEqual(report['childExposureNanodollars'], 10000000)
        with self.assertRaises(q.Denied):
            c.record_review(fixtures.review(self.keys, b, o), NOW)
        with self.assertRaises(q.Denied):
            c.simulate_one(fixtures.execute(self.keys, b, s, 4), fixtures.base.FakeTransport(self.responses[4]), NOW)
        self.assertEqual(len(list(c._fixture.directory.glob('fake-send-*'))), 4)

    def test_process_exit_after_loss_outcome_before_outer_halt_remains_blocked(self):
        c, b, s, previous = self.reach(3)
        process = multiprocessing.get_context('fork').Process(target=crash_child,
            args=(c, fixtures.execute(self.keys, b, s, 3, previous), self.responses[3]))
        process.start(); process.join(30)
        self.assertFalse(process.is_alive()); self.assertEqual(process.exitcode, 73)
        # No outer HALT was appended, yet durable OUTCOME is sufficient to deny.
        self.assertFalse(c.report()['childHalted']); self.assertTrue(c.report()['progressionBlocked'])
        o = c._engine.state()[1][-1]
        self.assertEqual(o['kind'], 'OUTCOME')
        with self.assertRaises(q.Denied): c.record_review(fixtures.review(self.keys, b, o), NOW)
        with self.assertRaises(q.Denied):
            c.simulate_one(fixtures.execute(self.keys, b, s, 4), fixtures.base.FakeTransport(self.responses[4]), NOW)
        self.assertEqual(c.report()['childAttempts'], 4)

    def test_uncertain_send_retains_charge_halts_and_cannot_retry(self):
        c, b, s = self.fixture()
        with self.assertRaises(q.Denied):
            c.simulate_one(fixtures.execute(self.keys, b, s), fixtures.base.FakeTransport(self.responses[0], failure='uncertain_send'), NOW)
        self.assertTrue(c.report()['childHalted'])
        self.assertEqual(c.report()['childExposureNanodollars'], 2500000)
        with self.assertRaises(q.Denied):
            c.simulate_one(fixtures.execute(self.keys, b, s), fixtures.base.FakeTransport(self.responses[0]), NOW)
        self.assertEqual(c.report()['childAttempts'], 1)

    def test_reviews_duplicate_scope_wrong_identity_consumed_slot_and_raw_failure(self):
        c, b, s = self.fixture()
        with self.assertRaises(q.Denied): c.activate_synthetic_scope(s, NOW)
        good = fixtures.execute(self.keys, b, s)
        wrong = deepcopy(good); wrong['envelope'] = wrong['envelope'].replace('extension-repeated', 'journey-07')
        with self.assertRaises(q.Denied): c.simulate_one(wrong, fixtures.base.FakeTransport(self.responses[0]), NOW)
        self.assertEqual(c.report()['childAttempts'], 0)
        bad = fixtures.mutate(self.responses[0], lambda v: v['journey']['order'].pop(0))
        o = c.simulate_one(good, fixtures.base.FakeTransport(bad), NOW)
        self.assertTrue(o['data']['assessment']['raw']['extractionFailures'])
        with self.assertRaises(q.Denied): c.record_review(fixtures.review(self.keys, b, o), NOW)
        self.assertTrue(c.report()['childHalted'])

    def test_missing_independent_response_review_never_progresses(self):
        c, b, s = self.fixture()
        c.simulate_one(fixtures.execute(self.keys, b, s), fixtures.base.FakeTransport(self.responses[0]), NOW)
        with self.assertRaises(q.Denied):
            c.simulate_one(fixtures.execute(self.keys, b, s, 1), fixtures.base.FakeTransport(self.responses[1]), NOW)
        self.assertEqual(c.report()['childAttempts'], 1)

    def test_fifth_contradiction_still_checked_offline_not_skipped_or_planned(self):
        r = fixtures.assess(fixtures.identity.plan()['slots'][4]['slot'], self.responses[4])
        self.assertEqual(r['raw']['extractionFailures'], [])
        self.assertEqual(r['guarded']['disposition'], 'appropriate_clarification')
        self.assertFalse(r['planningAuthorized'])
        self.assertIsNone(r['raw']['fullyCorrectIndependent'])

    def test_unknown_build_or_parent_hash_refuses_before_inspection(self):
        with patch.object(identity, 'MANIFEST_SHA', '0'*64), patch.object(q.reader, 'inspect_original', side_effect=AssertionError('No inspect')):
            with self.assertRaises(ValueError): q.inspect_original()
