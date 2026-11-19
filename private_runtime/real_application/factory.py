"""Authenticated ordinary public DTOs over real source-only checkpoints.

No source/graph/provider evidence is accepted from browsers. Dependencies and
identity verifier are installed by trusted role composition, never request JSON.
"""
from copy import deepcopy
from email.message import Message
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
import ast,secrets
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from psycopg.types.json import Jsonb
from pydantic import BaseModel
from experiments.shared_state.contracts import Denied,SessionHandle
from experiments.shared_state.evidence_models import canonical,strict_json
from experiments.service_isolation.auth import unb64
from experiments.ordinary_hosted.public_json import decode
from experiments.ordinary_hosted.request_auth import RequestVerifier
from backend.interpretation import InterpretationInput,ClarificationAnswers
from backend.real_planning import PlannerInput
from .checkpoint import Checkpoint,Ticket,Execution
VERSION='52-private-ordinary-outing-v1'


def _routing():
    # Reuse exactly the existing opaque locator/CAS algorithms, with real
    # namespace and typed source-only Ticket. Never import/invoke graph Session.
    root=Path(__file__).resolve().parents[2]
    from .identity import source_bytes
    tree=ast.parse(source_bytes('experiments/service_isolation/factory.py'))
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Factory')
    funcs=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in ('put','get','public')]
    text=ast.unparse(ast.Module(body=funcs,type_ignores=[])).replace("'synthetic'","'real'")
    ns=dict(globals());exec(compile(text,str(__file__)+':reviewed-locator','exec'),ns)
    return [ns[n] for n in ('put','get','public')]

class Factory:
    put,get,public=_routing()
    def __init__(self,config,*,broker,issuer,auth):
        from .identity import verify_application
        verify_application()
        self.config=deepcopy(config);self.make_broker,self._issuer=broker,issuer;self.verifier=RequestVerifier(auth)
        from experiments.ordinary_hosted import request_auth
        request_auth.PATHS={'/health':'GET','/api/interpret':'POST','/api/plans/generate':'POST','/api/planning-mode':'GET','/api/private-ordinary/revoke':'POST'}
        if auth.c['service']!='factory' or auth.c['build']!=config['build'] or auth.c['epoch']!=config['epoch']:raise Denied('real_factory_identity')
    def issuer(self):return self._issuer()
    def owner(self,owner):return sha256(('real\0'+VERSION+'\0'+self.config['ordinaryBuild']+'\0'+owner).encode()).hexdigest()
    def scope(self,s,token,owner):
        if type(token)is not str or not owner:raise Denied('real_ticket_owner')
        return dict(route=s._hash(token,'service-route'),owner=self.owner(owner),build=self.config['build'],epoch=self.config['epoch'])
    def sql(self,a,p):
        with self.issuer() as c:return c.execute('SELECT provider_state.service_route(%s,%s)',(a,Jsonb(p))).fetchone()[0]
    def aad(self,p,revision):return canonical(dict(**p,revision=revision,kind='real-source-locator'))
    def response(self,cp,owner,result,token=None,previous=None):
        route=self.put(cp.store,cp.ticket,owner,token,previous)
        out=self.public(result)
        if type(out)is not dict:raise Denied('real_public_result')
        out['privateOuting']=dict(version=VERSION,handle=route['ticket'],revision=route['revision'],expiresMs=cp.record.expires)
        return out
    def ordinary(self,envelope):
        path=envelope.get('path')
        methods={'/api/interpret':'POST','/api/plans/generate':'POST','/api/private-ordinary/revoke':'POST'}
        if type(envelope)is not dict or set(envelope)!={'path','body','headers'} or path not in methods or type(envelope['headers'])is not dict or set(envelope['headers'])!={'Authorization','X-Whereto-Context'}:raise Denied('real_public_envelope')
        headers=Message()
        for k,v in envelope['headers'].items():headers[k]=v
        wire=unb64(envelope['body']);owner=self.verifier.check(headers,methods[path],path,wire)
        value=decode(wire)
        if type(value)is not dict:raise Denied('real_public_input')
        broker=self.make_broker();s=broker.store;handle=value.pop('privateOuting',None)
        if handle is None:
            if path!='/api/interpret' or value.get('pending') is not None or any(value.get('answers',{}).values()):raise Denied('real_fresh_source')
            request=InterpretationInput.model_validate(value)
            with self.issuer() as c:c.execute('SELECT provider_state.service_start(%s)',(Jsonb(dict(owner=self.owner(owner),id=str(uuid4()),request=sha256(wire).hexdigest(),build=self.config['build'],epoch=self.config['epoch'])),))
            token,result=broker.interpret(request);cp=Checkpoint.capture(broker,token,self.issuer,self.owner(owner))
            return self.response(cp,owner,result)
        if type(handle)is not dict or set(handle)!={'version','handle','revision','expiresMs'} or handle['version']!=VERSION or type(handle['expiresMs'])is not int:raise Denied('real_outing_shape')
        ticket,blob,row=self.get(s,dict(ticket=handle['handle'],revision=handle['revision']),owner,consume=True)
        if row['expires']!=handle['expiresMs'] or row['mode']!='source':raise Denied('real_outing_expiry')
        cp=Checkpoint.resume(broker,ticket,self.issuer,self.owner(owner));source=broker._source(cp.token)
        if path=='/api/private-ordinary/revoke':
            if value:raise Denied('real_revoke_shape')
            s._call('native_revoke',**s._lease(cp.lease));return {'discarded':True}
        if path=='/api/interpret':
            if 'pending' in value:raise Denied('real_client_pending')
            answers=ClarificationAnswers.model_validate(value.pop('answers',{}));request=InterpretationInput.model_validate(value)
            if canonical(request.model_dump(mode='json'))!=canonical(source.value.model_dump(mode='json')):
                s._call('native_revoke',**s._lease(cp.lease));raise Denied('real_source_edit')
            result=cp.invoke('answer',answers)
            return self.response(cp,owner,result,handle['handle'],blob)
        if source.payload is None or source.result.request is None:raise Denied('real_ordinary_required')
        proposed=PlannerInput.model_validate(value);expected=source.payload
        execution={'startingLocation'}
        if any(getattr(proposed,k)!=getattr(expected,k) for k in PlannerInput.model_fields if k not in execution):raise Denied('real_changed_meaning')
        controls=Execution(startingLocation=proposed.startingLocation)
        # Terminal planning cannot publish a Google result or another handle.
        result=cp.invoke('plan',controls);out=self.public(result)
        out.pop('privateOuting',None)
        return out
