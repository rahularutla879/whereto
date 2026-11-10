"""V5.1 integration with disposable FICTIONAL signers/state/responses only."""
from copy import deepcopy
from datetime import timedelta
import json
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from backend import test_task52_q4c as prior
from backend.test_task52_q4a import fake_responses as v4_fake_responses
from scripts import task52_q4a as base
from scripts import task52_q4c_auth as original_auth
from scripts import task52_q4c_protocol as original_protocol
from scripts import task52_v51_eval_auth as a
from scripts import task52_v51_eval_protocol as p
from scripts import task52_v51_eval_identity as identity
from scripts.task52_v51_eval_scoring import assess

NOW=prior.NOW


def fake_responses():
    # Edit authored fake fixtures ONLY; never a recorded provider response.
    values=v4_fake_responses()
    for index in (0,3):
        value=json.loads(values[index]['output'][0]['content'][0]['text'])
        edge={'before':0,'after':1,'source':identity.plan()['slots'][index]['source']}
        value['journey']['order'].insert(0,edge);value['journey']['ordering']='constrained'
        values[index]['output'][0]['content'][0]['text']=json.dumps(value)
    return values


class SyntheticKeys(prior.SyntheticKeys):
    # Reuse disposable-key creation, Trust format, roles and signer helper.
    # New signed envelope cannot be verified as the historical V4 domain.
    def packet(self,role,data,fixture,*,now=NOW,change=None,signer=None,namespace=None):
        e={'version':a.VERSION,'audience':a.AUDIENCE,'purpose':a.PURPOSE,'role':role,
           'principal':'q4c-'+self.name(role),'namespace':'whereto.task52b.'+a.ROLES[role],
           'scope':fixture.scope,'journal':fixture.journal_hash,'nonce':prior.uuid.uuid4().hex+prior.uuid.uuid4().hex,
           'issuedAt':p.utc(now),'expiresAt':p.utc(now+timedelta(hours=1)),
           'trustHash':self.trust.document_hash,'revocationHash':self.trust.revocation_hash,
           'binding':identity.binding(),'data':deepcopy(data)}
        if change:change(e)
        return self.sign_bytes(a.canonical(e),role,signer=signer,namespace=namespace)


_context={**vars(prior),'a':a,'p':p,'identity':identity,'SyntheticKeys':SyntheticKeys,
          'fake_responses':fake_responses,'base':SimpleNamespace(plan=identity.plan,FakeTransport=base.FakeTransport,
                                                               Refused=base.Refused,live_dispatch=base.live_dispatch)}
for _name in ('scope','execute','review','crash_child','competitor'):
    _context[_name]=a.bind_function(getattr(prior,_name),_context)
scope,execute,review=(_context[n] for n in ('scope','execute','review'))


def _reused_security_class():
    methods={}
    for name,value in vars(prior.Q4CTests).items():
        if isinstance(value,classmethod):methods[name]=classmethod(a.bind_function(value.__func__,_context))
        elif callable(value) and hasattr(value,'__code__'):methods[name]=a.bind_function(value,_context)
    return type('VerifiedQ4CSecurityForV51',(unittest.TestCase,),methods)


def mutate(response,change):
    result=deepcopy(response);value=json.loads(result['output'][0]['content'][0]['text']);change(value)
    result['output'][0]['content'][0]['text']=json.dumps(value);return result


