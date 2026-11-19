"""Real-profile native tests: authored HTTP facts, actual SQL/witness/Redis money."""
from datetime import timedelta
from hashlib import sha256
from http.server import HTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json,multiprocessing as mp,os,ssl,subprocess,time,unittest
from backend import action_dispatch as io
from backend.interpretation import InterpretationInput,ClarificationAnswers
from backend.testing_clock import calendar_clock
from backend.test_provider_responses import TEXT,NOW,response,extraction
from backend.test_real_planning import outing
from backend.real_fixtures import search_fixture,matrix_fixture
from backend.provider_responses import HTTPResult
from private_runtime.provider_callbacks import CounterCallback,DispatcherCallback,OpenAIHTTP
from private_runtime.real_finance import test_sql as g
from private_runtime.real_finance.runtime import CounterAuthority,CounterWitness,Accounting
from .native import Broker,Issuer,Inference,require_native
from .sql import application_sql
from .store import Store


def responder(pipe,cert,key,behavior):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def do_POST(self):
            wire=self.rfile.read(int(self.headers['Content-Length']));body=json.loads(wire)
            pipe.send((self.path,sha256(wire).hexdigest()))
            if behavior==self.path:
                self.close_connection=True;return
            if self.path=='/v1/responses/input_tokens':data={'object':'response.input_tokens','input_tokens':100}
            elif self.path=='/v1/responses':data=response(extraction(),usage=dict(input_tokens=100,output_tokens=10,total_tokens=110)).decode()
            elif self.path=='/v1/places:searchText':data=search_fixture(body)
            elif self.path=='/distanceMatrix/v2:computeRouteMatrix':data=matrix_fixture(body)
            else:self.send_error(405);return
            if behavior=='bad_model' and self.path=='/v1/responses':data['model']='wrong-model'
            if behavior=='empty_places' and self.path=='/v1/places:searchText':data={'places':[]}
            raw=json.dumps(data).encode();self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
    server=HTTPServer(('127.0.0.1',0),Handler);context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2;context.load_cert_chain(cert,key);server.socket=context.wrap_socket(server.socket,server_side=True);pipe.send(server.server_port);server.serve_forever()

def app_store():
    from private_runtime.real_finance.runtime import Service,namespaced
    from experiments.shared_state.application_grants import Witness
    service=Service(Witness(namespaced(lambda:g.connect('witness')),namespaced(lambda:g.connect('reader'))),lambda:g.connect('issuer'))
    return Store(connection=lambda **kw:g.connect('runtime',**kw),issuer=lambda:g.connect('issuer'),service=service,evidence=g.cache(),key=g.KEY,limits=g.LIMITS)

def fixture(rates=None):
    if rates is None:
        rates=g.rates();rates['models']['gpt-6-luna']['cache_write_ppm']=0
    g.fixture(r=rates)
    with g.admin() as c:c.execute('SET LOCAL ROLE whereto_real_owner');c.execute(application_sql(),prepare=False)

