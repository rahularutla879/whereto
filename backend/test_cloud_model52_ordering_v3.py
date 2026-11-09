"""Offline-only ordering/normalization policy, raw records never changed."""
import json
from pathlib import Path
import unittest

from backend.ai import Interpretation
from scripts import cloud_model52_ordering_v3 as v3
from scripts.cloud_model52_ordering_compatibility import fixture_reply, positive
from backend.test_cloud_model52_ordering import cases as originals
from backend.test_cloud_model52_ordering_v2 import cases as v2cases

DOCS=Path(__file__).resolve().parents[1]/'docs'


def cases():
    return json.loads((DOCS/'task52-ordering-compatibility-v3-cases.json').read_text())['cases']


class OrderingPolicyTests(unittest.TestCase):
    def test_predeclared_source_contracts_and_exact_relationships(self):
        for c in cases():
            with self.subTest(case=c['id']):
                ai=fixture_reply(c);before=ai.model_dump(mode='json')
                r=v3.inspect_order(c['text'],ai)
                self.assertEqual(r['source']['category'],c['sourceCategory'],r)
                self.assertEqual(positive(r),c['sourceCategory']!='unknown',r)
                if positive(r):
                    self.assertEqual([(p['before'],p['after']) for p in r['source']['proofs']],
                        [tuple(x) for x in c['expectedRelationships']])
                self.assertEqual(before,ai.model_dump(mode='json'))

    def test_source_intent_independent_of_proposed_graph_and_model_status(self):
        for c in cases():
            ai=fixture_reply(c);expected=v3.source_analysis(c['text'],ai)
            for graph in ([],[{'before':0,'after':1,'source':c['text']}],
                          [{'before':1,'after':0,'source':c['text']}]):
                if len(c['stops'])<2 and graph:continue
                raw=ai.model_dump(mode='json');raw['journey']['order']=graph
                raw['journey']['order_conflict']=True
                for s in raw['journey']['stops']:s['requirement']='optional'
                self.assertEqual(v3.source_analysis(c['text'],Interpretation.model_validate(raw)),expected)

    def test_no_unsupported_edge_can_survive_projection(self):
        # Covers old 31, v2 40, and new 29; normalizing an invented edge is
        # distinct from accepting that edge or marking raw output correct.
        count=0
        for c in originals()+v2cases()+cases():
            if c.get('accept') is False or c.get('expectedOutcome')=='clarification_required' or c.get('sourceCategory')=='unknown':continue
            for a in range(len(c['stops'])):
                for b in range(len(c['stops'])):
                    if a==b or v3.reach(c['expectedRelationships'],a,b):continue
                    ai=fixture_reply(c);data=ai.model_dump(mode='json')
                    data['journey'].update(order=[{'before':a,'after':b,'source':c['text']}],ordering='constrained')
                    r=v3.inspect_order(c['text'],Interpretation.model_validate(data))
                    if positive(r):
                        self.assertEqual(r['source']['category'],'unordered')
                        self.assertEqual(r['trustedGraph'],[])
                        self.assertFalse(r['rawModelOrderingCorrect'])
                    else:self.assertIsNone(r['trustedGraph'])
                    count+=1
        self.assertEqual(count,147)

    def test_normalization_is_explicit_hash_bound_and_preserves_every_other_field(self):
        c=next(c for c in cases() if c['id']=='ordinary');ai=fixture_reply(c)
        data=ai.model_dump(mode='json');data['journey'].update(order=[{'before':0,'after':1,'source':c['text']}],ordering='constrained')
        ai=Interpretation.model_validate(data)
        raw=ai.model_dump(mode='json');r=v3.inspect_order(c['text'],ai)
        projected=v3.project(c['text'],ai,r).model_dump(mode='json')
        expected=json.loads(json.dumps(raw));expected['journey'].update(order=[],ordering='unspecified')
        self.assertEqual(projected,expected);self.assertEqual(ai.model_dump(mode='json'),raw)
        self.assertEqual(r['originalGraph'],[[0,1]]);self.assertFalse(r['rawModelOrderingCorrect'])
        r['trustedGraph']=[[0,1]]
        with self.assertRaises(ValueError):v3.project(c['text'],ai,r)

    def test_missing_or_bad_evidence_never_erases_real_order(self):
        for name in ('start-finish','head-out','repeated-partial','partial','optional-third'):
            c=next(c for c in cases() if c['id']==name);ai=fixture_reply(c)
            self.assertEqual(v3.project(c['text'],ai,v3.inspect_order(c['text'],ai)),ai)
            ai.journey.order[0].source='then'
            self.assertFalse(positive(v3.inspect_order(c['text'],ai)))
            ai.journey.order=[]
            self.assertIn('missing_proven_required_relationship',v3.inspect_order(c['text'],ai)['issues'])

    def test_qualifier_scope_status_and_conditional_negatives(self):
        c=next(c for c in cases() if c['id']=='optional-third');ai=fixture_reply(c)
        ai.journey.stops[2].requirement='required'
        self.assertIn('source_optionality_mismatch',v3.inspect_order(c['text'],ai)['issues'])
        c=next(c for c in cases() if c['id']=='independent-required');ai=fixture_reply(c)
        ai.journey.stops[2].requirement='optional'
        self.assertIn('source_optionality_mismatch',v3.inspect_order(c['text'],ai)['issues'])
        for text in ('Maybe pharmacy and bank.','Pharmacy before bank, maybe coffee before museum.',
                     'Pharmacy before bank unless coffee.','Pharmacy before bank; never coffee.'):
            stops=['pharmacy','bank']+(['coffee'] if 'coffee' in text else [])+(['museum'] if 'museum' in text else [])
            c={'text':text,'stops':stops,'expectedRelationships':[]}
            self.assertFalse(positive(v3.inspect_order(text,fixture_reply(c))))

    def test_repeated_extra_and_reversed_indices_rejected(self):
        c=next(c for c in cases() if c['id']=='repeated-partial');ai=fixture_reply(c)
        data=ai.model_dump(mode='json');data['journey']['order'].append({'before':0,'after':1,'source':'Coffee, museum, then'})
        r=v3.inspect_order(c['text'],Interpretation.model_validate(data))
        self.assertEqual(r['unsupportedModelEdges'],[[0,1]]);self.assertIsNone(r['trustedGraph'])
        data['journey']['order']=[{'before':2,'after':1,'source':c['text']}]
        self.assertFalse(positive(v3.inspect_order(c['text'],Interpretation.model_validate(data))))

    def test_limits_unknown_connectors_and_ungrounded_edge_fail_closed(self):
        c=next(c for c in cases() if c['id']=='ordinary');ai=fixture_reply(c)
        data=ai.model_dump(mode='json');data['journey']['order']=[{'before':0,'after':1,'source':'invented quote'}]
        self.assertFalse(positive(v3.inspect_order(c['text'],Interpretation.model_validate(data))))
        self.assertFalse(positive(v3.inspect_order(' '*8001+c['text'],ai)))
        self.assertEqual(v3.source_analysis('Dinner subsequently bowling.',ai)['category'],'unknown')

    def test_recorded_unordered_plan_imperative_and_other_constraints_survive(self):
        c={'text':'Plan dinner and drinks in Hyderabad tomorrow.','stops':['dinner','drinks'],
            'location':'Hyderabad','expectedRelationships':[]}
        ai=fixture_reply(c)
        self.assertTrue(positive(v3.inspect_order(c['text'],ai)))
        data=ai.model_dump(mode='json');data['journey'].update(order=[{'before':0,'after':1,'source':c['text']}],ordering='constrained')
        ai=Interpretation.model_validate(data);r=v3.inspect_order(c['text'],ai)
        projected=v3.project(c['text'],ai,r)
        self.assertEqual(projected.location,'Hyderabad')
        self.assertEqual(projected.journey.stops,ai.journey.stops)
        self.assertFalse(r['rawModelOrderingCorrect'])

    def test_flexible_mode_is_source_bound_not_an_invented_preference(self):
        c={'text':'Visit bank and grocery store, whichever is closer first, tomorrow in New York.',
            'stops':['bank','grocery store'],'location':'New York','expectedRelationships':[]}
        ai=fixture_reply(c)
        self.assertEqual(v3.source_analysis(c['text'],ai)['category'],'unordered')
        self.assertIn('source_flexible_mode_mismatch',v3.inspect_order(c['text'],ai)['issues'])
        ai.journey.ordering='flexible'
        r=v3.inspect_order(c['text'],ai)
        self.assertTrue(positive(r));self.assertEqual(v3.project(c['text'],ai,r),ai)
        ai=fixture_reply(next(c for c in cases() if c['id']=='ordinary'));ai.journey.ordering='flexible'
        self.assertFalse(positive(v3.inspect_order('Dinner and bowling tomorrow.',ai)))

    def test_post_freeze_holdouts(self):
        import hashlib
        data=json.loads((DOCS/'task52-ordering-compatibility-v3-holdouts.json').read_text())
        self.assertEqual(data['frozenModuleSHA256'],hashlib.sha256(Path(v3.__file__).read_bytes()).hexdigest())
        for c in data['cases']+data['regressionCases']:
            r=v3.inspect_order(c['text'],fixture_reply(c))
            self.assertEqual(r['source']['category'],c['sourceCategory'],(c['id'],r))
            self.assertEqual(positive(r),c['sourceCategory']!='unknown')

    def test_all_recorded_replays_keep_halt_and_historical_evidence_immutable(self):
        from scripts import cloud_model52 as evaluation
        if not (evaluation.STATE/'journal.sqlite').is_file():
            self.skipTest('Owner-private paid evidence unavailable; pure fixture tests still run')
        from scripts.cloud_model52_ordering_policy_replay import build
        from scripts.task52_b2_test_fixture import reference_scope
        with reference_scope():r=build()
        s=r['summary']
        self.assertEqual((s['qwenRows'],s['qwenV3Clarifications'],s['qwenAuditedUnorderedNormalizations']),(27,2,7))
        self.assertEqual((s['openaiRows'],s['openaiV3Compatible']),(7,5))
        self.assertEqual(s['qwenOtherCanonicalBlocksPreserved'],5)
        self.assertEqual(s['unsupportedEdgesAccepted'],0)
        j=r['journal'];self.assertEqual(j['totalAttempts'],10)
        self.assertEqual(j['accountedNanodollars'],47366625)
        self.assertTrue(j['persistentHalt']);self.assertTrue(j['allIgnoredFilesUnchanged'])
        self.assertEqual(j['sha256Before'],j['sha256After'])
        self.assertEqual(r['requestsSent'],0);self.assertFalse(r['productionActivated'])
        self.assertFalse(r['independentHumanSignoff'])
        self.assertEqual(s['releaseLimitV3FalseClarifications'],3)


if __name__=='__main__':unittest.main()
