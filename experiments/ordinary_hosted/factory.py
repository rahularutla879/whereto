"""Two public contracts over the existing native factory, not a second planner."""
from uuid import uuid4
from email.message import Message
from copy import deepcopy
from experiments.service_isolation.factory import Factory as Parent
from experiments.service_isolation.runtime import make_broker,connection
from experiments.hosted_identity.auth import Auth
from experiments.ordinary_hosted.request_auth import RequestVerifier
from experiments.ordinary_hosted.stable_session import Session
from experiments.shared_state.contracts import Denied
from experiments.shared_state.evidence_models import canonical
from experiments.service_isolation.auth import unb64
VERSION='52-private-ordinary-outing-v1'
EXECUTION={'startingLocation','currentArea','locationFirst','useOriginAsSearchAnchor','referenceToken','manualStartingPlace','searchRadius'}
class Factory(Parent):
 def scope(self,s,token,owner):
  # Durable locator ownership includes this public adapter build; no silent cross-build migration.
  return super().scope(s,token,VERSION+"\0"+self.config["ordinaryBuild"]+"\0"+owner)
 def response(self,s,session,owner,result,previous=None,blob=None):
  route=self.put(s,session.ticket,owner,previous,blob);row=self.sql('get',dict(**self.scope(s,route['ticket'],owner),revision=route['revision']))
  out=self.public(result)
  if not isinstance(out,dict):raise Denied('ordinary_result')
  # Unreviewed options/Details/save routes remain unavailable, not implied grants.
  for key in ('optionsToken','detailsToken','saveReceipt','saveAccessToken'):
   if key in out:out[key]=None
  for key in ('canExpand','canDiscover','canShowBeyond'):
   if key in out:out[key]=False
  out.setdefault('notes',[]).append('Local synthetic provider evidence; not verified real venues or routes.')
  out['privateOuting']=dict(version=VERSION,handle=route['ticket'],revision=route['revision'],expiresMs=row['expires'])
  return out
 def ordinary(self,envelope):
  if set(envelope)!={'path','body','headers'}:raise Denied('public_envelope')
  c=deepcopy(self.config);c['identityBuild']=c['ordinaryBuild']
  def consume(*args):
   with connection(c,'witness') as db:db.execute('SELECT witness.hosted_nonce(%s,%s,%s,%s,%s)',args)
  from experiments.service_isolation.server import epoch
  headers=Message()
  if type(envelope['headers']) is not dict or set(envelope['headers'])!={'Authorization','X-Whereto-Context'}:raise Denied('public_headers')
  for k,v in envelope['headers'].items():headers[k]=v
  body=unb64(envelope['body']);owner=RequestVerifier(Auth(c,consume,lambda:epoch(c))).check(headers,'POST',envelope['path'],body)
  from experiments.ordinary_hosted.identity import verify
  if c['ordinaryBuild']!=verify():raise Denied('ordinary_build')
  from experiments.ordinary_hosted.public_json import decode
  value=decode(body)
  if type(value) is not dict:raise Denied('ordinary_input')
  from backend.interpretation import InterpretationInput,ClarificationAnswers
  from backend.real_planning import PlannerInput
  broker=make_broker(self.config);s=broker.store
  handle=value.pop('privateOuting',None)
  if handle is None:
   if envelope['path']!='/api/interpret' or value.get('pending') is not None or value.get('answers'):raise Denied('fresh_source_required')
   source=InterpretationInput.model_validate(value)
   # The native initial request is server-generated and consumed before inference.
   from hashlib import sha256
   from psycopg.types.json import Jsonb
   with self.issuer() as db:db.execute('SELECT synthetic_state.service_start(%s)',(Jsonb(dict(owner=sha256(('synthetic\0'+owner).encode()).hexdigest(),id=str(uuid4()),request=sha256(canonical(value)).hexdigest(),build=c['build'],epoch=c['epoch'])),))
   token,result=broker.interpret(source);session=Session.capture(broker,token,self.issuer)
   return self.response(s,session,owner,result)
  if type(handle) is not dict or set(handle)!={'version','handle','revision','expiresMs'} or handle['version']!=VERSION or type(handle['expiresMs']) is not int:raise Denied('outing_shape')
  route=dict(ticket=handle['handle'],revision=handle['revision'])
  ticket,blob,row=self.get(s,route,owner,consume=True)
  if row['expires']!=handle['expiresMs'] or row['mode']!='source':raise Denied('outing_expiry')
  session=Session.resume(broker,ticket,self.issuer);source=broker._source(session.token)
  if envelope['path']=='/api/interpret':
   if 'pending' in value:raise Denied('client_pending_evidence')
   answers=ClarificationAnswers.model_validate(value.pop('answers',{}));request=InterpretationInput.model_validate(value)
   if request.model_dump()!=source.value.model_dump():
    session.revoke();raise Denied('source_edit_requires_new_interpretation')
   if not source.result.questions:
    if any(answers.model_dump().values()):raise Denied('not_pending')
    result=source.result;session.persist()
   else:
    if {k for k,v in answers.model_dump().items() if v}-{q.field for q in source.result.questions}:
     session.revoke();raise Denied('unexpected_clarification_field')
    result=session.invoke('answer',answers)
  else:
   if source.result.request is None or source.payload is None:raise Denied('ordinary_not_executable')
   proposed=PlannerInput.model_validate(value);expected=PlannerInput.model_validate({**source.result.request.model_dump(),**source.execution})
   if any(getattr(proposed,k)!=getattr(expected,k) for k in PlannerInput.model_fields if k not in EXECUTION):raise Denied('changed_planning_meaning')
   controls={k:getattr(proposed,k) for k in EXECUTION if k in proposed.model_fields_set}
   # Typed, source-preserving execution controls; no new graph/date/model evidence.
   source.execution.update(controls);source.payload=PlannerInput.model_validate({**source.result.request.model_dump(),**source.execution});source.digest=broker._seal(source)
   # Reissue the existing native admission receipt for changed typed execution
   # controls using retained raw evidence; Recorded never performs inference.
   if not session.answers and not source.planned_revision:
    from experiments.shared_state.native_sessions import restore_validation
    registry,scope,outcome=restore_validation(session.state(),session.evidence.clock())
    source.scope=scope;source.outcome=(registry,outcome);source.digest=broker._seal(source)
   session.persist()
   result=session.invoke('plan')
  return self.response(s,session,owner,result,route['ticket'],blob)
