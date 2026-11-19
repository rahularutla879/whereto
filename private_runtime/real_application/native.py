"""Actual native interpretation/planner over real SQL. No public startup selector.

Trusted factory dependencies are explicit. Counts and generation must be remote
callbacks in the eventual service composition; nothing discovers credentials.
Google result graphs remain request-local, never portable source evidence.
"""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from threading import Lock
from time import monotonic
from uuid import uuid4
import ast
from psycopg.types.json import Jsonb
from backend import action_dispatch as io
from backend.ai.openai_candidate import OpenAICandidateProvider,request_bytes
from backend.interpretation import InterpretationInput,ClarificationAnswers
from backend.provider_budget import ProviderBudget,ProviderSettings
from experiments.shared_state.contracts import Denied,Unavailable,Kind
from experiments.shared_state.bridge_models import ProviderAction
from experiments.shared_state.action_bridge import Broker as Parent
from experiments.shared_state.application_grants import GrantBroker
from experiments.shared_state.evidence_models import canonical,plain
from private_runtime.provider_callbacks import count_payload,inference_response
from .store import Store
from private_runtime.real_finance.profile import verify


def require_native():
    broker=io._active.get()
    if type(broker) is not Broker or type(broker.store) is not Store:raise Denied('real_native_action_required')
    broker._check()
    if monotonic()>=broker._deadline:raise Denied('real_native_expired')
    broker.store.snapshot() # Current protected grant/epoch/fence protocol; not a spending grant.
    return broker

def enabled():
    if io._active.get() is None:return False
    require_native();return True

def usage_report(usage):
    if usage is None:return None
    # Normalized no-discount/no-extra-category fields, not invented provider
    # measurements: raw usage remains hash-bound; SQL requires zero write price.
    return dict(provider='openai',model='gpt-6-luna',input_tokens=usage['input_tokens'],output_tokens=usage['output_tokens'],cached_tokens=usage.get('input_tokens_details',{}).get('cached_tokens',0),cache_write_tokens=0,reasoning_tokens=usage.get('output_tokens_details',{}).get('reasoning_tokens',0),tool_calls=0)

class Inference:
    def __init__(self,store,issuer,root,counter,dispatch):
        self.store,self.issuer,self.root,self.counter,self.dispatch=store,issuer,root,counter,dispatch
        self.broker=None;self.calls=0;self.receipts=[]
    def interpret(self,text):
        b=require_native();a=b._Broker__current;s=self.store;value=a['source']
        if b is not self.broker or type(value) is not InterpretationInput or value.pending is not None or text!=value.text:raise Denied('real_owned_inference')
        wire=request_bytes(text);record=ProviderAction(purpose='ordinary',sourceDigest=b._digest(value),interpretationDigest=sha256(b'null').hexdigest(),requestRevision=a['revision'])
        h=s.create(Kind.ACTION,record,ttl=b.remaining());l=s.claim(h,1);a['inference_lease']=l;cap=s.issue(l,'provider_action',str(uuid4()));r=None
        try:
            with self.issuer() as c:
                c.execute('SELECT provider_state.real_register_inference(%s,%s,%s)',(s._hash(h.token,'session'),a['http'],s._current_inference))
                c.execute('SELECT provider_state.app_bind_inference(%s,%s,%s,%s)',(s._hash(h.token,'session'),self.root,str(uuid4()),s._current_inference))
            s.publish(l,{'request':value},'real-source-v1',self.issuer)
            with self.issuer() as c:c.execute('SELECT provider_state.real_enroll_request(%s,%s,%s,%s)',(s._hash(cap.token,'cap'),canonical(plain(value)),wire,count_payload(wire)))
            with self.issuer() as c:c.execute('SELECT provider_state.real_application_input_policy(%s)',(s._hash(cap.token,'cap'),))
            s.recover(l);self.counter.count(s._hash(cap.token,'cap'),wire)
            with self.issuer() as c:
                spec=c.execute('SELECT provider_state.real_llm_spec(%s)',(s._hash(cap.token,'cap'),)).fetchone()[0]
                c.execute('SELECT provider_state.app_approve_llm(%s,%s,%s,%s)',(s._hash(cap.token,'cap'),Jsonb(spec),a['http'],s._current_inference))
            r=s.reserve(l,cap,str(uuid4()));s.transition(r,'INTENT')
            def generate(payload):
                s._call('dispatch',**s._lease(l),capability=s._hash(cap.token,'cap'),operation=r.operation,ordinal=1,payload_digest=sha256(payload).hexdigest())
                return inference_response(s.service.send(s,r,1,payload,self.dispatch))
            model=OpenAICandidateProvider(generate)
            try:parsed=model.interpret(text)
            finally:
                if model.raw_response is not None:
                    usage=usage_report(model.usage)
                    with self.issuer() as c:c.execute('SELECT provider_state.real_capture_response(%s,%s,%s,%s,%s)',(r.operation,s._hash(cap.token,'cap'),wire,model.raw_response.body,Jsonb(usage)))
            if model.usage is None:raise Denied('real_missing_usage')
            report=usage_report(model.usage)
            # The fixed source-pinned candidate refuses cache writes/tools/extra
            # categories. Unknown categories never become invented zero charges.
            if not s.service.usage(s,r,report)['valid']:raise Denied('real_invalid_usage')
            s.transition(r,'SUCCEEDED');self.calls+=1;self.receipts.append(r.operation);return parsed
        except BaseException:
            if r is not None:
                try:s.transition(r,'UNCERTAIN')
                except (Denied,Unavailable):s.service.witness.call('quarantine')
            raise
        finally:s.revoke(h,1)