class Tests(unittest.TestCase):
    def setUp(self):
        fixture()
        self.enterContext(calendar_clock(NOW));self.enterContext(patch.dict(os.environ,{'K_SERVICE':'offline-real-native-fixture','NODE_ENV':'production','WHERETO_ENV':'production'},clear=False))
        for key in ('VENUE_DATA_MODE','WHERETO_REAL_DEV','WHERETO_PLACES_DEV','WHERETO_ROUTES_DEV'):os.environ.pop(key,None)
        self.s=app_store();self.temp=self.enterContext(TemporaryDirectory(prefix='real-native-http-'))
    def broker(self,behavior=None):
        from private_runtime.https import HTTPS,Endpoint
        p=Path(self.temp);cert=p/'cert.pem';key=p/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        ctx=mp.get_context('spawn');parent,child=ctx.Pipe();process=ctx.Process(target=responder,args=(child,str(cert),str(key),behavior));process.start()
        self.addCleanup(lambda:(process.terminate(),process.join(5),parent.close(),child.close()))
        self.assertTrue(parent.poll(10));port=parent.recv();local=Endpoint('https://localhost:'+str(port),'https://localhost:'+str(port));tls=HTTPS(ca_file=str(cert),deadline=15,request_limit=100000,response_limit=700000)
        class AITransport:
            def request(self,endpoint,method,path,body,headers):
                assert endpoint.url=='https://api.openai.com'
                return tls.request(local,method,path,body,headers)
        class Google:
            account='fictional-google-project'
            def __call__(self,wire,sku,units):
                from backend.provider_responses import google_request
                v,s,u=google_request(wire);assert(s,u)==(sku,units)
                endpoint='/v1/places:searchText' if v['operation']=='search' else '/distanceMatrix/v2:computeRouteMatrix'
                raw=tls.request(local,'POST',endpoint,json.dumps(v['body']).encode(),{'Content-Type':'application/json'})
                return HTTPResult(200,raw)
        counter=CounterCallback(OpenAIHTTP(g.PROJECT,lambda:'sk-FICTIONAL',AITransport(),purpose='count'),CounterAuthority(lambda:g.connect('counter'),CounterWitness(lambda:g.connect('counter-witness'),lambda:g.connect('counter-witness')),g.PROJECT))
        dispatch=DispatcherCallback(OpenAIHTTP(g.PROJECT,lambda:'sk-FICTIONAL',AITransport(),purpose='generation'),Google(),Accounting(),lambda:time.time())
        issuer=Issuer(lambda:g.connect('issuer'),g.ROOT);model=Inference(self.s,lambda:g.connect('issuer'),g.ROOT,counter,dispatch)
        broker=Broker(self.s,issuer,model,dispatch,now=NOW)
        self.pipe=parent;self.process=process;self.model=model;return broker
    def ready(self,b):
        token,result=b.interpret(InterpretationInput(text=TEXT,calendarTimezone='America/New_York'),execution={'startingLocation':outing().startingLocation})
        self.assertIsNotNone(result.pending);before=self.s.snapshot()['gross']
        result=b.answer(token,ClarificationAnswers(date='2026-11-07'))
        self.assertIsNotNone(result.request);self.assertEqual(self.model.calls,1);self.assertEqual(self.s.snapshot()['gross'],before)
        return token
    def calls(self):
        out=[]
        while self.pipe.poll(.05):out.append(self.pipe.recv()[0])
        return out
    def test_native_interpret_pending_origin_plan_actual_sql_and_no_google_storage(self):
        b=self.broker();token=self.ready(b);result=b.plan(token)
        self.assertEqual(len(result.provisionalPlans),3)
        for card in result.provisionalPlans:
            self.assertEqual([v.activity for v in card.candidate.venues],['coffee','museum']);self.assertGreater(card.totalTravel,0)
            self.assertEqual(card.stops[0].venue.evidenceLabels['attribution']['brand'],'Google Maps')
            self.assertEqual(card.stops[0].venue.evidenceLabels['attribution']['third_party'][0]['provider'],'Synthetic credit')
        self.assertIn('refreshing will not retry',result.continuationStatus['message']);self.assertIsNone(result.optionsToken);self.assertIsNone(result.detailsToken);self.assertFalse(result.canExpand)
        from backend.option_sessions import option_sessions
        from backend.venue_details import details_sessions
        self.assertFalse(option_sessions.entries);self.assertFalse(details_sessions.entries)
        paths=self.calls();self.assertEqual(paths.count('/v1/responses'),1);self.assertEqual(paths.count('/v1/responses/input_tokens'),1);self.assertIn('/v1/places:searchText',paths);self.assertIn('/distanceMatrix/v2:computeRouteMatrix',paths)
        with g.admin() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM provider_state.real_response_receipts').fetchone()[0],1)
            self.assertEqual(c.execute('SELECT count(*) FROM provider_state.llm_usage WHERE valid').fetchone()[0],1)
            rows=c.execute('SELECT payload FROM provider_state.evidence').fetchall();self.assertNotIn('Fixture_',json.dumps(rows))
        self.assertEqual(self.s.snapshot()['gross'],self.s.service.witness.call('status')['gross']);self.assertGreater(self.s.snapshot()['gross'],6148)
        with self.assertRaises(Exception):b.plan(token)
        self.assertFalse(self.calls())
    def test_interrupted_count_never_generates_or_retries(self):
        b=self.broker('/v1/responses/input_tokens')
        with self.assertRaises(Exception):self.ready(b)
        self.assertEqual(self.calls(),['/v1/responses/input_tokens']);self.assertEqual(self.s.snapshot()['gross'],0);self.assertTrue(self.s.service.witness.call('status')['quarantined'])
    def test_generation_uncertainty_retains_reserved_charge(self):
        b=self.broker('/v1/responses')
        with self.assertRaises(Exception):self.ready(b)
        self.assertEqual(self.calls(),['/v1/responses/input_tokens','/v1/responses']);self.assertEqual(self.s.snapshot()['gross'],6148);self.assertTrue(self.s.service.witness.call('status')['quarantined'])
    def test_missing_grant_and_source_mutation_and_unsupported_routes(self):
        with self.assertRaises(Exception):require_native()
        b=self.broker();token=self.ready(b);source=b._source(token);source.execution['searchRadius']=999
        with self.assertRaises(Exception):b.plan(token)
        self.assertEqual(self.calls(),['/v1/responses/input_tokens','/v1/responses'])
        for name in ('lookup','more','contact','advance','refresh'):
            with self.assertRaises(Exception):getattr(b,name)(None)

    def test_wrong_model_captures_immutable_hash_and_preserves_charge(self):
        b=self.broker('bad_model')
        with self.assertRaises(Exception):self.ready(b)
        self.assertEqual(self.calls(),['/v1/responses/input_tokens','/v1/responses'])
        self.assertEqual(self.s.snapshot()['gross'],6148)
        with g.admin() as c:self.assertEqual(c.execute('SELECT count(*) FROM provider_state.real_response_receipts').fetchone()[0],1)
    def test_empty_places_ends_source_without_invented_cards_or_retry(self):
        b=self.broker('empty_places');token=self.ready(b);result=b.plan(token)
        self.assertFalse(result.provisionalPlans);paths=self.calls();self.assertNotIn('/distanceMatrix/v2:computeRouteMatrix',paths)
        with self.assertRaises(Exception):b.plan(token)
        self.assertFalse(self.calls())
    def test_batch_validation_is_atomic_and_worker_cannot_skip_receipt_gate(self):
        from psycopg.errors import InsufficientPrivilege
        data=g.source(self.s,llm=False);cap=self.s._hash(data[1].token,'cap');wire=g.search();bad=json.loads(wire);bad['mask']='*'
        with self.assertRaises(Exception):
            with g.connect('issuer') as c:c.execute('SELECT provider_state.real_approve_google_batch(%s,%s)',(cap,[wire,json.dumps(bad).encode()]))
        with g.admin() as c:self.assertEqual(c.execute('SELECT count(*) FROM provider_state.request_plans').fetchone()[0],0)
        with self.assertRaises(InsufficientPrivilege):
            with g.connect('runtime') as c:c.execute("SELECT provider_state.app_protocol('snapshot','{}','real',%s,NULL)",(g.EPOCH,))
        with self.assertRaises(InsufficientPrivilege):
            with g.connect('runtime') as c:c.execute('DELETE FROM provider_state.real_response_receipts')
    def test_new_interpretation_and_expired_source_never_resend(self):
        b=self.broker();token=self.ready(b);before=self.s.snapshot()['gross']
        with self.assertRaises(Exception):b.interpret(InterpretationInput(text=TEXT))
        source=b._source(token);source.created-=601;source.digest=b._seal(source)
        with self.assertRaises(Exception):b.plan(token)
        self.assertEqual(self.s.snapshot()['gross'],before);self.assertEqual(self.calls(),['/v1/responses/input_tokens','/v1/responses'])

    def test_unrequested_answer_and_terminal_source_replay_refuse(self):
        b=self.broker();token,result=b.interpret(InterpretationInput(text=TEXT,calendarTimezone='America/New_York'))
        before=self.s.snapshot()['gross']
        with self.assertRaises(Exception):b.answer(token,ClarificationAnswers(location='New York'))
        self.assertEqual(self.s.snapshot()['gross'],before);self.assertEqual(self.calls(),['/v1/responses/input_tokens','/v1/responses'])
        b.revoke(token)
        with self.assertRaises(Exception):b.answer(token,ClarificationAnswers(date='2026-11-07'))


    def test_pending_source_lost_on_independent_worker_restart_refuses_without_spend(self):
        ctx=mp.get_context('spawn');q=ctx.Queue();p=ctx.Process(target=produce_pending_source,args=(q,));p.start()
        record=q.get(timeout=45);p.join(10);self.assertEqual(p.exitcode,0)
        self.assertEqual(record['paths'],['/v1/responses/input_tokens','/v1/responses'])
        q2=ctx.Queue();replacement=ctx.Process(target=refuse_lost_source,args=(q2,record['token']));replacement.start();result=q2.get(timeout=20);replacement.join(10)
        self.assertEqual(replacement.exitcode,0);self.assertEqual(result,{'refused':True,'gross':6148})
        with g.admin() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM provider_state.count_attempts').fetchone()[0],1)
            self.assertEqual(c.execute('SELECT count(*) FROM provider_state.real_response_receipts').fetchone()[0],1)


    def test_owner_current_check_survives_independent_callback_thread(self):
        from concurrent.futures import ThreadPoolExecutor
        b=self.broker();original=self.s.service.send;checked=[]
        def send(*args):
            with ThreadPoolExecutor(max_workers=1) as executor:executor.submit(b.check_current).result(timeout=5)
            checked.append(True);return original(*args)
        with patch.object(self.s.service,'send',side_effect=send):
            token=self.ready(b);result=b.plan(token);self.assertEqual(len(result.provisionalPlans),3)
        self.assertGreaterEqual(len(checked),4)
        with self.assertRaises(Exception):b.check_current()
    def test_lost_admission_after_dispatch_blocks_delivery_and_keeps_charge(self):
        data=g.maps(self.s);l,cap,wire,http,_=data
        reservation=self.s.reserve(l,cap,str(__import__('uuid').uuid4()));self.s.transition(reservation,'INTENT')
        self.s._call('dispatch',**self.s._lease(l),capability=self.s._hash(cap.token,'cap'),operation=reservation.operation,ordinal=1,payload_digest=sha256(wire).hexdigest())
        self.s._call('admission_release',id=http,worker=self.s._worker);sent=[]
        with self.assertRaises(Exception):self.s.service.send(self.s,reservation,1,wire,lambda _:sent.append(True))
        self.assertFalse(sent);self.assertEqual(self.s.snapshot()['gross'],32000);self.assertEqual(self.s.service.witness.call('status')['gross'],32000)


    def test_unreported_priced_category_refuses_before_count_or_generation(self):
        fixture(rates=g.rates());self.s=app_store();b=self.broker()
        with self.assertRaises(Exception):self.ready(b)
        self.assertFalse(self.calls());self.assertEqual(self.s.snapshot()['gross'],0)
        with g.admin() as c:self.assertEqual(c.execute('SELECT count(*) FROM provider_state.count_attempts').fetchone()[0],0)


