"""New purpose, only disposable synthetic signers/state/fake transports."""
from copy import deepcopy
from datetime import timedelta,date
from types import SimpleNamespace
import json
import multiprocessing
import unittest
from unittest.mock import patch
from backend import test_task52_v51_evaluator as prior
from scripts import task52_diag_auth as a
from scripts import task52_diag_protocol as p
from scripts import task52_diag_identity as identity
from scripts import task52_diag_scoring as scoring
from scripts import task52_v51_eval_auth as old_auth
from scripts import task52_q4d as q4d

NOW=prior.NOW
fake_responses=prior.fake_responses
mutate=prior.mutate


class SyntheticKeys(prior.SyntheticKeys):
    def packet(self,role,data,fixture,*,now=NOW,change=None,signer=None,namespace=None):
        e={'version':a.VERSION,'audience':a.AUDIENCE,'purpose':a.PURPOSE,'role':role,
           'principal':'q4c-'+self.name(role),'namespace':'whereto.task52b.'+a.ROLES[role],
           'scope':fixture.scope,'journal':fixture.journal_hash,'nonce':prior.prior.uuid.uuid4().hex+prior.prior.uuid.uuid4().hex,
           'issuedAt':p.utc(now),'expiresAt':p.utc(now+timedelta(hours=1)),
           'trustHash':self.trust.document_hash,'revocationHash':self.trust.revocation_hash,
           'binding':identity.binding(),'data':deepcopy(data)}
        if change:change(e)
        return self.sign_bytes(a.canonical(e),role,signer=signer,namespace=namespace)


def review(keys,f,o,*,disagree=False,**kw):
    d=o['data']['assessment']['diagnostic']
    data={'operationID':o['operation'],'outcomeHash':o['hash'],'responseHash':o['data']['responseHash'],
          'judgments':{k:'agree' for k in identity.plan()['slots'][0]['Q1FieldExpectations']},
          'decision':'disagree' if disagree else 'agree',
          'diagnostic':{'purpose':identity.PURPOSE,'defectHash':d['allowlistedDefect'],
             'systemIncompatible':d['systemIncompatible']is True,'planningAuthorized':False}}
    return keys.packet('review',data,f,**kw)


_context={**prior._context,**vars(prior),'a':a,'p':p,'identity':identity,'SyntheticKeys':SyntheticKeys,
          'assess':scoring.assess,'review':review,
          'base':SimpleNamespace(plan=identity.plan,FakeTransport=prior.base.FakeTransport,
                               Refused=prior.base.Refused,live_dispatch=prior.base.live_dispatch)}
for _name in ('scope','execute','crash_child','competitor'):
    _context[_name]=a.bind_function(prior._context[_name],_context)
scope,execute=(_context[n] for n in ('scope','execute'))


def inherited():
    methods={}
    # Reuse all 29 security/semantic/crash test algorithms with the fixed new
    # dependencies; do not change frozen test classes or module globals.
    for cls in reversed(prior.V51IntegrationTests.__mro__[:-2]):
        for name,value in vars(cls).items():
            if isinstance(value,classmethod):methods[name]=classmethod(a.bind_function(value.__func__,_context))
            elif callable(value) and hasattr(value,'__code__'):methods[name]=a.bind_function(value,_context)
    return type('InheritedDiagnosticSecurity',(unittest.TestCase,),methods)


def crash_before_loss_review(directory,trust,permission,response):
    with patch('socket.socket.connect',side_effect=AssertionError('No provider/network')):
        p.Engine(directory,trust).simulate_one(permission,p.FakeTransport(response),NOW,crash_at='after_outcome')