class V51IntegrationTests(_reused_security_class()):
    def reach(self,index):
        f,e,s=self.fixture();previous=a.ZERO
        for i in range(index):
            o=e.simulate_one(execute(self.keys,f,s,i,previous),base.FakeTransport(self.responses[i]),NOW)
            self.assertEqual(o['data']['assessment']['raw']['mechanicalFailures'],[])
            e.record_review(review(self.keys,f,o),NOW);previous=e.state()[1][-1]['hash']
        return f,e,s,previous

    def test_fixed_dependency_binding_reuses_core_and_preserves_original_globals(self):
        self.assertIs(p.Engine.state.__code__,original_protocol.Engine.state.__code__)
        self.assertIs(p.Engine.simulate_one.__code__,original_protocol.Engine.simulate_one.__code__)
        self.assertIs(a.canonical,original_auth.canonical);self.assertIs(a.Trust,original_auth.Trust)
        self.assertIsNot(p.REGISTRY,original_protocol.REGISTRY)
        from scripts.task52_q4a_scoring import assess as old_assess
        self.assertIs(original_protocol.assess,old_assess)
        self.assertIs(original_protocol.base.plan,base.plan)
        self.assertIs(original_auth.plan,base.plan)
        self.assertEqual(original_protocol.VERSION,'52b-q4c-signed-real-schema-OFFLINE-v1')
        self.assertEqual(base.plan()['identity'],'52b-q3-openai-b2-v4-guarded-PROPOSED-v1')
        f,_,_=self.fixture(active=False)
        with self.assertRaises(a.Denied):original_protocol.Engine(f.directory,f.trust)

    def test_cross_version_signatures_and_plain_owner_document_cannot_authorize(self):
        f,_,_=self.fixture(active=False)
        new=self.keys.packet('owner',a.owner_data(),f)
        self.assertFalse(a.verify(new,'owner',f.trust,NOW).execution_authorized)
        with self.assertRaises(a.Denied):original_auth.verify(new,'owner',f.trust,NOW)
        old=prior.SyntheticKeys.packet(self.keys,'owner',a.owner_data(),f)
        with self.assertRaises(a.Denied):a.verify(old,'owner',f.trust,NOW)
        product=prior.q1.ROOT/'docs/task52-v51-five-case-owner-review-v1.json'
        with self.assertRaises(a.Denied):a.verify(json.loads(product.read_text()),'owner',f.trust,NOW)

    def test_five_raw_legacy_guarded_axes_and_known_legacy_order_loss(self):
        results=[assess(s['slot'],r) for s,r in zip(identity.plan()['slots'],self.responses)]
        self.assertTrue(all(r['structuredValid'] and not r['raw']['extractionFailures'] and not r['raw']['mechanicalFailures'] for r in results))
        self.assertTrue(all(r['raw']['fullyCorrectIndependent']is None and not r['planningAuthorized'] for r in results))
        self.assertEqual(results[3]['guarded']['disposition'],'blocked_by_legacy_effective_order_loss')
        self.assertTrue(results[3]['mappingKnown']);self.assertFalse(results[3]['legacy']['requiredOrderPreserved'])
        self.assertEqual(results[4]['guarded']['disposition'],'appropriate_clarification')
        self.assertFalse(results[4]['legacy']['accepted'])

    def test_review_disagreement_wrong_signer_and_critical_raw_order_error(self):
        # Preserve the original security test's review negatives; V5.1 now
        # requires0→1, so use a reversed edge rather than V4's old0→1 probe.
        f,e,s=self.fixture();o=e.simulate_one(execute(self.keys,f,s),base.FakeTransport(self.responses[0]),NOW)
        with self.assertRaises(a.Denied):e.record_review(review(self.keys,f,o,signer='owner'),NOW)
        e.record_review(review(self.keys,f,o,disagree=True),NOW)
        with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,1),base.FakeTransport(self.responses[1]),NOW)
        f,e,s=self.fixture();bad=mutate(self.responses[0],lambda v:v['journey']['order'].append({'before':2,'after':0,'source':identity.plan()['slots'][0]['source']}))
        o=e.simulate_one(execute(self.keys,f,s),base.FakeTransport(bad),NOW)
        self.assertIn('unsupported_missing_or_unproven_order',o['data']['assessment']['raw']['extractionFailures'])
        with self.assertRaises(a.Denied):e.record_review(review(self.keys,f,o),NOW)
        with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,1),base.FakeTransport(self.responses[1]),NOW)

    def test_missing_order_repeated_merge_return_duration_endpoint_and_inventions_halt(self):
        changes={
            'missing_order':lambda v:v['journey']['order'].pop(0),
            'merged_occurrence':lambda v:(v['activities'].pop(),v['journey']['stops'].pop(),v['journey'].update(order=[])),
            'missing_return':lambda v:v['journey'].update(endpoint=None),
            'missing_duration':lambda v:v['journey'].update(total_duration=None),
            'changed_relation':lambda v:v['journey']['total_duration'].update(relation='under'),
            'wrong_endpoint':lambda v:v['journey']['endpoint'].update(kind='home'),
            'borrowed_endpoint_quote':lambda v:v['journey']['endpoint'].update(source='Coffee'),
            'borrowed_time_quote':lambda v:v['journey']['total_duration'].update(source='tomorrow'),
            'invented_budget':lambda v:v.update(budget_per_person=20,currency='USD'),
            'inappropriate_clarification':lambda v:v['journey'].update(clarification='museum'),
        }
        for name,change in changes.items():
            with self.subTest(failure=name):
                f,e,s=self.fixture();bad=mutate(self.responses[0],change)
                o=e.simulate_one(execute(self.keys,f,s),base.FakeTransport(bad),NOW)
                self.assertTrue(o['data']['assessment']['raw']['mechanicalFailures'])
                self.assertEqual(e.state()[1][-1]['kind'],'HALT')
                with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,1),base.FakeTransport(self.responses[1]),NOW)
                self.assertEqual(len(list(f.directory.glob('fake-send-*'))),1)
                f.close()

    def test_wrong_named_place_partial_order_optionality_and_contradiction_halt(self):
        probes=[(1,lambda v:(v['activities'].__setitem__(0,'Another College'),v['journey']['stops'][0].update(source='Another College'))),
                (2,lambda v:v['journey']['order'].append({'before':1,'after':2,'source':identity.plan()['slots'][2]['source']})),
                (2,lambda v:v['journey']['stops'][2].update(requirement='optional',evidence='coffee whenever convenient')),
                (3,lambda v:v['journey']['stops'][1].update(requirement='required')),
                (3,lambda v:v['journey'].update(order=[])),
                (4,lambda v:v['journey'].update(clarification=None)),
                (4,lambda v:v['journey'].update(clarification='before'))]
        for index,change in probes:
            f,e,s,previous=self.reach(index)
            o=e.simulate_one(execute(self.keys,f,s,index,previous),base.FakeTransport(mutate(self.responses[index],change)),NOW)
            self.assertTrue(o['data']['assessment']['raw']['mechanicalFailures']);self.assertEqual(e.state()[1][-1]['kind'],'HALT')
            with self.assertRaises(a.Denied):e.record_review(review(self.keys,f,o),NOW)
            if index<4:
                with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,index+1),base.FakeTransport(self.responses[index+1]),NOW)
            f.close()

    def test_unresolved_occurrence_mapping_stops_without_claiming_raw_hallucination(self):
        from scripts import task52_v51_eval_scoring as scoring
        original=scoring.interpret_request
        def changed(*args,**kw):
            result=original(*args,**kw);result.interpretation.journey.stops[0].source='unresolved effective occurrence';return result
        f,e,s=self.fixture()
        with patch.object(scoring,'interpret_request',side_effect=changed):
            o=e.simulate_one(execute(self.keys,f,s),base.FakeTransport(self.responses[0]),NOW)
            self.assertEqual(o['data']['assessment']['raw']['extractionFailures'],[])
            self.assertIn('unresolved_effective_occurrence_mapping',o['data']['assessment']['systemFailures'])
            self.assertEqual(e.state()[1][-1]['kind'],'HALT')
            with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,1),base.FakeTransport(self.responses[1]),NOW)

    def test_provider_shape_truncation_caps_and_unknown_tools_halt(self):
        bad=[]
        for field,value in [('model','other'),('status','incomplete')]:
            r=deepcopy(self.responses[0]);r[field]=value;bad.append(r)
        r=deepcopy(self.responses[0]);r['output'][0]['content'][0]['text']='{';bad.append(r)
        bad.append(mutate(self.responses[0],lambda v:v.update(booking_reference='invented')))
        for field,value in [('input_tokens',12001),('output_tokens',2001),('input_tokens',True),('input_tokens',-1)]:
            r=deepcopy(self.responses[0]);r['usage'][field]=value;bad.append(r)
        r=deepcopy(self.responses[0]);r['output'].append({'type':'function_call','name':'unexpected'});bad.append(r)
        r=deepcopy(self.responses[0]);r['output'][0]['content'].append({'type':'unknown'});bad.append(r)
        for r in bad:
            scored=assess(identity.plan()['slots'][0]['slot'],r)
            self.assertFalse(scored['structuredValid']);self.assertTrue(scored['raw']['mechanicalFailures'])
        f,e,s=self.fixture();o=e.simulate_one(execute(self.keys,f,s),base.FakeTransport(bad[-2]),NOW)
        self.assertTrue(o['data']['assessment']['raw']['mechanicalFailures'])
        self.assertEqual(e.state()[1][-1]['kind'],'HALT')
        with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,1),base.FakeTransport(self.responses[1]),NOW)
