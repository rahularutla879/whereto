"""Inactive native reconstruction. Server-owned tickets, synthetic evidence only."""
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime,timezone
from hashlib import sha256
import hmac
import json
import secrets
from threading import Lock
from time import monotonic
import zlib

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from pydantic import BaseModel
from psycopg.types.json import Jsonb
from experiments.shared_state.contracts import Denied,Kind,SessionHandle
from experiments.shared_state.bridge_models import ProviderAction
from experiments.shared_state.application_grants import GrantStore,GrantBroker,GrantIssuer,Witness
from experiments.shared_state.action_bridge import Source
from experiments.shared_state.evidence_models import canonical,strict_json,plain,data_view
from experiments.shared_state.native_graph import VERSION,Graph

MAX_RAW=512*1024
HEADER=b'WTNATIVE1\0'


class NativeWitness(Witness):
    def call(self,a,**p):
        if a!='checkpoint':return super().call(a,**p)
        import psycopg
        from experiments.shared_state.contracts import Unavailable
        try:
            with self.serial():
                r=self._active.get().execute('SELECT witness.native_protocol(%s,%s)',(a,Jsonb(p))).fetchone()[0]
        except (psycopg.IntegrityError,psycopg.DataError,psycopg.errors.RaiseException):raise Denied('native_witness') from None
        except psycopg.Error:raise Unavailable() from None
        if 'denied' in r:raise Denied('native_witness_stopped')
        return r


class NativeStore(GrantStore):
    def __init__(self,**kwargs):
        from experiments.shared_state.native_identity import verify
        verify();super().__init__(**kwargs)
    def _invoke(self,c,action,args):
        return c.execute('SELECT synthetic_state.native_protocol(%s,%s,%s,%s,%s) AS result',
          (action,Jsonb(args),'synthetic',self._epoch_context.get(),self._proof)).fetchone()['result']
    def _call(self,verb,**args):
        if verb in ('claim','revise','revoke','native_begin','native_revise','native_revoke'):
            with self.service.witness.serial():return super()._call(verb,**args)
        return super()._call(verb,**args)


@dataclass(frozen=True,repr=False)
class Ticket:
    handle: SessionHandle
    revision: int


class Evidence:
    def __init__(self,store,issuer):self.store,self.issuer=store,issuer
    def clock(self):return self.store._call('evidence_clock')['now_ms']
    def read(self,lease):
        s=self.store;m=s.meta(lease);a=m['anchor']
        if not a or a['revision']!=lease.revision or a['epoch']!=s.current_epoch():raise Denied('native_missing_evidence')
        blob=s.evidence.get(s.evidence.path('synthetic',a['epoch'],m['session']))
        if not hmac.compare_digest(sha256(blob).hexdigest(),a['commitment']):raise Denied('native_integrity')
        try:
            aad={k:v for k,v in a.items() if k!='commitment'}
            raw=AESGCM(s.evidence.keys.key(a['key_id'])).decrypt(blob[:12],blob[12:],s._aad(m,aad))
            if not raw.startswith(HEADER):raise ValueError()
            z=zlib.decompressobj();raw=z.decompress(raw[len(HEADER):],MAX_RAW+1)
            if len(raw)>MAX_RAW or not z.eof or z.unused_data or z.unconsumed_tail:raise ValueError()
            doc=strict_json(raw)
            from experiments.shared_state.native_identity import verify
            identity=verify()
            if set(doc)!={'version','build','data','routeDeadline'} or doc['version']!=VERSION or doc['build']!=identity:raise ValueError()
            if s.meta(lease)!=m:raise ValueError()
            return doc,blob
        except (InvalidTag,ValueError,KeyError,TypeError):raise Denied('native_incompatible_evidence') from None
    def publish(self,lease,data,graph,previous_blob=None):
        s=self.store;now=self.clock();m=s.meta(lease);a=m['anchor'];old=previous_blob
        if a:
            if old is None or sha256(old).hexdigest()!=a['commitment']:raise Denied('native_cas')
        elif old is not None:raise Denied('native_cas')
        from experiments.shared_state.native_identity import verify
        doc=dict(version=VERSION,build=verify(),data=data,routeDeadline=graph.route_deadline)
        graph.load(data) # Refuse unsupported/corrupted native state before publication.
        raw=canonical(doc)
        if len(raw)>MAX_RAW:raise Denied('native_record_bound')
        deadline=min(m['expires_ms'],graph.deadline,a['expires_ms'] if a else m['expires_ms'])
        if deadline<=now:raise Denied('native_expired')
        anchor=dict(session=m['session'],revision=m['revision'],generation=(a['generation'] if a else 0)+1,
            expires_ms=deadline,key_id=s.evidence.keys.active,environment='synthetic',epoch=s.current_epoch())
        nonce=secrets.token_bytes(12);body=HEADER+zlib.compress(raw)
        blob=nonce+AESGCM(s.evidence.keys.key(anchor['key_id'])).encrypt(nonce,body,s._aad(m,anchor))
        s.evidence.publish(s.evidence.path('synthetic',anchor['epoch'],m['session']),old,blob,deadline)
        with self.issuer() as c:
            c.execute('SELECT synthetic_state.evidence_anchor(%s,%s,%s,%s,%s,%s,%s,%s)',
              (m['session'],m['revision'],anchor['generation']-1,sha256(blob).hexdigest(),anchor['key_id'],deadline,'synthetic',anchor['epoch']))
        with s.service.witness.serial():
            s.service.sync(s);quote=s._call('native_quote',**s._lease(lease))
            s.service.witness.call('checkpoint',quote=quote,observed=s.service.observed(s))
            with self.issuer() as c:c.execute('SELECT synthetic_state.native_commit(%s,%s)',(Jsonb(s._lease(lease)),Jsonb(quote)))
            s.service.sync(s)
        return blob


