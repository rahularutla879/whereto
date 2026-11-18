"""Disposable actual SQL/witness authority; authored requests/rates, no live API.

Mutation is restricted to provider_* schemas in the harness's new databases.
No original journal, credential loader, hosted DB or real financial grant used.
"""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime,timezone,timedelta
from pathlib import Path
from uuid import uuid4
import json,multiprocessing as mp,os,sys,time,unittest
import psycopg
from psycopg.types.json import Jsonb
from backend.interpretation import InterpretationInput
from backend.ai.openai_candidate import request_bytes
from backend.provider_responses import HTTPResult
from backend.provider_budget import ProviderSettings
from backend.action_dispatch import Request
from backend.places import DiscoveryRequest,SearchArea,search_body,ENDPOINT,FIELD_MASK
from experiments.shared_state.contracts import Kind,Limits,VERSION as CORE,digest,Denied,Unavailable
from experiments.shared_state.bridge_models import ProviderAction
from experiments.shared_state.redis_evidence import RedisEvidence,Keys
from experiments.shared_state.application_grants import Witness
from experiments.shared_state.test_store import KEY
from .profile import scripts,contracts,VERSION
from .runtime import Store,Service,CounterAuthority,Accounting,CounterWitness,namespaced,canonical
from private_runtime.provider_callbacks import CounterCallback,DispatcherCallback,OpenAIHTTP,count_payload,inference_response
from .profile import digest as sha

EPOCH='e'*64;ROOT='00000000-0000-4000-8000-000000000001';OUTING='00000000-0000-4000-8000-000000000010';PROJECT='proj_FICTIONALAPPLICATION';TEXT='coffee then museum in Baltimore'
LIMITS=Limits(10**12,10**12,10**12,10**12,16)

def connect(role,**kw):
    account={'runtime':('whereto_real_worker','SYNTHETIC_WORKER_PASSWORD'), 'issuer':('real_issuer_client','SYNTHETIC_ISSUER_PASSWORD'), 'counter':('real_counter_client','SYNTHETIC_COUNTER_PASSWORD'), 'witness':('real_witness_service','SYNTHETIC_WITNESS_SERVICE_PASSWORD'), 'reader':('real_witness_reader','SYNTHETIC_WITNESS_READER_PASSWORD'), 'counter-witness':('real_counter_witness_client','SYNTHETIC_COUNTER_PASSWORD')}[role]
    return psycopg.connect(host='127.0.0.1',port=5433 if role in ('witness','reader','counter-witness') else 5432,dbname='whereto_witness' if role in ('witness','reader','counter-witness') else 'whereto_synthetic',user=account[0],password=sha((os.environ[account[1]]+'\0'+account[0]).encode()),connect_timeout=2,**kw)
def admin(witness=False):
    return psycopg.connect(host='127.0.0.1',port=5433 if witness else 5432,dbname='whereto_witness' if witness else 'whereto_synthetic',user='synthetic_witness_admin' if witness else 'whereto_synthetic_admin',password=os.environ['SYNTHETIC_WITNESS_ADMIN_PASSWORD' if witness else 'SYNTHETIC_ADMIN_PASSWORD'])

class Redis(RedisEvidence):
    def path(self,env,epoch,sid):
        import re
        if env!='real' or not re.fullmatch('[0-9a-f]{64}',epoch) or not re.fullmatch('[0-9a-f]{64}',sid):raise Denied('real_redis_namespace')
        return '52-real-source:{real:'+epoch+'}:'+sid

def cache():return Redis(os.environ['SYNTHETIC_REDIS_PASSWORD'],Keys('real-fixture',{'real-fixture':b'f'*32}))
def rates(now=None):
    now=int(time.time()) if now is None else now
    template=json.loads(request_bytes(TEXT));template['input'][-1]['content']=''
    return dict(version='fictional-reviewed-real-profile-v1',checked=now-1,expires=now+3600,price_evidence='a'*64,qualification_evidence='b'*64,count_fee_evidence='c'*64,count_fee=0,google_account='fictional-google-project',currency='USD',maps=dict(search_pro=32000,matrix_element=5000,matrix_pro_element=10000),models={'gpt-6-luna':dict(account=PROJECT,revision='fictional-qualified-revision',profile='openai-full-input-cache-write-output-v1',input_ppm=1000000,cache_write_ppm=500000,output_ppm=2000000,extra_fee=0,max_input=12000,max_output=2000,margin=2048,template=template,counter_version='openai-complete-count-v1',count_ttl=600)})
def grant(**kw):return dict(id='11111111-1111-4111-8111-111111111111',version='real-app-grant-v1',domain='whereto-real-providers-v1',epoch=EPOCH,total=2000000,daily=2000000,outing=2000000,session=kw.get('total',2000000),providers={'google':2000000,'openai':2000000},timezone='UTC',expires='2099-01-01T00:00:00Z',roots=[ROOT,'00000000-0000-4000-8000-000000000002'],attempts=100,concurrency=4)|kw

