"""Independent authenticated role processes, real SQL/witness/Redis, local TLS.

All signing keys/provider credentials below are fictional disposable fixtures.
No provider/Google identity endpoint or original journal is contacted.
"""
from copy import deepcopy
from datetime import timedelta
from email.message import Message
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import base64,json,multiprocessing as mp,os,secrets,socket,subprocess,time,unittest
from unittest.mock import patch
import jwt,psycopg
from psycopg import sql
from cryptography.hazmat.primitives.asymmetric import rsa,ec,ed25519
from cryptography.hazmat.primitives import serialization
from backend.test_provider_responses import TEXT,NOW
from backend.testing_clock import calendar_clock
from backend.provider_responses import HTTPResult,google_request
from private_runtime.https import Endpoint,HTTPS
from private_runtime.service_client import ServiceClient
from private_runtime.dispatch_owner import DispatchOwner,Owner,OwnerRouter
from private_runtime.provider_callbacks import OpenAIHTTP,CounterCallback,DispatcherCallback
from private_runtime.real_finance.runtime import CounterAuthority,CounterWitness,Accounting
from experiments.hosted_identity.auth import Auth,signed,digest
from experiments.hosted_identity.tokens import ISSUERS
from experiments.hosted_startup.public_auth import REQUEST,FORWARD,binding
from experiments.service_isolation.auth import b64
from experiments.shared_state.evidence_models import canonical
from .test_native import fixture,responder,g
from .native import Broker,Issuer,Inference
from .store import Store
from .rpc import RemoteSend,RemoteCounter,ScopedWitness,DeliveryStore
from .service import Role,privileged_server,backend_app
from .rpc_sql import scripts

BUILD='1'*64
ROLES={'backend':'real_backend_auth','factory':'real_factory_witness','counter':'real_counter_witness_client','dispatcher':'real_dispatch_witness','recovery':'real_recovery_client'}

def connect(name,**kw):
    if name=='dispatcher-db':role='real_dispatch_client';port=5432;env='SYNTHETIC_WORKER_PASSWORD'
    else:role=ROLES[name];port=5433;env='SYNTHETIC_COUNTER_PASSWORD' if name=='counter' else 'SYNTHETIC_WITNESS_SERVICE_PASSWORD'
    return psycopg.connect(host='127.0.0.1',port=port,dbname='whereto_witness' if port==5433 else 'whereto_synthetic',user=role,password=sha256((os.environ[env]+'\0'+role).encode()).hexdigest(),connect_timeout=2,**kw)

def enroll_fixture():
    fixture()
    for witness,roles in [(False,['real_dispatch_client']),(True,['real_backend_auth','real_factory_witness','real_dispatch_witness','real_recovery_client'])]:
        with g.admin(witness) as c:
            for role in roles:
                env='SYNTHETIC_WORKER_PASSWORD' if not witness else 'SYNTHETIC_WITNESS_SERVICE_PASSWORD'
                if not c.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(role,)).fetchone():
                    c.execute(sql.SQL('CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}').format(sql.Identifier(role),sql.Literal(sha256((os.environ[env]+'\0'+role).encode()).hexdigest())))
                c.execute(sql.SQL('GRANT CONNECT ON DATABASE {} TO {}').format(sql.Identifier('whereto_witness' if witness else 'whereto_synthetic'),sql.Identifier(role)))
            c.execute('SET LOCAL ROLE whereto_real_owner');c.execute(scripts()['witness' if witness else 'operational'],prepare=False)
            if not witness:c.execute('INSERT INTO provider_state.service_profile VALUES(1,%s,%s)',(BUILD,g.EPOCH))