def produce_pending_source(queue):
    # A fresh fixture before ANY operation; the replacement below never resets it.
    t=Tests()
    try:
        t.setUp();b=t.broker();token=t.ready(b);queue.put(dict(token=token,paths=t.calls()))
    finally:t.doCleanups()
def refuse_lost_source(queue,token):
    from experiments.shared_state.contracts import Denied
    s=app_store()
    def no_send(*args):raise AssertionError('Lost source must never send')
    issuer=Issuer(lambda:g.connect('issuer'),g.ROOT);model=Inference(s,lambda:g.connect('issuer'),g.ROOT,None,no_send)
    b=Broker(s,issuer,model,no_send,now=NOW)
    try:b.plan(token)
    except Denied:queue.put(dict(refused=True,gross=s.snapshot()['gross']))
    else:raise AssertionError('Missing source reconstructed')

def seed_restore():
    t=Tests()
    try:t.setUp();b=t.broker();t.ready(b)
    finally:t.doCleanups()
def consume_restore():
    s=app_store();r,_=g.perform(s,g.maps(s),DispatcherCallback(None,g.GoogleFixture(),Accounting(),lambda:time.time()));s.transition(r,'SUCCEEDED')
def detect_restore():
    s=app_store()
    try:s.service.sync(s)
    except Exception:pass
    else:raise AssertionError('Restored application financial history accepted')
    status=s.service.witness.call('status');assert status['quarantined'] and status['quarantineExposure']==g.grant()['total']
    with g.admin() as c:assert c.execute('SELECT count(*) FROM provider_state.real_response_receipts').fetchone()[0]==1
    print('Real-native response receipt/history restore mismatch: full grant quarantined.',flush=True)