def roles(witness):
    from psycopg import sql
    accounts={'whereto_real_owner':None,'real_grant_operator':None,'real_counter_witness':None} if witness else {'whereto_real_owner':None,'whereto_real_issuer':None,'real_token_counter':None}
    accounts.update({'real_witness_service':('SYNTHETIC_WITNESS_SERVICE_PASSWORD',None),'real_witness_reader':('SYNTHETIC_WITNESS_READER_PASSWORD',None),'real_counter_witness_client':('SYNTHETIC_COUNTER_PASSWORD','real_counter_witness')} if witness else {'whereto_real_worker':('SYNTHETIC_WORKER_PASSWORD',None),'real_issuer_client':('SYNTHETIC_ISSUER_PASSWORD','whereto_real_issuer'),'real_counter_client':('SYNTHETIC_COUNTER_PASSWORD','real_token_counter')})
    with admin(witness) as c:
        for name,values in accounts.items():
            if not c.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(name,)).fetchone():
                query=sql.SQL('CREATE ROLE {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS ').format(sql.Identifier(name))
                query+=sql.SQL('NOLOGIN') if values is None else sql.SQL('LOGIN PASSWORD {}').format(sql.Literal(sha((os.environ[values[0]]+'\0'+name).encode())))
                c.execute(query)
                if values and values[1]:c.execute(sql.SQL('GRANT {} TO {}').format(sql.Identifier(values[1]),sql.Identifier(name)))
            if values:c.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(sql.Identifier('whereto_witness' if witness else 'whereto_synthetic'),sql.Identifier(name)))
        c.execute(sql.SQL('GRANT CREATE ON DATABASE {} TO whereto_real_owner').format(sql.Identifier('whereto_witness' if witness else 'whereto_synthetic')))

def fixture(g=None,r=None):
    if not Path('/.dockerenv').exists() or {p.name for p in Path('/sys/class/net').iterdir()}!={'lo'}:raise RuntimeError('Disposable no-network fixture required')
    roles(False);roles(True)
    g=g or grant();r=r or rates();sql=scripts()
    # Only these disposable schemas; never the old synthetic-state schema.
    for witness in (False,True):
        with admin(witness) as c:
            c.execute('DROP SCHEMA IF EXISTS private_runtime CASCADE');c.execute('DROP SCHEMA IF EXISTS provider_state CASCADE');c.execute('DROP SCHEMA IF EXISTS provider_witness CASCADE');c.execute('DROP SCHEMA IF EXISTS provider_rules CASCADE')
            c.execute('SET LOCAL ROLE whereto_real_owner')
            c.execute(sql['witness' if witness else 'operational'],prepare=False)
            c.execute('SELECT provider_rules.validate(%s,%s)',(Jsonb(g),Jsonb(r)))
            c.execute('INSERT INTO provider_rules.configuration VALUES(1,%s,%s)',(Jsonb(g),Jsonb(r)))
            if not witness:
                c.execute('INSERT INTO provider_state.policy VALUES(1,%s,%s,%s)',(CORE,digest(KEY,'key',CORE),Jsonb(asdict(LIMITS))))
                settings=ProviderSettings().model_dump(exclude={'mode','exploration'})
                c.execute('INSERT INTO provider_state.finance_policy VALUES(1,%s,%s,%s,%s,%s,NULL,10000000,false,%s,%s)',(VERSION,r['version'],Jsonb(r['maps']),Jsonb(settings),'UTC','real-provider-accounts-v1','bounded'))
                c.execute('INSERT INTO provider_state.evidence_policy VALUES(1,%s,%s,%s)',('real',EPOCH,'52-encrypted-shared-evidence-local-v1'))
    with admin(True) as c:c.execute("SET LOCAL ROLE real_grant_operator");c.execute("SELECT provider_witness.operator('epoch',%s)",(Jsonb({'epoch':EPOCH}),))
    cache().client.flushdb()

def store():
    w=Witness(namespaced(lambda:connect('witness')),namespaced(lambda:connect('reader')))
    service=Service(w,lambda:connect('issuer'))
    return Store(connection=lambda **kw:connect('runtime',**kw),issuer=lambda:connect('issuer'),service=service,evidence=cache(),key=KEY,limits=LIMITS)

def source(s,*,llm=True,root=ROOT,outing=None):
    value=InterpretationInput(text=TEXT,calendarTimezone='America/New_York');body=canonical(value.model_dump(mode='json'))
    action=ProviderAction(purpose='ordinary',sourceDigest=sha(body),interpretationDigest=sha(b'null'),requestRevision=1)
    h=s.create(Kind.ACTION,action);lease=s.claim(h,1);http=os.urandom(32).hex();inference=os.urandom(32).hex() if llm else None
    s._call('admit',id=http,worker=s._worker,domain='http',fingerprint=http)
    if llm:s._call('admit',id=inference,worker=s._worker,domain='inference',fingerprint=action.sourceDigest)
    with connect('issuer') as c:
        c.execute('SELECT provider_state.real_register_inference(%s,%s,%s)' if llm else 'SELECT provider_state.register_action(%s,%s,%s,NULL)',(s._hash(h.token,'session'),http,inference))
        if llm:c.execute('SELECT provider_state.app_bind_inference(%s,%s,%s,%s)',(s._hash(h.token,'session'),root,outing or str(uuid4()),inference))
        else:c.execute('SELECT provider_state.app_enroll_budget(%s,%s,%s)',(s._hash(h.token,'session'),root,outing or str(uuid4())))
    cap=s.issue(lease,'provider_action',str(uuid4()));s.publish(lease,{'request':value},'real-source-v1',lambda:connect('issuer'))
    wire=request_bytes(TEXT)
    if llm:
        with connect('issuer') as c:c.execute('SELECT provider_state.real_enroll_request(%s,%s,%s,%s)',(s._hash(cap.token,'cap'),body,wire,count_payload(wire)))
    return lease,cap,wire,http,inference

