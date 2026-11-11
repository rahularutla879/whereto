"""Inactive loopback-container composition of actual app actions and SQL authority.

No credential discovery, HTTP client, startup/environment selector, or public grant.
Trusted issuer and fake responder are supplied only by the isolated test harness.
Python object privacy is not an OS/process security boundary.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass,field
import hashlib
import hmac
import json
import secrets
from pathlib import Path
from time import monotonic
from threading import Lock
from uuid import UUID,uuid4
from pydantic import BaseModel

from psycopg.types.json import Jsonb
from backend import action_dispatch as io
from backend.planning_admission import AdmissionRegistry,_plain,_fresh_ordinary
from backend.interpretation import InterpretationInput,ClarificationAnswers
from backend.real_planning import PlannerInput,real_plans,more_real_plans
from backend.validation_phases import validate_legacy
from backend.provider_budget import ProviderBudget
from experiments.shared_state.contracts import Kind,Denied
from experiments.shared_state.bridge_models import ProviderAction
from experiments.shared_state.financial import FinancialPostgres

VERSION='52-server-action-bridge-local-v4'


class BridgeStore(FinancialPostgres):
    @staticmethod
    def _invoke(c,action,args):
        return c.execute('SELECT synthetic_state.bridge_protocol(%s,%s) AS result',(action,Jsonb(args))).fetchone()['result']


class LocalIssuer:
    """Trusted issuer adapter; worker objects never receive this connection factory.

    The fixture factory SET ROLEs to the NOLOGIN issuer. Real issuer enrollment
    and protected cross-process authentication remain deliberately unavailable.
    """
    def __init__(self,connection,root):self.__connection,self.__root=connection,root;self.__outings={}
    def register(self,store,lease,http,inference=None,refresh=None):
        with self.__connection() as c:
            c.execute('SELECT synthetic_state.register_action(%s,%s,%s,%s)',(store._hash(lease.session.token,'session'),http,inference,refresh))
    def approve(self,store,lease,cap,outing,plans):
        if outing not in self.__outings:self.__outings[outing]=str(uuid4())
        with self.__connection() as c:
            sid=store._hash(lease.session.token,'session')
            # Enrollment once per action, subsequent batches keep the same scope.
            c.execute('SELECT synthetic_state.enroll_budget(%s,%s,%s)',(sid,self.__root,self.__outings[outing]))
            c.execute('SELECT synthetic_state.approve_requests(%s,%s)',(store._hash(cap.token,'cap'),Jsonb(plans)))
    def plan(self,store,cap,plans):
        with self.__connection() as c:c.execute('SELECT synthetic_state.approve_requests(%s,%s)',(store._hash(cap.token,'cap'),Jsonb(plans)))


@dataclass(repr=False)
class Source:
    value: object
    result: object
    raw: object
    outcome: object
    scope: object
    digest: str
    created: float=field(default_factory=monotonic)
    revision: int=1
    inference: str|None=None
    advanced: str|None=None
    advanced_identity: object=None
    options: str|None=None
    details: str|None=None
    payload: object=None
    execution: object=field(default_factory=dict)
    planned_revision: int=0
    revoked: bool=False


class Broker:
    def __init__(self,store,issuer,model,budget,fake,*,now):
        from experiments.shared_state.action_identity import verify_build
        verify_build()
        # No external networking or host ADC paths in this local-only composition.
        if not Path('/.dockerenv').exists() or {p.name for p in Path('/sys/class/net').iterdir()}!={'lo'}:
            raise Denied('isolated_fixture_required')
        self.store,self.__issuer,self.__model,self.__fake=store,issuer,model,fake
        self.budget,self.now=budget,now
        self.__key=store._key;self.__sources={};self.__current=None;self.__batch=None;self.__action_lock=Lock()
        from backend.advanced_planning import Sessions
        from backend.saved_refresh import RefreshSessions
        self.__advanced=Sessions();self.__refresh=RefreshSessions()

    def _digest(self,value):
        def all_fields(v):
            if isinstance(v,UUID):return str(v)
            if isinstance(v,BaseModel):return {k:all_fields(getattr(v,k)) for k in type(v).model_fields}
            if isinstance(v,dict):return {k:all_fields(x) for k,x in v.items()}
            if isinstance(v,(list,tuple)):return [all_fields(x) for x in v]
            return _plain(v)
        return hmac.digest(self.__key,(VERSION+'\0'+json.dumps(all_fields(value),sort_keys=True,separators=(',',':'),allow_nan=False)).encode(),'sha256').hex()

    def _seal(self,s):return self._digest([s.value,s.raw,s.result,s.payload,s.execution,s.created,s.revision,s.planned_revision,s.inference,s.advanced,s.options,s.details])

    def _source(self,token):
        s=self.__sources.get(token)
        if not s or s.revoked or monotonic()-s.created>=600 or s.digest!=self._seal(s):raise Denied('source_authority')
        return s

    def _proof(self,token):
        expected=self._source(token).digest
        def verify():
            current=self._source(token)
            if not hmac.compare_digest(current.digest,expected):raise Denied('source_revision_changed')
            return current
        return verify

    def revoke(self,token):self._source(token).revoked=True

    def replace(self,token,value,execution=None):
        self.revoke(token)
        return self.interpret(value,execution)

    def interpret(self,value,execution=None):
        if type(value) is not InterpretationInput or value.pending is not None:raise Denied('fresh_input_required')
        # Same separately verified execution controls accepted by the native registry.
        allowed={'startingLocation','currentArea','locationFirst','useOriginAsSearchAnchor','referenceToken','manualStartingPlace','searchRadius'}
        if execution is not None and (not isinstance(execution,dict) or set(execution)-allowed):raise Denied('execution_controls')
        registry=AdmissionRegistry();scope=registry.new_scope()
        # Inference is an owned action, not permission to use a cloud model.
        with self._action('ordinary',value,None,1) as action:
            inference=secrets.token_hex(32)
            self.store._call('admit',id=inference,worker=self.store._worker,domain='inference',fingerprint=self._digest(value))
            try:out=registry.validate(value,scope,1,self.__model,now=self.now,execution=execution)
            finally:self.store._call('admission_release',id=inference,worker=self.store._worker)
        result=out.disposition.result
        token=secrets.token_urlsafe(32);raw=out.disposition.raw_model
        s=Source(value.model_copy(deep=True),deepcopy(result),deepcopy(raw),(registry,out),scope,'')
        s.inference=inference;s.execution=deepcopy(execution or {})
        self.__sources[token]=s
        if out.receipt is not None and result.request is not None:
            s.payload=PlannerInput.model_validate({**result.request.model_dump(),**(execution or {})})
        s.digest=self._seal(s)
        return token,deepcopy(result)

    def answer(self,token,answers):
        s=self._source(token)
        if type(answers) is not ClarificationAnswers or s.result.pending is None:raise Denied('pending_required')
        value=InterpretationInput(text=s.value.text,preferences=s.value.preferences,pending=deepcopy(s.result.pending),answers=answers,calendarTimezone=s.value.calendarTimezone)
        with self._action('pending',s.value,s.result,s.revision+1):d=validate_legacy(value,self.__model,now=self.now)
        s.result=deepcopy(d.result);s.revision+=1;s.outcome=None
        s.payload=PlannerInput.model_validate({**s.result.request.model_dump(),**s.execution}) if s.result.request is not None else None
        s.digest=self._seal(s)
        return deepcopy(s.result)

    def plan(self,token):
        s=self._source(token)
        if s.planned_revision==s.revision:raise Denied('planning_action_consumed')
        s.planned_revision=s.revision;s.digest=self._seal(s)
        if s.outcome is not None:
            registry,out=s.outcome
            if out.receipt is None:return deepcopy(s.result)
            if s.payload is not None:
                def run(payload):
                    with self._action('ordinary',s.value,[s.result,s.payload],s.revision,inference=s.inference,verify=self._proof(token)):return real_plans(payload,self.budget)
                result=registry.run(out.receipt,s.scope,1,s.payload,run)
            else:
                candidate={'text':s.value.text,'result':s.result,'preferences':s.value.preferences}
                def handoff(owned):return self.__advanced.create(owned['text'],owned['result'],self.budget,owned['preferences'])
                s.advanced=registry.run(out.receipt,s.scope,1,candidate,handoff)
                if s.advanced:s.advanced_identity=self.__advanced.items[s.advanced]
                s.digest=self._seal(s)
                return s.advanced
        elif s.payload is not None:
            _fresh_ordinary(s.payload)
            with self._action('pending',s.value,[s.result,s.payload],s.revision,inference=s.inference,verify=self._proof(token)):result=real_plans(s.payload,self.budget)
        elif s.result.executionStatus=='advanced_unavailable':
            with self._action('pending',s.value,s.result,s.revision,inference=s.inference,verify=self._proof(token)):
                s.advanced=self.__advanced.create(s.value.text,s.result,self.budget,s.value.preferences)
            if s.advanced:s.advanced_identity=self.__advanced.items[s.advanced]
            s.digest=self._seal(s)
            return s.advanced
        else:return deepcopy(s.result)
        s.options=getattr(result,'optionsToken',None);s.details=getattr(result,'detailsToken',None)
        s.digest=self._seal(s)
        return result

    def advance(self,token,value):
        from backend.advanced_planning import AdvancedInput
        s=self._source(token)
        if type(value) is not AdvancedInput or value.token!=s.advanced or not s.advanced or self.__advanced.items.get(s.advanced) is not s.advanced_identity:raise Denied('advanced_owner')
        if self._digest(s.advanced_identity.journey)!=self._digest(s.result.interpretation.journey):raise Denied('journey_changed')
        with self._action('advanced',s.value,[s.result,s.advanced_identity.context,value],s.revision,inference=s.inference,verify=self._proof(token)):result=self.__advanced.run(value)
        s.details=getattr(result,'detailsToken',None)
        s.digest=self._seal(s)
        return result

    def more(self,token):
        s=self._source(token)
        if s.payload is None or not s.options:raise Denied('options_owner')
        _fresh_ordinary(s.payload)
        with self._action('options',s.value,[s.result,s.payload],s.revision,inference=s.inference,verify=self._proof(token)):return more_real_plans(s.options)

    def lookup(self,value):
        from backend.starting_places import StartingPlaceQuery,lookup_starting_places
        from backend.starting_areas import StartingAreaQuery,suggest_starting_areas
        if type(value) not in (StartingPlaceQuery,StartingAreaQuery):raise Denied('lookup_type')
        with self._action('lookup' if type(value) is StartingPlaceQuery else 'area',value,None,1):
            return lookup_starting_places(value,self.budget) if type(value) is StartingPlaceQuery else suggest_starting_areas(value,self.budget)

    def contact(self,token,identity):
        from backend.venue_details import details_sessions
        s=self._source(token)
        if not s.details:raise Denied('details_owner')
        with self._action('details',s.value,s.result,s.revision,inference=s.inference,verify=self._proof(token)):return details_sessions.get(s.details,identity)

    def refresh(self,request):
        from backend.saved_refresh import RefreshRequest
        from backend.saved_plans import OpenRequest,reopen
        if type(request) is not RefreshRequest:raise Denied('refresh_type')
        document=reopen(OpenRequest(accessToken=request.accessToken))
        selected=next((p for p in document['itineraries'] if p['candidateId']==request.candidateId),None)
        if request.candidateId!=document['selectedId'] or selected is None or document['dataMode']!='real':raise Denied('refresh_owner')
        with self._action('refresh',request,document,1,refresh=self._digest([request.accessToken,str(request.refreshId)])) as action:
            action['refresh_check']=lambda:self._digest(reopen(OpenRequest(accessToken=request.accessToken)))==self._digest(document)
            action['venues']={v['reference'] for v in selected['stops']}
            return self.__refresh.refresh(request,self.budget)

    @contextmanager
    def _action(self,purpose,source,interpretation,revision,refresh=None,inference=None,verify=None):
        if not self.__action_lock.acquire(blocking=False):raise Denied('concurrent_or_nested_action')
        http=secrets.token_hex(32);fingerprint=self._digest([purpose,source,interpretation,revision])
        try:self.store._call('admit',id=http,worker=self.store._worker,domain='http',fingerprint=fingerprint)
        except BaseException:
            self.__action_lock.release();raise
        action={'purpose':purpose,'source':deepcopy(source),'interpretation':deepcopy(interpretation),'revision':revision,'http':http,'refresh':refresh,'inference':inference,'verify':verify,'lease':None,'outing':None}
        self.__current=action;ctx=io._active.set(self)
        try:yield action
        finally:
            try:
                if action['lease']:
                    try:self.store.revoke(action['lease'].session,1)
                    except Denied:pass  # Already revoked/expired; financial exposure is retained.
            finally:
                try:self.store._call('admission_release',id=http,worker=self.store._worker)
                finally:
                    io._active.reset(ctx);self.__current=None;self.__action_lock.release()

    def _check(self):
        a=self.__current
        if a is None or io._active.get() is not self:raise Denied('action_required')
        if a.get('verify'):a['verify']()
        if a.get('refresh_check') and not a['refresh_check']():raise Denied('refresh_changed')
        return a

    @contextmanager
    def reserve(self,outing,attempts,payloads):
        a=self._check()
        if outing._session is not self.budget or payloads is None or len(payloads)!=len(attempts) or not all(type(p) is io.Request for p in payloads):raise Denied('server_payload_required')
        plans=[]
        from backend.routes_transport import _validate_basic_body
        from backend.routes import ENDPOINT as routes_url,FIELD_MASK as routes_mask
        from backend.places import ENDPOINT as places_url,FIELD_MASK as places_mask
        from backend.search_fields import search_mask
        from backend.saved_refresh import REFRESH_MASK,CONTACT_REFRESH_MASK,HOURS_REFRESH_FIELDS
        from backend.venue_details import DETAILS_MASK
        for (op,key,rows,cols),request in zip(attempts,payloads):
            v=request.value();body=v['body'];variant=None
            if op=='matrix':
                _validate_basic_body(body)
                if v['operation']!='matrix' or v['url']!=routes_url or v['mask']!=routes_mask or v['method']!='POST' or len(body['origins'])!=rows or len(body['destinations'])!=cols:raise Denied('matrix_payload')
                variant='drive' if body['travelMode']=='DRIVE' else 'walk'
            elif op in ('search','lookup'):
                allowed={places_mask,places_mask+',places.containingPlaces',search_mask(places_mask),search_mask(places_mask)+',places.containingPlaces'}
                if v['operation']!='search' or v['url']!=places_url or v['method']!='POST' or v['mask'] not in allowed or type(body) is not dict:raise Denied('search_payload')
                variant='enterprise' if any(word in v['mask'] for word in ('rating','OpeningHours')) else 'pro'
                if op=='lookup' and variant!='pro':raise Denied('lookup_sku')
            elif op=='details':
                identity=v['url'].removeprefix('https://places.googleapis.com/v1/places/')
                allowed={DETAILS_MASK,REFRESH_MASK,CONTACT_REFRESH_MASK,REFRESH_MASK+','+HOURS_REFRESH_FIELDS,CONTACT_REFRESH_MASK+','+HOURS_REFRESH_FIELDS}
                if v['operation']!='details' or v['url']!='https://places.googleapis.com/v1/places/'+identity or v['method']!='GET' or body is not None or v['mask'] not in allowed:raise Denied('details_payload')
                if a['purpose']=='refresh' and identity not in a['venues']:raise Denied('refresh_venue')
                variant='pro' if v['mask']==REFRESH_MASK else 'essentials'
            else:raise Denied('unsupported_provider_operation')
            plans.append(dict(operation=op,request_digest=request.digest,rows=rows,cols=cols,variant=variant))
        if a['lease'] is None:
            evidence=ProviderAction(purpose=a['purpose'],sourceDigest=self._digest(a['source']),interpretationDigest=self._digest(a['interpretation']),requestRevision=a['revision'])
            h=self.store.create(Kind.ACTION,evidence);a['lease']=self.store.claim(h,1)
            self.__issuer.register(self.store,a['lease'],a['http'],inference=a['inference'],refresh=a['refresh'])
            a['outing']=outing
        elif a['outing'] is not outing:raise Denied('outing_transfer')
        cap=self.store.issue(a['lease'],'provider_action',str(uuid4()))
        if not a.get('enrolled'):
            self.__issuer.approve(self.store,a['lease'],cap,outing,plans);a['enrolled']=True
        else:self.__issuer.plan(self.store,cap,plans)
        reservation=self.store.reserve(a['lease'],cap,str(uuid4()))
        self.store.transition(reservation,'INTENT');self.__batch={'reservation':reservation,'payloads':tuple(payloads),'index':0}
        try:
            yield
            if self.__batch['index']!=len(payloads):self.store.transition(reservation,'FAILED')
            else:self.store.transition(reservation,'SUCCEEDED')
        except BaseException:
            try:self.store.transition(reservation,'UNCERTAIN')
            except Denied:pass  # Core expiry/revocation already blocks and retains the reservation.
            raise
        finally:self.__batch=None

    def dispatch(self,request):
        from backend.provider_work import check_cancelled
        check_cancelled()
        self._check();b=self.__batch
        if b is None or type(request) is not io.Request or b['index']>=len(b['payloads']) or not hmac.compare_digest(request.canonical,b['payloads'][b['index']].canonical):raise Denied('payload_or_dispatch_authority')
        r=b['reservation'];ordinal=b['index']+1
        self.store._call('dispatch',**self.store._lease(r.lease),capability=self.store._hash(r.capability.token,'cap'),operation=r.operation,ordinal=ordinal,payload_digest=request.digest)
        b['index']=ordinal
        return deepcopy(self.__fake(request.value()))
