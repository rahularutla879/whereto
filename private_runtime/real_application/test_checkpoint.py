"""Source-only ticket tests over real disposable OP/witness SQL and Redis."""
from tempfile import TemporaryDirectory
from unittest.mock import patch
import multiprocessing as mp,os,unittest
from datetime import timedelta
from hashlib import sha256
from backend.testing_clock import calendar_clock
from backend.test_provider_responses import TEXT,NOW
from backend.interpretation import InterpretationInput,ClarificationAnswers
from backend.test_real_planning import outing
from experiments.shared_state.contracts import Denied,SessionHandle
from . import test_native as harness
from .test_native import fixture,app_store,g
from backend.routes import AuthorizedStart
from .checkpoint import Checkpoint,Ticket,Record,Execution

OWNER='a'*64

class Tests(unittest.TestCase):
    setUp=harness.Tests.setUp
    def broker(self,*args,**kwargs):
        b=harness.Tests.broker(self,*args,**kwargs)
        if not hasattr(self,'pipes'):self.pipes=[]
        self.pipes.append(self.pipe);return b
    def calls(self):
        out=[]
        for pipe in self.pipes:
            while pipe.poll(.05):out.append(pipe.recv()[0])
        return out
    def pending(self):
        b=self.broker();token,result=b.interpret(InterpretationInput(text=TEXT,calendarTimezone='America/New_York'),execution={'startingLocation':AuthorizedStart(point={'id':'device-origin','coordinates':{'latitude':39.29,'longitude':-76.61}},explicitly_authorized=True,source='device')})
        self.assertIsNotNone(result.pending)
        cp=Checkpoint.capture(b,token,lambda:g.connect('issuer'),OWNER)
        return b,cp
    def test_source_handoff_clarification_and_terminal_planning_in_fresh_process(self):
        b,cp=self.pending();gross=self.s.snapshot()['gross'];expiry=cp.record.expires
        ctx=mp.get_context('spawn');q=ctx.Queue();p=ctx.Process(target=continue_source,args=(q,cp.ticket.handle.token,cp.ticket.revision));p.start()
        result=q.get(timeout=100);p.join(10);self.assertEqual(p.exitcode,0);self.assertNotIn('error',result)
        self.assertEqual(result['cards'],3);self.assertEqual(result['activities'],['coffee','museum']);self.assertEqual(result['expires'],expiry)
        self.assertEqual(result['inference'],0);self.assertEqual(result['gross_before'],gross);self.assertEqual(result['gross_after_answer'],gross)
        self.assertEqual(self.calls(),['/v1/responses/input_tokens','/v1/responses'])
        with self.assertRaises(Exception):cp.check()
        with self.assertRaises(Exception):Checkpoint.resume(self.broker(),cp.ticket,lambda:g.connect('issuer'),OWNER)
        with g.admin() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM provider_state.real_response_receipts').fetchone()[0],1)
            self.assertEqual(c.execute('SELECT count(*) FROM provider_state.native_turns').fetchone()[0],2)
            self.assertTrue(c.execute('SELECT revoked FROM provider_state.sessions WHERE id=%s',(self.s._hash(cp.ticket.handle.token,'session'),)).fetchone()[0])
            rows=c.execute('SELECT payload FROM provider_state.evidence').fetchall();self.assertNotIn('Fixture_',str(rows))
    def test_wrong_owner_revision_and_direct_broker_bypass(self):
        b,cp=self.pending();before=self.s.snapshot()['gross']
        with self.assertRaises(Exception):Checkpoint.resume(self.broker(),cp.ticket,lambda:g.connect('issuer'),'b'*64)
        with self.assertRaises(Exception):Checkpoint.resume(self.broker(),Ticket(cp.ticket.handle,99),lambda:g.connect('issuer'),OWNER)
        with self.assertRaises(Denied):b.answer(cp.token,ClarificationAnswers(date='2026-11-07'))
        cp.check();self.assertEqual(self.s.snapshot()['gross'],before)
    def test_redis_loss_never_recreates_source_or_inference(self):
        b,cp=self.pending();before=self.s.snapshot()['gross'];self.s.evidence.client.flushdb()
        with self.assertRaises(Exception):Checkpoint.resume(self.broker(),cp.ticket,lambda:g.connect('issuer'),OWNER)
        self.assertEqual(self.s.snapshot()['gross'],before);self.assertEqual(self.calls(),['/v1/responses/input_tokens','/v1/responses'])
    def test_reclaim_invalidates_old_fence_and_stale_revision(self):
        b,cp=self.pending()
        # Sanitized diagnostics: field paths only, never source/model values.
        from backend.planning_admission import AdmissionRegistry
        from experiments.shared_state.evidence_models import plain
        class Recorded:
            def interpret(self,text):return cp.record.raw.model_copy(deep=True)
        registry=AdmissionRegistry();out=registry.validate(cp.record.value,registry.new_scope(),1,Recorded(),now=cp.record.reference,execution=cp.record.execution.controls())
        paths=[]
        def differences(a,b,path='result'):
            if isinstance(a,dict) and isinstance(b,dict):
                for k in a.keys()|b.keys():differences(a.get(k),b.get(k),path+'.'+k)
            elif isinstance(a,list) and isinstance(b,list):
                if len(a)!=len(b):paths.append(path+'.length')
                for i,(x,y) in enumerate(zip(a,b)):differences(x,y,path+f'[{i}]')
            elif a!=b:paths.append(path)
        differences(plain(cp.record.result),plain(out.disposition.result))
        self.assertEqual(paths,['result.notes.length']) # Original out-of-action replay defect.
        print({'sourceReplayDifferencePaths':paths},flush=True)
        replacement=Checkpoint.resume(self.broker(),cp.ticket,lambda:g.connect('issuer'),OWNER)
        with self.assertRaises(Exception):cp.check()
        replacement.invoke('answer',ClarificationAnswers(date='2026-11-07'))
        with self.assertRaises(Exception):Checkpoint.resume(self.broker(),cp.ticket,lambda:g.connect('issuer'),OWNER)
        self.assertEqual(replacement.record.expires,cp.record.expires)
    def test_interrupted_turn_is_not_replayed_after_restart(self):
        b,cp=self.pending();self.s._call('native_begin',**self.s._lease(cp.lease));before=self.s.snapshot()['gross']
        with self.assertRaises(Exception):Checkpoint.resume(self.broker(),cp.ticket,lambda:g.connect('issuer'),OWNER)
        self.assertEqual(self.s.snapshot()['gross'],before)
    def test_expired_checkpoint_and_altered_ciphertext_refuse_without_new_calls(self):
        b,cp=self.pending();before=self.s.snapshot()['gross'];m=self.s.meta(cp.lease)
        path=self.s.evidence.path('real',m['anchor']['epoch'],m['session']);blob=self.s.evidence.get(path)
        self.s.evidence.client.set(path,blob[:-1]+bytes([blob[-1]^1]))
        with self.assertRaises(Exception):Checkpoint.resume(self.broker(),cp.ticket,lambda:g.connect('issuer'),OWNER)
        with g.admin() as c:c.execute("UPDATE provider_state.sessions SET expires=clock_timestamp()-interval '1 millisecond' WHERE id=%s",(m['session'],))
        with self.assertRaises(Exception):Checkpoint.resume(self.broker(),cp.ticket,lambda:g.connect('issuer'),OWNER)
        self.assertEqual(self.s.snapshot()['gross'],before);self.assertEqual(self.calls(),['/v1/responses/input_tokens','/v1/responses'])

    def test_competing_independent_workers_cannot_both_consume_turn(self):
        b,cp=self.pending();before=self.s.snapshot()['gross'];ctx=mp.get_context('spawn');go=ctx.Event()
        queues=[ctx.Queue(),ctx.Queue()];workers=[ctx.Process(target=compete,args=(queues[i],go,cp.ticket.handle.token,cp.ticket.revision)) for i in range(2)]
        for p in workers:p.start()
        stages=[q.get(timeout=60) for q in queues];go.set()
        outcomes=[q.get(timeout=60) for q in queues]
        for p in workers:p.join(10);self.assertEqual(p.exitcode,0)
        self.assertEqual(outcomes.count('answered'),1);self.assertEqual(outcomes.count('refused'),1)
        self.assertEqual(self.s.snapshot()['gross'],before);self.assertEqual(self.calls(),['/v1/responses/input_tokens','/v1/responses'])
        with g.admin() as c:self.assertEqual(c.execute('SELECT count(*) FROM provider_state.native_turns').fetchone()[0],1)
    def test_only_completed_inference_enrollment_is_exposed_to_issuer(self):
        from psycopg.errors import InsufficientPrivilege
        from uuid import uuid4
        b,cp=self.pending();sid=self.s._hash(cp.lease.session.token,'session')
        with self.assertRaises(InsufficientPrivilege):
            with g.connect('issuer') as c:c.execute('SELECT provider_state.native_enroll(%s,%s)',(sid,cp.record.inference))
        with self.assertRaises(Exception):
            with g.connect('issuer') as c:c.execute('SELECT provider_state.real_source_enroll(%s,%s,%s,%s,%s)',(sid,cp.record.inference,OWNER,cp.record.build,str(uuid4())))
        with self.assertRaises(InsufficientPrivilege):
            with g.connect('runtime') as c:c.execute('DELETE FROM provider_state.real_source_owners')
        cp.check()

    def test_source_record_rejects_google_origin_and_unknown_graph(self):
        b,cp=self.pending();raw=cp.record.model_dump(mode='json');raw['venues']=[]
        with self.assertRaises(ValueError):Record.model_validate(raw)
        origin=outing().startingLocation.model_copy(update={'source':'suggested'})
        with self.assertRaises(ValueError):Execution(startingLocation=origin)
        self.assertNotIn('last',Record.model_fields);self.assertNotIn('budget',Record.model_fields)
        invalid=cp.record.model_copy(update={'revision':21,'answers':[ClarificationAnswers(date='2026-11-07')]*20})
        with self.assertRaises(ValueError):cp._publish(invalid,cp.blob)
        cp.check()


