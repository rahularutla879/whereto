"""Real bindings for existing /count, /send and exact-owner callback RPCs.

No credentials, networking target discovery or startup selector. All dependencies
are supplied by the role's reviewed connection/identity lifecycle.
"""
from dataclasses import asdict
from hashlib import sha256
import os,re
import psycopg
from psycopg.types.json import Jsonb
from experiments.shared_state.contracts import Denied,Unavailable,WorkerLease,SessionHandle,Reservation,Capability
from experiments.shared_state.application_grants import Witness as ParentWitness
from experiments.service_isolation.auth import b64,unb64
from experiments.shared_state.evidence_models import canonical,strict_json
from private_runtime.real_finance.runtime import Service
from private_runtime.provider_callbacks import CountRecord,count_payload,generation_source
from .store import Store

class ScopedWitness(ParentWitness):
    def epoch(self):return self.call('epoch')['epoch']
    def call(self,a,**p):
        try:
            with self.serial():r=self._active.get().execute('SELECT provider_witness.service_protocol(%s,%s)',(a,Jsonb(p))).fetchone()[0]
        except (psycopg.IntegrityError,psycopg.DataError,psycopg.errors.RaiseException,psycopg.errors.NoDataFound):raise Denied('real_service_witness') from None
        except psycopg.Error:raise Unavailable() from None
        if 'denied' in r:raise Denied('grant_quarantined_or_stopped')
        return r

class RemoteCounter:
    def __init__(self,client):self.client=client
    def count(self,capability,wire):
        generation_source(wire)
        if type(capability)is not str or not re.fullmatch('[0-9a-f]{64}',capability):raise Denied('real_counter_capability')
        result=self.client.request('counter','/count',dict(capability=capability,wire=b64(wire)))
        if type(result)is not dict or set(result)!=set(CountRecord.__dataclass_fields__):raise Denied('real_counter_response')
        r=CountRecord(**result)
        if r.generation_sha256!=sha256(wire).hexdigest() or r.count_sha256!=sha256(count_payload(wire)).hexdigest() or type(r.raw_response_sha256)is not str or not re.fullmatch('[0-9a-f]{64}',r.raw_response_sha256) or type(r.tokens)is not int or not 1<=r.tokens<=100000:raise Denied('real_counter_response')
        return r # Not a permit: factory still reads protected real_llm_spec.

def count(value,callback):
    if type(value)is not dict or set(value)!={'capability','wire'} or type(value['capability'])is not str or not re.fullmatch('[0-9a-f]{64}',value['capability']):raise Denied('real_counter_shape')
    wire=unb64(value['wire']);generation_source(wire)
    return asdict(callback.count(value['capability'],wire))

class RemoteSend(Service):
    def __init__(self,witness,issuer,client,owner):
        super().__init__(witness,issuer);self.client,self.owner=client,owner
    def send(self,store,reservation,ordinal,payload,_unused):
        lease=reservation.lease
        with self.owner.permit(reservation.operation,ordinal,payload,self.check_current) as callback:
            return self.client.request('dispatcher','/send',dict(operation=reservation.operation,capability=reservation.capability.token,token=lease.session.token,revision=lease.revision,worker=lease.worker,fence=lease.fence,ordinal=ordinal,payload=b64(payload),callback=callback))

class DeliveryConnection:
    """The dispatcher has no issuer connection or arbitrary app_accept access."""
    def __init__(self,connection):self.connection=connection
    def __enter__(self):self.cm=self.connection();self.c=self.cm.__enter__();return self
    def __exit__(self,*a):return self.cm.__exit__(*a)
    def execute(self,query,args):
        if query!='SELECT provider_state.app_accept(%s,%s,%s)' or args[1]!='deliver':raise Denied('real_delivery_method')
        return self.c.execute('SELECT provider_state.service_accept_delivery(%s,%s)',(args[0],args[2]))

class DeliveryStore(Store):
    def __init__(self,worker,*,connection,witness,evidence,key,limits):
        from experiments.shared_state.postgres import uuid
        uuid(worker)
        super().__init__(connection=connection,issuer=lambda:DeliveryConnection(connection),service=Service(witness,lambda:DeliveryConnection(connection)),evidence=evidence,key=key,limits=limits)
        self._worker=worker
    def _invoke(self,c,a,p):
        return c.execute('SELECT provider_state.service_dispatch(%s,%s,%s,%s) AS result',(a,Jsonb(p),'real',self._epoch_context.get())).fetchone()['result']

def dispatch(value,*,store_factory,router,caller,responder):
    if type(value)is not dict or set(value)!=set('operation capability token revision worker fence ordinal payload callback'.split()):raise Denied('real_dispatch_shape')
    from experiments.shared_state.postgres import uuid
    uuid(value['worker']);uuid(value['operation'])
    if any(type(value[k])is not int or value[k]<1 for k in ('ordinal','revision','fence')):raise Denied('real_dispatch_numeric')
    for k in ('token','capability'):
        if type(value[k])is not str or not re.fullmatch('[A-Za-z0-9_-]{40,100}',value[k]):raise Denied('real_dispatch_token')
    payload=unb64(value['payload']);callback=value['callback']
    if len(payload)>100000 or canonical(strict_json(payload))!=payload or type(callback)is not dict or any(callback.get(k)!=v for k,v in dict(operation=value['operation'],ordinal=value['ordinal'],digest=sha256(payload).hexdigest()).items()):raise Denied('real_dispatch_callback')
    s=store_factory(value['worker'])
    if type(s)is not DeliveryStore:raise Denied('real_delivery_store')
    lease=WorkerLease(SessionHandle(value['token']),value['revision'],value['worker'],value['fence'])
    r=Reservation(value['operation'],lease,Capability(value['capability']))
    s.recover(lease);router.check(callback,caller)
    return s.service.send(s,r,value['ordinal'],payload,responder)
