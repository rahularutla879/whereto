"""Independent-process native continuation using actual planners and fake providers."""
from contextlib import ExitStack
from datetime import datetime,timezone
from pathlib import Path
from time import monotonic
from copy import deepcopy
import json,multiprocessing as mp,os,unittest
from unittest.mock import patch
from psycopg.types.json import Jsonb
from experiments.shared_state import test_application_grants as g
from experiments.shared_state import test_bridge as b,test_store as core,test_financial as f,test_evidence as e
from experiments.shared_state.application_grants import GrantService
from experiments.shared_state.native_sessions import *
from experiments.shared_state.native_graph import Graph


def fixture():
    g.fixture()
    with core.admin() as c:
        c.execute('SET LOCAL ROLE whereto_synthetic_owner');c.execute(Path(__file__).with_name('native_sessions.sql').read_text(),prepare=False)
    with g.witness_admin() as c:
        c.execute('SET LOCAL ROLE whereto_synthetic_owner');c.execute(Path(__file__).with_name('native_witness.sql').read_text(),prepare=False)


def store():
    w=NativeWitness(lambda:g.witness_connection('synthetic_witness_service',os.environ['SYNTHETIC_WITNESS_SERVICE_PASSWORD']),lambda:g.witness_connection('synthetic_witness_reader',os.environ['SYNTHETIC_WITNESS_READER_PASSWORD']))
    return NativeStore(service=GrantService(w,g.issuer_connection),issuer_connection=g.issuer_connection,evidence=e.cache(),key=core.KEY,password=os.environ['SYNTHETIC_WORKER_PASSWORD'],limits=f.LIMITS)


class Harness:
    fake=b.BridgeTests.fake
    def __init__(self,s):self.s=s;self.calls=[];self.model=b.Model()
    def make(self,model=None):
        broker=g.ApplicationGrantTests.make(self,model or self.model)
        broker.__class__=NativeBroker
        broker._Broker__issuer=NativeIssuer(g.issuer_connection,f.ROOT,broker._Broker__issuer._records)
        self.broker=broker;return broker


class CodecTests(unittest.TestCase):
    def test_no_executable_or_unknown_object_deserialization(self):
        with self.assertRaises(Denied):Graph(1000).dump({'callback':lambda:None})
        with self.assertRaises(Denied):Graph(1000).load({'root':{'ref':0},'nodes':[{'native':'InjectedClass','fields':{}}]})
        with self.assertRaises(Denied):Graph(1000).load({'root':{'ref':0},'nodes':[{'model':'os.system','fields':{}}]})
    def test_alias_sets_tuple_keys_and_nonfinite_refusal(self):
        from backend.provider_budget import ProviderBudget
        b=ProviderBudget();o=b.outing();v={'a':o,'b':o,'seen':{(1,'x')}}
        graph=Graph(1000);restored=Graph(1000).load(graph.dump(v));self.assertIs(restored['a'],restored['b']);self.assertEqual(restored['seen'],v['seen'])
        with self.assertRaises(Denied):Graph(1000).dump(float('nan'))

    def test_actual_ordinary_context_roundtrip_with_provider_attribution_urls(self):
        from backend.test_real_planning import RealPlanningTests
        from backend.option_sessions import option_sessions
        case=RealPlanningTests('test_complete_pipeline_three_real_provisional_options_and_source_labels');case.setUp()
        try:
            result=case.run_plan(budget=10,dinner=True);context,_=option_sessions.get(result.optionsToken)
            graph=Graph(int(__import__('time').time()*1000));restored=graph.load(graph.dump({'result':result,'context':context}))
            self.assertEqual(restored['context']['request'],context['request']);self.assertEqual(restored['result'],result)
        finally:case.doCleanups()


class NativeTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.object(b,'fixture',fixture));self.enterContext(patch.object(b,'store',store));b.BridgeTests.setUp(self)
    fake=b.BridgeTests.fake
    initial=b.BridgeTests.initial
    advanced_fixture=b.BridgeTests.advanced_fixture
    make=Harness.make
    def test_pending_resume_no_inference_and_stale_worker(self):
        self.model.data['date']=None;token,result=self.initial(text='Coffee and museum in Baltimore')
        session=Session.capture(self.broker,token,g.issuer_connection);ticket=session.ticket;before=self.s.snapshot()['gross']
        other=Harness(store());next_broker=other.make();next_broker.now=b.NOW+__import__('datetime').timedelta(days=1)
        restored=Session.resume(next_broker,ticket,g.issuer_connection);self.assertEqual(next_broker.now,b.NOW)
        from backend.interpretation import ClarificationAnswers
        result=restored.invoke('answer',ClarificationAnswers(date='2026-11-07'))
        self.assertIsNotNone(result.request);self.assertEqual(other.model.calls,0);self.assertEqual(other.s.snapshot()['gross'],before)
        with self.assertRaises(Denied):session.invoke('plan')
        with self.assertRaises(Denied):session.revoke()
        with self.assertRaises(Denied):self.s.revise(session.lease.session,session.lease.revision,Kind.ACTION,ProviderAction(purpose='ordinary',sourceDigest='a'*64,interpretationDigest='b'*64,requestRevision=1))
        again=Session.resume(Harness(store()).make(),restored.ticket,g.issuer_connection);self.assertEqual(again.broker._source(again.token).result,result)
    def test_ordinary_options_details_and_reusable_selected_receipt(self):
        token,_=self.initial();session=Session.capture(self.broker,token,g.issuer_connection)
        planned=session.invoke('plan');self.assertTrue(planned.optionsToken)
        from backend.saved_plans import receipts,SaveRequest
        issued=receipts.issue(planned);receipt_ticket=session.receipt_ticket(issued)
        ids=[x.candidate.id for x in issued.provisionalPlans+issued.plans];request=SaveRequest(receipt=issued.saveReceipt,accessToken=issued.saveAccessToken,candidateIds=ids,selectedId=ids[0])
        selected=session.select(request);self.assertEqual(session.select(request),selected)
        self.assertEqual(SelectedReceipt.select(store(),receipt_ticket,g.issuer_connection,request),selected)
        ticket=session.ticket;other=Harness(store());restored=Session.resume(other.make(),ticket,g.issuer_connection)
        self.assertEqual(restored.select(request),selected);self.assertEqual(restored.select(request),selected)
        from backend.option_sessions import option_sessions
        ctx,_=option_sessions.get(restored.broker._source(restored.token).options);before=set(ctx['seen']);self.assertTrue(before)
        result=restored.invoke('more');self.assertTrue(before<=ctx['seen']);self.assertEqual(other.model.calls,0)
        with self.assertRaises(Exception):restored.select(request.model_copy(update={'accessToken':'X'*43}))
    def test_advanced_resolver_router_and_history(self):
        from backend.advanced_planning import AdvancedInput
        from backend.test_advanced_routing import start
        source,_,token=self.advanced_fixture();session=Session.capture(self.broker,source,g.issuer_connection)
        # Source fixture supplies its own fake venue/router implementation.
        result=session.invoke('advance',AdvancedInput(token=token,date='2026-11-07',destination='New York',startingLocation=start()))
        self.assertTrue(result.options);old=session.broker._source(source).advanced_identity
        seen=set(old.seen);checked=set(old.router.checked);ticket=session.ticket
        other=Harness(store());broker=other.make();broker._Broker__fake=self.broker._Broker__fake
        restored=Session.resume(broker,ticket,g.issuer_connection);new=broker._source(restored.token).advanced_identity
        self.assertEqual(new.seen,seen);self.assertEqual(new.router.checked,checked);self.assertIs(new.router.resolver,new.resolver)
        self.assertEqual(new.outing.usage(),old.outing.usage());self.assertEqual(other.model.calls,0)
        again=restored.invoke('advance',AdvancedInput(token=new.token,action='different',startingLocation=start()))
        self.assertIn(again.status,('results','no_results','unsupported'));self.assertTrue(seen<=new.seen)
        from datetime import timedelta
        for key,leg in list(new.router._evidence.items()):
            if leg.status!='same_location':new.router._evidence[key]=leg.model_copy(update={'observed_at':datetime.now(timezone.utc)-timedelta(seconds=301)})
        restored.persist()
        with self.assertRaises(Denied):Session.resume(Harness(store()).make(),restored.ticket,g.issuer_connection)
    def test_busy_missing_evidence_wrong_key_build_and_epoch_refuse(self):
        token,_=self.initial();session=Session.capture(self.broker,token,g.issuer_connection)
        ticket=session.ticket;self.s._call('native_begin',**self.s._lease(session.lease))
        with self.assertRaises(Denied):Session.resume(Harness(store()).make(),ticket,g.issuer_connection)
        # No paid operation is retried after the interrupted durable turn.
        self.assertEqual(self.s.snapshot()['attempts'],1)


    def test_encrypted_loss_corruption_wrong_key_revision_and_revoke(self):
        for fault in ('missing','corrupt','key','revision','revoked','expired','build'):
            with self.subTest(fault=fault):
                fixture();self.s=store();self.broker=self.make(self.model);token,_=self.initial()
                session=Session.capture(self.broker,token,g.issuer_connection);ticket=session.ticket;before=self.s.snapshot()['gross'];other=Harness(store())
                if fault=='missing':self.s.evidence.client.flushdb()
                if fault=='corrupt':
                    m=self.s.meta(session.lease);key=self.s.evidence.path('synthetic',e.EPOCH,m['session']);blob=self.s.evidence.get(key);self.s.evidence.client.set(key,b'x'+blob[1:])
                if fault=='key':other.s.evidence.keys=e.Keys('k1',{'k1':b'0'*32})
                if fault=='revision':ticket=Ticket(ticket.handle,ticket.revision+1)
                if fault=='revoked':session.revoke()
                if fault=='expired':
                    with core.admin() as c:c.execute("UPDATE synthetic_state.sessions SET expires=clock_timestamp()-interval '1 second' WHERE id=%s",(self.s._hash(ticket.handle.token,'session'),))
                from experiments.shared_state import native_identity
                with patch.object(native_identity,'PIN','0'*64 if fault=='build' else native_identity.PIN),self.assertRaises(Denied):Session.resume(other.make(),ticket,g.issuer_connection)
                self.assertEqual(self.s.snapshot()['gross'],before);self.assertEqual(other.calls,[]);self.assertEqual(other.model.calls,0)
    def test_key_rotation_keeps_expiry_and_edit_durably_revokes(self):
        token,_=self.initial();session=Session.capture(self.broker,token,g.issuer_connection);deadline=self.s.meta(session.lease)['anchor']['expires_ms']
        self.s.evidence.keys=e.Keys('k2',{'k1':e.KEY,'k2':b'2'*32});session.persist()
        self.assertEqual(self.s.meta(session.lease)['anchor']['expires_ms'],deadline)
        other=Harness(store());other.s.evidence.keys=e.Keys('k2',{'k2':b'2'*32});restored=Session.resume(other.make(),session.ticket,g.issuer_connection)
        from backend.interpretation import InterpretationInput
        with self.assertRaises(Denied):other.broker.replace(restored.token,InterpretationInput(text='Changed request'))
        with self.assertRaises(Denied):Session.resume(Harness(store()).make(),restored.ticket,g.issuer_connection)
        self.assertEqual(other.model.calls,0)
    def test_details_membership_and_attempts_survive_handoff(self):
        from backend.venue_details import details_sessions
        token,_=self.initial();session=Session.capture(self.broker,token,g.issuer_connection);session.invoke('plan')
        native=self.broker._source(token);identity=next(iter(details_sessions.entries[native.details][1]))
        session.invoke('contact',identity);other=Harness(store());restored=Session.resume(other.make(),session.ticket,g.issuer_connection)
        before=other.s.snapshot()['gross'];from backend.places import DiscoveryError
        with self.assertRaises(DiscoveryError):restored.invoke('contact',identity)
        self.assertEqual(other.calls,[]);self.assertEqual(other.s.snapshot()['gross'],before)
    def test_runtime_cannot_write_native_history_or_commit(self):
        import psycopg
        for statement in ["DELETE FROM synthetic_state.native_turns","UPDATE synthetic_state.native_commits SET commitment='x'","SELECT synthetic_state.native_commit('{}','{}')","SELECT synthetic_state.app_protocol('snapshot','{}','synthetic','a',NULL)"]:
            with self.assertRaises(psycopg.Error),psycopg.connect(**self.s._connection) as c:c.execute(statement)
    def test_refresh_across_workers_uses_current_access_and_durable_consumption(self):
        from backend.saved_refresh import RefreshRequest
        doc={'dataMode':'real','selectedId':'chosen','itineraries':[{'candidateId':'chosen','stops':[{'reference':'Synthetic_one'},{'reference':'Synthetic_two'}]}]}
        request=RefreshRequest(accessToken='A'*43,candidateId='chosen',refreshId=__import__('uuid').uuid4())
        with patch('backend.saved_plans.reopen',return_value=doc),patch('backend.saved_refresh.reopen',return_value=doc):
            result=refresh_saved(self.broker,request);self.assertTrue(all(v['status']=='refreshed' for v in result['venues'].values()))
            other=Harness(store());duplicate=refresh_saved(other.make(),request);self.assertTrue(all(v['status']=='already_attempted' for v in duplicate['venues'].values()));self.assertEqual(other.calls,[])
        from backend.saved_plans import PersistenceError
        with patch('backend.saved_plans.reopen',side_effect=PersistenceError(404)),self.assertRaises(PersistenceError):refresh_saved(Harness(store()).make(),request)
    def test_optional_flexible_return_state_and_corrupt_history_refuse(self):
        from backend.advanced_planning import AdvancedInput
        from backend.test_advanced_routing import start
        for index in (5,7,9):
            with self.subTest(index=index):
                fixture();self.s=store();self.calls=[]
                source,_,token=self.advanced_fixture(index);session=Session.capture(self.broker,source,g.issuer_connection)
                result=session.invoke('advance',AdvancedInput(token=token,date='2026-11-07',destination='New York',startingLocation=start()));self.assertTrue(result.options)
                other=Harness(store());restored=Session.resume(other.make(),session.ticket,g.issuer_connection);advanced=other.broker._source(restored.token).advanced_identity
                self.assertEqual(advanced.journey,session.broker._Broker__sources[source].advanced_identity.journey)
                if index==5:self.assertEqual(advanced.journey.stops[1].requirement,'optional')
                if index==9:self.assertTrue(all(o.ending=='origin' for o in result.options))
                advanced.seen.add(('forged-history',));graph=Graph(restored.evidence.clock());record=graph.dump(advanced)
                with self.assertRaises(Denied):Graph(restored.evidence.clock()).load(record)