class NativeIssuer(GrantIssuer):
    checkpoint=None
    def register(self,store,lease,http,inference=None,refresh=None):
        self._continuing=self.checkpoint is not None and refresh is None
        if not self._continuing:return super().register(store,lease,http,inference,refresh)
        with self._connection() as c:c.execute('SELECT synthetic_state.native_action(%s,%s,%s)',
            (Jsonb(store._lease(self.checkpoint)),store._hash(lease.session.token,'session'),http))
    def approve(self,store,lease,cap,outing,plans):
        if not getattr(self,'_continuing',False):return super().approve(store,lease,cap,outing,plans)
        with self._connection() as c:c.execute('SELECT synthetic_state.approve_requests(%s,%s)',(store._hash(cap.token,'cap'),Jsonb(plans)))
        records,provenance=self._records();store.publish(lease,records,provenance,self._connection)


class NativeBroker(GrantBroker):
    def _source(self,token):
        source=super()._source(token)
        if getattr(self,'native',None):self.store.meta(self.native.lease)
        return source
    @contextmanager
    def _action(self,*args,**kwargs):
        if getattr(self,'native',None) and not getattr(self.native,'_running',False):raise Denied('native_action_scope_required')
        with super()._action(*args,**kwargs) as action:yield action
    def replace(self,token,value,execution=None):
        if getattr(self,'native',None):
            self.native.revoke();raise Denied('native_new_validated_source_required')
        return super().replace(token,value,execution)
    def _check(self):
        if getattr(self,'native',None):self.store.meta(self.native.lease)
        return super()._check()


def restore_validation(record,now_ms):
    from backend.planning_admission import AdmissionRegistry
    from backend.interpretation import InterpretationInput
    registry=AdmissionRegistry();scope=registry.new_scope();scope.created=monotonic()+(record['created']-now_ms)/1000;raw=record['raw']
    class Recorded:
        def interpret(self,text):
            if raw is None or text!=record['value'].text:raise Denied('native_original_source')
            return raw.model_copy(deep=True)
    out=registry.validate(record['value'],scope,1,Recorded(),now=record['reference'],execution=record['execution'])
    result=out.disposition.result
    from backend.validation_phases import validate_legacy
    for answer in record['answers']:
        if result.pending is None:raise Denied('native_pending_history')
        value=InterpretationInput(text=record['value'].text,preferences=record['value'].preferences,pending=result.pending,
            answers=answer,calendarTimezone=record['value'].calendarTimezone)
        result=validate_legacy(value,Recorded(),now=record['reference']).result
    if canonical(plain(result))!=canonical(plain(record['result'])):raise Denied('native_validation_difference')
    return registry,scope,out


