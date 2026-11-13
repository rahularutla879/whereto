"""Exact-owner, nonportable admission callbacks. No reconstruction or retry."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from threading import Condition
from time import monotonic
from hashlib import sha256
import secrets,os,re
from experiments.shared_state.contracts import Denied

@dataclass(frozen=True)
class Owner:
    slot:str
    build:str
    epoch:str
    principal:str|None=None
    def __post_init__(self):
        if self.principal is None:object.__setattr__(self,'principal',self.slot)
        if not re.fullmatch('[a-z][a-z0-9-]{0,62}',self.slot) or any(not re.fullmatch('[0-9a-f]{64}',x) for x in (self.build,self.epoch)) or not re.fullmatch('[a-z][a-z0-9-]{0,62}',self.principal):raise Denied('dispatch_owner_enrollment')

class DispatchOwner:
    def __init__(self,owner):
        if type(owner) is not Owner:raise Denied('dispatch_owner_enrollment')
        self.owner=owner;self.boot=secrets.token_hex(32);self._pid=os.getpid();self._condition=Condition();self._state='active';self._actions=0;self._pending={};self._action=ContextVar('owned_dispatch_action',default=None)
    @contextmanager
    def action(self):
        with self._condition:
            if self._pid!=os.getpid() or self._state!='active':raise Denied('factory_draining')
            self._actions+=1
        token=self._action.set(secrets.token_hex(32))
        try:yield
        finally:
            self._action.reset(token)
            with self._condition:self._actions-=1;self._condition.notify_all()
    @contextmanager
    def permit(self,operation,ordinal,payload,check_current):
        if self._action.get() is None or not callable(check_current) or type(payload) is not bytes or type(ordinal) is not int or ordinal<1:raise Denied('dispatch_action')
        value=dict(owner=self.owner.slot,principal=self.owner.principal,build=self.owner.build,epoch=self.owner.epoch,boot=self.boot,permit=secrets.token_hex(32),operation=operation,ordinal=ordinal,digest=sha256(payload).hexdigest())
        with self._condition:
            if self._state=='stopped' or self._pid!=os.getpid():raise Denied('dispatch_owner_stopped')
            self._pending[value['permit']]=(value,monotonic()+5,check_current)
        try:yield dict(value)
        finally:
            with self._condition:self._pending.pop(value['permit'],None);self._condition.notify_all()
    def check(self,value):
        if type(value) is not dict or set(value)!=set('owner principal build epoch boot permit operation ordinal digest'.split()):raise Denied('dispatch_owner_shape')
        with self._condition:
            if self._pid!=os.getpid() or self._state=='stopped' or value['boot']!=self.boot:raise Denied('dispatch_owner_replaced')
            p=self._pending.get(value['permit'])
            if p is None or p[0]!=value:raise Denied('dispatch_owner_missing')
            self._pending.pop(value['permit'])
        if monotonic()>=p[1]:raise Denied('dispatch_owner_expired')
        p[2]() # Original live source, SQL/evidence/fence and HTTP/inference admission check.
        return {'current':True,'owner':self.owner.slot,'boot':self.boot}
    def drain(self,timeout=8):
        if not 0<=timeout<=8:raise Denied('drain_deadline')
        end=monotonic()+timeout
        with self._condition:
            self._state='draining'
            while self._actions and monotonic()<end:self._condition.wait(end-monotonic())
            completed=self._actions==0
            self._state='stopped';self._pending.clear();return completed

class OwnerRouter:
    """Only reviewed endpoint slots. Caller never supplies a URL/audience."""
    def __init__(self,owners,client):
        self.owners=dict(owners);self.client=client
        if not 1<=len(owners)<=4 or any(type(v) is not Owner or k!=v.slot for k,v in owners.items()):raise Denied('dispatch_owner_enrollment')
    def check(self,value,principal):
        if type(value) is not dict:raise Denied('dispatch_owner_shape')
        owner=self.owners.get(value.get('owner'))
        if owner is None or principal!=owner.principal or value.get('principal')!=owner.principal or value.get('build')!=owner.build or value.get('epoch')!=owner.epoch:raise Denied('dispatch_owner_scope')
        result=self.client.request(owner.slot,'/dispatch-check',value)
        if result!={'current':True,'owner':owner.slot,'boot':value['boot']}:raise Denied('dispatch_owner_response')