def advanced_fake(calls):
    from backend.test_advanced_planning import IntegrationTests
    from backend.test_advanced_routing import AdvancedRoutingTests,COLLEGE,COFFEE,GROCERY,BANK,PHARMACY,STATION
    from types import SimpleNamespace
    search=IntegrationTests('test_named_roundtrip_dto_and_receipt');search.searches=[];search.records=[COLLEGE,COFFEE,GROCERY,BANK,PHARMACY,STATION]
    route=SimpleNamespace(calls=[],values={},route_error=None,partial=False)
    def fake(v):
        calls.append(deepcopy(v))
        if v['operation']=='matrix':return AdvancedRoutingTests.matrix(route,v['body'])
        if v['operation']=='details':return {'id':v['url'].rsplit('/',1)[-1]}
        return search.search(v['body'])
    return fake


def child(job,wire,queue):
    # Trusted test IPC carries JSON scalars only; never pickle application evidence.
    try:
        from backend.testing_clock import calendar_clock
        from backend import advanced_planning
        with ExitStack() as stack:
            stack.enter_context(calendar_clock(b.NOW))
            stack.enter_context(patch('requests.sessions.Session.send',side_effect=AssertionError('External HTTP forbidden')))
            clock=stack.enter_context(patch('backend.advanced_planning.datetime',wraps=datetime));clock.now.side_effect=lambda tz=None:b.NOW.astimezone(tz or timezone.utc)
            data=json.loads(wire);ticket=Ticket(SessionHandle(data['token']),data['revision']);worker=Harness(store());broker=worker.make()
            before=worker.s.snapshot()['gross']
            if job=='select':
                from backend.saved_plans import SaveRequest
                result=SelectedReceipt.select(worker.s,ticket,g.issuer_connection,SaveRequest.model_validate(data['request']))
                output={'selected':result.selectedId,'noCharge':before==worker.s.snapshot()['gross']}
            else:
                if job=='advanced':broker._Broker__fake=advanced_fake(worker.calls)
                session=Session.resume(broker,ticket,g.issuer_connection)
                assert not worker.calls and worker.model.calls==0
                output={'restoredWithoutCharge':before==worker.s.snapshot()['gross']}
                if job=='die':
                    worker.s._call('native_begin',**worker.s._lease(session.lease));os._exit(42)
                elif job=='pending':
                    from backend.interpretation import ClarificationAnswers
                    result=session.invoke('answer',ClarificationAnswers(date='2026-11-07'));output['ready']=result.request is not None
                elif job=='plan':
                    result=session.invoke('plan')
                    from backend.saved_plans import receipts
                    issued=receipts.issue(result);receipt=session.receipt_ticket(issued)
                    ids=[x.candidate.id for x in issued.provisionalPlans+issued.plans]
                    output.update(receiptToken=receipt.handle.token,receiptRevision=receipt.revision,request=dict(receipt=issued.saveReceipt,accessToken=issued.saveAccessToken,candidateIds=ids,selectedId=ids[0]))
                elif job=='more':
                    from backend.option_sessions import option_sessions
                    context,_=option_sessions.get(broker._source(session.token).options);seen=set(context['seen'])
                    session.invoke('more');output['historyRetained']=seen<=context['seen']
                elif job=='advanced':
                    from backend.advanced_planning import AdvancedInput
                    advanced=broker._source(session.token).advanced_identity;seen=set(advanced.seen);checked=set(advanced.router.checked)
                    result=session.invoke('advance',AdvancedInput(token=advanced.token,action='different',startingLocation=advanced.origin))
                    output.update(historyRetained=seen<=advanced.seen,routesRetained=checked<=advanced.router.checked,status=result.status)
                output.update(token=session.ticket.handle.token,revision=session.ticket.revision,modelCalls=worker.model.calls)
            queue.put(json.dumps({'ok':output}))
    except BaseException as error:
        import traceback
        traceback.print_exc();queue.put(json.dumps({'error':type(error).__name__,'code':getattr(error,'code',None)}))


