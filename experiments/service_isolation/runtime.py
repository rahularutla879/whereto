"""Role-specific local adapters. Reuse existing grant, evidence and native algorithms."""
from contextlib import contextmanager
from contextvars import ContextVar
import json,os,secrets
from hashlib import sha256
from threading import RLock
from threading import Lock
from uuid import uuid4
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from experiments.shared_state.contracts import Denied,Unavailable,Limits,Reservation,WorkerLease,SessionHandle,Capability
from experiments.shared_state.application_grants import GrantService,FakeInference
from experiments.shared_state.native_sessions import NativeStore,NativeWitness,NativeIssuer,NativeBroker
from experiments.shared_state.redis_evidence import RedisEvidence,Keys
from experiments.shared_state.evidence_models import canonical,model_types,Membership
from experiments.service_isolation.auth import Client,b64,unb64


def connection(config,key='database'):
    p=config[key]
    if set(p)!=set('port dbname user password'.split()) or p['dbname'] not in ('whereto_synthetic','whereto_witness') or p['port'] not in (5432,5433):raise Denied('local_database')
    return psycopg.connect(host='127.0.0.1',connect_timeout=2,**p)

class ScopedWitness(NativeWitness):
    def __init__(self,service,reader):
        super().__init__(service,reader);self.epoch_reader=reader
    def epoch(self):
        try:
            active=self._active.get()
            if active is not None:return active.execute('SELECT witness.epoch()').fetchone()[0]
            with self.epoch_reader() as c:return c.execute('SELECT witness.epoch()').fetchone()[0]
        except psycopg.Error:raise Unavailable() from None
    def call(self,a,**p):
        try:
            with self.serial():r=self._active.get().execute('SELECT witness.service_protocol(%s,%s)',(a,Jsonb(p))).fetchone()[0]
        except (psycopg.IntegrityError,psycopg.DataError,psycopg.errors.RaiseException):raise Denied('scoped_witness') from None
        except psycopg.Error:raise Unavailable() from None
        if 'denied' in r:raise Denied('grant_stopped')
        return r

def witness(config):return ScopedWitness(lambda:connection(config,'witness'),lambda:connection(config,'witness'))
def cache(config):
    cache=RedisEvidence(config['redisPassword'],Keys('isolated-k1',{'isolated-k1':unb64(config['encryptionKey'])}))
    cache.client.connection_pool.connection_kwargs['username']=config['redisUsername']
    return cache

class CounterConnection:
    def __init__(self,client):self.client=client
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def execute(self,query,args):
        if query!='SELECT synthetic_state.app_count_input(%s,%s)' or len(args)!=2:raise Denied('counter_method')
        self.client.request('counter','/count',dict(capability=args[0],wire=b64(args[1])))

PENDING={}
PENDING_LOCK=Lock()
def current_dispatch(value):
    if set(value)!=set('permit operation ordinal digest'.split()):raise Denied('current_dispatch_shape')
    with PENDING_LOCK:
        expected=PENDING.pop(value['permit'],None)
    if expected is None or expected[:3]!=(value['operation'],value['ordinal'],value['digest']):raise Denied('current_dispatch_missing')
    expected[3]()
    return {'current':True}

class RemoteSend(GrantService):
    def __init__(self,w,issuer,client):super().__init__(w,issuer);self.client=client
    def send(self,store,reservation,ordinal,payload,fake):
        # Neither callbacks nor worker-selected responses cross this interface.
        l=reservation.lease
        permit=secrets.token_hex(32)
        with PENDING_LOCK:PENDING[permit]=(reservation.operation,ordinal,sha256(payload).hexdigest(),self.check_current)
        try:
            return self.client.request('dispatcher','/send',dict(operation=reservation.operation,capability=reservation.capability.token,
                token=l.session.token,revision=l.revision,worker=l.worker,fence=l.fence,ordinal=ordinal,payload=b64(payload),permit=permit))
        finally:
            with PENDING_LOCK:PENDING.pop(permit,None)


class DeliveryConnection:
    def __init__(self,config):self.config=config
    def __enter__(self):self.c=connection(self.config);return self
    def __exit__(self,*args):return self.c.__exit__(*args)
    def execute(self,query,args):
        if query!='SELECT synthetic_state.app_accept(%s,%s,%s)' or args[1]!='deliver':raise Denied('delivery_method')
        return self.c.execute('SELECT synthetic_state.service_accept_delivery(%s,%s)',(args[0],args[2]))