def configurations(ports,cert):
    names=['frontend','backend','factory-a','factory-b','counter','dispatcher','recovery'];roles={n:('factory' if n.startswith('factory') else n) for n in names}
    proofkeys={n:ed25519.Ed25519PrivateKey.generate() for n in names}
    def rawkey(k):return k.private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption())
    trust={n:dict(role=roles[n],publicKey=b64(k.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw))) for n,k in proofkeys.items()}
    enrollment={n:dict(sub=str(100000000000000000000+i),email=n+'@fixture-project.iam.gserviceaccount.com') for i,n in enumerate(names)}
    keys={'workload':rsa.generate_private_key(public_exponent=65537,key_size=2048),'iap':ec.generate_private_key(ec.SECP256R1())};docs={}
    for kind,key in keys.items():
        value=json.loads((jwt.algorithms.RSAAlgorithm if kind=='workload' else jwt.algorithms.ECAlgorithm).to_jwk(key.public_key()));value.update(kid='task52-offline-'+kind,alg='RS256' if kind=='workload' else 'ES256',use='sig');docs[kind]=dict(keys=[value],fixture=True)
    aud={n:'https://'+n+'-task52-offline.run.app' for n in set(roles.values())};iap='/projects/000000000000/locations/us-east4/services/fixture-frontend';now=int(time.time())
    def token(kind,**claims):return jwt.encode(dict(iss=ISSUERS[kind],iat=now,exp=now+600,**claims),keys[kind],algorithm='RS256' if kind=='workload' else 'ES256',headers={'kid':'task52-offline-'+kind})
    users={n:token('iap',aud=iap,sub='accounts.google.com:fixture-'+n,email=n+'@example.invalid') for n in ('alice','bob')}
    allow={'factory':{'/ordinary':['backend'],'/dispatch-check':['dispatcher']},'counter':{'/count':['factory-a','factory-b'],'/ui-probe':['factory-a','factory-b']},'dispatcher':{'/send':['factory-a','factory-b'],'/ui-probe':['factory-a','factory-b']},'recovery':{'/recover':['operator'],'/ui-probe':['factory-a','factory-b']},'backend':{},'frontend':{}}
    # Operator is only a public trust record, no operator credential is created.
    trust['operator']=dict(role='operator',publicKey=trust['frontend']['publicKey']);enrollment['operator']=dict(sub='999999999999999999999',email='operator@example.invalid')
    configs={}
    for n in names:
        role=roles[n];targets={}
        if role=='backend':targets={'factory':'factory-a'}
        if role=='factory':targets={'counter':'counter','dispatcher':'dispatcher','recovery':'recovery'}
        if role=='dispatcher':targets={'factory-a':'factory-a','factory-b':'factory-b'}
        methods={'factory':['/ordinary'],'counter':['/count','/ui-probe'],'dispatcher':['/send','/ui-probe'],'recovery':['/ui-probe'],'factory-a':['/dispatch-check'],'factory-b':['/dispatch-check']}
        configs[n]=dict(service=role,principal=n,port=ports.get(n,0),build=BUILD,identityBuild=BUILD,ordinaryBuild=BUILD,epoch=g.EPOCH,identityEnvironment='offline-hosted-contract',trust=trust,enrollment=enrollment,revoked=[],allow=allow[role],audiences=aud,iapAudience=iap,testers=['accounts.google.com:fixture-alice','accounts.google.com:fixture-bob'],googleKeys=docs,signingKey=b64(rawkey(proofkeys[n])),networkTargets={k:dict(url='https://localhost:'+str(ports[v]),audience=aud[roles[v]],service=roles[v]) for k,v in targets.items()},networkMethods={k:methods[k] for k in targets},oidcTokens={a:token('workload',aud=a,sub=enrollment[n]['sub'],email=enrollment[n]['email'],email_verified=True) for a in aud.values()})
        if role=='factory':configs[n]['encryptionKey']=b64(b'f'*32)
    return configs,users

class Identity:
    def __init__(self,c):self.c=c
    def token(self,audience):return self.c['oidcTokens'][audience]

class AITransport:
    def __init__(self,port,cert):self.http=HTTPS(ca_file=cert);self.endpoint=Endpoint('https://localhost:'+str(port),'https://localhost:'+str(port))
    def request(self,endpoint,method,path,body,headers):
        assert endpoint.url=='https://api.openai.com'
        return self.http.request(self.endpoint,method,path,body,headers)