def held_worker(wire,ready,release,result):
    # An actually concurrent stale worker, not two objects in one interpreter.
    try:
        with patch('requests.sessions.Session.send',side_effect=AssertionError('External HTTP forbidden')):
            data=json.loads(wire);worker=Harness(store());session=Session.resume(worker.make(),Ticket(SessionHandle(data['token']),data['revision']),g.issuer_connection)
            ready.set()
            if not release.wait(60):raise AssertionError('Competing worker did not finish')
            try:session.revoke()
            except Denied:result.put('stale_refused')
            else:result.put('UNSAFE')
            assert worker.calls==[] and worker.model.calls==0
    except BaseException:
        import traceback
        traceback.print_exc();result.put('error');ready.set()


class ProcessTests(unittest.TestCase):
    setUp=NativeTests.setUp
    make=NativeTests.make
    fake=NativeTests.fake
    initial=NativeTests.initial
    advanced_fixture=NativeTests.advanced_fixture
    def run_child(self,job,ticket,**more):
        ctx=mp.get_context('spawn');q=ctx.Queue();wire=json.dumps(dict(token=ticket.handle.token,revision=ticket.revision,**more))
        p=ctx.Process(target=child,args=(job,wire,q));p.start();p.join(180)
        if p.is_alive():p.terminate();p.join();self.fail('Synthetic child timed out')
        self.assertEqual(p.exitcode,0);result=json.loads(q.get(timeout=3));self.assertIn('ok',result);return result['ok']
    def test_process_pending_plan_options_and_readonly_receipt(self):
        self.model.data['date']=None;token,_=self.initial(text='Coffee and museum in Baltimore')
        session=Session.capture(self.broker,token,g.issuer_connection)
        data=self.run_child('pending',session.ticket);self.assertTrue(data['ready']);self.assertTrue(data['restoredWithoutCharge']);self.assertEqual(data['modelCalls'],0)
        with self.assertRaises(Denied):session.invoke('plan')
        data=self.run_child('plan',Ticket(SessionHandle(data['token']),data['revision']))
        self.assertEqual(data['modelCalls'],0);self.assertTrue(data['restoredWithoutCharge'])
        request=data['request'];receipt=Ticket(SessionHandle(data['receiptToken']),data['receiptRevision'])
        more=self.run_child('more',Ticket(SessionHandle(data['token']),data['revision']));self.assertTrue(more['historyRetained']);self.assertEqual(more['modelCalls'],0)
        first=self.run_child('select',receipt,request=request);second=self.run_child('select',receipt,request=request)
        self.assertEqual(first['selected'],request['selectedId']);self.assertEqual(first,second);self.assertTrue(first['noCharge'])
    def test_process_advanced_history_with_new_resolver_factory(self):
        from backend.advanced_planning import AdvancedInput
        from backend.test_advanced_routing import start
        source,_,token=self.advanced_fixture();session=Session.capture(self.broker,source,g.issuer_connection)
        result=session.invoke('advance',AdvancedInput(token=token,date='2026-11-07',destination='New York',startingLocation=start()))
        self.assertTrue(result.options)
        data=self.run_child('advanced',session.ticket);self.assertTrue(data['historyRetained']);self.assertTrue(data['routesRetained']);self.assertEqual(data['modelCalls'],0);self.assertTrue(data['restoredWithoutCharge'])
    def test_competing_processes_stale_fence_cannot_revoke_current_worker(self):
        self.model.data['date']=None;token,_=self.initial(text='Coffee and museum in Baltimore')
        session=Session.capture(self.broker,token,g.issuer_connection);before=self.s.snapshot()['gross']
        ctx=mp.get_context('spawn');ready=ctx.Event();release=ctx.Event();result=ctx.Queue()
        p=ctx.Process(target=held_worker,args=(json.dumps(dict(token=session.ticket.handle.token,revision=session.ticket.revision)),ready,release,result));p.start()
        try:
            self.assertTrue(ready.wait(30));current=self.run_child('pending',session.ticket);self.assertTrue(current['ready'])
            release.set();p.join(30);self.assertEqual(p.exitcode,0);self.assertEqual(result.get(timeout=3),'stale_refused')
            self.assertEqual(self.s.snapshot()['gross'],before)
        finally:
            release.set()
            if p.is_alive():p.terminate();p.join()
    def test_process_death_busy_turn_never_retries(self):
        token,_=self.initial();session=Session.capture(self.broker,token,g.issuer_connection);before=self.s.snapshot()['gross']
        ctx=mp.get_context('spawn');queue=ctx.Queue();p=ctx.Process(target=child,args=('die',json.dumps(dict(token=session.ticket.handle.token,revision=session.ticket.revision)),queue));p.start();p.join(45);self.assertEqual(p.exitcode,42)
        with self.assertRaises(Denied):Session.resume(Harness(store()).make(),session.ticket,g.issuer_connection)
        self.assertEqual(self.s.snapshot()['gross'],before)


