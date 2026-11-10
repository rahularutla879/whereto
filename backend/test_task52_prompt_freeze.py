"""Prompt review is documentation evidence, never an execution grant."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import unittest
from scripts import cloud_model52 as original
from scripts import cloud_model52_proposal as old_prompt
from scripts import task52_prompt_v51 as proposed
from scripts import task52_ordering_v51 as policy
from scripts import task52_q1 as q1
from scripts.task52_ordering_v51_identity import verify

ROOT=Path(__file__).resolve().parents[1]
REVIEW_SHA='02b20af7fbabeb93d9d305a10c1327b8e97043b2b995f830fc88ab44f218f5da'
PROMPT_SHA='1741e5b5ae344fff0e4fff1fba2c4b45fd73b0b86baf73bdae35607f4b1919c9'
REVIEW_PATH=ROOT/'docs/task52-cloud-prompt-v51-REVIEWED-v1.json'


def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate review JSON key')
        result[key]=value
    return result


def load(name):return json.loads((ROOT/'docs'/name).read_text(),object_pairs_hook=unique)


def checked_review(raw=None):
    raw=REVIEW_PATH.read_bytes() if raw is None else raw
    if hashlib.sha256(raw).hexdigest()!=REVIEW_SHA:raise ValueError('Unknown or altered documentation review')
    return json.loads(raw,object_pairs_hook=unique)


class PromptFreezeTests(unittest.TestCase):
    def test_exact_prompt_and_file_bytes_are_distinct_pinned_identities(self):
        verify();r=checked_review();p=load('task52-cloud-prompt-v51-PROPOSED-v1.json')
        actual=(ROOT/r['parentProposal']['path']).read_bytes()
        self.assertEqual(q1.sha(actual),r['parentProposal']['fileSHA256'])
        messages=r['frozenRequestTemplate']['input']
        exact=json.dumps(messages,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')
        self.assertEqual(q1.sha(exact),PROMPT_SHA);self.assertEqual(r['promptHash'],PROMPT_SHA)
        self.assertEqual(messages,p['messagesWithEmptyFinalUser'])
        self.assertEqual(q1.sha(messages[0]['content'].encode()),r['hashSpecification']['systemUTF8SHA256'])
        self.assertEqual(r['frozenRequestTemplate'],p['fullOpenAIRequestTemplate'])
        self.assertEqual(q1.digest(r['frozenConfiguration']),r['configurationHash'])
        self.assertEqual(r['configurationHash'],'4239ddf4810ce65dfc5593c64cb011372abb1e350560ed848ceded06811d28a8')

    def test_all19_messages_and_remaining15_full_replies_unchanged(self):
        r=checked_review();messages=r['frozenRequestTemplate']['input'];base=old_prompt.messages('')
        self.assertEqual(len(messages),40);self.assertEqual(messages[-1],{'role':'user','content':''})
        self.assertEqual(len(r['exampleConsistencyReview']),19)
        for i in range(1,20):
            u,a=1+2*(i-1),2+2*(i-1)
            self.assertEqual(messages[u],base[u])
            new=json.loads(messages[a]['content']);old=json.loads(base[a]['content'])
            original.Interpretation.model_validate(new)
            if i not in (10,12,15,19):self.assertEqual(new,old)
            else:
                for reply in (new,old):reply['journey'].pop('order',None);reply['journey'].pop('ordering',None)
                self.assertEqual(new,old)
            audit=r['exampleConsistencyReview'][i-1]
            self.assertEqual(audit['userMessageHash'],q1.digest(messages[u]))
            self.assertEqual(audit['assistantMessageHash'],q1.digest(messages[a]))
            self.assertFalse(audit['independent24FieldCertification'])

    def test_four_owner_product_judgments_have_the_exact_approved_facts(self):
        r=checked_review();d=load('task52-v51-owner-example-decisions-v1.json')
        self.assertEqual(q1.sha((ROOT/r['ownerDecisionRecord']['path']).read_bytes()),r['ownerDecisionRecord']['fileSHA256'])
        self.assertEqual([a['index'] for a in d['examples']],[10,12,15,19]);self.assertIsNone(d['cryptographicSignature'])
        m=r['frozenRequestTemplate']['input']
        replies={i:original.Interpretation.model_validate(json.loads(m[2+2*(i-1)]['content'])) for i in (10,12,15,19)}
        for i,ai in replies.items():
            self.assertEqual([[e.before,e.after] for e in ai.journey.order],[[0,1]])
            self.assertTrue(all(s.requirement=='required' for s in ai.journey.stops) if i!=12 else ai.journey.stops[1].requirement=='optional')
        a=replies[10];self.assertEqual(a.activities,['Dinner','drinks']);self.assertEqual(a.location,'Jersey City');self.assertEqual(a.date_expressions,['tomorrow']);self.assertIsNone(a.date)
        a=replies[12];self.assertEqual(a.activities,['groceries','coffee']);self.assertEqual(a.journey.stops[0].requirement,'required')
        self.assertEqual(a.journey.endpoint.kind,'origin');self.assertEqual((a.journey.total_duration.minutes,a.journey.total_duration.relation),(45,'maximum'))
        source=m[1+2*(12-1)]['content'];snapshot=a.model_dump(mode='json');proof=policy.inspect_order(source,a)
        self.assertIsNotNone(proof['trustedGraph'])
        self.assertEqual(policy.selected_visit_projection(proof,[0])['requiredReachability'],[])
        self.assertEqual(policy.selected_visit_projection(proof,[0,1])['requiredReachability'],[[0,1]])
        self.assertEqual(snapshot,a.model_dump(mode='json'))
        a=replies[15];self.assertEqual(a.activities,['Zara','Nike']);self.assertEqual([s.kind for s in a.journey.stops],['brand','brand'])
        self.assertEqual((a.journey.shared_place.kind,a.journey.shared_place.stops),('same_mall',[0,1]))
        a=replies[19];self.assertEqual(a.activities,['bank','coffee']);self.assertEqual([(s.duration.minutes,s.duration.relation) for s in a.journey.stops],[(15,'exact'),(10,'exact')])

    def test_nonorder_system_and_conflicting_instruction_removal(self):
        r=checked_review();p=load('task52-cloud-prompt-v51-PROPOSED-v1.json');system=r['frozenRequestTemplate']['input'][0]['content']
        for bad in ('Never infer edges from list order','Only explicit ordering creates edges','Source text is not visit order.'):
            self.assertNotIn(bad,system)
        restored=system
        for edit in reversed(p['systemReplacements']):restored=restored.replace(edit['proposed'],edit['original'])
        self.assertEqual(restored,old_prompt.messages('')[0]['content'])
        self.assertEqual(r['consistencyReview']['contradictionsFound'],[])
        self.assertEqual(p,proposed.proposal())

    def test_unchanged_schema_runtime_corpus_and_policy_bindings(self):
        r=checked_review();b=r['bindings'];manifest=load('task52-q1-offline-manifest-v1.json')
        self.assertEqual(q1.digest(original.schema()),b['schemas']['strictEvaluationCanonical'])
        self.assertEqual(q1.digest(original.wire_schema('openai')),b['schemas']['openaiWireProjection'])
        self.assertEqual(b['schemas']['runtimePydantic'],manifest['schema']['canonicalPydanticSHA256'])
        for key,path in [('offlineManifestSHA256',b['offlineManifestPath']),('runtimeManifestSHA256',b['runtimeManifestPath']),('proposedRubricSHA256','docs/task52-q1-rubric-v3-v51-PROPOSED.json')]:
            self.assertEqual(q1.sha((ROOT/path).read_bytes()),b[key])
        self.assertEqual(b['corpusSHA256'],q1.sha((ROOT/b['corpusPath']).read_bytes()))
        self.assertEqual(b['policy'],policy.VERSION);self.assertEqual(b['scorer'],policy.SCORER)
        self.assertEqual(b['clock'],manifest['clock'])
        with self.assertRaisesRegex(ValueError,'Reference source changed; review required: backend/journey.py'):original.corpus()

    def test_five_slot_source_payload_rubric_compatibility_and_unused_status(self):
        r=checked_review();proposal=load('task52-q3-v51-PROPOSED-v3.json');rubric=load('task52-q1-rubric-v3-v51-PROPOSED.json')
        self.assertEqual(q1.sha((ROOT/'docs/task52-q3-v51-PROPOSED-v3.json').read_bytes()),r['Q3']['proposalFileSHA256'])
        cases={c['id']:c for c in rubric['cases']};original_cases={c['id']:c for c in load('task52-evaluation-corpus.json')['cases']}
        self.assertEqual([s['slot'][1:] for s in r['Q3']['slots']],[['extension-repeated',2],['journey-04',2],['extension-partial',2],['journey-06',2],['journey-21',1]])
        db=sqlite3.connect(f'file:{original.STATE}/journal.sqlite?mode=ro',uri=True)
        try:consumed=set(db.execute('select provider,case_id,repetition from attempts'))
        finally:db.close()
        hashes=proposed.payload_hashes(load('task52-cloud-prompt-v51-PROPOSED-v1.json'))
        for s,old in zip(r['Q3']['slots'],proposal['slots']):
            self.assertNotIn(tuple(s['slot']),consumed);id=s['slot'][1]
            self.assertEqual(s['source'],original_cases[id]['text']);self.assertEqual(s['sourceSHA256'],q1.sha(s['source'].encode()))
            self.assertEqual(s['proposedPayloadHash'],hashes[id]);self.assertEqual(s['rubricCaseDigest'],q1.digest(cases[id]))
            self.assertEqual(s['ordering'],old['ordering']);self.assertEqual(s['unresolvedFields'],[])
            self.assertTrue(s['specificationCompatible']);self.assertFalse(s['independentRubricApproval']);self.assertFalse(s['dispatchAuthorized'])
        self.assertEqual(cases['extension-repeated']['fields']['mandatory_order']['expected']['requiredReachability'],[[0,1],[0,2],[1,2]])
        self.assertEqual(cases['extension-partial']['fields']['mandatory_order']['expected']['requiredReachability'],[[0,1]])
        self.assertEqual(cases['journey-06']['fields']['mandatory_order']['expected']['conditionalReachability'],[[0,1]])
        self.assertEqual(cases['journey-21']['fields']['safe_disposition']['expected']['semanticClarification'],['contradictory order'])

    def test_document_approval_never_authorizes_execution_or_qualification(self):
        r=checked_review();d=load('task52-v51-owner-example-decisions-v1.json')
        self.assertFalse(r['authority']['paidDispatchAuthorized']);self.assertFalse(r['authority']['promptActivated']);self.assertIsNone(r['authority']['cryptographicGrant'])
        self.assertFalse(d['independentGoldReviewCompleted']);self.assertFalse(d['paidDispatchAuthorized']);self.assertIsNone(d['ownerFinancialApproval'])
        for key in ('futureLiveBuild','realJournalWriteAdapter','ownerFinancialApproval','realOperatorEnrollment','freshReadiness','operationPermission'):self.assertIsNone(r['Q3'][key])
        self.assertFalse(r['Q3']['oldQ4BuildsCanAuthorizeV51'])
        self.assertEqual(r['remainingReview']['independentGoldApprovals'],0);self.assertEqual(r['remainingReview']['independentHistoricalResponseApprovals'],0)
        from scripts.task52_q4a import Refused,live_dispatch
        with self.assertRaises(Refused):live_dispatch(r)

    def test_modified_review_and_duplicate_keys_refuse(self):
        r=checked_review()
        for key,value in [('identity','unknown-version'),('promptHash','0'*64)]:
            changed=deepcopy(r);changed[key]=value
            with self.assertRaises(ValueError):checked_review(json.dumps(changed).encode())
        changed=deepcopy(r);changed['authority']['paidDispatchAuthorized']=True
        with self.assertRaises(ValueError):checked_review(json.dumps(changed).encode())
        with self.assertRaises(ValueError):json.loads('{"approval":false,"approval":true}',object_pairs_hook=unique)