def seed_crash():
    fixture();s=app_store();data=g.maps(s);r=s.reserve(data[0],data[1],str(__import__('uuid').uuid4()));s.transition(r,'INTENT')
    p=Path('/tmp/real-native-crash.json');p.write_text(json.dumps(dict(token=data[0].session.token,revision=data[0].revision)));p.chmod(0o600)
def op_down():
    try:app_store()
    except Exception:print('Real-native SQL outage: refused.',flush=True)
    else:raise AssertionError('Operational outage accepted')
def after_crash():
    from experiments.shared_state.contracts import SessionHandle
    s=app_store();assert s.snapshot()['gross']==32000 and s.service.witness.call('status')['gross']==32000
    d=json.loads(Path('/tmp/real-native-crash.json').read_text());lease=s.claim(SessionHandle(d['token']),d['revision']);g.cache().client.flushdb()
    try:s.recover(lease)
    except Exception:pass
    else:raise AssertionError('Missing evidence reconstructed')
    assert s.snapshot()['gross']==32000
    print('Real-native restart/Redis loss: full exposure retained; no resend.',flush=True)

if __name__=='__main__':
    import sys
    modes=dict(seed_restore=seed_restore,consume_restore=consume_restore,detect_op_restore=detect_restore,detect_witness_restore=detect_restore,seed_crash=seed_crash,op_down=op_down,after_crash=after_crash)
    if len(sys.argv)==2 and sys.argv[1] in modes:modes[sys.argv[1]]()
    else:unittest.main()