class Issuer:
    def __init__(self,connection,root):self.connection,self.root=connection,root;self.broker=None;self.wires=None
    def register(self,s,lease,http,inference=None,refresh=None):
        checkpoint=getattr(self,'checkpoint',None)
        if checkpoint is not None:
            if refresh is not None:raise Denied('real_unsupported_refresh')
            with self.connection() as c:c.execute('SELECT provider_state.native_action(%s,%s,%s)',(Jsonb(s._lease(checkpoint)),s._hash(lease.session.token,'session'),http))
            return
        if refresh is not None:raise Denied('real_unsupported_refresh')
        with self.connection() as c:c.execute('SELECT provider_state.register_action(%s,%s,%s,NULL)',(s._hash(lease.session.token,'session'),http,inference))
    def _approve(self,s,lease,cap):
        b=require_native()
        if b is not self.broker or self.wires is None:raise Denied('real_server_batch_required')
        with self.connection() as c:c.execute('SELECT provider_state.real_approve_google_batch(%s,%s)',(s._hash(cap.token,'cap'),list(self.wires)))
    def approve(self,s,lease,cap,outing,plans):
        if getattr(self,'checkpoint',None) is None:
            with self.connection() as c:c.execute('SELECT provider_state.app_enroll_budget(%s,%s,NULL)',(s._hash(lease.session.token,'session'),self.root))
        self._approve(s,lease,cap)
        a=self.broker._check();result=a['interpretation'];result=result[0] if isinstance(result,list) else result
        s.publish(lease,{'request':a['source'],'interpretation_result':result},'real-source-v1',self.connection,lifetime=self.broker.remaining())
    def plan(self,s,cap,plans):self._approve(s,self.broker._check()['lease'],cap)