class DiagnosticTests(inherited()):
    def reach(self,index):
        f,e,s=self.fixture();previous=a.ZERO
        for i in range(index):
            o=e.simulate_one(execute(self.keys,f,s,i,previous),p.FakeTransport(self.responses[i]),NOW)
            self.assertEqual(o['data']['assessment']['raw']['mechanicalFailures'],[])
            e.record_review(review(self.keys,f,o),NOW);previous=e.state()[1][-1]['hash']
        return f,e,s,previous

    def test_new_purpose_and_explicit_owner_exception_not_old_grants(self):
        f,_,_=self.fixture(active=False)
        packet=self.keys.packet('owner',a.owner_data(),f)
        with self.assertRaises(a.Denied):old_auth.verify(packet,'owner',f.trust,NOW)
        old=prior.SyntheticKeys.packet(self.keys,'owner',old_auth.owner_data(),f)
        with self.assertRaises(a.Denied):a.verify(old,'owner',f.trust,NOW)
        for key in ('diagnosticPurpose','allowlistedDefectHash'):
            bad=a.owner_data();bad.pop(key)
            with self.assertRaises(a.Denied):a.verify(self.keys.packet('owner',bad,f),'owner',f.trust,NOW)
        with self.assertRaises(prior.base.Refused):p.live_dispatch(packet)
        self.assertFalse(a.verify(packet,'owner',f.trust,NOW).execution_authorized)

    def test_all_five_after_explicit_synthetic_loss_review_never_planning(self):
        f,e,s,previous=self.reach(3)
        o=e.simulate_one(execute(self.keys,f,s,3,previous),p.FakeTransport(self.responses[3]),NOW)
        result=o['data']['assessment'];d=result['diagnostic']
        self.assertEqual(result['raw']['extractionFailures'],[])
        self.assertIsNone(result['raw']['fullyCorrectIndependent'])
        self.assertEqual(result['guarded']['disposition'],q4d.LOSS)
        self.assertTrue(d['systemIncompatible']);self.assertTrue(d['mechanicallyEligibleAfterReview'])
        self.assertFalse(d['actualContinuationAuthorized']);self.assertFalse(d['planningAuthorized'])
        with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,4),p.FakeTransport(self.responses[4]),NOW)
        for bad in ('missing','false_compatible','wrong_signer'):
            packet=review(self.keys,f,o,signer='owner' if bad=='wrong_signer' else None)
            if bad!='wrong_signer':
                data=a.parse(packet['envelope'].encode())['data']
                if bad=='missing':data.pop('diagnostic')
                else:data['diagnostic'].update(systemIncompatible=False,defectHash=None)
                packet=self.keys.packet('review',data,f)
            with self.assertRaises(a.Denied):e.record_review(packet,NOW)
        self.assertEqual(len(e.state()[0]),14)
        e.record_review(review(self.keys,f,o),NOW);previous=e.state()[1][-1]['hash']
        final=e.simulate_one(execute(self.keys,f,s,4,previous),p.FakeTransport(self.responses[4]),NOW)
        self.assertEqual(final['data']['assessment']['guarded']['disposition'],'appropriate_clarification')
        e.record_review(review(self.keys,f,final),NOW)
        self.assertEqual(len(e.state()[0]),15);self.assertEqual(e.state()[3],12500000)
        self.assertFalse(any(f['kind']=='HALT' for f in e.state()[1]))
        self.assertEqual(e.state()[0][9][4],'recorded_halted')
        with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,4,previous),p.FakeTransport(self.responses[4]),NOW)

    def test_only_allowlisted_delta_and_calendar_pending_context_intact(self):
        original=scoring.interpret_request
        for change in ('extra_preference','extra_edge','context_date','pending_revision'):
            def changed(*args,**kwargs):
                result=original(*args,**kwargs)
                if change=='extra_preference':result.interpretation.preferences.append('unknown effective preference')
                elif change=='extra_edge':
                    from backend.journey import OrderConstraint
                    result.interpretation.journey.order=[OrderConstraint(before=1,after=0,source='Buy groceries and maybe stop for coffee.')]
                elif change=='context_date':result.context.date=date(2026,11,12)
                else:result.pending.text+=' changed'
                return result
            with self.subTest(change=change),patch.object(scoring,'interpret_request',side_effect=changed):
                r=scoring.assess(identity.plan()['slots'][3]['slot'],self.responses[3])
                self.assertFalse(r['diagnostic']['mechanicallyEligibleAfterReview'])
                self.assertEqual(r['raw']['extractionFailures'],[])
                self.assertTrue(r['raw']['mechanicalFailures'])
                self.assertFalse(r['planningAuthorized'])

    def test_reproducible_unknown_additional_mutation_halts_signed_run(self):
        from scripts import task52_v51_eval_scoring as parent
        original=parent.interpret_request
        def changed(*args,**kwargs):
            result=original(*args,**kwargs)
            if args[0].text==identity.plan()['slots'][3]['source']:
                result.interpretation.preferences.append('unexpected effective mutation')
            return result
        f,e,s,previous=self.reach(3)
        with patch.object(scoring,'interpret_request',side_effect=changed),patch.object(parent,'interpret_request',side_effect=changed):
            o=e.simulate_one(execute(self.keys,f,s,3,previous),p.FakeTransport(self.responses[3]),NOW)
            self.assertIn('unallowlisted_legacy_difference',o['data']['assessment']['systemFailures'])
            self.assertEqual(e.state()[1][-1]['kind'],'HALT')
            with self.assertRaises(a.Denied):e.record_review(review(self.keys,f,o),NOW)
            with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,4),p.FakeTransport(self.responses[4]),NOW)

    def test_loss_with_wrong_raw_source_optional_endpoint_never_exception(self):
        for change in (lambda v:v['journey']['stops'][1].update(requirement='required'),
                       lambda v:v['journey']['order'][0].update(source='maybe'),
                       lambda v:v['journey'].update(endpoint={'kind':'origin','source':'Buy groceries'}),
                       lambda v:v['journey'].update(order=[])):
            r=scoring.assess(identity.plan()['slots'][3]['slot'],mutate(self.responses[3],change))
            self.assertFalse(r['diagnostic']['mechanicallyEligibleAfterReview'])
            self.assertTrue(r['raw']['extractionFailures']);self.assertFalse(r['planningAuthorized'])

    def test_after_outcome_process_exit_still_needs_loss_review(self):
        f,e,s,previous=self.reach(3)
        process=multiprocessing.get_context('fork').Process(target=crash_before_loss_review,
            args=(f.directory,f.trust,execute(self.keys,f,s,3,previous),self.responses[3]))
        process.start();process.join(30)
        self.assertFalse(process.is_alive());self.assertEqual(process.exitcode,73)
        e=p.Engine(f.directory,f.trust);o=e.state()[1][-1]
        self.assertEqual(o['kind'],'OUTCOME');self.assertEqual(len(e.state()[0]),14)
        with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,4),p.FakeTransport(self.responses[4]),NOW)
        e.record_review(review(self.keys,f,o),NOW);previous=e.state()[1][-1]['hash']
        e.simulate_one(execute(self.keys,f,s,4,previous),p.FakeTransport(self.responses[4]),NOW)
        self.assertEqual(len(e.state()[0]),15)

    def test_q4d_still_has_its_strict_gate_and_frozen_purpose(self):
        self.assertEqual(q4d.identity.verify()['identity'],'52b-q4d-v51-journal-bridge-OFFLINE-v1')
        f,_,_=self.fixture(active=False)
        with self.assertRaises(a.Denied):q4d.protocol.Engine(f.directory,f.trust)
        self.assertEqual(q4d.FictionalContinuation._loss([{'kind':'OUTCOME','data':{'assessment':{'guarded':{'disposition':q4d.LOSS}}}}]),True)

    def test_known_loss_review_disagreement_is_terminal(self):
        f,e,s,previous=self.reach(3)
        o=e.simulate_one(execute(self.keys,f,s,3,previous),p.FakeTransport(self.responses[3]),NOW)
        e.record_review(review(self.keys,f,o,disagree=True),NOW)
        self.assertEqual(e.state()[1][-1]['kind'],'HALT')
        self.assertEqual(e.state()[3],10000000)
        with self.assertRaises(a.Denied):e.simulate_one(execute(self.keys,f,s,4),p.FakeTransport(self.responses[4]),NOW)

    def test_fixed_dependency_binding_reuses_core_and_preserves_original_globals(self):
        from scripts import task52_q4c_protocol as original_protocol
        from scripts import task52_q4c_auth as original_auth
        from scripts import task52_v51_eval_protocol as v51
        from scripts import task52_v51_eval_identity as v51_identity
        from scripts.task52_q4a_scoring import assess as original_assess
        self.assertIs(p.Engine.state.__code__,original_protocol.Engine.state.__code__)
        self.assertIs(p.Engine.simulate_one.__code__,original_protocol.Engine.simulate_one.__code__)
        self.assertIs(a.canonical,original_auth.canonical);self.assertIs(a.Trust,original_auth.Trust)
        self.assertIsNot(p.REGISTRY,original_protocol.REGISTRY);self.assertIsNot(p.REGISTRY,v51.REGISTRY)
        self.assertIs(original_protocol.assess,original_assess)
        self.assertIs(original_protocol.base.plan,prior.base.plan)
        self.assertIs(original_auth.plan,prior.base.plan)
        self.assertIs(v51._context['base'].plan,v51_identity.plan)
        self.assertIs(p._context['base'].plan,identity.plan)
        self.assertEqual(original_protocol.VERSION,'52b-q4c-signed-real-schema-OFFLINE-v1')
        self.assertEqual(prior.base.plan()['identity'],'52b-q3-openai-b2-v4-guarded-PROPOSED-v1')
        f,_,_=self.fixture(active=False)
        for engine in (original_protocol.Engine,v51.Engine):
            with self.assertRaises(a.Denied):engine(f.directory,f.trust)

    def test_mutation_and_pending_copy_comparisons_are_type_exact(self):
        self.assertEqual(scoring.delta({'a':False},{'a':0}),['/a'])
        self.assertEqual(scoring.delta({'a':1},{'a':1.0}),['/a'])
        self.assertEqual(scoring.delta({'a':[False]},{'a':[0]}),['/a'])
        from scripts import task52_v51_eval_scoring as parent
        original=parent.interpret_request
        def changed(*args,**kw):
            result=original(*args,**kw)
            result.interpretation.journey.order_conflict=0
            return result
        with patch.object(scoring,'interpret_request',side_effect=changed),patch.object(parent,'interpret_request',side_effect=changed):
            r=scoring.assess(identity.plan()['slots'][3]['slot'],self.responses[3])
            self.assertFalse(r['diagnostic']['mechanicallyEligibleAfterReview'])
            self.assertIn('unallowlisted_legacy_difference',r['systemFailures'])
            self.assertEqual(r['raw']['extractionFailures'],[])
