"""Approved current-runtime reconstruction; never historical execution/readiness."""
import ast
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from backend import journey
from scripts import cloud_model52 as paid
from scripts import task52_b2_behavior as behavior
from scripts.task52_b2_test_fixture import reference_scope,ORIGINAL_CORPUS,PAID_STATE
from scripts import task52_version_review as h

DOCS=h.ROOT/'docs'


class DurationExtractionTests(unittest.TestCase):
    def test_all_25_frozen_mutations_errors_and_dynamic_lookup_sequences_match(self):
        base=json.loads((DOCS/'task52-b2-behavior-baseline-v1.json').read_text())
        self.assertFalse(base['byteIdenticalHistoricalEnvironment'])
        self.assertFalse(base['paidInferenceAuthorized'])
        self.assertFalse(base['planningAdmissionAuthorized'])
        self.assertEqual([behavior.duration_trace(c) for c in base['durationCases']],base['durationExpected'])
        for before,after in [(r['before'],r['after']) for r in base['durationExpected']]:
            # Fields other than the two supported duration positions cannot change.
            b=deepcopy(before);a=deepcopy(after)
            b['total_duration']=a['total_duration']=None
            for stop in b['stops']+a['stops']:stop['duration']=None
            self.assertEqual(a,b)

    def test_body_is_only_relocated_and_qualified_not_a_new_algorithm(self):
        original=h.git('show','2fec366:backend/journey.py').decode()
        fn=next(n for n in ast.parse(original).body if isinstance(n,ast.FunctionDef) and n.name=='normalize_explicit_durations')
        current=next(n for n in ast.parse((h.ROOT/'backend/duration_preparation.py').read_text()).body if isinstance(n,ast.FunctionDef))
        class Unqualify(ast.NodeTransformer):
            def visit_Attribute(self,node):
                if isinstance(node.value,ast.Name) and node.value.id=='legacy':return ast.copy_location(ast.Name(id=node.attr,ctx=ast.Load()),node)
                return self.generic_visit(node)
        current.body=[n for n in current.body if not isinstance(n,ast.ImportFrom)]
        self.assertEqual(ast.dump(fn,include_attributes=False),ast.dump(Unqualify().visit(current),include_attributes=False))
        # Original wrapper stays between the same reference and graph stages.
        source=(h.ROOT/'backend/journey.py').read_text()
        self.assertIn('normalize_extracted_references(raw, ai)\n    normalize_explicit_durations(raw,guarded,j)',source)

    def test_real_evaluator_remains_fail_closed_before_and_after_offline_fixture(self):
        for fn in (ORIGINAL_CORPUS,paid.corpus,paid.metadata):
            with self.assertRaisesRegex(ValueError,'Reference source changed'):fn()
        with reference_scope():
            self.assertEqual(len(paid.corpus()['cases']),66)
        self.assertIs(paid.corpus,ORIGINAL_CORPUS)
        with self.assertRaisesRegex(ValueError,'Reference source changed'):paid.corpus()

    def test_original_gate_prevents_even_fake_reservation_outside_fixture(self):
        base=json.loads((DOCS/'task52-b2-behavior-baseline-v1.json').read_text())
        with tempfile.TemporaryDirectory() as tmp:
            ledger=paid.Ledger(Path(tmp)/'fake-unit.sqlite',base['baselineMetadataFixture'])
            try:
                with self.assertRaises(ValueError):ledger.reserve('openai','journey-01',1)
                self.assertEqual(ledger.db.execute('select count(*) from attempts').fetchone()[0],0)
            finally:ledger.close()

    def test_fixture_cannot_write_paid_state_read_keys_or_use_http(self):
        import requests
        with reference_scope():
            with self.assertRaises(AssertionError):sqlite3.connect(PAID_STATE/'journal.sqlite')
            with self.assertRaises(AssertionError):(PAID_STATE/'blocked-test.json').write_text('not written')
            with self.assertRaises(AssertionError):(h.ROOT/'backend/.env.cloud-evaluation').read_text()
            with self.assertRaises(AssertionError):requests.get('https://example.invalid',timeout=1)

    def test_old_runtime_identity_is_not_relabelled_b2(self):
        from scripts import task52_phase_b_identity as b1,task52_phase_b2_identity as b2
        with self.assertRaises(h.VersionError):b1.verify()
        self.assertTrue(b2.verify()['verified'])
        with self.assertRaises(h.VersionError):b2.verify(runtime='52b-runtime-phase-b1')
        read=Path.read_bytes
        def corrupt_baseline(path):
            data=read(path)
            return data+b' ' if path.name=='task52-b2-behavior-baseline-v1.json' else data
        with patch.object(Path,'read_bytes',corrupt_baseline),self.assertRaises(h.VersionError):b2.verify()