def count(s,data,raw=None):
    l,cap,wire,_,_=data
    class HTTP:
        def request(self,*args):return raw if raw is not None else b'{"object":"response.input_tokens","input_tokens":100}'
    s.recover(l) # Factory validates private evidence; counter receives no Redis/issuer key.
    authority=CounterAuthority(lambda:connect('counter'),CounterWitness(lambda:connect('counter-witness'),lambda:connect('counter-witness')),PROJECT)
    result=CounterCallback(OpenAIHTTP(PROJECT,lambda:'sk-FICTIONAL',HTTP(),purpose='count'),authority).count(s._hash(cap.token,'cap'),wire)
    return result

def approve_llm(s,data):
    l,cap,wire,http,inference=data
    with connect('issuer') as c:
        spec=c.execute('SELECT provider_state.real_llm_spec(%s)',(s._hash(cap.token,'cap'),)).fetchone()[0]
        c.execute('SELECT provider_state.app_approve_llm(%s,%s,%s,%s)',(s._hash(cap.token,'cap'),Jsonb(spec),http,inference))
    return spec

def search():return Request.make('search','POST',ENDPOINT,FIELD_MASK,search_body(DiscoveryRequest(activity='coffee',destination=SearchArea(name='Baltimore')),3)).canonical

class GoogleFixture:
    account='fictional-google-project'
    def __init__(self,exchange=None):self.exchange=exchange or (lambda *_:HTTPResult(200,b'{"places":[]}'))
    def __call__(self,*args):return self.exchange(*args)

def maps(s,**kw):
    data=source(s,llm=False,**kw);wire=search()
    with connect('issuer') as c:c.execute('SELECT provider_state.real_approve_google(%s,%s)',(s._hash(data[1].token,'cap'),wire))
    return (data[0],data[1],wire,*data[3:])

def perform(s,data,callback):
    l,cap,wire,_,_=data;r=s.reserve(l,cap,str(uuid4()));s.transition(r,'INTENT')
    s._call('dispatch',**s._lease(l),capability=s._hash(cap.token,'cap'),operation=r.operation,ordinal=1,payload_digest=sha(wire))
    result=s.service.send(s,r,1,wire,callback)
    return r,result

class Tests(unittest.TestCase):
    def setUp(self):fixture();self.s=store()
    def test_openai_count_reservation_dispatch_and_non_refund(self):
        data=source(self.s);record=count(self.s,data);self.assertEqual(record.tokens,100);self.assertNotEqual(record.tokens,len(data[2]))
        spec=approve_llm(self.s,data);self.assertEqual(spec['input_tokens'],2148)
        class HTTP:
            def request(self,*args):return b'{"model":"gpt-6-luna","status":"completed"}'
        callback=DispatcherCallback(OpenAIHTTP(PROJECT,lambda:'sk-FICTIONAL',HTTP(),purpose='generation'),None,Accounting(),lambda:time.time())
        r,result=perform(self.s,data,callback);self.assertEqual(inference_response(result).decode()['model'],'gpt-6-luna')
        report=dict(provider='openai',model='gpt-6-luna',input_tokens=100,output_tokens=10,cached_tokens=0,cache_write_tokens=0,reasoning_tokens=0,tool_calls=0)
        self.assertTrue(self.s.service.usage(self.s,r,report)['valid']);self.s.transition(r,'SUCCEEDED')
        self.assertEqual(self.s.snapshot()['gross'],7222) # 2148 +1074 +4000, rounded individually.
        self.assertEqual(self.s.service.witness.call('status')['gross'],7222)
        with self.assertRaises(Exception):count(self.s,data)
    def test_google_real_codec_and_sql_unit_price(self):
        data=maps(self.s);calls=[]
        def exchange(wire,sku,units):calls.append((sku,units));return HTTPResult(200,b'{"places":[]}')
        cb=DispatcherCallback(None,GoogleFixture(exchange),Accounting(),lambda:time.time())
        r,result=perform(self.s,data,cb);self.assertEqual(result,{'places':[]});self.s.transition(r,'SUCCEEDED')
        self.assertEqual(self.s.snapshot()['gross'],32000);self.assertEqual(calls,[('search_pro',1)])
        with self.assertRaises(Exception):self.s.reserve(data[0],data[1],str(uuid4()))


