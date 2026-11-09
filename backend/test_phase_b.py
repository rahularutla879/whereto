"""Finite Phase B equivalence and uncertainty tests, always fake providers."""
from dataclasses import replace
from datetime import datetime,timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock,patch

from backend.ai import Interpretation
from backend.interpretation import InterpretationInput
from backend.journey_fixtures import reply
from backend.source_preparation import prepare_source,observe_effective,strict_extraction
from backend.validation_phases import validate_legacy
from backend.planning_admission import AdmissionRegistry,AdmissionError
from scripts import task52_phase_b_replay as replay
from scripts import task52_phase_b2_identity as identity
from scripts import task52_version_review as historical

NOW=replay.NOW
DOCS=Path(__file__).resolve().parents[1]/'docs'


class PhaseBTests(unittest.TestCase):
    def run_case(self,text,data,**extra):
        ai=Interpretation.model_validate(data)
        value=InterpretationInput(text=text,**extra)
        provider=Mock(interpret=Mock(return_value=ai))
        d=validate_legacy(value,provider,now=NOW)
        self.assertEqual(provider.interpret.call_count,0 if value.pending else 1)
        return value,d

    def test_75_frozen_traces_and_full_dtos_errors_identical_to_direct_legacy(self):
        from scripts.task52_b2_test_fixture import reference_scope
        with reference_scope():
            baseline=json.loads((DOCS/'task52-phase-b-legacy-characterization-v1.json').read_text())
            self.assertEqual(replay.characterize(),baseline)
            cases=replay.scenarios()
            self.assertEqual(sum(r['id'].startswith('qwen-') for r in cases),27)
            self.assertEqual(sum(r['id'].startswith('openai-') for r in cases),7)
            for row in cases:
                with self.subTest(case=row['id']):
                    self.assertEqual(replay.run(row)[1],replay.run(row,direct=True)[1])

    def test_raw_snapshot_precedes_home_removal_and_duration_normalization(self):
        text='Museum, then go home tomorrow in Jersey City.'
        data=reply(['Museum','go home'],location='Jersey City',order=[(0,1,'Museum, then go home')])
        _,d=self.run_case(text,data)
        p=d.preparation
        self.assertEqual(json.loads(p.basis_snapshot)['activities'],['Museum','go home'])
        self.assertEqual(json.loads(p.effective_snapshot)['activities'],['Museum'])
        self.assertEqual([m.effective_index for m in p.mapping],[0,None])
        self.assertEqual(p.mapping[1].status,'unresolved')
        self.assertEqual(json.loads(p.effective_snapshot)['journey']['endpoint']['kind'],'home')
        _,d=self.run_case('Spend 20 minutes at the museum.',reply(['museum']))
        self.assertIsNone(json.loads(d.preparation.basis_snapshot)['journey']['stops'][0]['duration'])
        self.assertEqual(json.loads(d.preparation.effective_snapshot)['journey']['stops'][0]['duration']['minutes'],20)

    def test_repeated_coffee_owns_distinct_spans_not_graph_proof(self):
        text='Coffee, museum, then coffee.'
        _,d=self.run_case(text,reply(['Coffee','museum','coffee'],order=[(1,2,'museum, then coffee')]))
        p=d.preparation
        self.assertEqual([o.logical_id for o in p.occurrences],['basis:0','basis:1','basis:2'])
        self.assertEqual([text[s.span[0]:s.span[1]] for s in p.occurrences],['Coffee','museum','coffee'])
        self.assertEqual([m.effective_index for m in p.mapping],[0,1,2])
        self.assertEqual([(e.before,e.after) for e in d.raw_model.journey.order],[(1,2)])

    def test_count_and_ambiguous_lexical_ownership_never_invent_span_or_index(self):
        for text,phrases in [('Coffee twice.',['Coffee','Coffee']),
                             ('Coffee, coffee, museum.',['Coffee','museum']),
                             ('Coffee.',['Coffee','Coffee'])]:
            _,d=self.run_case(text,reply(phrases))
            self.assertTrue(all(o.span is None for o in d.preparation.occurrences))
            self.assertTrue(all(m.effective_index is None for m in d.preparation.mapping))

    def test_named_optional_evidence_and_wrong_quote_ownership(self):
        text='Visit SUNY College of Optometry, maybe coffee.'
        data=reply(['SUNY College of Optometry','coffee'],kinds={0:'named_place'},optional={1:'maybe coffee'})
        _,d=self.run_case(text,data)
        p=d.preparation
        self.assertEqual(p.occurrences[1].evidence_status,'lexically_bound')
        a,b=p.occurrences[1].evidence_span;self.assertEqual(text[a:b],'maybe coffee')
        data['journey']['stops'][1]['evidence']='SUNY College of Optometry'
        _,d=self.run_case(text,data)
        self.assertEqual(d.preparation.occurrences[1].evidence_status,'unresolved')
        self.assertIsNone(d.result.request)

    def test_field_presence_reference_manual_and_immutable_capture(self):
        text='Dinner in Jersey City tomorrow.'
        data=dict(activities=['Dinner'],budget_per_person=None,date=None,location='Jersey City',preferences=[])
        _,d=self.run_case(text,data,preferences={'location':'New York'},calendarTimezone='America/New_York')
        p=d.preparation
        self.assertNotIn('journey',p.explicit_fields)
        self.assertEqual(json.loads(p.manual_snapshot)['location'],'New York')
        self.assertEqual(p.reference_time,NOW)
        self.assertEqual(p.reference_basis,'explicit_now')
        self.assertEqual(p.calendar_timezone,'America/New_York')
        d.raw_model.activities.clear()
        self.assertEqual(json.loads(p.basis_snapshot)['activities'],['Dinner'])
        self.assertNotIn(text,repr(p))
        self.assertIsNone(p.occurrences[0].journey_index)

    def test_wall_clock_not_moved_or_fabricated(self):
        value=InterpretationInput(text='Dinner tomorrow.')
        ai=strict_extraction(reply(['Dinner']))
        p=prepare_source(value,ai,source_kind='raw_model')
        self.assertIsNone(p.reference_time)
        self.assertEqual(p.reference_basis,'legacy_clock_unobserved')

    def test_pending_is_effective_not_raw_and_answer_mapping_unresolved(self):
        text='Dinner and drinks in Jersey City tomorrow.'
        _,first=self.run_case(text,reply(['Dinner','drinks'],location='Jersey City'))
        pending=first.result.pending
        value,d=self.run_case(text,reply(['Dinner','drinks']),pending=pending,answers={'activities':'Coffee and museum'})
        p=d.preparation
        self.assertEqual(p.source_kind,'legacy_effective_pending')
        self.assertIsNone(d.raw_snapshot)
        self.assertEqual(p.reference_time,pending.referenceTime)
        self.assertIsNotNone(p.pending_answer_snapshot)
        self.assertTrue(all(m.effective_index is None for m in p.mapping))
        with self.assertRaises(ValueError):prepare_source(value,pending.interpretation,source_kind='raw_model')

    def test_mismatched_journey_indices_and_unicode_offsets_are_not_guessed(self):
        value=InterpretationInput(text='Café → museum.')
        data=reply(['Café','museum']);data['journey']['stops'][0]['source']='Different venue'
        p=prepare_source(value,strict_extraction(data),source_kind='raw_model',now=NOW)
        self.assertTrue(all(o.journey_index is None for o in p.occurrences))
        self.assertEqual(value.text[slice(*p.occurrences[0].span)],'Café')

    def test_similar_names_and_partial_words_do_not_acquire_owned_spans(self):
        from backend.source_preparation import _bindings
        self.assertEqual(_bindings('Visit Banker Hall.', ['bank']), (None,))

    def test_binding_search_is_bounded_and_unknown_stays_unknown(self):
        from backend.source_preparation import _bindings
        self.assertEqual(_bindings('a '*2000,['a']*32),(None,)*32)

    def test_forged_or_copied_preparation_cannot_issue_or_consume_receipts(self):
        _,d=self.run_case('Dinner in Jersey City tomorrow.',reply(['Dinner'],location='Jersey City'))
        registry=AdmissionRegistry();scope=registry.new_scope();work=Mock();provider=Mock()
        fake=replace(d.preparation,source_kind='raw_model',runtime_identity='invented')
        with self.assertRaises(AdmissionError):
            registry.validate(fake,scope,1,provider,now=NOW)
        with self.assertRaises(AdmissionError):registry.run(fake,scope,1,{},work)
        provider.interpret.assert_not_called();work.assert_not_called()

    def test_new_identity_is_separate_from_historical_working_equality(self):
        self.assertTrue(identity.verify()['verified'])
        self.assertFalse(identity.verify(purpose='legacy_ordinary')['planningAuthorized'])
        historical.verify('52b-historical-evaluator-b04','historical_evaluator')
        with self.assertRaises(historical.VersionError):
            historical.verify('52b-historical-evaluator-b04','historical_evaluator',working=True)
        for kw in ({'runtime':'unknown'},{'purpose':'v4_enforced'},{'purpose':'public_receipt'}):
            with self.assertRaises(historical.VersionError):identity.verify(**kw)

    def test_altered_manifest_or_runtime_source_is_rejected(self):
        with TemporaryDirectory() as tmp:
            p=Path(tmp)/'manifest.json';p.write_bytes(identity.MANIFEST.read_bytes()+b' ')
            with patch.object(identity,'MANIFEST',p),self.assertRaises(historical.VersionError):identity.verify()
        read=Path.read_bytes
        def mutate(path):
            data=read(path)
            return data+b'\n# changed' if str(path).endswith('source_preparation.py') else data
        with patch.object(Path,'read_bytes',mutate),self.assertRaises(historical.VersionError):identity.verify()
