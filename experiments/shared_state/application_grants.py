"""Inactive fictional application grant + independent witness composition.

No HTTP client, credential loader, production selector or live model exists here.
Database/issuer factories are trusted synthetic harness dependencies, not enrollment.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb

from experiments.shared_state.contracts import Denied,Unavailable,Kind,Reservation
from experiments.shared_state.redis_evidence import EvidenceStore,EvidenceVerifier,EvidenceIssuer
from experiments.shared_state.action_bridge import Broker
from experiments.shared_state.bridge_models import ProviderAction
from experiments.shared_state.evidence_models import canonical

VERSION='52-application-financial-authority-local-v1'
PROMPT='Fictional offline interpretation. No real provider or qualification claim.'
DEFAULT_MODEL='fictional-tiny@offline-v1'


class Witness:
    """Independent database and role. No mutable epoch file or cached default."""
    def __init__(self,connection,reader):
        self.__connection,self.__reader=connection,reader
        self._active=ContextVar('witness_connection',default=None)
        self._pid=os.getpid()

    def epoch(self):
        try:
            active=self._active.get()
            if active is not None:r=active.execute("SELECT witness.protocol('epoch','{}')").fetchone()[0]['epoch']
            else:
                with self.__reader() as c:r=c.execute('SELECT witness.epoch()').fetchone()[0]
        except psycopg.Error:raise Unavailable() from None
        if type(r) is not str or len(r)!=64:raise Denied('external_epoch_missing')
        return r

    @contextmanager
    def serial(self):
        if os.getpid()!=self._pid:raise Denied('witness_process')
        if self._active.get() is not None:yield;return
        try:
            with self.__connection() as c:
                c.autocommit=True;c.execute("SET lock_timeout='5s'")
                c.execute('SELECT pg_advisory_lock(527300311)')
                token=self._active.set(c)
                try:yield
                finally:
                    self._active.reset(token);c.execute('SELECT pg_advisory_unlock(527300311)')
        except psycopg.Error:raise Unavailable() from None

    def call(self,a,**p):
        try:
            c=self._active.get()
            if c is None:
                with self.serial():return self.call(a,**p)
            result=c.execute('SELECT witness.protocol(%s,%s)',(a,Jsonb(p))).fetchone()[0]
        except (psycopg.IntegrityError,psycopg.DataError,psycopg.errors.RaiseException,psycopg.errors.NoDataFound):
            raise Denied('witness_protocol') from None
        except psycopg.Error:raise Unavailable() from None
        # Function returned, committed in autocommit, BEFORE reporting quarantine.
        if 'denied' in result:raise Denied('grant_quarantined_or_stopped')
        return result


class GrantService:
    def __init__(self,witness,issuer_connection):self.witness,self.__issuer=witness,issuer_connection

    def observed(self,store):return store._call('app_observed')
    def sync(self,store):return self.witness.call('confirm',observed=self.observed(store))

    def prepare(self,store,verb,args):
        self.sync(store)
        if verb=='reserve':quote=store._call('app_quote',**args)
        else:
            # Immutable reservation quote, not repriced next-day/payload reconstruction.
            quote=store._call('app_reserved',operation=args['operation'])
        ordinal=args.get('ordinal')
        identifier=verb+':'+args['operation']+(':'+str(ordinal) if ordinal is not None else '')
        self.witness.call(verb,id=identifier,quote=quote,ordinal=ordinal,observed=self.observed(store))
        try:
            with self.__issuer() as c:c.execute('SELECT synthetic_state.app_accept(%s,%s,%s)',(identifier,verb,Jsonb(quote)))
        except Exception:
            self.witness.call('quarantine');raise Denied('witness_install') from None

    def failed(self):
        try:
            if self.witness.call('status')['pending']:
                self.witness.call('quarantine')
        except (Denied,Unavailable):pass  # No retry/refund; retained pending claims stop future work.

    def finish(self,store,operation):
        state=store._call('app_state',operation=operation)['state']
        if state in ('SUCCEEDED','FAILED','UNCERTAIN'):
            self.witness.call('outcome',operation=operation,state=state,observed=self.observed(store))
            self.sync(store)
            if state=='UNCERTAIN':self.witness.call('quarantine')

    def send(self,store,reservation,ordinal,payload,fake):
        if type(payload) is not bytes or not callable(fake):raise Denied('fake_transport')
        with self.witness.serial():
            self.sync(store);q=store._call('app_reserved',operation=reservation.operation)
            if not 1<=ordinal<=len(q['lines']) or sha256(payload).hexdigest()!=q['lines'][ordinal-1]['request_digest']:
                raise Denied('transport_payload')
            if q['lines'][ordinal-1]['kind']=='llm':
                records,_=store.recover(reservation.lease)
                body=json.loads(payload)
                if 'request' not in records or body.get('input')!=records['request'].text:raise Denied('inference_source_payload')
            args=dict(**store._lease(reservation.lease),capability=store._hash(reservation.capability.token,'cap'),
                      operation=reservation.operation,ordinal=ordinal,payload_digest=sha256(payload).hexdigest())
            self.prepare(store,'deliver',args)
            store._call('app_deliver',**args);self.sync(store)
            # Delivery claim is durable outside OP SQL BEFORE I/O. This token is
            # the current call stack only; restart cannot reconstruct or retry it.
            return fake(payload)

    def usage(self,store,reservation,report):
        result=store._call('app_usage',**store._lease(reservation.lease),capability=store._hash(reservation.capability.token,'cap'),operation=reservation.operation,report=report)
        if not result['valid']:self.witness.call('quarantine')
        return result


class GrantVerifier(EvidenceVerifier):
    def __init__(self,connection,service):super().__init__(connection);self.service=service
    def authorize(self,store,lease,verb,args):
        store.recover(lease)  # Missing Redis refuses BEFORE external reservation.
        self.service.prepare(store,verb,args)
        return super().authorize(store,lease,verb,args)


class GrantStore(EvidenceStore):
    def __init__(self,*,service,issuer_connection,**kwargs):
        from experiments.shared_state.grant_identity import verify
        verify()
        self.service=service
        self._epoch_context=ContextVar('transaction_epoch',default=None)
        super().__init__(verifier=GrantVerifier(issuer_connection,service),current_epoch=service.witness.epoch,**kwargs)
    @contextmanager
    def _tx(self):
        # Fetch before taking OP gate: never authenticate to another DB while
        # holding that lock. Financial/send paths also hold witness serialization.
        token=self._epoch_context.set(self.service.witness.epoch())
        try:
            with super()._tx() as c:yield c
        except Unavailable as error:
            error.add_note('synthetic_sqlstate='+str(getattr(error.__context__,'sqlstate',None)))
            raise
        finally:self._epoch_context.reset(token)

    def _invoke(self,c,action,args):
        return c.execute('SELECT synthetic_state.app_protocol(%s,%s,%s,%s,%s) AS result',
                         (action,Jsonb(args),'synthetic',self._epoch_context.get(),self._proof)).fetchone()['result']
    def _call(self,verb,**args):
        if verb not in ('reserve','dispatch','transition'):
            result=super()._call(verb,**args)
            if verb=='admit' and args.get('domain')=='inference':self._current_inference=args['id']
            return result
        with self.service.witness.serial():
            try:
                result=super()._call(verb,**args)
                if verb in ('reserve','dispatch'):self.service.sync(self)
                elif args.get('state') in ('SUCCEEDED','FAILED','UNCERTAIN'):self.service.finish(self,args['operation'])
                return result
            except BaseException:
                self.service.failed();raise


class GrantIssuer(EvidenceIssuer):
    def register(self,store,lease,http,inference=None,refresh=None):
        self._has_financial_source=inference is not None
        super().register(store,lease,http,inference,refresh)

    def approve(self,store,lease,cap,outing,plans):
        # Keep the frozen issuer's outing map; use the new operator-root gate.
        mapping=self._LocalIssuer__outings
        if outing not in mapping:mapping[outing]=str(uuid4())
        with self._connection() as c:
            c.execute('SELECT synthetic_state.app_enroll_budget(%s,%s,%s)',(store._hash(lease.session.token,'session'),self._LocalIssuer__root,None if getattr(self,'_has_financial_source',False) else mapping[outing]))
            c.execute('SELECT synthetic_state.approve_requests(%s,%s)',(store._hash(cap.token,'cap'),Jsonb(plans)))
        records,provenance=self._records();store.publish(lease,records,provenance,self._connection)


class GrantBroker(Broker):
    def dispatch(self,request):
        original=self._Broker__fake
        def guarded(value):
            batch=self._Broker__batch;ordinal=batch['index']
            return self.store.service.send(self.store,batch['reservation'],ordinal,request.canonical,lambda _:original(value))
        self._Broker__fake=guarded
        try:return super().dispatch(request)
        finally:self._Broker__fake=original


def inference_payload(value,model=DEFAULT_MODEL,max_output=64):
    from backend.ai import Interpretation
    return canonical(dict(provider='fictional_llm_a' if model!= 'fictional-other@offline-v1' else 'fictional_llm_b',model=model,
        system=PROMPT,input=value.text,schema=Interpretation.model_json_schema(),max_output_tokens=max_output,
        reasoning='none',tools=[],cache=False,store=False))


class FakeInference:
    """Only server-owned Broker source; no production HTTP/token counter exists."""
    def __init__(self,store,issuer_connection,counter_connection,root,reply,*,model=DEFAULT_MODEL,max_output=64):
        self.store,self.__issuer,self.root,self.reply=store,issuer_connection,root,reply
        self.__counter=counter_connection
        self.model,self.max_output=model,max_output;self.broker=None;self.calls=0

    def interpret(self,text):
        from backend.interpretation import InterpretationInput
        from backend.ai import Interpretation
        s=self.store;b=self.broker
        if b is None or b._Broker__current is None:raise Denied('inference_action')
        action=b._Broker__current;value=action['source']
        if type(value) is not InterpretationInput or value.pending is not None or text!=value.text:raise Denied('fresh_owned_inference')
        payload=inference_payload(value,self.model,self.max_output);body=json.loads(payload)
        record=ProviderAction(purpose='ordinary',sourceDigest=b._digest(value),interpretationDigest=b._digest(None),requestRevision=action['revision'])
        h=s.create(Kind.ACTION,record);l=s.claim(h,1);cap=s.issue(l,'provider_action',str(uuid4()))
        # Fake complete-input units are UTF-8 bytes, NOT a real tokenizer estimate.
        spec=dict(kind='llm',provider=body['provider'],model=self.model,rate_version='fictional-b-rate-v1' if body['provider']=='fictional_llm_b' else 'fictional-a-rate-v1',
            input_tokens=len(payload),max_output=self.max_output,cached_tokens=0,reasoning_cap=0,tool_calls=0,
            prompt_hash=sha256(PROMPT.encode()).hexdigest(),schema_hash=sha256(canonical(body['schema'])).hexdigest(),request_digest=sha256(payload).hexdigest())
        with self.__counter() as c:c.execute('SELECT synthetic_state.app_count_input(%s,%s)',(s._hash(cap.token,'cap'),payload))
        with self.__issuer() as c:
            c.execute('SELECT synthetic_state.app_bind_inference(%s,%s,%s,%s)',(s._hash(h.token,'session'),self.root,str(uuid4()),s._current_inference))
            c.execute('SELECT synthetic_state.app_approve_llm(%s,%s,%s,%s)',(s._hash(cap.token,'cap'),Jsonb(spec),action['http'],s._current_inference))
        s.publish(l,{'request':value},'synthetic_fresh',self.__issuer)
        r=s.reserve(l,cap,str(uuid4()));s.transition(r,'INTENT')
        try:
            s._call('dispatch',**s._lease(l),capability=s._hash(cap.token,'cap'),operation=r.operation,ordinal=1,payload_digest=sha256(payload).hexdigest())
            response=s.service.send(s,r,1,payload,self.reply);self.calls+=1
            if not s.service.usage(s,r,response.get('usage'))['valid']:raise Denied('uncertain_usage')
            parsed=Interpretation.model_validate(response['output'])
            s.transition(r,'SUCCEEDED');return parsed
        except BaseException:
            try:s.transition(r,'UNCERTAIN')
            except (Denied,Unavailable):s.service.witness.call('quarantine')
            raise
        finally:s.revoke(h,1)