class DeliveryStore(NativeStore):
    """Minimal versioned connection adapter; runtime has a delivery-only SQL principal."""
    def __init__(self,config,worker):
        from experiments.service_isolation.identity import verify
        verify()
        self.service=GrantService(witness(config),lambda:DeliveryConnection(config))
        self.evidence=cache(config);self.current_epoch=self.service.witness.epoch
        self._epoch_context=ContextVar('delivery_epoch',default=None);self._proof=None;self._dispatch_lock=RLock()
        self._key=unb64(config['hashKey']);self._limits=Limits(**config['limits']);self._pid=os.getpid();self._worker=worker
        self._connection=dict(host='127.0.0.1',connect_timeout=2,prepare_threshold=None,row_factory=dict_row,**config['database'])
        with self._tx():pass
    def _invoke(self,c,action,args):
        return c.execute('SELECT synthetic_state.service_dispatch(%s,%s,%s,%s) AS result',
            (action,Jsonb(args),'synthetic',self._epoch_context.get())).fetchone()['result']


def make_broker(config):
    from backend.provider_budget import ProviderBudget,ProviderSettings
    from datetime import datetime
    issuer=lambda:connection(config,'issuer');client=Client(config)
    service=RemoteSend(witness(config),issuer,client)
    s=NativeStore(service=service,issuer_connection=issuer,evidence=cache(config),key=unb64(config['hashKey']),password=config['database']['password'],limits=Limits(**config['limits']))
    broker=None
    def records():
        a=broker._Broker__current;out={}
        def add(v):
            if isinstance(v,(list,tuple)):
                for x in v:add(x)
            else:
                from backend.interpretation import InterpretationResult
                if type(v) is InterpretationResult:out['interpretation_result']=v;return
                for k,t in model_types().items():
                    if type(v) is t:out[k]=v;break
        add(a['source']);add(a['interpretation'])
        if a['purpose']=='refresh':
            d=a['interpretation'];selected=next(x for x in d['itineraries'] if x['candidateId']==d['selectedId'])
            out={'membership':Membership(purpose='refresh',documentDigest=broker._digest(d),selectedId=str(d['selectedId']),allowedIds=[x['reference'] for x in selected['stops']])}
        if not out:raise Denied('unsupported_evidence')
        pending=out.get('request') is not None and out['request'].pending is not None
        return out,'synthetic_refresh' if a['purpose']=='refresh' else 'synthetic_pending_effective' if pending else 'synthetic_fresh'
    def no_inline(_):raise Denied('inline_transport_unavailable')
    model=FakeInference(s,issuer,lambda:CounterConnection(client),config['root'],no_inline)
    broker=NativeBroker(s,NativeIssuer(issuer,config['root'],records),model,ProviderBudget(ProviderSettings(mode='real',candidates_per_activity=3)),no_inline,now=datetime.fromisoformat(config['referenceTime']))
    model.broker=broker
    def check_current():
        from backend import action_dispatch as io
        context=io._active.set(broker)
        try:broker._check()
        finally:io._active.reset(context)
    service.check_current=check_current
    return broker


def dispatch(config,value):
    if set(value)!=set('operation capability token revision worker fence ordinal payload permit'.split()):raise Denied('dispatch_shape')
    from experiments.shared_state.postgres import uuid
    uuid(value['worker']);uuid(value['operation'])
    if type(value['ordinal']) is not int or type(value['revision']) is not int or type(value['fence']) is not int:raise Denied('dispatch_numeric')
    s=DeliveryStore(config,value['worker']);lease=WorkerLease(SessionHandle(value['token']),value['revision'],value['worker'],value['fence'])
    r=Reservation(value['operation'],lease,Capability(value['capability']));payload=unb64(value['payload'])
    if canonical(json.loads(payload))!=payload:raise Denied('canonical_payload')
    s.recover(lease) # Read trusted encrypted source, not only a matching digest.
    Client(config).request('factory','/dispatch-check',dict(permit=value['permit'],operation=value['operation'],ordinal=value['ordinal'],digest=sha256(payload).hexdigest()))
    from experiments.service_isolation.synthetic import respond
    return s.service.send(s,r,value['ordinal'],payload,respond)
