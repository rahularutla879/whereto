"""Design-boundary characterization only; no enforcement prototype or activation.

Exercises the real legacy interpreter and frozen offline V4 on separate copies.
These tests expose why composing the two validators is not enforcement.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from pydantic import ValidationError
from backend.ai import Interpretation
from backend.advanced_routing import _ancestors
from backend.interpretation import (InterpretationInput, PendingClarification,
                                    ClarificationAnswers, interpret_request)
from backend.journey import Endpoint, OrderConstraint
from scripts.cloud_model52_ordering_compatibility import fixture_reply, positive
from scripts import cloud_model52_ordering_v4 as policy

DOCS=Path(__file__).resolve().parents[1]/'docs'
NOW=datetime(2026,11,8,12,tzinfo=timezone.utc)


def case(name):
    return next(c for c in json.loads((DOCS/'task52-ordering-v4-cases.json').read_text())['cases'] if c['id']==name)


class EnforcementDesignBoundaries(unittest.TestCase):
    def legacy(self, text, ai):
        provider=Mock();provider.interpret.return_value=ai
        with patch('requests.sessions.Session.send',side_effect=AssertionError('No network')):
            result=interpret_request(InterpretationInput(text=text),provider,now=NOW)
        self.assertEqual(provider.interpret.call_count,1)
        return result

    def test_global_start_finish_requires_more_than_pre_or_post_guard(self):
        for name in ('city-date','three-global'):
            with self.subTest(case=name):
                c=case(name);ai=fixture_reply(c);before=ai.model_dump(mode='json')
                decision=policy.inspect_order(c['text'],ai)
                self.assertTrue(positive(decision))
                projected=policy.project(c['text'],ai,decision)
                legacy=self.legacy(c['text'],projected)
                self.assertEqual(legacy.interpretation.journey.order,[])
                self.assertEqual(legacy.executionStatus,'clarification_required')
                self.assertIsNone(legacy.request)
                self.assertIsNone(legacy.pending)
                # Legacy also treats every "finish at" as a distinct endpoint.
                # A V4 final VISIT must not simply inherit that omission check.
                self.assertIsNone(legacy.interpretation.journey.endpoint)
                self.assertEqual(ai.model_dump(mode='json'),before)

    def test_real_quote_extra_repeated_edge_is_still_legacy_accepted(self):
        c=case('partial-remains');ai=fixture_reply(c)
        text=c['text']+' in Jersey City tomorrow.';ai.location='Jersey City'
        ai.journey.order.insert(0, OrderConstraint(before=0,after=1,source='Coffee, museum, then'))
        ai=Interpretation.model_validate(ai.model_dump())
        legacy=self.legacy(text,ai)
        self.assertIsNotNone(legacy.request)
        self.assertEqual([(e.before,e.after) for e in legacy.interpretation.journey.order],[(0,1),(1,2)])
        decision=policy.inspect_order(text,ai)
        self.assertFalse(positive(decision))
        self.assertEqual(decision['unsupportedModelEdges'],[[0,1]])
        self.assertIn((1,2),[(p['before'],p['after']) for p in decision['source']['proofs']])

    def test_audited_list_projection_preserves_raw_error_and_nonorder_values(self):
        text='Dinner and bowling tomorrow in Jersey City.'
        ai=fixture_reply({'text':text,'stops':['Dinner','bowling'],
                          'expectedRelationships':[[0,1]],'location':'Jersey City'})
        raw=ai.model_dump(mode='json');decision=policy.inspect_order(text,ai)
        self.assertEqual(decision['trustedGraph'],[])
        self.assertFalse(decision['rawModelOrderingCorrect'])
        effective=policy.project(text,ai,decision).model_dump(mode='json')
        want=deepcopy(raw);want['journey']['order']=[];want['journey']['ordering']='unspecified'
        self.assertEqual(effective,want)
        self.assertEqual(ai.model_dump(mode='json'),raw)
        for changed_text,changed_ai in [(text+' Please.',ai), (text,ai.model_copy(update={'people':3}))]:
            with self.assertRaises(ValueError):policy.project(changed_text,changed_ai,decision)

    def test_verified_order_is_not_endpoint_authorization(self):
        text='Dinner and bowling tomorrow in Jersey City.'
        ai=fixture_reply({'text':text,'stops':['Dinner','bowling'],
                          'expectedRelationships':[],'location':'Jersey City'})
        ai.journey.endpoint=Endpoint(kind='origin',source='Invented return')
        self.assertTrue(positive(policy.inspect_order(text,ai)))
        result=self.legacy(text,ai)
        self.assertIsNone(result.request)
        self.assertEqual(result.executionStatus,'clarification_required')

    def test_missing_journey_is_an_explicit_profile_compatibility_gap(self):
        text='Dinner and bowling tomorrow in Jersey City.'
        ai=Interpretation(activities=['Dinner','bowling'],location='Jersey City',
                          budget_per_person=None,date=None,preferences=[])
        self.assertIsNotNone(self.legacy(text,ai).request)
        self.assertFalse(positive(policy.inspect_order(text,ai)))
        self.assertIn('bounded_input_or_missing_contract',policy.inspect_order(text,ai)['issues'])

    def test_partial_order_and_repeated_occurrence_closure_are_distinct(self):
        c=case('partial-remains');ai=fixture_reply(c)
        decision=policy.inspect_order(c['text'],ai)
        self.assertTrue(positive(decision))
        ancestors=_ancestors(ai.journey)
        self.assertEqual(ancestors,{0:set(),1:set(),2:{1}})
        c=case('three-global');ai=fixture_reply(c)
        self.assertTrue(positive(policy.inspect_order(c['text'],ai)))
        self.assertEqual(_ancestors(ai.journey),{0:set(),1:{0},2:{0,1}})

    def test_browser_pending_is_revalidated_data_not_authenticated_capability(self):
        text='Dinner and bowling tomorrow in Jersey City.'
        ai=fixture_reply({'text':text,'stops':['Dinner','bowling'],
                          'expectedRelationships':[],'location':'Jersey City'})
        first=self.legacy(text,ai)
        self.assertIsNotNone(first.pending)
        data=first.pending.model_dump(mode='json')
        data['referenceTime']='2040-01-01T12:00:00Z'
        self.assertEqual(PendingClarification.model_validate(data).referenceTime.year,2040)
        provider=Mock(side_effect=AssertionError('No fresh inference on a followup'))
        provider.interpret.side_effect=AssertionError('No fresh inference on a followup')
        result=interpret_request(InterpretationInput(text=text,pending=first.pending),provider,now=NOW)
        self.assertIsNotNone(result.request);provider.interpret.assert_not_called()
        for model,body in [(InterpretationInput,{'text':text,'orderingProfile':'v4'}),
                           (ClarificationAnswers,{'ordering':'0 before 1'}),
                           (PendingClarification,{**data,'orderingReceipt':'invented'})]:
            with self.assertRaises(ValidationError):model.model_validate(body)