class Broker(GrantBroker):
    def __init__(self,store,issuer,model,dispatch,*,now):
        from .identity import verify_application
        verify_application()
        if type(store) is not Store or type(issuer) is not Issuer or type(model) is not Inference or not callable(dispatch):raise Denied('real_native_dependencies')
        if model.store is not store or model.root!=issuer.root or model.dispatch is not dispatch:raise Denied('real_dependency_scope')
        if now.tzinfo is None or now.utcoffset() is None:raise Denied('real_reference_clock')
        # Original constructor bookkeeping; no old fixture/environment/bootstrap
        # constructor is called. All planning/action/validation methods inherited.
        self.store,self._Broker__issuer,self._Broker__model,self._Broker__fake=store,issuer,model,lambda v:dispatch(canonical(v))
        self.budget=ProviderBudget(ProviderSettings(mode='real',candidates_per_activity=3));self.now=now
        self._Broker__key=store._key;self._Broker__sources={};self._Broker__current=None;self._Broker__batch=None;self._Broker__action_lock=Lock()
        self._deadline=0.0;self._plan_lock=Lock();self._start_lock=Lock();self._started=False
        issuer.broker=model.broker=self
    def _source(self,token):
        source=super()._source(token)
        if getattr(self,'checkpoint',None) is not None:self.checkpoint.check()
        return source
    def _check(self):
        if getattr(self,'checkpoint',None) is not None:self.checkpoint.check()
        return super()._check()
    @contextmanager
    def _action(self,*args,**kwargs):
        if getattr(self,'checkpoint',None) is not None and not self.checkpoint.running:raise Denied('real_source_turn_required')
        with super()._action(*args,**kwargs) as action:yield action
    def check_current(self):
        # Existing owner callback executes in another authenticated HTTP thread.
        # One broker owns one outing; the absolute scalar deadline never renews.
        token=io._active.set(self)
        try:
            require_native();a=self._check();lease=a['lease'] or a.get('inference_lease')
            if lease is not None:self.store.meta(lease)
        finally:io._active.reset(token)
    def _digest(self,value):
        # SQL source identity is exact full-request SHA. The native Source seal
        # remains the parent's keyed HMAC over every source/state field.
        return sha256(canonical(plain(value))).hexdigest() if type(value) is InterpretationInput else super()._digest(value)
    def remaining(self):
        seconds=int(self._deadline-monotonic())
        if seconds<1:raise Denied('real_native_expired')
        return min(600,seconds)
    def interpret(self,value,execution=None):
        with self._start_lock:
            if self._started:raise Denied('real_initial_action_consumed')
            self._started=True
        start=monotonic();self._deadline=start+600
        token,result=super().interpret(value,execution)
        source=self._source(token);source.created=start;source.digest=self._seal(source)
        return token,result
    def answer(self,token,answers):
        source=self._source(token)
        if type(answers) is not ClarificationAnswers or {k for k,v in answers.model_dump().items() if v}-{q.field for q in source.result.questions}:raise Denied('real_unrequested_answer')
        self._deadline=source.created+600
        return super().answer(token,answers)
    @contextmanager
    def reserve(self,outing,attempts,payloads):
        if payloads is None:raise Denied('real_batch_missing')
        self._Broker__issuer.wires=tuple(p.canonical for p in payloads)
        try:
            with super().reserve(outing,attempts,payloads):yield
        finally:self._Broker__issuer.wires=None
    def plan(self,token):
        if not self._plan_lock.acquire(False):raise Denied('real_plan_in_progress')
        try:
            source=self._source(token)
            if source.payload is None:raise Denied('real_ordinary_only')
            self._deadline=source.created+600
            try:
                result=super().plan(token)
                return result.model_copy(update=dict(optionsToken=None,detailsToken=None,saveReceipt=None,saveAccessToken=None,canExpand=False,canDiscover=False,canShowBeyond=False,continuationStatus={'kind':'search_exhausted','message':'This private outing is complete. Additional provider actions and restart continuation are unavailable; refreshing will not retry provider work.'}),deep=True)
            finally:
                # Financial history survives; no Google graph or source can replay.
                source.revoked=True;self._Broker__sources.pop(token,None)
        finally:self._plan_lock.release()
    def replace(self,token,*_args,**_kw):self.revoke(token);raise Denied('real_source_edit_requires_new_action')
    def _unsupported(self,*_args,**_kw):raise Denied('real_route_unavailable')
    advance=more=lookup=contact=refresh=_unsupported
