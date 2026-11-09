"""Finite release-gap tests; no provider, counting or model calls."""
import hashlib
import json
from pathlib import Path
import unittest

from backend.ai import Interpretation
from scripts.cloud_model52_ordering_compatibility import fixture_reply,positive
from scripts import cloud_model52_ordering_v3 as old
from scripts import cloud_model52_ordering_v4 as policy

DOCS=Path(__file__).resolve().parents[1]/'docs'


def cases(name='cases'):
    return json.loads((DOCS/f'task52-ordering-v4-{name}.json').read_text())['cases']


class ReleaseGapTests(unittest.TestCase):
    def test_predeclared_positive_negative_contracts(self):
        for c in cases():
            with self.subTest(case=c['id']):
                ai=fixture_reply(c);before=ai.model_dump(mode='json');r=policy.inspect_order(c['text'],ai)
                self.assertEqual(positive(r),c['accept'],r)
                self.assertEqual(before,ai.model_dump(mode='json'))
                if c['accept']:
                    self.assertEqual([(p['before'],p['after']) for p in r['source']['proofs']],
                        [tuple(x) for x in c['expectedRelationships']])
                    self.assertEqual(policy.project(c['text'],ai,r),ai)

    def test_three_original_gaps_pass_without_changing_nonordering_fields(self):
        for c in json.loads((DOCS/'task52-ordering-v3-release-limits.json').read_text())['cases']:
            ai=fixture_reply(c);before=ai.model_dump(mode='json')
            self.assertFalse(positive(old.inspect_order(c['text'],ai)))
            r=policy.inspect_order(c['text'],ai);self.assertTrue(positive(r),r)
            self.assertEqual(policy.project(c['text'],ai,r).model_dump(mode='json'),before)

    def test_unsupported_reversed_extra_and_missing_edges(self):
        count=0
        for c in cases()+cases('holdouts'):
            if not c['accept']:continue
            expected=c['expectedRelationships'];ai=fixture_reply(c)
            analysis=policy.source_analysis(c['text'],ai)
            for a in range(len(c['stops'])):
                for b in range(len(c['stops'])):
                    if a==b or policy.reach(expected,a,b):continue
                    d=ai.model_dump(mode='json');d['journey'].update(order=[{'before':a,'after':b,'source':c['text']}],ordering='constrained')
                    wrong=Interpretation.model_validate(d);r=policy.inspect_order(c['text'],wrong)
                    self.assertEqual(policy.source_analysis(c['text'],wrong),analysis)
                    if positive(r):
                        self.assertEqual(r['trustedGraph'],[]);self.assertFalse(r['rawModelOrderingCorrect'])
                    else:self.assertIsNone(r['trustedGraph'])
                    count+=1
            if expected:
                ai.journey.order=[]
                self.assertFalse(positive(policy.inspect_order(c['text'],ai)))
        self.assertGreater(count,20)

    def test_global_scope_proof_is_not_a_comma_or_borrowed_cue(self):
        c=next(x for x in cases() if x['id']=='three-global');ai=fixture_reply(c)
        ai.journey.order[0].source='coffee, visit museum'
        self.assertFalse(positive(policy.inspect_order(c['text'],ai)))
        ai=fixture_reply(c);ai.journey.order[1].source='museum, and finish at pharmacy'
        self.assertFalse(positive(policy.inspect_order(c['text'],ai)))
        c=next(x for x in cases() if x['id']=='partial-remains');d=fixture_reply(c).model_dump(mode='json')
        d['journey']['order'].append({'before':0,'after':1,'source':'Coffee, museum, then'})
        self.assertFalse(positive(policy.inspect_order(c['text'],Interpretation.model_validate(d))))

    def test_optional_required_and_named_identity_remain_separate(self):
        for name in ('optional-third','independent-required'):
            c=next(x for x in json.loads((DOCS/'task52-ordering-compatibility-v3-cases.json').read_text())['cases'] if x['id']==name)
            ai=fixture_reply(c);self.assertTrue(positive(policy.inspect_order(c['text'],ai)))
            ai.journey.stops[2].requirement='required' if name=='optional-third' else 'optional'
            self.assertFalse(positive(policy.inspect_order(c['text'],ai)))
        c=next(x for x in cases() if x['id']=='named-words');ai=fixture_reply(c)
        ai.journey.stops[0].source='Invented Start Cafe'
        self.assertFalse(positive(policy.inspect_order(c['text'],ai)))

    def test_all_frozen_v3_development_and_holdouts_remain_compatible(self):
        sources=json.loads((DOCS/'task52-ordering-compatibility-v3-cases.json').read_text())['cases']
        held=json.loads((DOCS/'task52-ordering-compatibility-v3-holdouts.json').read_text())
        for c in sources+held['cases']+held['regressionCases']:
            ai=fixture_reply(c)
            self.assertEqual(positive(old.inspect_order(c['text'],ai)),positive(policy.inspect_order(c['text'],ai)),c['id'])

    def test_separated_post_freeze_cases(self):
        data=json.loads((DOCS/'task52-ordering-v4-holdouts.json').read_text())
        self.assertEqual(data['frozenModuleSHA256'],hashlib.sha256(Path(policy.__file__).read_bytes()).hexdigest())
        for c in data['cases']:
            self.assertEqual(positive(policy.inspect_order(c['text'],fixture_reply(c))),c['accept'],c['id'])