class Session:
    """One durable source plus its native continuations; no serialized admission."""
    def __init__(self,broker,token,evidence,lease,blob,answers=None,receipts=None):
        self.broker,self.token,self.evidence,self.lease,self.blob=broker,token,evidence,lease,blob
        self.answers=answers or [];self.receipts=receipts or {};self.last=None
        broker.native=self;broker._Broker__issuer.checkpoint=lease
    @classmethod
    def capture(cls,broker,token,issuer):
        s=broker._source(token)
        if not isinstance(broker.now,datetime) or broker.now.utcoffset() is None:raise Denied('native_reference_clock_required')
        if len(broker._Broker__sources)!=1:raise Denied('native_single_source_required')
        record=ProviderAction(purpose='pending' if s.result.pending else 'ordinary',sourceDigest=broker._digest(s.value),interpretationDigest=broker._digest(s.result),requestRevision=s.revision)
        h=broker.store.create(Kind.ACTION,record);lease=broker.store.claim(h,1)
        with issuer() as c:c.execute('SELECT synthetic_state.native_enroll(%s,%s)',(broker.store._hash(h.token,'session'),s.inference))
        self=cls(broker,token,Evidence(broker.store,issuer),lease,None)
        self.persist(initial=True);return self
    @property
    def ticket(self):return Ticket(self.lease.session,self.lease.revision)
    def state(self):
        from backend.option_sessions import option_sessions
        from backend.venue_details import details_sessions
        from backend.starting_areas import references
        from backend.starting_places import _calendars,_calendar_lock
        s=self.broker._source(self.token);now=self.evidence.clock();mono=monotonic()
        def absolute(t):return int(now+(t-mono)*1000)
        advanced=self.broker._Broker__advanced.items.get(s.advanced) if s.advanced else None
        options=None
        if s.options:
            entry=option_sessions.entries.get(s.options)
            if entry is None:raise Denied('native_options_missing')
            options=(absolute(entry[0]+600),entry[1])
        details=None
        if s.details:
            entry=details_sessions.entries.get(s.details)
            if entry is None:raise Denied('native_details_missing')
            details=(absolute(entry[0]+1800),entry[1],entry[2],entry[3])
        origin_refs={}
        ref=s.execution.get('referenceToken')
        if ref:
            entry=references.entries.get(ref)
            if entry is None or entry[1]['session'] is not self.broker.budget:raise Denied('native_origin_reference_missing')
            origin_refs[ref]=(absolute(entry[0]+600),entry[1],entry[2])
        # Only source-owned origin calendars, never the whole global cache.
        calendars={}
        origins=[s.execution.get('startingLocation'),advanced.origin if advanced else None]
        for origin in origins:
            if origin and origin.point.coordinates:
                p=origin.point.coordinates;key=(p.latitude,p.longitude)
                with _calendar_lock:
                    if key in _calendars:calendars[key]=(absolute(_calendars[key][0]),*_calendars[key][1:])
        return dict(value=s.value,raw=s.raw,result=s.result,execution=s.execution,reference=self.broker.now,
          revision=s.revision,planned=s.planned_revision,created=absolute(s.created),inference=s.inference,advancedToken=s.advanced,
          optionsToken=s.options,detailsToken=s.details,advanced=advanced,options=options,details=details,
          budget=self.broker.budget,answers=self.answers,receipts=self.receipts,last=self.last,originRefs=origin_refs,calendars=calendars)
    def persist(self,initial=False):
        with self.broker.store.service.witness.serial():return self._persist(initial)
    def _persist(self,initial=False):
        state=self.state();graph=Graph(self.evidence.clock());data=graph.dump(state)
        graph.deadline=min(graph.deadline,state['created']+600000)
        if not initial:
            s=self.broker._source(self.token)
            action=ProviderAction(purpose='pending' if s.result.pending else 'ordinary',sourceDigest=self.broker._digest(s.value),interpretationDigest=self.broker._digest(s.result),requestRevision=s.revision)
            rev=self.broker.store._call('native_revise',**self.broker.store._lease(self.lease),**self.broker.store._prepared(Kind.ACTION,action))['revision']
            self.lease=self.broker.store.claim(self.lease.session,rev)
            self.broker._Broker__issuer.checkpoint=self.lease
        self.blob=self.evidence.publish(self.lease,data,graph,self.blob)
    def invoke(self,method,*args):
        if method not in ('answer','plan','advance','more','contact'):raise Denied('native_action')
        s=self.broker.store
        doc,_=self.evidence.read(self.lease)
        if doc['routeDeadline'] is not None and doc['routeDeadline']<=self.evidence.clock():raise Denied('native_route_expired')
        s.service.sync(s);s._call('native_begin',**s._lease(self.lease))
        # If anything fails, the persisted turn remains BUSY. No reconstruction retry.
        if method=='answer':self.answers.append(args[0])
        self._running=True
        try:result=getattr(self.broker,method)(self.token,*args)
        finally:self._running=False
        self.last=data_view(result) if isinstance(result,BaseModel) else result
        self.persist();return result
    def attach_receipt(self,result):
        from backend.saved_plans import receipts,digest
        if self.last is None or canonical(plain(data_view(result)))!=canonical(plain(data_view(self.last))):raise Denied('native_receipt_source')
        item=receipts.items.get(result.saveReceipt)
        if item is None or item[1].get('bound')!=digest(result.saveAccessToken):raise Denied('native_receipt_owned')
        now=self.evidence.clock();deadline=int(now+(item[0]-monotonic())*1000)
        self.receipts[digest(result.saveReceipt)]=(deadline,item[1]);self.persist()
    def revoke(self):
        self.broker.store._call('native_revoke',**self.broker.store._lease(self.lease))
    def receipt_ticket(self,result):
        self.attach_receipt(result)
        s=self.broker._source(self.token);store=self.broker.store
        action=ProviderAction(purpose='details',sourceDigest=self.broker._digest(s.value),interpretationDigest=self.broker._digest(s.result),requestRevision=s.revision)
        h=store.create(Kind.ACTION,action);lease=store.claim(h,1)
        with self.evidence.issuer() as c:c.execute('SELECT synthetic_state.native_enroll(%s,%s)',(store._hash(h.token,'session'),s.inference))
        from backend.saved_plans import digest
        entry=self.receipts[digest(result.saveReceipt)];graph=Graph(self.evidence.clock());graph.deadline=entry[0]
        self.evidence.publish(lease,graph.dump({'receipts':{digest(result.saveReceipt):entry}}),graph)
        return Ticket(h,1)
    def select(self,request):
        from backend.saved_plans import Receipts,digest,PersistenceError
        self.broker.store.meta(self.lease)
        item=self.receipts.get(digest(request.receipt))
        now=self.evidence.clock()
        if item is None or item[0]<=now:raise PersistenceError(409)
        native=Receipts();native.items[request.receipt]=(monotonic()+(item[0]-now)/1000,item[1])
        return native.select(request) # Reusable, unchanged native bearer/membership validation.
    @classmethod
    def resume(cls,broker,ticket,issuer):
        if type(ticket) is not Ticket:raise Denied('native_ticket')
        s=broker.store;s.service.sync(s);lease=s.claim(ticket.handle,ticket.revision)
        s._call('native_ready',**s._lease(lease));e=Evidence(s,issuer);doc,blob=e.read(lease)
        now=e.clock()
        if doc['routeDeadline'] is not None and doc['routeDeadline']<=now:raise Denied('native_route_expired')
        record=Graph(now).load(doc['data'])
        required=set('value raw result execution reference revision planned created inference advancedToken optionsToken detailsToken advanced options details budget answers receipts last originRefs calendars'.split())
        if type(record) is not dict or set(record)!=required:raise Denied('native_root_schema')
        if not isinstance(record['reference'],datetime) or record['reference'].utcoffset() is None:raise Denied('native_reference_clock_required')
        broker.now=record['reference']
        registry,scope,out=restore_validation(record,now)
        if broker._digest(record['value'])!=s.meta(lease)['action']['sourceDigest']:raise Denied('native_source_changed')
        broker.budget=record['budget']
        source=Source(record['value'],record['result'],record['raw'],None,scope,'')
        source.execution=record['execution'];source.inference=record['inference'];source.revision=record['revision'];source.planned_revision=record['planned']
        source.created=monotonic()+(record['created']-now)/1000
        if not record['planned'] and not record['answers']:source.outcome=(registry,out)
        from backend.real_planning import PlannerInput
        if source.result.request is not None:source.payload=PlannerInput.model_validate({**source.result.request.model_dump(),**source.execution})
        source.advanced=record['advancedToken'];source.options=record['optionsToken'];source.details=record['detailsToken']
        if record['advanced'] is not None:
            a=record['advanced']
            if a.text!=source.value.text or a.journey!=source.result.interpretation.journey:raise Denied('native_journey_changed')
            broker._Broker__advanced.items[a.token]=a;source.advanced_identity=a
        from backend.option_sessions import option_sessions
        from backend.venue_details import details_sessions
        from backend.starting_areas import references
        from backend.starting_places import _calendars,_calendar_lock
        def mono(stamp):return monotonic()+(stamp-now)/1000
        if record['options']:
            expiry,context=record['options']
            with option_sessions.lock:
                option_sessions.entries=OrderedDict((k,v) for k,v in option_sessions.entries.items() if monotonic()-v[0]<600)
                while len(option_sessions.entries)>=50:option_sessions.entries.popitem(last=False)
                option_sessions.entries[source.options]=(mono(expiry)-600,context,Lock())
        if record['details']:
            expiry,ids,outing,attempts=record['details']
            with details_sessions.lock:
                details_sessions.entries=OrderedDict((k,v) for k,v in details_sessions.entries.items() if monotonic()-v[0]<1800)
                while len(details_sessions.entries)>=50:details_sessions.entries.popitem(last=False)
                details_sessions.entries[source.details]=(mono(expiry)-1800,ids,outing,attempts)
        with references.lock:
            for key,(expiry,data,used) in record['originRefs'].items():
                if data['session'] is not broker.budget or expiry<=now:raise Denied('native_origin_owner')
                references.entries=OrderedDict((k,v) for k,v in references.entries.items() if monotonic()-v[0]<600)
                while len(references.entries)>=20:references.entries.popitem(last=False)
                references.entries[key]=(mono(expiry)-600,data,used)
        with _calendar_lock:
            for key,(expiry,*data) in record['calendars'].items():
                if expiry<=now:raise Denied('native_calendar_expired')
                if key not in _calendars and len(_calendars)>=100:raise Denied('native_calendar_capacity')
                _calendars[key]=(mono(expiry),*data)
        token=secrets.token_urlsafe(32);broker._Broker__sources[token]=source;source.digest=broker._seal(source)
        self=cls(broker,token,e,lease,blob,record['answers'],record['receipts']);self.last=record['last']
        return self