class Google:
    account=g.rates()['google_account']
    def __init__(self,port,cert):self.ai=AITransport(port,cert)
    def __call__(self,wire,sku,units):
        v,s,u=google_request(wire);assert (s,u)==(sku,units)
        path='/v1/places:searchText' if v['operation']=='search' else '/distanceMatrix/v2:computeRouteMatrix'
        return HTTPResult(200,self.ai.http.request(self.ai.endpoint,'POST',path,json.dumps(v['body']).encode(),{'Content-Type':'application/json'}))

def serve(pipe,c,credentials,provider,cert,key):
    name=c['principal'];role=c['service']
    expected={'SYNTHETIC_REDIS_PASSWORD'} if role in ('factory','dispatcher') else set()
    if {k for k in os.environ if k.startswith('SYNTHETIC_')}!=expected:raise AssertionError('Privileged fixture credentials inherited')
    if ('encryptionKey' in c)!=(role=='factory'):raise AssertionError('Unnecessary locator key')
    def db(name='witness',**kw):
        if name not in credentials:raise AssertionError('Role cannot acquire another credential')
        return psycopg.connect(**credentials[name],connect_timeout=2,**kw)
    try:
        with calendar_clock(NOW):
            def epoch():
                with db() as connection:return connection.execute('SELECT provider_witness.epoch()').fetchone()[0]
            def nonce(*args):
                with db() as connection:connection.execute('SELECT provider_witness.hosted_nonce(%s,%s,%s,%s,%s)',args)
            auth=Auth(c,nonce,epoch);client=ServiceClient(c,Identity(c),HTTPS(ca_file=cert)) if role not in ('counter','recovery') else None
            kw={}
            if role=='factory':
                owner=DispatchOwner(Owner(name,BUILD,g.EPOCH,name))
                def make():
                    w=ScopedWitness(lambda:db(),lambda:db());service=RemoteSend(w,lambda:db('issuer'),client,owner)
                    s=Store(connection=lambda **kw:db('runtime',**kw),issuer=lambda:db('issuer'),service=service,evidence=g.cache(),key=g.KEY,limits=g.LIMITS)
                    issuer=Issuer(lambda:db('issuer'),g.ROOT)
                    def no_send(*args):raise AssertionError('Factory cannot send provider traffic')
                    model=Inference(s,lambda:db('issuer'),g.ROOT,RemoteCounter(client),no_send);b=Broker(s,issuer,model,no_send,now=NOW);service.check_current=b.check_current;return b
                kw=dict(owner=owner,broker=make,issuer=lambda:db('issuer'))
            if role=='counter':kw=dict(counter=CounterCallback(OpenAIHTTP(g.PROJECT,lambda:'sk-FICTIONAL-COUNT-ONLY',AITransport(provider,cert),purpose='count'),CounterAuthority(lambda:db('counter'),CounterWitness(lambda:db(),lambda:db()),g.PROJECT)))
            if role=='dispatcher':
                def store(worker):return DeliveryStore(worker,connection=lambda **kw:db('delivery',**kw),witness=ScopedWitness(lambda:db(),lambda:db()),evidence=g.cache(),key=g.KEY,limits=g.LIMITS)
                router=OwnerRouter({n:Owner(n,BUILD,g.EPOCH,n) for n in ('factory-a','factory-b')},client)
                kw=dict(delivery=store,router=router,responder=DispatcherCallback(OpenAIHTTP(g.PROJECT,lambda:'sk-FICTIONAL-GENERATION',AITransport(provider,cert),purpose='generation'),Google(provider,cert),Accounting(),time.time))
            r=Role(c,auth=auth,client=client,epoch=epoch,**kw)
            if role=='backend':
                import uvicorn
                server=uvicorn.Server(uvicorn.Config(backend_app(r),host='127.0.0.1',port=c['port'],ssl_certfile=cert,ssl_keyfile=key,log_level='warning',access_log=False));pipe.send('ready');server.run()
            else:
                server=privileged_server(r,tls=(cert,key));pipe.send('ready');server.serve_forever()
    except BaseException as e:pipe.send({'error':type(e).__name__+':'+str(e)});raise

