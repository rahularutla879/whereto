"""Factory-only source tickets. No Google graphs, callbacks or result snapshots.

The caller supplies the authenticated principal digest from the existing verified
IAP boundary; this inactive library does not authenticate browser headers. No
public route or startup selector is installed by importing it.
"""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from time import monotonic
import hmac,secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from pydantic import BaseModel,ConfigDict,Field,model_validator
from psycopg.types.json import Jsonb
from backend.ai import Interpretation
from backend.interpretation import InterpretationInput,InterpretationResult,ClarificationAnswers
from backend.routes import AuthorizedStart
from backend.real_planning import PlannerInput
from experiments.shared_state.contracts import Denied,Kind,SessionHandle
from experiments.shared_state.bridge_models import ProviderAction
from experiments.shared_state.action_bridge import Source
from experiments.shared_state.native_sessions import restore_validation
from experiments.shared_state.evidence_models import canonical,plain,strict_json,MAX_BYTES,no_credentials
from experiments.shared_state.application_grants import Witness as ParentWitness
from .checkpoint_sql import VERSION

class Execution(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    startingLocation: AuthorizedStart|None=None
    @model_validator(mode='after')
    def user_origin_only(self):
        s=self.startingLocation
        # A manual place can contain geocoded Google content. Only explicitly
        # supplied device coordinates are admitted until its provenance is reviewed.
        if s is not None and (s.source!='device' or s.point.place_id is not None or s.label is not None or s.geographicDescription is not None or s.reference_coordinates is not None):raise ValueError('User device origin required')
        return self
    def controls(self):return {} if self.startingLocation is None else {'startingLocation':self.startingLocation}

class Record(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    version: str=Field(pattern='^52-real-source-ticket-v1$')
    build: str=Field(pattern='^[0-9a-f]{64}$')
    owner: str=Field(pattern='^[0-9a-f]{64}$')
    value: InterpretationInput
    raw: Interpretation
    result: InterpretationResult
    execution: Execution
    reference: datetime
    revision: int=Field(ge=1,le=20)
    created: int=Field(gt=0)
    expires: int=Field(gt=0)
    inference: str=Field(pattern='^[0-9a-f]{64}$')
    completed: str=Field(pattern='^[0-9a-f-]{36}$')
    answers: list[ClarificationAnswers]=Field(max_length=19)
    @model_validator(mode='after')
    def bounded(self):
        if self.reference.utcoffset() is None or self.value.pending is not None or any(self.value.answers.model_dump().values()) or self.expires>self.created+600000 or self.expires<=self.created or self.revision!=len(self.answers)+1:raise ValueError('Source contract')
        return self

class Witness(ParentWitness):
    def call(self,a,**p):
        if a!='checkpoint':return super().call(a,**p)
        with self.serial():
            result=self._active.get().execute('SELECT witness.native_protocol(%s,%s)',(a,Jsonb(p))).fetchone()[0]
        if 'denied' in result:raise Denied('real_source_witness')
        return result

@dataclass(frozen=True,repr=False)
class Ticket:
    handle: SessionHandle
    revision: int

class Checkpoint:
    def __init__(self,broker,token,issuer,owner,lease,record,blob):
        self.broker,self.token,self.issuer,self.owner,self.lease,self.record,self.blob=broker,token,issuer,owner,lease,record,blob
        self.running=False;broker.checkpoint=self
        broker._Broker__issuer.checkpoint=lease
    @staticmethod
    def build():
        from .identity import verify_application
        return verify_application()
    @staticmethod
    def action(b,source):
        return ProviderAction(purpose='pending' if source.result.pending else 'ordinary',sourceDigest=b._digest(source.value),interpretationDigest=b._digest(source.result),requestRevision=source.revision)
    @property
    def store(self):return self.broker.store
    @property
    def ticket(self):return Ticket(self.lease.session,self.lease.revision)
    def clock(self):return self.store._call('evidence_clock')['now_ms']
    def check(self):
        self.store.meta(self.lease)
        if self.clock()>=self.record.expires:raise Denied('real_source_expired')
    def _publish(self,record,previous=None):
        # model_copy is intentionally not a validation boundary in Pydantic.
        record=Record.model_validate_json(canonical(plain(record)))
        s=self.store;m=s.meta(self.lease);a=m['anchor']
        if (a is None)!=(previous is None) or (a and sha256(previous).hexdigest()!=a['commitment']):raise Denied('real_source_cas')
        raw=canonical(plain(record));no_credentials(plain(record))
        if len(raw)>MAX_BYTES:raise Denied('real_source_size')
        deadline=min(record.expires,m['expires_ms'],a['expires_ms'] if a else m['expires_ms'])
        if deadline!=record.expires or deadline<=self.clock():raise Denied('real_source_deadline')
        anchor=dict(session=m['session'],revision=m['revision'],generation=(a['generation'] if a else 0)+1,expires_ms=deadline,key_id=s.evidence.keys.active,environment='real',epoch=s.current_epoch())
        nonce=secrets.token_bytes(12);blob=nonce+AESGCM(s.evidence.keys.key(anchor['key_id'])).encrypt(nonce,raw,s._aad(m,anchor))
        s.evidence.publish(s.evidence.path('real',anchor['epoch'],m['session']),previous,blob,deadline)
        with self.issuer() as c:c.execute('SELECT provider_state.evidence_anchor(%s,%s,%s,%s,%s,%s,%s,%s)',(m['session'],m['revision'],anchor['generation']-1,sha256(blob).hexdigest(),anchor['key_id'],deadline,'real',anchor['epoch']))
        with s.service.witness.serial():
            s.service.sync(s);q=s._call('native_quote',**s._lease(self.lease))
            s.service.witness.call('checkpoint',quote=q,observed=s.service.observed(s))
            with self.issuer() as c:c.execute('SELECT provider_state.native_commit(%s,%s)',(Jsonb(s._lease(self.lease)),Jsonb(q)))
            s.service.sync(s)
        self.record,self.blob=record,blob
    @classmethod
    def capture(cls,b,token,issuer,owner):
        source=b._source(token);s=b.store
        if getattr(b,'checkpoint',None) is not None or len(b._Broker__model.receipts)!=1 or source.planned_revision or source.advanced or source.options or source.details:raise Denied('real_source_only')
        now=s._call('evidence_clock')['now_ms'];created=now-int((monotonic()-source.created)*1000)
        record=Record(version=VERSION,build=cls.build(),owner=owner,value=source.value,raw=source.raw,result=source.result,execution=Execution.model_validate(source.execution),reference=b.now,revision=1,created=created,expires=created+600000,inference=source.inference,completed=b._Broker__model.receipts[0],answers=[])
        h=s.create(Kind.ACTION,cls.action(b,source),ttl=b.remaining());lease=s.claim(h,1)
        # Fixed SQL expiry may round below the original deadline; never renew it.
        record=record.model_copy(update={'expires':min(record.expires,s.meta(lease)['expires_ms'])})
        with issuer() as c:c.execute('SELECT provider_state.real_source_enroll(%s,%s,%s,%s,%s)',(s._hash(h.token,'session'),source.inference,owner,record.build,record.completed))
        cp=cls(b,token,issuer,owner,lease,record,None);cp._publish(record);return cp
    @classmethod
    def resume(cls,b,ticket,issuer,owner):
        if type(ticket)is not Ticket or getattr(b,'checkpoint',None) is not None or b._started or b._Broker__sources:raise Denied('real_source_ticket')
        s=b.store;build=cls.build();s.service.sync(s)
        with s._tx() as c:owned=c.execute('SELECT provider_state.real_source_owner(%s,%s,%s,%s)',(s._hash(ticket.handle.token,'session'),ticket.revision,owner,build)).fetchone()['real_source_owner']
        if str(owned['root'])!=b._Broker__issuer.root:raise Denied('real_source_root')
        lease=s.claim(ticket.handle,ticket.revision);s._call('native_ready',**s._lease(lease));m=s.meta(lease);a=m['anchor']
        if m['budget']!={'root':owned['root'],'outing':owned['outing']}:raise Denied('real_source_budget')
        if not a or a['epoch']!=s.current_epoch():raise Denied('real_source_anchor')
        blob=s.evidence.get(s.evidence.path('real',a['epoch'],m['session']))
        if not hmac.compare_digest(sha256(blob).hexdigest(),a['commitment']):raise Denied('real_source_integrity')
        try:
            raw=AESGCM(s.evidence.keys.key(a['key_id'])).decrypt(blob[:12],blob[12:],s._aad(m,{k:v for k,v in a.items() if k!='commitment'}))
            record=Record.model_validate_json(raw)
            if canonical(plain(record))!=raw:raise ValueError()
        except (InvalidTag,ValueError):raise Denied('real_source_record') from None
        now=s._call('evidence_clock')['now_ms']
        if record.completed!=str(owned['completed']) or record.inference!=owned['inference']:raise Denied('real_source_inference')
        if record.owner!=owner or record.build!=build or record.expires!=a['expires_ms'] or record.expires<=now or s.meta(lease)!=m:raise Denied('real_source_changed')
        doc=record.model_dump();doc.update(value=record.value,raw=record.raw,result=record.result,reference=record.reference,execution=record.execution.controls(),answers=record.answers)
        # Interpretation consults the native real-mode guard. Revalidate under
        # a fresh HTTP admission, not outside the action (which selects mock
        # semantics). Recorded uses retained typed evidence, never provider I/O.
        stamp=monotonic();b.now=record.reference;b._deadline=stamp+(record.expires-now)/1000;b._started=True
        with b._action('pending',record.value,record.result,record.revision,verify=lambda:s.meta(lease)):
            registry,scope,out=restore_validation(doc,now)
        if b._digest(record.value)!=m['action']['sourceDigest'] or b._digest(record.result)!=m['action']['interpretationDigest'] or record.revision!=m['action']['requestRevision']:raise Denied('real_source_binding')
        source=Source(record.value,record.result,record.raw,None,scope,'');source.execution=record.execution.controls();source.inference=record.inference;source.revision=record.revision;source.created=stamp+(record.created-now)/1000
        if not record.answers:source.outcome=(registry,out)
        if record.result.request is not None:source.payload=PlannerInput.model_validate({**record.result.request.model_dump(),**source.execution})
        source.digest=b._seal(source);token=secrets.token_urlsafe(32);b._Broker__sources[token]=source
        return cls(b,token,issuer,owner,lease,record,blob)
    def invoke(self,method,*args):
        if method not in ('answer','plan'):raise Denied('real_source_method')
        s=self.store;self.check();s.service.sync(s);s._call('native_begin',**s._lease(self.lease));self.running=True
        try:
            if method=='plan' and args:
                if len(args)!=1 or type(args[0])is not Execution:raise Denied('real_execution_controls')
                source=self.broker._source(self.token)
                if source.result.request is None:raise Denied('real_ordinary_required')
                source.execution=args[0].controls();source.payload=PlannerInput.model_validate({**source.result.request.model_dump(),**source.execution});source.digest=self.broker._seal(source)
                if source.outcome is not None:
                    doc=self.record.model_dump();doc.update(value=source.value,raw=source.raw,result=source.result,reference=self.record.reference,execution=source.execution,answers=self.record.answers)
                    with self.broker._action('pending',source.value,source.result,source.revision,verify=lambda:s.meta(self.lease)):
                        registry,scope,out=restore_validation(doc,self.clock())
                    source.scope=scope;source.outcome=(registry,out);source.digest=self.broker._seal(source)
                result=self.broker.plan(self.token)
            else:result=getattr(self.broker,method)(self.token,*args)
            if method=='answer':
                source=self.broker._source(self.token)
                record=self.record.model_copy(update=dict(result=source.result,revision=source.revision,answers=[*self.record.answers,args[0]]))
                rev=s._call('native_revise',**s._lease(self.lease),**s._prepared(Kind.ACTION,self.action(self.broker,source)))['revision']
                self.lease=s.claim(self.lease.session,rev);self.broker._Broker__issuer.checkpoint=self.lease;self._publish(record,self.blob)
            return result
        finally:
            self.running=False
            if method=='plan':
                # The durable turn already forbids retry even if revocation fails.
                s._call('native_revoke',**s._lease(self.lease))