def continue_source(queue,token,revision):
    t=harness.Tests()
    try:
        with calendar_clock(NOW),TemporaryDirectory(prefix='real-source-worker-') as tmp,patch.dict(os.environ,{'K_SERVICE':'offline-real-native-fixture','NODE_ENV':'production','WHERETO_ENV':'production'}):
            t.s=app_store();t.temp=tmp;b=t.broker();before=t.s.snapshot()['gross']
            cp=Checkpoint.resume(b,Ticket(SessionHandle(token),revision),lambda:g.connect('issuer'),OWNER)
            cp.invoke('answer',ClarificationAnswers(date='2026-11-07'));after=t.s.snapshot()['gross'];expiry=cp.record.expires
            result=cp.invoke('plan')
            queue.put(dict(cards=len(result.provisionalPlans),activities=[v.activity for v in result.provisionalPlans[0].candidate.venues],expires=expiry,inference=t.model.calls,gross_before=before,gross_after_answer=after))
    except BaseException as e:
        queue.put({'error':type(e).__name__+':'+str(e)});raise
    finally:t.doCleanups()


def compete(queue,go,token,revision):
    from .native import Broker,Issuer,Inference
    cp=None
    try:
        with calendar_clock(NOW):
            s=app_store()
            def no_send(*args):raise AssertionError('Clarification must not contact providers')
            issuer=Issuer(lambda:g.connect('issuer'),g.ROOT);model=Inference(s,lambda:g.connect('issuer'),g.ROOT,None,no_send)
            b=Broker(s,issuer,model,no_send,now=NOW)
            try:cp=Checkpoint.resume(b,Ticket(SessionHandle(token),revision),lambda:g.connect('issuer'),OWNER)
            except Exception:pass
            queue.put('ready' if cp else 'refused')
            if not go.wait(60):raise AssertionError('Competing worker not released')
            if cp is None:queue.put('refused');return
            try:cp.invoke('answer',ClarificationAnswers(date='2026-11-07'))
            except Exception:queue.put('refused')
            else:queue.put('answered')
    except BaseException:
        queue.put('failed');raise
