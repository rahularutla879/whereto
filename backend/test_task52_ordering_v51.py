"""V5.1 offline contrasts. No paid, routing or production activation."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from backend.test_task52_ordering_v5 import reply
from scripts import task52_ordering_v5 as v5
from scripts import task52_ordering_v51 as v51
from scripts import task52_q1 as q1
ROOT=Path(__file__).resolve().parents[1]


def load(name):return json.loads((ROOT/'docs'/name).read_text())


class OwnerV51Tests(unittest.TestCase):
    def test_predeclared_connector_and_scope_cases(self):
        for c in load('task52-ordering-v51-cases-v1.json')['cases']:
            with self.subTest(case=c['id']):
                ai=reply(c);before=ai.model_dump(mode='json');r=v51.inspect_order(c['text'],ai)
                self.assertEqual(r['trustedGraph']is not None,c['category']!='unknown',r['issues'])
                self.assertEqual(ai.model_dump(mode='json'),before);self.assertFalse(r['planningAuthorized'])
                if c['category']!='unknown':self.assertEqual(r['requiredClosure'],v51.closure(c['expectedEdges'],len(c['stops'])))

    def test_frozen_v5_cases_holdouts_and_negative_edges(self):
        probes=0
        for file in ('task52-ordering-v5-cases-v1.json','task52-ordering-v5-holdouts-v1.json'):
            for c in load(file)['cases']:
                ai=reply(c);old=v5.inspect_order(c['text'],ai);new=v51.inspect_order(c['text'],ai)
                self.assertEqual(old['trustedGraph'],new['trustedGraph'],c['id'])
                self.assertEqual(old['requiredClosure'],new['requiredClosure'])
                if old['trustedGraph']is None:continue
                for a in range(len(c['stops'])):
                    for b in range(len(c['stops'])):
                        if a==b or [a,b]in old['requiredClosure']:continue
                        probes+=1;self.assertIsNone(v51.inspect_order(c['text'],reply(c,c['expectedEdges']+[[a,b]]))['trustedGraph'])
        self.assertEqual(probes,58)

    def test_aur_evidence_uses_actual_source_offsets_and_new_identity(self):
        c=load('task52-ordering-v51-cases-v1.json')['cases'][0];ai=reply(c)
        self.assertIsNone(v5.inspect_order(c['text'],ai)['trustedGraph'])
        r=v51.inspect_order(c['text'],ai);p=r['source']['proofs'][0]
        self.assertEqual(p['source'],'Coffee aur dinner');self.assertEqual(p['source'],c['text'][slice(*p['span'])])
        self.assertEqual(p['source_sha256'],q1.sha(c['text'].encode()));self.assertEqual(p['rule'],'default_list_hi_aur')
        ai.journey.order[0].source='Coffee and dinner';self.assertIsNone(v51.inspect_order(c['text'],ai)['trustedGraph'])
        ai.journey.order[0].source='aur';self.assertIsNone(v51.inspect_order(c['text'],ai)['trustedGraph'])

    def test_optional_projection_keeps_required_closure_and_never_forces_optional(self):
        c=next(c for c in load('task52-ordering-v5-cases-v1.json')['cases'] if c['id']=='optional-middle')
        ai=reply(c);r=v51.inspect_order(c['text'],ai)
        self.assertEqual(r['mandatoryRequiredVisitClosure'],[[0,2]])
        self.assertEqual(v51.selected_visit_projection(r,[0,2])['requiredReachability'],[[0,2]])
        self.assertEqual(v51.selected_visit_projection(r,[0,1,2])['requiredReachability'],[[0,1],[0,2],[1,2]])
        self.assertEqual(ai.journey.stops[1].requirement,'optional')
        for selected in ([0],[0,2,2],[0,True,2]):
            with self.assertRaises(ValueError):v51.selected_visit_projection(r,selected)
        bad=deepcopy(r);bad['version']='unknown'
        with self.assertRaises(ValueError):v51.selected_visit_projection(bad,[0,2])

    def test_actual_shortlister_closes_before_optional_selection_without_providers(self):
        from backend.advanced_routing import _shortlist
        c=next(c for c in load('task52-ordering-v5-cases-v1.json')['cases'] if c['id']=='optional-middle')
        ai=reply(c);groups=[NS(occurrence=i,requested=s,status='candidates',candidates=[NS(place_id=f'fictional-{i}')]) for i,s in enumerate(ai.journey.stops)]
        with patch('backend.advanced_routing._gap',return_value=0):paths=_shortlist(NS(journey=ai.journey,stops=groups),None,None)
        self.assertEqual({tuple(i for i,_ in path) for path in paths},{(0,2),(0,1,2)})

    def test_new_connector_extra_reverse_and_missing_edges_reject(self):
        probes=0
        for c in load('task52-ordering-v51-cases-v1.json')['cases']:
            if c['category']=='unknown':continue
            allowed=v51.closure(c['expectedEdges'],len(c['stops']))
            for a in range(len(c['stops'])):
                for b in range(len(c['stops'])):
                    if a==b or [a,b]in allowed:continue
                    probes+=1;self.assertIsNone(v51.inspect_order(c['text'],reply(c,c['expectedEdges']+[[a,b]]))['trustedGraph'])
            if c['expectedEdges']:
                self.assertIsNone(v51.inspect_order(c['text'],reply(c,[]))['trustedGraph'])
        self.assertGreater(probes,10)

    def test_flexible_required_stop_is_not_optional_or_chain(self):
        c=next(c for c in load('task52-ordering-v51-cases-v1.json')['cases'] if c['id']=='flex-owner')
        ai=reply(c);r=v51.inspect_order(c['text'],ai)
        self.assertEqual(r['source']['requirements'],['required']*3);self.assertEqual(r['requiredClosure'],[[0,1]])
        ai.journey.stops[2].requirement='optional';self.assertIn('source_optionality_mismatch',v51.inspect_order(c['text'],ai)['issues'])

    def test_prompt_examples_keep_nonorder_contract_and_full_exact_payload(self):
        from scripts import task52_prompt_v51 as prompt
        from scripts import cloud_model52 as e
        proposed=prompt.proposal();self.assertEqual(q1.digest(proposed),q1.digest(load('task52-cloud-prompt-v51-PROPOSED-v1.json')))
        self.assertEqual(proposed['exampleOrderingChanges'],[10,12,15,19]);self.assertEqual(proposed['exampleCount'],19)
        for row in proposed['examples']:
            a,b=deepcopy(row['oldReply']),deepcopy(row['proposedReply'])
            for j in (a,b):j['journey'].pop('order',None);j['journey'].pop('ordering',None)
            self.assertEqual(a,b)
        new=proposed['messagesWithEmptyFinalUser'][0]['content']
        for item in reversed(proposed['systemReplacements']):new=new.replace(item['proposed'],item['original'])
        from scripts import cloud_model52_proposal as old
        self.assertEqual(new,old.messages('')[0]['content'])
        template=proposed['fullOpenAIRequestTemplate'];base=e.Adapter('openai',None).payload('')
        self.assertEqual({k:v for k,v in template.items() if k!='input'},{k:v for k,v in base.items() if k!='input'})
        self.assertEqual(len(prompt.payload_hashes(proposed)),66);self.assertFalse(proposed['canAuthorizeDispatch'])

    def test_all66_amendment_preserves_nonorder_gold_and_labels_resolution(self):
        from scripts import task52_ordering_v51_review as review
        rubric=review.amendment();self.assertEqual(q1.digest(rubric),q1.digest(load('task52-q1-rubric-v3-v51-PROPOSED.json')))
        self.assertEqual(rubric['counts'],{'mandatory_graph_change':19,'graph_unchanged':45,'conditional_graph_change':2})
        original=load('task52-q1-rubric-v1.json')
        for old,new in zip(original['cases'],rubric['cases']):
            self.assertEqual(old['sourceSHA256'],new['sourceSHA256'])
            for k,f in old['fields'].items():
                if k not in ('mandatory_order','unordered_flexible','source_provenance'):self.assertEqual(f,new['fields'][k])
        self.assertEqual(len(rubric['originalSixUnresolved']),6);self.assertEqual(rubric['remainingProposedUnresolvedFieldCount'],5)
        self.assertEqual(rubric['independentCaseApprovals'],0)

    def test_replay_and_successor_keep_historical_failures_and_blank_authority(self):
        from scripts import task52_ordering_v51_review as review
        from scripts import task52_prompt_v51 as prompt
        r=review.replay();self.assertEqual(q1.digest(r),q1.digest(load('task52-ordering-v51-replay-v1.json')))
        cases={c['slot'][1]:c for c in r['openai']}
        self.assertIsNotNone(cases['extension-repeated']['V51']['trustedGraph'])
        self.assertEqual(cases['extension-repeated']['originalV5Comparison']['originalQ1']['raw']['rubricFinding'],'incorrect_unsupported_order')
        self.assertIsNone(cases['journey-07']['V51']['trustedGraph'])
        for id in ('journey-01','ordinary-dinner'):self.assertIn('missing_source_required_relationship',cases[id]['V51']['issues'])
        p=review.successor(review.amendment(),prompt.proposal())
        self.assertEqual(q1.digest(p),q1.digest(load('task52-q3-v51-PROPOSED-v3.json')))
        self.assertIsNone(p['futureLiveBuild']);self.assertIsNone(p['ownerApproval']);self.assertFalse(p['historicalProposedCapOnly']['financialAuthorization'])
        self.assertEqual([s['slot'][1:] for s in p['slots']],[[a,b] for a,b in [('extension-repeated',2),('journey-04',2),('extension-partial',2),('journey-06',2),('journey-21',1)]])

    def test_post_freeze_contrasts_without_claiming_independence(self):
        data=load('task52-ordering-v51-holdouts-v1.json')
        self.assertFalse(data['independentHumanReviewed']);self.assertEqual(data['policySHA256'],q1.sha(Path(v51.__file__).read_bytes()))
        for c in data['cases']:
            r=v51.inspect_order(c['text'],reply(c))
            self.assertEqual(r['trustedGraph']is not None,c['category']!='unknown',(c['id'],r['issues']))

    def test_manifest_unknown_or_authorizing_identity_refuses(self):
        from scripts import task52_ordering_v51_identity as identity
        m=identity.verify();self.assertFalse(m['dispatchAuthorized'])
        for key,value in [('policy','unknown-policy'),('dispatchAuthorized',True)]:
            changed=deepcopy(m);changed[key]=value
            with self.assertRaises(ValueError):identity.verify_document(changed)
