"""Separately reviewed owner-policy expectations; frozen V1-V4 stay unchanged."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
import unittest
from pathlib import Path

from backend.ai import Interpretation
from scripts import task52_ordering_v5 as v5
from scripts import cloud_model52_ordering_v4 as v4

ROOT=Path(__file__).resolve().parents[1]


def reply(c,edges=None):
    return Interpretation(activities=c['stops'],budget_per_person=None,date=None,location=c.get('location'),preferences=[],
        journey={'stops':[{'source':s,'kind':c.get('kinds',['activity']*len(c['stops']))[i],
                          'requirement':'optional' if i in c.get('optional',[]) else 'required',
                          'evidence':c['text'] if i in c.get('optional',[]) else ''} for i,s in enumerate(c['stops'])],
                 'order':[{'before':a,'after':b,'source':c['text']} for a,b in (c['expectedEdges'] if edges is None else edges)],
                 'endpoint':c.get('endpoint'),'total_duration':c.get('duration')})


class V5OrderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases=json.loads((ROOT/'docs/task52-ordering-v5-cases-v1.json').read_text())['cases']
        cls.by={c['id']:c for c in cls.cases}

    def test_predeclared_positive_and_unknown_source_expectations(self):
        for c in self.cases:
            with self.subTest(case=c['id']):
                ai=reply(c);before=ai.model_dump(mode='json');r=v5.inspect_order(c['text'],ai)
                if c['category'] in ('unknown','contradictory'):
                    self.assertIsNone(r['trustedGraph']);self.assertEqual(r['source']['category'],c['category'])
                else:
                    self.assertIsNotNone(r['trustedGraph'],r['issues'])
                    self.assertEqual(r['requiredClosure'],v5.closure(c['expectedEdges'],len(c['stops'])))
                    self.assertEqual(r['source']['requirements'],['optional' if i in c['optional'] else 'required' for i in range(len(c['stops']))])
                self.assertEqual(before,ai.model_dump(mode='json'));self.assertFalse(r['planningAuthorized'])

    def test_every_unsupported_edge_is_rejected_without_projection(self):
        probes=0
        for c in self.cases:
            if c['category'] in ('unknown','contradictory'):continue
            allowed=v5.closure(c['expectedEdges'],len(c['stops']))
            for a in range(len(c['stops'])):
                for b in range(len(c['stops'])):
                    if a==b or [a,b] in allowed:continue
                    probes+=1;r=v5.inspect_order(c['text'],reply(c,c['expectedEdges']+[[a,b]]))
                    self.assertIsNone(r['trustedGraph'],(c['id'],a,b));self.assertIsNone(r['normalization'])
        self.assertGreater(probes,20)

    def test_missing_order_relationships_and_no_redundant_transitive_edge_requirement(self):
        c=self.by['comma-three'];ai=reply(c)
        r=v5.inspect_order(c['text'],ai)
        self.assertIn([0,2],r['impliedRelationships']);self.assertNotIn([0,2],r['trustedGraph'])
        for edge in c['expectedEdges']:
            got=v5.inspect_order(c['text'],reply(c,[e for e in c['expectedEdges'] if e!=edge]))
            self.assertIn('missing_source_required_relationship',got['issues'])
        got=v5.inspect_order(c['text'],reply(c,c['expectedEdges']+[[0,2]]));self.assertIsNotNone(got['trustedGraph'])

    def test_evidence_owned_occurrences_direction_and_old_provenance_failure(self):
        c=self.by['first-then'];ai=reply(c);ai.journey.order[0].source='first, then'
        r=v5.inspect_order(c['text'],ai)
        self.assertIsNone(r['trustedGraph']);self.assertIn('unsupported_direction_scope_or_occurrence',r['issues'])
        c=self.by['mixed-repeat'];ai=reply(c);ai.journey.order[0].source='Coffee, museum, then';ai.journey.order[1].source='museum, then coffee'
        old=v4.inspect_order(c['text'],ai);new=v5.inspect_order(c['text'],ai)
        self.assertIsNone(old['trustedGraph']);self.assertIsNotNone(new['trustedGraph'])
        self.assertEqual(new['source']['proofs'][0]['rule'],'default_list');self.assertEqual(new['source']['proofs'][1]['rule'],'explicit_then')
        ai.journey.order[0].source='then coffee';self.assertIsNone(v5.inspect_order(c['text'],ai)['trustedGraph'])

    def test_optional_relationships_do_not_make_visits_required_or_flexible_optional(self):
        c=self.by['optional-middle'];r=v5.inspect_order(c['text'],reply(c))
        self.assertEqual(r['mandatoryRequiredVisitClosure'],[[0,2]])
        self.assertEqual(r['conditionalClosure'],[[0,1],[1,2]])
        ai=reply(c);ai.journey.stops[1].requirement='required'
        self.assertIn('source_optionality_mismatch',v5.inspect_order(c['text'],ai)['issues'])
        c=self.by['partial'];ai=reply(c);ai.journey.stops[2].requirement='optional'
        self.assertIn('source_optionality_mismatch',v5.inspect_order(c['text'],ai)['issues'])
        c=self.by['optional-first'];ai=reply(c);ai.journey.stops[0].evidence='coffee'
        self.assertIn('optional_evidence_not_owned',v5.inspect_order(c['text'],ai)['issues'])

    def test_no_merged_repeated_occurrences_or_endpoint_as_visit(self):
        c=self.by['mixed-repeat'];ai=reply(c);ai.journey.stops.pop();ai.activities.pop();ai.journey.order=[]
        self.assertIsNone(v5.inspect_order(c['text'],ai)['trustedGraph'])
        c={'text':'Visit museum, then return to the starting point.','stops':['museum','return to the starting point'],'expectedEdges':[[0,1]]}
        self.assertIsNone(v5.inspect_order(c['text'],reply(c))['trustedGraph'])
        c=self.by['return-budget'];ai=reply(c);before=ai.model_dump(mode='json')
        self.assertIsNotNone(v5.inspect_order(c['text'],ai)['trustedGraph']);self.assertEqual(before,ai.model_dump(mode='json'))

    def test_source_proof_identity_and_frozen_evidence_record(self):
        c=self.by['comma-three'];r=v5.inspect_order(c['text'],reply(c));p=r['source']['proofs'][0]
        self.assertEqual(p['source'],c['text'][slice(*p['span'])]);self.assertEqual(p['source_sha256'],v5.q1.sha(c['text'].encode()))
        v=v5.Evidence(0,1,'default_list',(0,14),None,'Coffee, museum',v5.q1.sha(c['text'].encode()))
        with self.assertRaises(FrozenInstanceError):v.before=1
        r=v5.inspect_order('x'*8001,reply(c));self.assertIsNone(r['trustedGraph'])

    def test_post_freeze_same_agent_cases_without_relabeling_as_independent(self):
        held=json.loads((ROOT/'docs/task52-ordering-v5-holdouts-v1.json').read_text())
        self.assertEqual(held['policySHA256'],v5.q1.sha(Path(v5.__file__).read_bytes()));self.assertFalse(held['independentHumanReviewed'])
        for c in held['cases']:
            r=v5.inspect_order(c['text'],reply(c))
            self.assertEqual(r['trustedGraph']is not None,c['category']!='unknown',(c['id'],r['issues']))

    def test_all66_rubric_amendment_preserves_nonorder_original_gaps_and_sources(self):
        from scripts import task52_ordering_v5_review as review
        new=review.amendment();old=json.loads((ROOT/'docs/task52-q1-rubric-v1.json').read_text())
        self.assertEqual(v5.q1.digest(new),v5.q1.digest(json.loads((ROOT/'docs/task52-q1-rubric-v2-owner-list-PROPOSED.json').read_text())))
        self.assertEqual(new['caseCount'],66);self.assertEqual(new['counts'],{'mandatory_graph_change':18,'conditional_graph_change':1,'conditional_amendment_awaiting_owner':1,'language_order_awaiting_owner':1,'graph_unchanged':45})
        gaps=0
        for a,b in zip(old['cases'],new['cases']):
            self.assertEqual((a['id'],a['sourceText'],a['sourceSHA256'],a['originalReferenceDigest']),(b['id'],b['sourceText'],b['sourceSHA256'],b['originalReferenceDigest']))
            for k,f in a['fields'].items():
                if k not in ('mandatory_order','unordered_flexible','source_provenance') or f['applicability']=='awaiting_review':self.assertEqual(f,b['fields'][k])
                if f['applicability']=='awaiting_review':gaps+=1
            self.assertFalse(b['independentReviewComplete']);self.assertFalse(b['orderingV5Amendment']['individualCaseApproved'])
            if b['orderingV5Amendment']['changedFields']:
                for k,v in a['fields']['source_provenance']['expected'].items():
                    if k!='edgeEvidence':self.assertEqual(v,b['fields']['source_provenance']['expected'][k])
        self.assertEqual(gaps,6)

    def test_five_slot_amendment_supersedes_future_use_without_changing_old_plan(self):
        from scripts import task52_ordering_v5_review as review
        proposal=review.proposal(review.amendment());old=json.loads((ROOT/'docs/task52-q3-openai-proposal-v1.json').read_text())
        self.assertEqual(v5.q1.digest(proposal),v5.q1.digest(json.loads((ROOT/'docs/task52-q3-openai-v5-PROPOSED-v2.json').read_text())))
        self.assertEqual([s['slot'] for s in proposal['slots']],[s['slot'] for s in old['slots']])
        self.assertTrue(all(s['futureV5PayloadHash']is None and not s['currentlyAdmissible'] for s in proposal['slots']))
        self.assertIsNone(proposal['futurePromptVersion']);self.assertEqual(proposal['maxProposedAdditionalReservationNanodollars'],12500000)
        from scripts.task52_q4c_identity import verify_build
        self.assertFalse(verify_build(full=True)['liveDispatchAvailable'])

    def test_legacy_normalization_cannot_certify_lost_v5_requirements(self):
        from scripts import task52_ordering_v5_review as review
        from backend.journey import validate_journey
        c=self.by['and-two'];raw=reply(c);effective=raw.model_copy(deep=True)
        validate_journey(c['text'],effective)
        mapped=review.mapping(raw,effective,v5.inspect_order(c['text'],raw))
        self.assertTrue(mapped['occurrenceMappingKnown']);self.assertFalse(mapped['sourceRequiredOrderPreserved'])
        self.assertEqual(mapped['effectiveGraph'],[])

    def test_historical_replay_retains_original_errors_and_separates_new_policy(self):
        from scripts import task52_ordering_v5_review as review
        before=v5.q1.private_hashes();replay=review.replay()
        self.assertEqual(v5.q1.digest(replay),v5.q1.digest(json.loads((ROOT/'docs/task52-ordering-v5-historical-replay-v1.json').read_text())))
        cases={c['slot'][1]:c for c in replay['openai']};repeated=cases['extension-repeated'];old=repeated['originalQ1']
        self.assertEqual(repeated['originalRowState'],'recorded_halted');self.assertEqual(old['raw']['rubricFinding'],'incorrect_unsupported_order')
        self.assertEqual(old['proposedGuarded']['disposition'],'blocked_by_independent_ordering')
        self.assertIsNotNone(repeated['V5']['trustedGraph']);self.assertIsNone(repeated['newFullIndependentCorrectness'])
        self.assertIsNone(cases['journey-07']['V5']['trustedGraph'])
        self.assertIn('missing_source_required_relationship',cases['journey-01']['V5']['issues'])
        self.assertIn('missing_source_required_relationship',cases['ordinary-dinner']['V5']['issues'])
        self.assertEqual(before,v5.q1.private_hashes());self.assertEqual(len(replay['qwen']),27)

    def test_post_freeze_unsupported_edge_probes(self):
        held=json.loads((ROOT/'docs/task52-ordering-v5-holdouts-v1.json').read_text())['cases']
        probes=0
        for c in held:
            if c['category']=='unknown':continue
            allowed=v5.closure(c['expectedEdges'],len(c['stops']))
            for a in range(len(c['stops'])):
                for b in range(len(c['stops'])):
                    if a==b or [a,b]in allowed:continue
                    probes+=1
                    self.assertIsNone(v5.inspect_order(c['text'],reply(c,c['expectedEdges']+[[a,b]]))['trustedGraph'])
        self.assertEqual(probes,12)

    def test_version_manifest_is_offline_exact_and_fail_closed(self):
        from scripts import task52_ordering_v5_identity as identity
        manifest=identity.verify()
        self.assertFalse(manifest['dispatchAuthorized']);self.assertEqual(manifest['policy'],v5.VERSION)
        bad=deepcopy(manifest);bad['policy']='unknown-policy'
        with self.assertRaises(ValueError):identity.verify_document(bad)
        bad=deepcopy(manifest);bad['sources'].pop('scripts/task52_ordering_v5.py')
        with self.assertRaises(ValueError):identity.verify_document(bad)
        bad=deepcopy(manifest);bad['dispatchAuthorized']=True
        with self.assertRaises(ValueError):identity.verify_document(bad)
