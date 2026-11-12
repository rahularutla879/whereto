"""Trusted native factories and owner-bound opaque routing. Never accepts raw graphs."""
from hashlib import sha256
import json,secrets
from psycopg.types.json import Jsonb
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from pydantic import BaseModel
from experiments.service_isolation.runtime import connection,make_broker
from experiments.service_isolation.auth import unb64
from experiments.shared_state.evidence_models import canonical,strict_json
from experiments.shared_state.native_sessions import Session,Ticket,SelectedReceipt,refresh_saved
from experiments.shared_state.contracts import Denied,SessionHandle

class Factory:
    def __init__(self,config):self.config=config
    def issuer(self):return connection(self.config,'issuer')
    def scope(self,s,token,owner):
        if type(token) is not str or not owner:raise Denied('ticket_owner')
        return dict(route=s._hash(token,'service-route'),owner=sha256(('synthetic\0'+owner).encode()).hexdigest(),build=self.config['build'],epoch=self.config['epoch'])
    def sql(self,a,p):
        with self.issuer() as c:return c.execute('SELECT synthetic_state.service_route(%s,%s)',(a,Jsonb(p))).fetchone()[0]
    def aad(self,p,revision):return canonical(dict(**p,revision=revision,kind='native-service-locator'))
    def put(self,s,ticket,owner,token=None,previous=None,mode='source'):
        token=token or secrets.token_urlsafe(32);p=self.scope(s,token,owner);lease=s.claim(ticket.handle,ticket.revision);m=s.meta(lease)
        expires=m['anchor']['expires_ms'];raw=canonical(dict(token=ticket.handle.token,revision=ticket.revision))
        nonce=secrets.token_bytes(12);blob=nonce+AESGCM(unb64(self.config['encryptionKey'])).encrypt(nonce,raw,self.aad(p,ticket.revision))
        path=s.evidence.path('synthetic',self.config['epoch'],p['route'])
        s.evidence.publish(path,previous,blob,expires)
        self.sql('put',dict(**p,session=m['session'],revision=ticket.revision,commitment=sha256(blob).hexdigest(),expires=expires,mode=mode))
        return dict(ticket=token,revision=ticket.revision)
    def get(self,s,value,owner,*,consume=False):
        if set(value)!=set('ticket revision'.split()) or type(value['revision']) is not int:raise Denied('ticket_shape')
        p=self.scope(s,value['ticket'],owner);row=self.sql('begin' if consume else 'get',dict(**p,revision=value['revision']))
        blob=s.evidence.get(s.evidence.path('synthetic',self.config['epoch'],p['route']))
        if sha256(blob).hexdigest()!=row['commitment']:raise Denied('locator_integrity')
        try:
            raw=AESGCM(unb64(self.config['encryptionKey'])).decrypt(blob[:12],blob[12:],self.aad(p,row['revision']));d=strict_json(raw)
            if set(d)!={'token','revision'} or d['revision']!=row['revision']:raise ValueError()
        except (ValueError,KeyError,InvalidTag):raise Denied('locator_integrity') from None
        return Ticket(SessionHandle(d['token']),d['revision']),blob,row
    def public(self,result):
        if type(result) is str:return {'status':'advanced_ready'} # Internal native token stays server-owned.
        return result.model_dump(mode='json') if isinstance(result,BaseModel) else result
    def handle(self,path,value,owner):
        if not owner:raise Denied('owner_required')
        broker=make_broker(self.config);s=broker.store
        if path=='/interpret':
            if set(value)!=set('request execution requestId'.split()):raise Denied('input_shape')
            from backend.interpretation import InterpretationInput
            from backend.real_planning import PlannerInput
            from pydantic import TypeAdapter
            from typing import Annotated
            execution=value['execution'];allowed={'startingLocation','currentArea','locationFirst','useOriginAsSearchAnchor','referenceToken','manualStartingPlace','searchRadius'}
            if type(execution) is not dict or set(execution)-allowed:raise Denied('execution_shape')
            typed={}
            for name,item in execution.items():
                field=PlannerInput.model_fields[name];annotation=Annotated[field.annotation,*field.metadata] if field.metadata else field.annotation
                typed[name]=TypeAdapter(annotation).validate_python(item)
            from uuid import UUID
            if str(UUID(value['requestId']))!=value['requestId']:raise Denied('initial_request_id')
            source=InterpretationInput.model_validate(value['request'])
            with self.issuer() as c:c.execute('SELECT synthetic_state.service_start(%s)',(Jsonb(dict(owner=sha256(('synthetic\0'+owner).encode()).hexdigest(),id=value['requestId'],request=sha256(canonical(value)).hexdigest(),build=self.config['build'],epoch=self.config['epoch'])),))
            token,result=broker.interpret(source,typed)
            session=Session.capture(broker,token,self.issuer);ticket=self.put(s,session.ticket,owner)
            return dict(**ticket,result=self.public(result))
        if path=='/refresh':
            from backend.saved_refresh import RefreshRequest
            return refresh_saved(broker,RefreshRequest.model_validate(value))
        if path=='/select':
            if set(value)!={'route','request'}:raise Denied('select_shape')
            ticket,_,row=self.get(s,value['route'],owner)
            if row['mode']!='receipt':raise Denied('selection_scope')
            from backend.saved_plans import SaveRequest
            return self.public(SelectedReceipt.select(s,ticket,self.issuer,SaveRequest.model_validate(value['request'])))
        if path not in ('/continue','/lookup') or (path=='/lookup' and set(value)!={'ticket','revision'}):raise Denied('factory_method')
        if path=='/lookup':
            ticket,_,row=self.get(s,value,owner)
            if row['mode']!='source':raise Denied('source_scope')
            session=Session.resume(broker,ticket,self.issuer)
            return dict(status='owned_current_session',revision=session.ticket.revision)
        if set(value)!={'route','method','arguments'}:raise Denied('continuation_shape')
        method=value['method'];args=value['arguments']
        if method not in ('answer','plan','advance','more','contact','receipt') or type(args) is not dict:raise Denied('continuation_method')
        # Receipt attachment is a state transition but does not make selection single-use.
        ticket,old,row=self.get(s,value['route'],owner,consume=True)
        session=Session.resume(broker,ticket,self.issuer)
        if method=='answer':
            from backend.interpretation import ClarificationAnswers
            result=session.invoke('answer',ClarificationAnswers.model_validate(args))
        elif method=='advance':
            from backend.advanced_planning import AdvancedInput
            if 'token' in args:raise Denied('client_native_token')
            result=session.invoke('advance',AdvancedInput.model_validate(dict(args,token=broker._source(session.token).advanced)))
        elif method=='contact':
            if set(args)!={'id'}:raise Denied('details_shape')
            result=session.invoke('contact',args['id'])
        elif method=='receipt':
            if args or session.last is None:raise Denied('receipt_source')
            from backend.saved_plans import receipts
            result=receipts.issue(session.last);receipt=session.receipt_ticket(result)
            detached=self.put(s,receipt,owner,mode='receipt')
            updated=self.put(s,session.ticket,owner,value['route']['ticket'],old)
            return dict(**updated,result=self.public(result),selection=detached)
        else:
            if args:raise Denied('argument_shape')
            result=session.invoke(method)
        updated=self.put(s,session.ticket,owner,value['route']['ticket'],old)
        return dict(**updated,result=self.public(result))