def concurrent(root,barrier,queue,prepare=None,ready=None):
    from experiments.shared_state.financial_diagnostics import observe
    with observe():
        try:
            if prepare is not None:prepare.wait(20)
            s=store();data=maps(s,root=root)
            if ready is not None:ready.set()
            barrier.wait(20)
            r,_=perform(s,data,DispatcherCallback(None,GoogleFixture(),Accounting(),lambda:time.time()));s.transition(r,'SUCCEEDED');queue.put('accepted')
        except (Denied,psycopg.Error):queue.put('denied')
        except Exception as error:queue.put(type(error).__name__)

def crash_count():
    s=store();data=source(s);l,cap,wire,_,_=data;s.recover(l)
    authority=CounterAuthority(lambda:connect('counter'),CounterWitness(lambda:connect('counter-witness'),lambda:connect('counter-witness')),PROJECT)
    authority.begin(s._hash(cap.token,'cap'),wire,sha(count_payload(wire)),PROJECT)
    os._exit(42) # Durable reserve/INTENT/delivery, BEFORE any provider HTTP.

class AdversarialTests(unittest.TestCase):
    def setUp(self):fixture();self.s=store()
    def done(self,data):
        cb=DispatcherCallback(None,GoogleFixture(),Accounting(),lambda:time.time())
        r,result=perform(self.s,data,cb);self.s.transition(r,'SUCCEEDED');return r
    def test_concurrent_workers_one_nonrenewing_grant(self):
        fixture(grant(total=32000,daily=32000,outing=32000,providers={'google':32000,'openai':32000}));ctx=mp.get_context('spawn');barrier=ctx.Barrier(2);q=ctx.Queue()
        prepare=[ctx.Event(),ctx.Event()];ready=[ctx.Event(),ctx.Event()]
        children=[ctx.Process(target=concurrent,args=(root,barrier,q,prepare[i],ready[i])) for i,root in enumerate(grant()['roots'])]
        try:
            for p in children:p.start()
            prepare[0].set();self.assertTrue(ready[0].wait(20));prepare[1].set();self.assertTrue(ready[1].wait(20))
            for p in children:p.join(40);self.assertEqual(p.exitcode,0)
            self.assertEqual(sorted(q.get(timeout=3) for _ in children),['accepted','denied']);self.assertEqual(store().service.witness.call('status')['gross'],32000)
        finally:
            for p in children:
                if p.is_alive():p.terminate();p.join(5)
    def test_daily_outing_provider_and_total_limits(self):
        for change in [dict(session=31999),dict(daily=31999),dict(outing=31999),dict(providers={'google':31999,'openai':2000000}),dict(total=31999,daily=31999,outing=31999,providers={'google':31999,'openai':31999})]:
            fixture(grant(**change));s=store();data=maps(s)
            with self.assertRaises(Denied):s.reserve(data[0],data[1],str(uuid4()))
            self.assertEqual(s.snapshot()['gross'],0);self.assertEqual(s.service.witness.call('status')['gross'],0)
    def test_counter_role_cannot_price_sign_generate_or_change_epoch(self):
        attempts=[('runtime','INSERT INTO provider_rules.configuration VALUES(2,\'{}\',\'{}\')'),('issuer','UPDATE provider_rules.configuration SET grant_doc=\'{}\''),('counter',"SELECT provider_state.app_count_input('cap',''::bytea)"),('counter',"SELECT provider_state.app_protocol('reserve','{}','real','epoch',NULL)"),('counter-witness',"SELECT provider_witness.protocol('reserve','{}')"),('counter-witness',"SELECT provider_witness.operator('epoch','{}')")]
        for role,query in attempts:
            with self.subTest(role=role,query=query.split()[0]),self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with connect(role) as c:c.execute(query)
        http=OpenAIHTTP(PROJECT,lambda:'sk-FICTIONAL',purpose='count')
        with self.assertRaises(Exception):http.generate(request_bytes(TEXT))
    def test_missing_count_never_reserves_generation(self):
        data=source(self.s)
        with self.assertRaises(psycopg.Error):approve_llm(self.s,data)
        self.assertEqual(self.s.snapshot()['gross'],0);self.assertEqual(self.s.service.witness.call('status')['gross'],0)
    def test_modified_source_model_payload_and_project_refuse_before_count_send(self):
        data=source(self.s);l,cap,wire,http,inf=data
        with self.assertRaises(psycopg.errors.RaiseException):
            with connect('issuer') as c:c.execute('SELECT provider_state.real_enroll_request(%s,%s,%s,%s)',(self.s._hash(cap.token,'cap'),canonical({'text':'substituted'}),wire,count_payload(wire)))
        for altered in [request_bytes('museum then coffee in Baltimore'),canonical({**json.loads(wire),'model':'other'})]:
            sent=[]
            class HTTP:
                def request(self,*args):sent.append(args);return b'{}'
            authority=CounterAuthority(lambda:connect('counter'),CounterWitness(lambda:connect('counter-witness'),lambda:connect('counter-witness')),PROJECT)
            with self.assertRaises(Exception):CounterCallback(OpenAIHTTP(PROJECT,lambda:'sk-FICTIONAL',HTTP(),purpose='count'),authority).count(self.s._hash(cap.token,'cap'),altered)
            self.assertFalse(sent)
        self.assertEqual(self.s.snapshot()['gross'],0)
    def test_count_failure_and_excessive_count_are_terminal(self):
        for raw in [b'{"object":"response.input_tokens","input_tokens":0}',b'{"object":"response.input_tokens","input_tokens":12000}',b'{"object":"response.input_tokens","input_tokens":true}',b'{}']:
            fixture();s=store();data=source(s)
            with self.assertRaises(Exception):count(s,data,raw)
            self.assertTrue(s.service.witness.call('status')['quarantined'])
            with self.assertRaises(Exception):count(s,data)
            with self.assertRaises(Exception):approve_llm(s,data)
            self.assertEqual(s.snapshot()['gross'],0)
    def test_crash_after_count_intent_cannot_retry_from_new_process(self):
        child=mp.get_context('spawn').Process(target=crash_count);child.start();child.join(30);self.assertEqual(child.exitcode,42)
        with admin() as c:row=c.execute('SELECT capability FROM provider_state.count_attempts').fetchone();self.assertEqual(c.execute('SELECT count(*) FROM provider_state.count_results').fetchone()[0],0)
        authority=CounterAuthority(lambda:connect('counter'),CounterWitness(lambda:connect('counter-witness'),lambda:connect('counter-witness')),PROJECT)
        with self.assertRaises(Exception):authority.begin(row[0],request_bytes(TEXT),sha(count_payload(request_bytes(TEXT))),PROJECT)
        with admin() as c:self.assertEqual(c.execute('SELECT count(*) FROM provider_state.count_attempts').fetchone()[0],1)
    def test_timeout_after_reserved_delivery_keeps_full_charge(self):
        data=maps(self.s);sent=[]
        def fail(*args):sent.append(True);raise TimeoutError('Authored uncertain provider transport')
        with self.assertRaises(TimeoutError):perform(self.s,data,DispatcherCallback(None,GoogleFixture(fail),Accounting(),lambda:time.time()))
        self.assertEqual(sent,[True]);self.assertEqual(self.s.snapshot()['gross'],32000);status=self.s.service.witness.call('status');self.assertEqual(status['gross'],32000);self.assertTrue(status['quarantined'])
        with self.assertRaises(Exception):self.s.reserve(data[0],data[1],str(uuid4()))
    def test_changed_fence_and_released_admission_invalidate_count(self):
        data=source(self.s);count(self.s,data);self.s.claim(data[0].session,1)
        with self.assertRaises(psycopg.Error):approve_llm(self.s,data)
        fixture();s=store();data=source(s);count(s,data);s._call('admission_release',id=data[4],worker=s._worker)
        with self.assertRaises(psycopg.Error):approve_llm(s,data)
    def test_unknown_prices_categories_and_count_fees_refuse(self):
        for key,value in [('count_fee',1),('price_evidence',None),('qualification_evidence',None),('currency','EUR')]:
            r=rates();r[key]=value
            with self.assertRaises(psycopg.Error):fixture(r=r)
        for key,value in [('extra_fee',None),('cache_write_ppm',None),('profile','unknown'),('account','proj_E4EfEvC5uQYN4nqFaYZoo3I4')]:
            r=rates();r['models']['gpt-6-luna'][key]=value
            with self.assertRaises(psycopg.Error):fixture(r=r)
    def test_stale_rate_count_and_absolute_session_expiry(self):
        r=rates();r['checked']-=7200;r['expires']-=7200;fixture(r=r)
        with self.assertRaises(Denied):store()
        fixture();s=store();data=source(s);count(s,data)
        # Fixture-admin clock only; runtime roles have no clock-table access.
        future=datetime.now(timezone.utc)+timedelta(seconds=601)
        for wit in (False,True):
            with admin(wit) as c:
                c.execute('UPDATE provider_rules.test_clock SET value=%s',(future,))
                if not wit:c.execute('UPDATE provider_state.test_clock SET value=%s',(future,))
        with self.assertRaises(Exception):approve_llm(s,data)
    def test_redis_loss_blocks_paid_reservation_without_reset(self):
        data=maps(self.s);cache().client.flushdb()
        with self.assertRaises(Exception):self.s.reserve(data[0],data[1],str(uuid4()))
        self.assertEqual(self.s.snapshot()['gross'],0);self.assertEqual(self.s.service.witness.call('status')['gross'],0)
    def test_price_rounds_every_category_up(self):
        r=rates();r['models']['gpt-6-luna'].update(input_ppm=1,cache_write_ppm=1,output_ppm=1);fixture(r=r);s=store();data=source(s);count(s,data);spec=approve_llm(s,data)
        with connect('issuer') as c:
            # Owner-only price helper stays inaccessible even to issuer.
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):c.execute('SELECT provider_rules.price(%s,%s)',(Jsonb([spec]),Jsonb(r)))
        reservation=s.reserve(data[0],data[1],str(uuid4()));self.assertEqual(s.snapshot()['gross'],3)
    def test_google_enterprise_extra_fields_and_unit_substitution_refuse(self):
        data=source(self.s,llm=False)
        for change in [dict(mask='*'),dict(operation='details'),dict(url='https://example.invalid')]:
            body=json.loads(search());body.update(change)
            with self.assertRaises(psycopg.Error):
                with connect('issuer') as c:c.execute('SELECT provider_state.real_approve_google(%s,%s)',(self.s._hash(data[1].token,'cap'),canonical(body)))
        from backend.routes import matrix_body,RoutePoint,ENDPOINT as URL,FIELD_MASK as MASK
        point=RoutePoint(id='a',place_id='Fixture_A')
        for mode,sku,amount in [('walk','matrix_element',5000),('drive','matrix_pro_element',10000)]:
            fixture();s=store();d=source(s,llm=False);wire=Request.make('matrix','POST',URL,MASK,matrix_body([point],[point],mode)).canonical
            with connect('issuer') as c:c.execute('SELECT provider_state.real_approve_google(%s,%s)',(s._hash(d[1].token,'cap'),wire))
            calls=[]
            def matrix_exchange(payload,actual_sku,units):calls.append((actual_sku,units));return HTTPResult(200,b'[]')
            data=(d[0],d[1],wire,d[3],d[4]);rr,result=perform(s,data,DispatcherCallback(None,GoogleFixture(matrix_exchange),Accounting(),lambda:time.time()))
            self.assertEqual(result,[]);self.assertEqual(calls,[(sku,1)]);self.assertEqual(s.snapshot()['gross'],amount);s.transition(rr,'SUCCEEDED')
        fixture();s=store();d=source(s,llm=False);body=matrix_body([point],[point],'drive');body['routingPreference']='TRAFFIC_AWARE_OPTIMAL'
        with self.assertRaises(psycopg.Error):
            with connect('issuer') as c:c.execute('SELECT provider_state.real_approve_google(%s,%s)',(s._hash(d[1].token,'cap'),Request.make('matrix','POST',URL,MASK,body).canonical))
    def test_maps_and_counted_llm_share_exact_aggregate_allowance(self):
        for total in (39221,39222):
            with self.subTest(total=total):
                fixture(grant(total=total,daily=total,outing=total,providers={'google':total,'openai':total}));s=store();self.s=s;self.done(maps(s))
                if total==39221:
                    with self.assertRaises(Denied):complete_llm(s)
                    self.assertEqual(s.snapshot()['gross'],32000)
                else:complete_llm(s);self.assertEqual(s.snapshot()['gross'],39222)
                self.assertEqual(s.service.witness.call('status')['gross'],s.snapshot()['gross'])

    def test_calendar_rollover_does_not_renew_total(self):
        midnight=datetime.now(timezone.utc).replace(hour=23,minute=59,second=0,microsecond=0);start=int(midnight.timestamp());fixture(grant(total=64000,daily=32000,outing=64000,providers={'google':64000,'openai':64000}),r=rates(start))
        def clock(t):
            for wit in (False,True):
                with admin(wit) as c:
                    c.execute('UPDATE provider_rules.test_clock SET value=%s',(t,))
                    if not wit:c.execute('UPDATE provider_state.test_clock SET value=%s',(t,))
        clock(midnight);self.s=store();self.done(maps(self.s))
        with self.assertRaises(Denied):self.s.reserve(*maps(self.s)[:2],str(uuid4()))
        clock(midnight+timedelta(minutes=2));self.done(maps(self.s))
        with self.assertRaises(Denied):self.s.reserve(*maps(self.s,root=grant()['roots'][1])[:2],str(uuid4()))
        self.assertEqual(self.s.service.witness.call('status')['gross'],64000)
    def test_pricing_insert_guard_cannot_be_skipped_or_mutated(self):
        invalid=rates();invalid['count_fee']=1
        # No manual validate() call: INSERT itself must enforce the full policy.
        with self.assertRaises(psycopg.Error):
            with admin() as c:
                c.execute('SET LOCAL ROLE whereto_real_owner');c.execute('DELETE FROM provider_rules.configuration')
        with self.assertRaises(psycopg.errors.RaiseException) as caught:
            with admin() as c:
                c.execute('SET LOCAL ROLE whereto_real_owner');c.execute('INSERT INTO provider_rules.configuration VALUES(2,%s,%s)',(Jsonb(grant()),Jsonb(invalid)))
        self.assertEqual(caught.exception.diag.message_primary,'real_prices_missing_or_unknown_category')
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            with connect('runtime') as c:c.execute('ALTER TABLE provider_rules.configuration DISABLE TRIGGER validated_enrollment')
    def test_stale_count_before_absolute_session_expiry(self):
        r=rates();r['models']['gpt-6-luna']['count_ttl']=1;fixture(r=r);s=store();d=source(s);count(s,d)
        future=datetime.now(timezone.utc)+timedelta(seconds=3)
        for wit in (False,True):
            with admin(wit) as c:
                c.execute('UPDATE provider_rules.test_clock SET value=%s',(future,))
                if not wit:c.execute('UPDATE provider_state.test_clock SET value=%s',(future,))
        with self.assertRaises(psycopg.errors.RaiseException) as caught:approve_llm(s,d)
        self.assertEqual(caught.exception.diag.message_primary,'real_count_stale')
    def test_interrupted_count_has_no_generation_or_retry(self):
        d=source(self.s);l,cap,wire,_,_=d;sent=[]
        class HTTP:
            def request(self,*args):sent.append(args[2]);raise TimeoutError('Fictional interrupted count')
        authority=CounterAuthority(lambda:connect('counter'),CounterWitness(lambda:connect('counter-witness'),lambda:connect('counter-witness')),PROJECT)
        cb=CounterCallback(OpenAIHTTP(PROJECT,lambda:'sk-FICTIONAL',HTTP(),purpose='count'),authority)
        with self.assertRaises(TimeoutError):cb.count(self.s._hash(cap.token,'cap'),wire)
        with self.assertRaises(Exception):cb.count(self.s._hash(cap.token,'cap'),wire)
        self.assertEqual(sent,['/v1/responses/input_tokens']);self.assertTrue(self.s.service.witness.call('status')['quarantined'])
        with self.assertRaises(Exception):approve_llm(self.s,d)
    def test_llm_spec_substitution_cannot_reduce_or_increase_authority(self):
        d=source(self.s);count(self.s,d)
        with connect('issuer') as c:spec=c.execute('SELECT provider_state.real_llm_spec(%s)',(self.s._hash(d[1].token,'cap'),)).fetchone()[0]
        for key,value in [('model','other'),('model_revision','other'),('account','other'),('rate_version','other'),('input_tokens',1),('input_tokens',12001),('max_output',2001),('tool_calls',1)]:
            with self.subTest(field=key,value=value),self.assertRaises(psycopg.Error):
                with connect('issuer') as c:c.execute('SELECT provider_state.app_approve_llm(%s,%s,%s,%s)',(self.s._hash(d[1].token,'cap'),Jsonb({**spec,key:value}),d[3],d[4]))
        self.assertEqual(self.s.snapshot()['gross'],0)
    def test_epoch_rotation_and_invalid_usage_stop_further_work(self):
        d=source(self.s);count(self.s,d);approve_llm(self.s,d)
        r,_=perform(self.s,d,lambda _:None)
        with self.assertRaises(Denied):self.s.transition(r,'SUCCEEDED')
        self.assertFalse(self.s.service.usage(self.s,r,{'provider':'other'})['valid'])
        self.assertTrue(self.s.service.witness.call('status')['quarantined']);self.assertEqual(self.s.snapshot()['gross'],7222)
        fixture();s=store();d=maps(s)
        with admin(True) as c:c.execute('SET LOCAL ROLE real_grant_operator');c.execute("SELECT provider_witness.operator('epoch',%s)",(Jsonb({'epoch':'d'*64}),))
        with self.assertRaises(Exception):s.reserve(d[0],d[1],str(uuid4()))
        self.assertTrue(s.service.witness.call('status')['quarantined'])

    def test_hosted_port_contracts_reject_changed_schema_and_test_clock(self):
        from psycopg import sql
        for wit in (False,True):
            with admin(wit) as c:
                c.execute(contracts()['witness' if wit else 'operational'],prepare=False)
                logins={'real_witness_service':'witness-factory','real_counter_witness_client':'witness-counter'} if wit else {'whereto_real_worker':'runtime','real_issuer_client':'issuer','real_counter_client':'counter'}
                for login in logins:
                    c.execute(sql.SQL('GRANT USAGE ON SCHEMA private_runtime TO {}').format(sql.Identifier(login)))
                    c.execute(sql.SQL('GRANT EXECUTE ON FUNCTION private_runtime.connection_identity(),private_runtime.assert_session(integer) TO {}').format(sql.Identifier(login)))
                c.execute('SET LOCAL ROLE whereto_real_owner');h=c.execute('SELECT private_runtime.measure()').fetchone()[0];self.assertEqual(len(h),64)
                for login,purpose in logins.items():c.execute('INSERT INTO private_runtime.enrollment VALUES(%s,%s,%s)',(login,purpose,h))
            with connect('counter-witness' if wit else 'runtime') as c:self.assertEqual(c.execute('SELECT private_runtime.connection_identity()').fetchone()[0]['contract'],h)
        with admin() as c:c.execute('SET LOCAL ROLE whereto_real_owner');c.execute('ALTER TABLE provider_rules.configuration ADD COLUMN unreviewed_fixture_column text')
        with self.assertRaises(psycopg.errors.RaiseException):
            with connect('runtime') as c:c.execute('SELECT private_runtime.connection_identity()')
        with admin(True) as c:c.execute('UPDATE provider_rules.test_clock SET value=clock_timestamp()')
        with self.assertRaises(psycopg.errors.RaiseException):
            with connect('counter-witness') as c:c.execute('SELECT private_runtime.connection_identity()')
    def test_count_expiry_between_approval_reservation_and_dispatch_refuses(self):
        for reserved in (False,True):
            with self.subTest(reserved=reserved):
                policy=rates();policy['models']['gpt-6-luna']['count_ttl']=30;fixture(r=policy);s=store();d=source(s);count(s,d);approve_llm(s,d)
                if reserved:
                    r=s.reserve(d[0],d[1],str(uuid4()));s.transition(r,'INTENT')
                with admin() as c:c.execute("UPDATE provider_rules.test_clock SET value=clock_timestamp()+interval '31 seconds'")
                with admin(True) as c:c.execute("UPDATE provider_rules.test_clock SET value=clock_timestamp()+interval '31 seconds'")
                with self.assertRaises(Exception):
                    if reserved:s._call('dispatch',**s._lease(d[0]),capability=s._hash(d[1].token,'cap'),operation=r.operation,ordinal=1,payload_digest=sha(d[2]))
                    else:s.reserve(d[0],d[1],str(uuid4()))
                self.assertEqual(s.snapshot()['gross'],7222 if reserved else 0)
                # The independent claim precedes the OP refusal: retain it, never refund.
                status=s.service.witness.call('status');self.assertEqual(status['gross'],7222);self.assertTrue(status['quarantined'])
                with admin() as c:self.assertEqual(c.execute('SELECT count(*) FROM provider_state.financial_dispatch').fetchone()[0],0)

    def test_zero_output_usage_and_contradictory_report_never_refund(self):
        for changes,valid in [({'output_tokens':0},True),({'input_tokens':99},False),({'cached_tokens':101},False),({'cache_write_tokens':101},False),({'reasoning_tokens':11},False)]:
            with self.subTest(changes=changes):
                fixture();s=store();d=source(s);count(s,d);approve_llm(s,d);r,_=perform(s,d,lambda _:None)
                report=dict(provider='openai',model='gpt-6-luna',input_tokens=100,output_tokens=10,cached_tokens=0,cache_write_tokens=0,reasoning_tokens=0,tool_calls=0)|changes
                result=s.service.usage(s,r,report);self.assertEqual(result['valid'],valid);self.assertFalse(result['refund']);self.assertEqual(result['released'],0)
                self.assertEqual(s.snapshot()['gross'],7222);self.assertEqual(s.service.witness.call('status')['gross'],7222)
                if valid:self.assertEqual(result['reportedCharge'],100);s.transition(r,'SUCCEEDED')
                else:self.assertTrue(s.service.witness.call('status')['quarantined'])

    def test_new_outing_does_not_reset_session_root_money(self):
        fixture(grant(total=96000,daily=96000,outing=96000,session=32000,providers={'google':96000,'openai':96000}));self.s=store();self.done(maps(self.s))
        d=maps(self.s)
        with self.assertRaises(Denied):self.s.reserve(d[0],d[1],str(uuid4()))
        self.done(maps(self.s,root=grant()['roots'][1]));self.assertEqual(self.s.snapshot()['gross'],64000)
        with self.assertRaises(psycopg.errors.RaiseException):maps(self.s,root=str(uuid4()))