class SelectedReceipt:
    """Read-only portable native receipt. Never raw interpretation/provider authority."""
    @staticmethod
    def select(store,ticket,issuer,request):
        if type(ticket) is not Ticket:raise Denied('native_ticket')
        lease=store.claim(ticket.handle,ticket.revision)
        store._call('native_ready',**store._lease(lease))
        evidence=Evidence(store,issuer);doc,_=evidence.read(lease)
        if any('native' in row for row in doc['data']['nodes']):raise Denied('native_receipt_only')
        record=Graph(evidence.clock()).load(doc['data'])
        if type(record) is not dict or set(record)!={'receipts'}:raise Denied('native_receipt_record')
        from backend.saved_plans import Receipts,digest,PersistenceError
        item=record['receipts'].get(digest(request.receipt));now=evidence.clock()
        if item is None or item[0]<=now:raise PersistenceError(409)
        native=Receipts();native.items[request.receipt]=(monotonic()+(item[0]-now)/1000,item[1])
        selected=native.select(request);store.meta(lease);return selected


def refresh_saved(broker,request):
    """Fresh saved access checks on every action; never reconstruct original raw evidence."""
    from backend.saved_plans import OpenRequest,reopen,PersistenceError
    if getattr(broker,'native',None):raise Denied('native_refresh_separate_purpose')
    def current():
        document=reopen(OpenRequest(accessToken=request.accessToken))
        selected=next((x for x in document['itineraries'] if x['candidateId']==request.candidateId),None)
        if selected is None or document['selectedId']!=request.candidateId or document['dataMode']!='real':raise PersistenceError(404)
        return selected
    from backend.saved_refresh import RefreshRequest
    if type(request) is not RefreshRequest:raise Denied('native_refresh_type')
    selected=current();key=broker._digest([request.accessToken,str(request.refreshId)])
    def seen():return broker.store._call('native_refresh_seen',key=key)['seen']
    def duplicate():return dict(candidateId=request.candidateId,venues={s['reference']:dict(status='already_attempted',message='This detail-loading action was already attempted. No automatic retry.') for s in selected['stops']},diagnostics={})
    if seen():return duplicate()
    try:return broker.refresh(request)
    except Denied:
        # A race is a duplicate only after current access AND durable consumption.
        current()
        if seen():return duplicate()
        raise


def resume_native(broker,ticket,issuer):
    """Existing application error vocabulary; no new HTTP route or startup hook."""
    from backend.places import DiscoveryError
    from experiments.shared_state.contracts import Unavailable
    try:return Session.resume(broker,ticket,issuer)
    except Unavailable:raise DiscoveryError('provider','Shared session storage is unavailable. No provider retry was sent. Try opening a saved page or starting a new search later.') from None
    except Denied:raise DiscoveryError('expired','This outing can no longer be continued safely. Saved pages remain viewable; regenerate to start a new search.') from None
