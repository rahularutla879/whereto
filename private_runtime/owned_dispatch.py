"""Versioned routing adapter; retains original grant/evidence delivery algorithms."""
from hashlib import sha256
from contextvars import ContextVar
CALLER=ContextVar('verified_dispatch_caller',default=None)
from experiments.shared_state.application_grants import GrantService
from experiments.shared_state.contracts import Denied,Reservation,WorkerLease,SessionHandle,Capability
from experiments.service_isolation.auth import b64,unb64
from experiments.shared_state.evidence_models import canonical,strict_json
from private_runtime.registry import current
from private_runtime.dispatch_owner import DispatchOwner,Owner,OwnerRouter

_owner=None
_router=None

def configure(config):
    global _owner,_router
    p=current()
    if p.role=='factory':
        if _owner is not None:raise Denied('owner_installation')
        enrollment=Owner(**config['factoryOwner'])
        if enrollment.principal!=config['principal'] or enrollment.build!=config['build'] or enrollment.epoch!=config['epoch']:raise Denied('owner_scope')
        _owner=DispatchOwner(enrollment)
    elif p.role=='dispatcher':
        if _router is not None:raise Denied('owner_installation')
        enrolled={k:Owner(**v) for k,v in config['factoryOwners'].items()}
        if len({o.principal for o in enrolled.values()})!=len(enrolled):raise Denied('owner_principals')
        _router=OwnerRouter(enrolled,p.client)

def owner():
    current('factory')
    if _owner is None:raise Denied('owner_missing')
    return _owner

class OwnedRemoteSend(GrantService):
    def __init__(self,w,issuer,client):super().__init__(w,issuer);self.client=client
    def send(self,store,reservation,ordinal,payload,fake):
        l=reservation.lease
        with owner().permit(reservation.operation,ordinal,payload,self.check_current) as callback:
            return self.client.request('dispatcher','/send',dict(operation=reservation.operation,capability=reservation.capability.token,
                token=l.session.token,revision=l.revision,worker=l.worker,fence=l.fence,ordinal=ordinal,payload=b64(payload),callback=callback))

def dispatch(config,value,responder):
    current('dispatcher')
    if set(value)!=set('operation capability token revision worker fence ordinal payload callback'.split()):raise Denied('dispatch_shape')
    from experiments.shared_state.postgres import uuid
    from experiments.service_isolation.runtime import DeliveryStore
    uuid(value['worker']);uuid(value['operation'])
    if any(type(value[k]) is not int for k in ('ordinal','revision','fence')):raise Denied('dispatch_numeric')
    payload=unb64(value['payload']);callback=value['callback']
    if canonical(strict_json(payload))!=payload or type(callback) is not dict or any(callback.get(k)!=v for k,v in dict(operation=value['operation'],ordinal=value['ordinal'],digest=sha256(payload).hexdigest()).items()):raise Denied('dispatch_callback_binding')
    s=DeliveryStore(config,value['worker']);lease=WorkerLease(SessionHandle(value['token']),value['revision'],value['worker'],value['fence']);r=Reservation(value['operation'],lease,Capability(value['capability']))
    s.recover(lease)
    if _router is None:raise Denied('owner_missing')
    _router.check(callback,CALLER.get())
    return s.service.send(s,r,value['ordinal'],payload,responder)