def complete_llm(s):
    d=source(s);count(s,d);approve_llm(s,d)
    r,_=perform(s,d,lambda _:None)
    report=dict(provider='openai',model='gpt-6-luna',input_tokens=100,output_tokens=10,cached_tokens=0,cache_write_tokens=0,reasoning_tokens=0,tool_calls=0)
    assert s.service.usage(s,r,report)['valid'];s.transition(r,'SUCCEEDED')
    return r

def seed_restore():fixture();complete_llm(store())
def consume_restore():
    s=store();r,_=perform(s,maps(s),DispatcherCallback(None,GoogleFixture(),Accounting(),lambda:time.time()));s.transition(r,'SUCCEEDED')
def detect_restore():
    s=store()
    try:s.service.sync(s)
    except Denied:pass
    else:raise AssertionError('Restored history silently accepted')
    status=s.service.witness.call('status');assert status['quarantined'] and status['quarantineExposure']==grant()['total']
    print('Real-profile snapshot mismatch: full grant quarantined; no new delivery.',flush=True)
def seed_crash():
    fixture();s=store();d=maps(s);r=s.reserve(d[0],d[1],str(uuid4()));s.transition(r,'INTENT')
    p=Path('/tmp/real-finance-crash.json');p.write_text(json.dumps({'token':d[0].session.token,'revision':d[0].revision}));p.chmod(0o600)
def op_down():
    try:store()
    except (Denied,Unavailable):print('Real-profile operational outage: refused; no fallback.',flush=True)
    else:raise AssertionError('Operational outage accepted')
def after_crash():
    from experiments.shared_state.contracts import SessionHandle
    s=store();assert s.snapshot()['gross']==32000;assert s.service.witness.call('status')['gross']==32000
    data=json.loads(Path('/tmp/real-finance-crash.json').read_text());lease=s.claim(SessionHandle(data['token']),data['revision']);cache().client.flushdb()
    try:s.recover(lease)
    except (Denied,Unavailable):pass
    else:raise AssertionError('Lost Redis evidence reconstructed')
    assert s.snapshot()['gross']==32000 and s.service.witness.call('status')['gross']==32000
    print('Real-profile database restart and Redis loss: full exposure retained; no resend.',flush=True)

if __name__=='__main__':
    modes={'seed_restore':seed_restore,'consume_restore':consume_restore,'detect_op_restore':detect_restore,'detect_witness_restore':detect_restore,'seed_crash':seed_crash,'op_down':op_down,'after_crash':after_crash}
    if len(sys.argv)==2 and sys.argv[1] in modes:modes[sys.argv[1]]()
    else:unittest.main()
