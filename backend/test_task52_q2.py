"""Finite Q2 payload/schema/evidence checks. Never contacts providers."""
import copy
import json
import unittest
from pydantic import ValidationError
from backend.ai import Interpretation,parse_interpretation
from backend.journey import Duration,Journey,RequestedStop
from scripts import cloud_model52 as e
from scripts import task52_q1 as q1
from scripts import task52_q2 as q2


class ProviderCompatibilityTests(unittest.TestCase):
    def test_all_66_payloads_per_provider_construct_offline_with_same_prompt(self):
        with q1.offline():self.assertEqual(q2.static_payloads(),{'openai':66,'google':66,'anthropic':66})
        self.assertEqual(len(e.compact_examples()[0]),19)
        self.assertEqual(q2.old_proposal.messages('')[1:],e.messages('')[1:])
        self.assertEqual(len(q2.old_proposal.ADDITION.encode()),370)

    def test_frozen_proposals_and_full_expanded_equivalence(self):
        proposals=q2.proposals()
        for provider,p in proposals.items():
            self.assertEqual(p,json.loads((e.ROOT/f'docs/task52-q2-{provider}-proposal-v1.json').read_text()))
            self.assertFalse(p['activated']);self.assertFalse(p['remoteCompilationEstablished'])
            self.assertTrue(p['composedCanonicalContractEquivalent'])
            self.assertEqual(p['baseStats']['optionalProperties'],0)
            self.assertLessEqual(p['proposalStats']['expandedContainerDepth'],10)
        self.assertFalse(proposals['google']['wireAloneEquivalent'])
        a=proposals['anthropic'];self.assertTrue(a['wireAloneEquivalent'])
        self.assertEqual((a['baseStats']['unionNodes'],a['proposalStats']['unionNodes']),(15,14))
        self.assertEqual(a['baseStats']['expandedHash'],a['proposalStats']['expandedHash'])
        self.assertEqual((a['baseStats']['expandedUnionNodes'],a['proposalStats']['expandedUnionNodes']),(15,15))

    def test_required_nulls_types_enums_order_evidence_and_extra_fields_unchanged(self):
        canonical=q2.expanded(e.wire_schema('openai'))
        for provider,p in q2.proposals().items():
            proposed=p['schema']
            if provider=='google':proposed=q2.restored(proposed,'Canonical array bounds: ')
            else:proposed=q2.restored(proposed,'Validation constraints: ')
            self.assertEqual(q2.expanded(proposed),canonical)
        # Full-structure equality above includes each field, required set, null
        # branch, enum, object closure, bound, endpoint, duration and source.
        self.assertIs(canonical['additionalProperties'],False)
        self.assertIn('journey',canonical['required'])
        self.assertIn('anyOf',canonical['properties']['location'])

    def test_original_local_bounds_remain_enforced_not_provider_descriptions(self):
        for minutes in (-1,10081):
            with self.assertRaises(ValidationError):Duration(minutes=minutes,source='one minute')
        for text in ('','x'*501):
            with self.assertRaises(ValidationError):RequestedStop(source=text)
        with self.assertRaises(ValidationError):Journey(stops=[RequestedStop(source='coffee')]*33)
        for relation in ('invented','EXACT'):
            with self.assertRaises(ValidationError):Duration(minutes=20,relation=relation,source='20 minutes')
        with self.assertRaises(ValidationError):RequestedStop(source='coffee',unapproved=True)
        wire=Interpretation.model_validate({'activities':['coffee'],'location':None,'date':None,'budget_per_person':None,'preferences':[], 'journey':{'stops':[{'source':'coffee'}]}}).model_dump(mode='json')
        wire.pop('start_time');wire.pop('end_time');wire['journey'].pop('order_conflict')
        good=copy.deepcopy(wire);wire['journey']['stops'][0].pop('evidence')
        self.assertTrue(e.missing_properties(wire,e.schema()))
        with self.assertRaises(ValueError):parse_interpretation(json.dumps({**good,'unapproved':True}))

    def test_reference_expansion_rejects_unsupported_forms(self):
        for schema in ({'$ref':'https://example.invalid/schema'}, {'$ref':'#/$defs/A','$defs':{'A':{'$ref':'#/$defs/A'}}}, {'$defs':{'A':{'type':'string'}},'$ref':'#/$defs/A','description':'sibling'}):
            with self.assertRaises(ValueError):q2.expanded(schema)

    def test_exact_original_error_evidence_and_halt_unchanged(self):
        before=q1.private_hashes();r=q2.historical_evidence()
        self.assertEqual(r,json.loads((e.ROOT/'docs/task52-q2-evidence-v1.json').read_text()))
        self.assertEqual(len(r['errors']),3);self.assertTrue(r['IPRestrictionEvidence'])
        self.assertEqual(r['unchangedOpenAIV4PayloadHashesVerified'],3)
        self.assertTrue(r['journal']['persistentHalt']);self.assertEqual(r['journal']['attempts'],10)
        self.assertEqual(before,q1.private_hashes())
        for row in r['errors']:
            self.assertEqual(row['HTTP'],400);self.assertFalse(row['completeModelOutput'])
            if row['slot'][0]=='anthropic' or row['slot'][1]=='journey-02':
                self.assertTrue(row['currentPureBuilderReproducesPayloadHash'])
        self.assertFalse(r['originalGoogleEnvelope']['firstPayloadReexecuted'])

    def test_q1_stays_separate_and_original_paid_source_gate_still_refuses(self):
        q1.verify()
        with self.assertRaisesRegex(ValueError,'Reference source changed; review required: backend/journey.py'):
            e.corpus()
        replay=q1.replay()
        self.assertEqual(replay,json.loads((e.ROOT/'docs/task52-q1-openai-replay-v1.json').read_text()))
        self.assertEqual(replay['counts']['guardCandidateCompatible'],5)
        self.assertFalse(replay['paidDispatchAuthorized'])

    def test_exact_three_dispositions_without_dispatch_or_schema_activation(self):
        d=json.loads((e.ROOT/'docs/task52-q2-decisions-v1.json').read_text())
        self.assertEqual([(r['model'],r['disposition']) for r in d['providers']],
            [('gpt-6-luna','READY FOR Q3 PROPOSAL'),('gemini-3.8-flash','BLOCKED'),('claude-haiku-5-5','BLOCKED')])
        self.assertFalse(d['paidDispatchAuthorized']);self.assertFalse(d['persistentHaltCleared'])
        self.assertFalse(d['supportContactSubmitted']);self.assertFalse(d['ownerActionsPerformed'])
        self.assertEqual(d['frozenQ1']['unresolvedFields'],6)
        for provider,item in d['proposals'].items():
            self.assertFalse(item['activated'])
            self.assertEqual(q1.sha((e.ROOT/item['path']).read_bytes()),item['fileSHA256'])
        self.assertEqual(q1.sha((e.ROOT/'docs/task52-q2-evidence-v1.json').read_bytes()),d['errorEvidenceSHA256'])


if __name__=='__main__':unittest.main()