def recovery_phase(mode):
    """Actual disposable pg_dump rollback, SIGKILL and lost-Redis drills."""
    from backend.testing_clock import calendar_clock
    from experiments.shared_state.contracts import Unavailable
    path=Path('/tmp/synthetic-native-recovery')
    with ExitStack() as stack:
        stack.enter_context(calendar_clock(b.NOW))
        stack.enter_context(patch.dict(os.environ,b.ENV,clear=False))
        stack.enter_context(patch('requests.sessions.Session.send',side_effect=AssertionError('External HTTP forbidden')))
        if mode.startswith('seed_'):
            fixture();h=Harness(store());broker=h.make();h.model.data['date']=None
            from backend.interpretation import InterpretationInput
            token,_=broker.interpret(InterpretationInput(text='Coffee and museum in Baltimore',calendarTimezone='America/New_York'))
            session=Session.capture(broker,token,g.issuer_connection)
            path.write_text(json.dumps(dict(token=session.ticket.handle.token,revision=session.ticket.revision,gross=h.s.snapshot()['gross'])))
        elif mode=='consume_restore':
            d=json.loads(path.read_text());h=Harness(store());session=Session.resume(h.make(),Ticket(SessionHandle(d['token']),d['revision']),g.issuer_connection)
            from backend.interpretation import ClarificationAnswers
            session.invoke('answer',ClarificationAnswers(date='2026-11-07'))
            assert h.model.calls==0 and h.s.snapshot()['gross']==d['gross']
        elif mode.startswith('detect_'):
            s=store()
            try:s.service.sync(s)
            except Denied:pass
            else:raise AssertionError('Restored native history was accepted')
            status=s.service.witness.call('status');assert status['quarantined'] and status['quarantineExposure']==g.grant()['total']
            print(mode+': native nonfinancial history rollback quarantined full synthetic grant.')
        elif mode=='op_down':
            try:store()
            except Unavailable:print('Native SQL outage refused; no fallback.')
            else:raise AssertionError('SQL outage admitted')
        elif mode=='after_crash':
            d=json.loads(path.read_text());h=Harness(store());assert h.s.snapshot()['gross']==d['gross'];h.s.service.sync(h.s)
            try:Session.resume(h.make(),Ticket(SessionHandle(d['token']),d['revision']),g.issuer_connection)
            except Denied:pass
            else:raise AssertionError('Native state recreated after Redis loss')
            assert h.calls==[] and h.model.calls==0
            print('SQL/witness restart retained committed inference exposure; lost Redis refused without provider work.')
        else:raise AssertionError('Unknown synthetic recovery phase')


if __name__=='__main__':
    import sys
    recovery_phase(sys.argv[1])