class Tests(unittest.TestCase):
    def setUp(self):
        for n in ('K_SERVICE','NODE_ENV','WHERETO_ENV','WHERETO_REAL_DEV','WHERETO_PLACES_DEV','WHERETO_ROUTES_DEV'):os.environ.pop(n,None)
        if self._testMethodName=='test_uncertain_google_send_preserves_charge_and_never_retries':self.behavior='/v1/places:searchText'
        enroll_fixture();self.tmp=self.enterContext(TemporaryDirectory(prefix='real-rpc-fixture-'));p=Path(self.tmp);self.cert=str(p/'cert.pem');self.key=str(p/'key.pem')
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',self.key,'-out',self.cert,'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.ctx=mp.get_context('spawn');self.workers=[]
        self.addCleanup(self.cleanup)
        self.pp,self.provider=self.start(responder,self.cert,self.key,getattr(self,'behavior',None));self.provider_port=self.pp.recv()
        ports={}
        for n in ('backend','factory-a','factory-b','counter','dispatcher','recovery'):
            with socket.socket() as s:s.bind(('127.0.0.1',0));ports[n]=s.getsockname()[1]
        self.configs,self.users=configurations(ports,self.cert);self.ports=ports
        self.credentials={}
        for name in ports:
            role='factory' if name.startswith('factory') else name
            mapping={'witness':(ROLES[role],5433,'SYNTHETIC_COUNTER_PASSWORD' if role=='counter' else 'SYNTHETIC_WITNESS_SERVICE_PASSWORD')}
            if role=='factory':mapping.update(runtime=('whereto_real_worker',5432,'SYNTHETIC_WORKER_PASSWORD'),issuer=('real_issuer_client',5432,'SYNTHETIC_ISSUER_PASSWORD'))
            if role=='counter':mapping['counter']=('real_counter_client',5432,'SYNTHETIC_COUNTER_PASSWORD')
            if role=='dispatcher':mapping['delivery']=('real_dispatch_client',5432,'SYNTHETIC_WORKER_PASSWORD')
            self.credentials[name]={k:dict(host='127.0.0.1',port=port,dbname='whereto_witness' if port==5433 else 'whereto_synthetic',user=user,password=sha256((os.environ[env]+'\0'+user).encode()).hexdigest()) for k,(user,port,env) in mapping.items()}
        for n in ('counter','dispatcher','recovery','factory-a','factory-b','backend'):
            pipe,process=self.start(serve,self.configs[n],self.credentials[n],self.provider_port,self.cert,self.key);self.assertTrue(pipe.poll(15));self.assertEqual(pipe.recv(),'ready')
            self.workers[-1]=(process,pipe,n)
        self.http=HTTPS(ca_file=self.cert)
        self.endpoint=Endpoint('https://localhost:'+str(ports['backend']),self.configs['backend']['audiences']['backend'])
        self.wait_backend()
    def wait_backend(self):
        for _ in range(50):
            try:
                with socket.create_connection(('127.0.0.1',self.ports['backend']),timeout=.2):return
            except OSError:time.sleep(.1)
        raise AssertionError('Backend did not listen')
    def handoff(self):
        for p,pipe,name in self.workers:
            if name in ('backend','factory-a'):p.terminate();p.join(5)
        c=deepcopy(self.configs['backend']);c['networkTargets']['factory']['url']='https://localhost:'+str(self.ports['factory-b'])
        pipe,p=self.start(serve,c,self.credentials['backend'],self.provider_port,self.cert,self.key)
        self.assertTrue(pipe.poll(15));self.assertEqual(pipe.recv(),'ready');self.workers[-1]=(p,pipe,'backend-replacement');self.wait_backend()
    def start(self,target,*args):
        parent,child=self.ctx.Pipe();p=self.ctx.Process(target=target,args=(child,*args))
        # Strip controller/admin credential seeds BEFORE spawning, not after the
        # child has received them. Only explicit role-owned credentials cross.
        env={k:v for k,v in os.environ.items() if not k.startswith('SYNTHETIC_')}
        if target is serve and args[0]['service'] in ('factory','dispatcher'):env['SYNTHETIC_REDIS_PASSWORD']=os.environ['SYNTHETIC_REDIS_PASSWORD']
        with patch.dict(os.environ,env,clear=True):p.start()
        self.workers.append((p,parent,'provider'));return parent,p
    def cleanup(self):
        for p,pipe,_ in reversed(self.workers):
            if p.is_alive():p.terminate()
            p.join(5);pipe.close()
    def call(self,path,value,who='alice',*,alter_body=False):
        c=self.configs['frontend'];raw=json.dumps(value,separators=(',',':')).encode();now=int(time.time());iap=self.users[who]
        f=signed(c,dict(iss=FORWARD,sub='frontend',aud='public-user-pipeline',iat=now,exp=now+60,jti=secrets.token_hex(16),build=BUILD,environment=c['identityEnvironment'],epoch=g.EPOCH,request=binding('public-user-pipeline','POST',path,raw),iap=digest(iap.encode())))
        oidc=c['oidcTokens'][c['audiences']['backend']]
        proof=signed(c,dict(iss=REQUEST,sub='frontend',aud='backend',iat=now,exp=now+60,jti=secrets.token_hex(16),build=BUILD,environment=c['identityEnvironment'],epoch=g.EPOCH,request=binding('backend','POST',path,raw),oidc=digest(oidc.encode()),iap=digest(iap.encode()),forward=digest(f.encode())))
        headers={'Content-Type':'application/json','Authorization':'Bearer '+oidc,'X-Whereto-Context':b64(canonical(dict(proof=proof,iap=iap,forward=f)))}
        self.last_request=(path,raw,headers)
        return json.loads(self.http.request(self.endpoint,'POST',path,raw+(b' ' if alter_body else b''),headers))
    def packets(self):
        out=[]
        while self.pp.poll(.05):out.append(self.pp.recv())
        return out
    def paths(self):return [v[0] for v in self.packets()]
    def test_public_fastapi_factory_counter_dispatcher_source_terminal(self):
        source=dict(text=TEXT,calendarTimezone='America/New_York');pending=self.call('/api/interpret',source)
        path,raw,headers=self.last_request
        with self.assertRaises(Exception):self.http.request(self.endpoint,'POST',path,raw,headers)
        handle=pending['privateOuting'];self.assertTrue(pending['questions'])
        with g.admin() as c:before=c.execute('SELECT sum(charge) FROM provider_state.operations').fetchone()[0]
        with self.assertRaises(Exception):self.call('/api/interpret',dict(**source,privateOuting=handle,answers={'date':'2026-11-07'}),who='bob')
        self.handoff()
        answered=self.call('/api/interpret',dict(**source,privateOuting=handle,answers={'date':'2026-11-07'}));self.assertIsNotNone(answered['request'])
        with g.admin() as c:self.assertEqual(c.execute('SELECT sum(charge) FROM provider_state.operations').fetchone()[0],before)
        self.assertEqual(answered['privateOuting']['expiresMs'],handle['expiresMs'])
        origin=dict(point=dict(id='device-origin',coordinates=dict(latitude=39.29,longitude=-76.61)),source='device',explicitly_authorized=True)
        cards=self.call('/api/plans/generate',dict(**answered['request'],privateOuting=answered['privateOuting'],startingLocation=origin));self.assertEqual(len(cards['provisionalPlans']),3);self.assertNotIn('privateOuting',cards)
        packets=self.packets();paths=[v[0] for v in packets];self.assertEqual(paths.count('/v1/responses/input_tokens'),1);self.assertEqual(paths.count('/v1/responses'),1);self.assertEqual(paths.count('/v1/places:searchText'),2)
        # Native plan_matrices creates origin→coffee (3 cells) and coffee→museum (9), not a retry.
        self.assertEqual(paths.count('/distanceMatrix/v2:computeRouteMatrix'),2);self.assertEqual(len({h for p,h in packets if p=='/distanceMatrix/v2:computeRouteMatrix'}),2)
        with g.admin() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM provider_state.real_response_receipts').fetchone()[0],1)
            self.assertEqual(c.execute('SELECT count(*) FROM provider_state.token_counts').fetchone()[0],1)
            self.assertEqual(c.execute('SELECT sum(charge) FROM provider_state.operations').fetchone()[0],190148)
            self.assertEqual(c.execute('SELECT count(*) FROM provider_state.native_checkpoints').fetchone()[0],1)
            self.assertEqual(c.execute("SELECT count(*) FROM provider_state.app_operations WHERE jsonb_array_length(quote->'lines')=2").fetchone()[0],1)
            self.assertNotIn('Fixture_',json.dumps(c.execute('SELECT payload FROM provider_state.evidence').fetchall()))
            self.assertEqual(c.execute('SELECT count(*) FROM provider_state.sessions s JOIN provider_state.native_checkpoints n ON n.session=s.id WHERE NOT s.revoked').fetchone()[0],0)
        with self.assertRaises(Exception):self.call('/api/plans/generate',dict(**answered['request'],privateOuting=answered['privateOuting'],startingLocation=origin))
        self.assertFalse(self.paths())


    def test_invalid_auth_and_wrong_role_cannot_reach_provider_or_counter(self):
        counter=Endpoint('https://localhost:'+str(self.ports['counter']),self.configs['counter']['audiences']['counter'])
        with self.assertRaises(Exception):self.http.request(counter,'POST','/count',b'{}',{'Content-Type':'application/json'})
        for principal,target,path in [('frontend','counter','/count'),('backend','dispatcher','/send')]:
            c=deepcopy(self.configs[principal]);c['networkTargets']={target:dict(url='https://localhost:'+str(self.ports[target]),audience=c['audiences'][target],service=target)};c['networkMethods']={target:[path]}
            with self.assertRaises(Exception):ServiceClient(c,Identity(c),self.http).request(target,path,{})
        with self.assertRaises(Exception):self.call('/api/interpret',dict(text=TEXT),alter_body=True)
        self.assertFalse(self.paths())
        with g.admin() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM provider_state.count_attempts').fetchone()[0],0)
            self.assertEqual(c.execute('SELECT count(*) FROM provider_state.operations').fetchone()[0],0)

    def test_real_delivery_role_cannot_issue_or_override_financial_authority(self):
        from psycopg.errors import InsufficientPrivilege
        with self.assertRaises(InsufficientPrivilege):
            with connect('dispatcher-db') as c:c.execute("SELECT provider_state.native_protocol('snapshot','{}','real',%s,NULL)",(g.EPOCH,))
        with self.assertRaises(InsufficientPrivilege):
            with connect('dispatcher-db') as c:c.execute("SELECT provider_state.app_accept('unapproved','reserve','{}')")
        with self.assertRaises(InsufficientPrivilege):
            with connect('dispatcher') as c:c.execute("SELECT provider_witness.protocol('reserve','{}')")
        from private_runtime.provider_callbacks import OpenAIHTTP
        counter=OpenAIHTTP(g.PROJECT,lambda:(_ for _ in ()).throw(AssertionError('Must refuse before key acquisition')),AITransport(self.provider_port,self.cert),purpose='count')
        from backend.ai.openai_candidate import request_bytes
        with self.assertRaises(Exception):counter.generate(request_bytes(TEXT))
        self.assertFalse(self.paths())


    def test_completed_request_reissues_native_admission_for_confirmed_device_origin(self):
        result=self.call('/api/interpret',dict(text=TEXT,preferences={'date':'2026-11-07'},calendarTimezone='America/New_York'))
        self.assertFalse(result['questions']);self.assertIsNotNone(result['request'])
        origin=dict(point=dict(id='device-origin',coordinates=dict(latitude=39.29,longitude=-76.61)),source='device',explicitly_authorized=True)
        cards=self.call('/api/plans/generate',dict(**result['request'],privateOuting=result['privateOuting'],startingLocation=origin));self.assertEqual(len(cards['provisionalPlans']),3)
        paths=self.paths();self.assertEqual(paths.count('/v1/responses'),1);self.assertEqual(paths.count('/v1/responses/input_tokens'),1)


    def test_uncertain_google_send_preserves_charge_and_never_retries(self):
        source=dict(text=TEXT,calendarTimezone='America/New_York');first=self.call('/api/interpret',source)
        ready=self.call('/api/interpret',dict(**source,privateOuting=first['privateOuting'],answers={'date':'2026-11-07'}))
        value=dict(**ready['request'],privateOuting=ready['privateOuting'],startingLocation=dict(point=dict(id='device-origin',coordinates=dict(latitude=39.29,longitude=-76.61)),source='device',explicitly_authorized=True))
        from private_runtime.https import Refused
        try:
            result=self.call('/api/plans/generate',value);self.assertFalse(result['provisionalPlans'])
        except Refused:pass
        self.assertEqual(self.paths(),['/v1/responses/input_tokens','/v1/responses','/v1/places:searchText'])
        with g.admin() as c:self.assertEqual(c.execute('SELECT sum(charge) FROM provider_state.operations').fetchone()[0],38148)
        with g.connect('witness') as c:status=c.execute("SELECT provider_witness.protocol('status','{}')").fetchone()[0]
        self.assertTrue(status['quarantined']);self.assertEqual(status['gross'],38148)
        with self.assertRaises(Refused):self.call('/api/plans/generate',value)
        self.assertFalse(self.paths())


    def test_missing_redis_locator_cannot_reinfer_or_reset_exposure(self):
        source=dict(text=TEXT,calendarTimezone='America/New_York');pending=self.call('/api/interpret',source)
        self.assertEqual(self.paths(),['/v1/responses/input_tokens','/v1/responses']);g.cache().client.flushdb()
        with self.assertRaises(Exception):self.call('/api/interpret',dict(**source,privateOuting=pending['privateOuting'],answers={'date':'2026-11-07'}))
        self.assertFalse(self.paths())
        with g.admin() as c:self.assertEqual(c.execute('SELECT sum(charge) FROM provider_state.operations').fetchone()[0],6148)

    def test_independent_epoch_change_stops_public_continuation(self):
        from psycopg.types.json import Jsonb
        source=dict(text=TEXT,calendarTimezone='America/New_York');pending=self.call('/api/interpret',source)
        self.assertEqual(self.paths(),['/v1/responses/input_tokens','/v1/responses'])
        with g.admin(True) as c:
            c.execute('SET LOCAL ROLE real_grant_operator');c.execute("SELECT provider_witness.operator('epoch',%s)",(Jsonb({'epoch':'f'*64}),))
        with self.assertRaises(Exception):self.call('/api/interpret',dict(**source,privateOuting=pending['privateOuting'],answers={'date':'2026-11-07'}))
        self.assertFalse(self.paths())
        with g.admin() as c:self.assertEqual(c.execute('SELECT sum(charge) FROM provider_state.operations').fetchone()[0],6148)

    def test_meaning_edit_revokes_source_without_new_inference(self):
        source=dict(text=TEXT,calendarTimezone='America/New_York');pending=self.call('/api/interpret',source)
        self.assertEqual(self.paths(),['/v1/responses/input_tokens','/v1/responses'])
        with self.assertRaises(Exception):self.call('/api/interpret',{**source,'text':TEXT+' and dinner','privateOuting':pending['privateOuting'],'answers':{'date':'2026-11-07'}})
        with self.assertRaises(Exception):self.call('/api/interpret',dict(**source,privateOuting=pending['privateOuting'],answers={'date':'2026-11-07'}))
        self.assertFalse(self.paths())
        with g.admin() as c:
            self.assertEqual(c.execute('SELECT sum(charge) FROM provider_state.operations').fetchone()[0],6148)
            self.assertEqual(c.execute('SELECT count(*) FROM provider_state.sessions s JOIN provider_state.native_checkpoints n ON n.session=s.id WHERE NOT s.revoked').fetchone()[0],0)
