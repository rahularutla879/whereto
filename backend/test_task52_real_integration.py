"""Integration checks using new exact-schema fixtures and test signatures."""
from contextlib import closing
from datetime import timedelta
import json
import multiprocessing
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from backend import test_task52_diagnostic_progression as fake
from scripts import task52_q1 as q1
from scripts import task52_q4a as original_protocol
from scripts import task52_q4b as reader
from scripts import task52_q4d as strict_bridge
from scripts import task52_v51_eval_protocol as v51
from scripts import task52_real_integration as integration

NOW = fake.NOW


def crash(fixture, permission, response, point):
    fixture.simulate_one(permission, fake.p.FakeTransport(response), NOW, crash_at=point)


def compete(fixture):
    try:
        fixture.report()
    except integration.Denied:
        return
    raise AssertionError("Competing process acquired the synthetic experiment lock")


class RealIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keys = fake.SyntheticKeys()
        cls.responses = fake.fake_responses()

    @classmethod
    def tearDownClass(cls):
        cls.keys.close()

    def fixture(self, *, active=True, base_charge=1000000):
        fixture = integration.SyntheticIntegration(self.keys.trust, base_charge=base_charge)
        self.addCleanup(fixture.close)
        binding = SimpleNamespace(**fixture.fixture_binding())
        scope = fake.scope(self.keys, binding)
        if active:
            fixture.activate_synthetic_scope(scope, NOW)
        return fixture, binding, scope

    def step(self, fixture, binding, scope, index=0, previous=fake.a.ZERO, response=None):
        return fixture.simulate_one(
            fake.execute(self.keys, binding, scope, index, previous),
            fake.p.FakeTransport(self.responses[index] if response is None else response), NOW)

    def test_original_connections_are_read_only(self):
        connect = sqlite3.connect

        def observed(path, *args, **kwargs):
            self.assertEqual(path, reader.READ_URI)
            return connect(path, *args, **kwargs)

        with patch.object(sqlite3, "connect", side_effect=observed) as observed_connect:
            result = integration.inspect_original()["inspection"]["original"]
            self.assertEqual(result["rowIDs"], list(range(1, 11)))
            self.assertEqual(result["privateFilesUnchanged"], 324)
            self.assertTrue(result["persistentHistoricalHalt"])
            with self.assertRaises(integration.Denied):
                integration._AppendEngine(reader.STATE, self.keys.trust)
            with self.assertRaises(TypeError):
                integration.SyntheticIntegration(self.keys.trust, directory=reader.STATE)
        self.assertTrue(observed_connect.called)

    def test_exact_schema_and_sql_refusals(self):
        fixture, _, _ = self.fixture(active=False)
        with self.assertRaises(integration.Denied):
            fixture._engine.db()
        with fixture._engine.lock(), closing(fixture._engine.db()) as connection:
            schema = dict(connection.execute(
                "SELECT name,sql FROM sqlite_master WHERE type='table'").fetchall())
            self.assertEqual(schema, reader.DDL)
            for statement in (
                "UPDATE attempts SET charge=0", "DELETE FROM attempts",
                "INSERT OR REPLACE INTO attempts VALUES(?,?,?,?,?,?)",
                "REPLACE INTO attempts VALUES(?,?,?,?,?,?)",
                "UPDATE metadata SET config='changed'", "ATTACH DATABASE ':memory:' AS other",
                "DROP TABLE attempts", "PRAGMA synchronous=OFF",
            ):
                with self.subTest(statement=statement), self.assertRaises(integration.Denied):
                    connection.execute(statement)
        self.assertEqual(fixture.report()["attempts"], 10)

    def test_five_slots_only_after_explicit_synthetic_loss_review(self):
        fixture, binding, scope = self.fixture()
        with fixture._engine.lock():
            prefix = fixture._engine.state()[0]
        expected = json.loads((q1.ROOT / "docs/task52-diagnostic-progression-fake-v1.json").read_text())
        previous = fake.a.ZERO
        for index in range(5):
            outcome = self.step(fixture, binding, scope, index, previous)
            assessment = outcome["data"]["assessment"]
            self.assertEqual(q1.digest(assessment), q1.digest(expected["operations"][index]["assessment"]))
            self.assertEqual(q1.digest(outcome["data"]["response"]), q1.digest(self.responses[index]))
            self.assertEqual(assessment["raw"]["extractionFailures"], [])
            self.assertFalse(assessment["planningAuthorized"])
            self.assertFalse(assessment["diagnostic"]["actualContinuationAuthorized"])
            self.assertIsNone(assessment["raw"]["fullyCorrectIndependent"])
            if index == 3:
                self.assertTrue(assessment["diagnostic"]["systemIncompatible"])
                self.assertEqual(assessment["diagnostic"]["allowlistedDefect"], fake.identity.defect_hash())
                with self.assertRaises(integration.Denied):
                    self.step(fixture, binding, scope, 4, previous)
                with self.assertRaises(integration.Denied):
                    fixture.record_review(fake.review(self.keys, binding, outcome, signer="owner"), NOW)
                self.assertEqual(fixture.report()["attempts"], 14)
            fixture.record_review(fake.review(self.keys, binding, outcome), NOW)
            with fixture._engine.lock():
                rows, facts, _, _ = fixture._engine.state()
                previous = facts[-1]["hash"]
                self.assertEqual(rows[:10], prefix)
                self.assertEqual(rows[-1][0], 11 + index)
        with self.assertRaises(integration.Denied):
            self.step(fixture, binding, scope, 4, previous)
        report = fixture.report()
        self.assertEqual(report["counts"], {"openai": 12, "google": 2, "anthropic": 1})
        self.assertEqual(report["childExposureNanodollars"], 12500000)
        self.assertEqual(report["factKinds"], ["SCOPE"] + ["START", "INTENT", "OUTCOME", "REVIEW"] * 5)
        self.assertTrue(report["historicalHaltPreserved"])

    def test_document_build_and_stale_permission_refusals(self):
        fixture, binding, scope = self.fixture(active=False)
        decision = json.loads((q1.ROOT / "docs/task52-owner-diagnostic-continuation-v1.json").read_text())
        with self.assertRaises(integration.Denied):
            fixture.activate_synthetic_scope({**scope, "owner": decision}, NOW)
        for module in (integration, fake.p, strict_bridge, v51, original_protocol):
            with self.subTest(module=module.__name__), self.assertRaises(original_protocol.Refused):
                module.live_dispatch(scope)
        changes = (
            lambda value: value["binding"].update(executionBuildHash="0" * 64),
            lambda value: value["binding"].update(parentProposalHash="0" * 64),
            lambda value: value.update(scope="0" * 64),
            lambda value: value["binding"]["parentSpecification"].update(promptHash="0" * 64),
            lambda value: value["binding"]["parentSpecification"].update(wireSchemaHash="0" * 64),
            lambda value: value["binding"]["parentSpecification"].update(Q1RubricHash="0" * 64),
        )
        for change in changes:
            wrong = self.keys.packet("owner", fake.a.owner_data(), binding, change=change)
            with self.assertRaises(integration.Denied):
                fixture.activate_synthetic_scope({**scope, "owner": wrong}, NOW)
        fixture.activate_synthetic_scope(scope, NOW)
        with self.assertRaises(integration.Denied):
            fixture.activate_synthetic_scope(scope, NOW)
        with self.assertRaises(integration.Denied):
            fixture.simulate_one(fake.execute(self.keys, binding, scope),
                                 fake.p.FakeTransport(self.responses[0]), NOW + timedelta(days=1))
        wrong_slot = fake.execute(
            self.keys, binding, scope,
            change=lambda value: value["data"].update(slot=["openai", "journey-07", 1]))
        with self.assertRaises(integration.Denied):
            fixture.simulate_one(wrong_slot, fake.p.FakeTransport(self.responses[0]), NOW)
        self.assertEqual(fixture.report()["attempts"], 10)

    def test_invalid_rows_and_exhausted_budget(self):
        for slot, status, charge in (
            ((None, "journey-04", 2), "reserved_uncertain", 2500000),
            (("openai", "journey-04", 2), "unknown", 2500000),
            (("openai", "journey-04", 2), "reserved_uncertain", -1),
        ):
            with self.subTest(slot=slot, status=status, charge=charge):
                fixture, binding, scope = self.fixture()
                with closing(sqlite3.connect(fixture._fixture.directory / "journal.sqlite")) as connection:
                    connection.execute("INSERT INTO attempts VALUES(?,?,?,?,?,?)", (*slot, status, charge, "{}"))
                    connection.commit()
                with self.assertRaises(integration.Denied):
                    self.step(fixture, binding, scope)
                self.assertFalse(list(fixture._fixture.directory.glob("fake-send-*")))
        fixture, binding, scope = self.fixture(base_charge=1200000000)
        with self.assertRaises(integration.Denied):
            self.step(fixture, binding, scope)
        self.assertEqual(fixture.report()["attempts"], 10)

    def test_raw_error_and_uncertain_send_stop(self):
        fixture, binding, scope = self.fixture()
        response = fake.mutate(self.responses[0], lambda value: value["journey"]["order"].pop(0))
        outcome = self.step(fixture, binding, scope, response=response)
        self.assertTrue(outcome["data"]["assessment"]["raw"]["extractionFailures"])
        self.assertEqual(fixture.report()["factKinds"][-1], "HALT")
        with self.assertRaises(integration.Denied):
            fixture.record_review(fake.review(self.keys, binding, outcome), NOW)
        fixture, binding, scope = self.fixture()
        with self.assertRaises(integration.Denied):
            fixture.simulate_one(fake.execute(self.keys, binding, scope),
                                 fake.p.FakeTransport(failure="response_loss"), NOW)
        report = fixture.report()
        self.assertEqual(report["factKinds"], ["SCOPE", "START", "INTENT", "HALT"])
        self.assertEqual(report["childExposureNanodollars"], 2500000)
        fixture._engine = integration._AppendEngine(fixture._fixture.directory, self.keys.trust)
        with self.assertRaises(integration.Denied):
            self.step(fixture, binding, scope)

    def test_process_exit_and_lock_exclusion(self):
        context = multiprocessing.get_context("fork")
        for point, attempts in (("before_reserve", 10), ("after_reserve", 11), ("after_intent", 11)):
            with self.subTest(point=point):
                fixture, binding, scope = self.fixture()
                process = context.Process(target=crash, args=(
                    fixture, fake.execute(self.keys, binding, scope), self.responses[0], point))
                process.start()
                process.join(45)
                self.assertEqual(process.exitcode, 73)
                report = fixture.report()
                self.assertEqual(report["attempts"], attempts)
                self.assertEqual(report["childExposureNanodollars"], (attempts - 10) * 2500000)
                self.assertFalse(list(fixture._fixture.directory.glob("fake-send-*")))
                with self.assertRaises(integration.Denied):
                    self.step(fixture, binding, scope)
        with fixture._engine.lock():
            process = context.Process(target=compete, args=(fixture,))
            process.start()
            process.join(45)
            self.assertEqual(process.exitcode, 0)
