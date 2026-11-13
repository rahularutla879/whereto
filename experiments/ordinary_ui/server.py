"""New local-only adapter; parent bytes/pins remain frozen, no normal startup import."""
from copy import deepcopy
from email.message import Message
from experiments.hosted_identity import server as host
from experiments.service_isolation import server as base
from experiments.ordinary_hosted.factory import Factory as Parent
from experiments.service_isolation.runtime import connection,make_broker,cache
from experiments.hosted_identity.auth import Auth,Client
from experiments.service_isolation.auth import unb64
from experiments.shared_state.contracts import Denied
from experiments.ordinary_hosted.public_json import decode
from experiments.ordinary_hosted import request_auth,identity
PATHS={**request_auth.PATHS,'/api/planning-mode':'GET','/api/private-ordinary/revoke':'POST'}
original=base.handler
class Factory(Parent):
 def ordinary(self,envelope):
  if envelope.get('path') not in ('/api/planning-mode','/api/private-ordinary/revoke'):return super().ordinary(envelope)
  if set(envelope)!={'path','body','headers'} or set(envelope['headers'])!={'Authorization','X-Whereto-Context'}:raise Denied('public_envelope')
  c=deepcopy(self.config);c['identityBuild']=c['ordinaryBuild'];headers=Message()
  for k,v in envelope['headers'].items():headers[k]=v
  def consume(*args):
   with connection(c,'witness') as db:db.execute('SELECT witness.hosted_nonce(%s,%s,%s,%s,%s)',args)
  raw=unb64(envelope['body']);owner=request_auth.RequestVerifier(Auth(c,consume,lambda:base.epoch(c))).check(headers,PATHS[envelope['path']],envelope['path'],raw)
  if envelope['path']=='/api/planning-mode':
   with connection(c,'issuer') as db:
    db.execute('SET TRANSACTION READ ONLY');op=db.execute('SELECT synthetic_state.ui_snapshot(%s,%s)',(c['epoch'],c['build'])).fetchone()[0]
   with connection(c,'witness') as db:
    db.execute('SET TRANSACTION READ ONLY');w=db.execute('SELECT witness.ui_snapshot(%s)',(c['epoch'],)).fetchone()[0]
   if op!=w:raise Denied('readiness_history_disagreement')
   if cache(c).client.ping() is not True:raise Denied('readiness_evidence')
   for target in ('counter','dispatcher','recovery'):
    try:result=Client(self.config).request(target,'/ui-probe',{})
    except Exception:raise Denied('readiness_'+target)
    if result!={'available':True}:raise Denied('readiness_service')
   return dict(enabled=False,mode='unavailable',startingLookupEnabled=False,privateOrdinary=dict(version='52-private-ordinary-ui-v1',dependencyReady=True,ordinarySyntheticOnly=True,financialAuthorization=False,productionReady=False))
  value=decode(raw)
  if set(value)!={'privateOuting'}:raise Denied('revoke_shape')
  handle=value['privateOuting']
  if type(handle) is not dict or set(handle)!={'version','handle','revision','expiresMs'} or handle['version']!='52-private-ordinary-outing-v1':raise Denied('revoke_shape')
  broker=make_broker(c);s=broker.store;ticket,blob,row=self.get(s,dict(ticket=handle['handle'],revision=handle['revision']),owner,consume=True)
  if type(handle['expiresMs']) is not int or row['expires']!=handle['expiresMs']:raise Denied('revoke_expiry')
  from experiments.ordinary_hosted.stable_session import Session
  Session.resume(broker,ticket,self.issuer).revoke()
  return dict(discarded=True)
def handler(c,path,value,owner):
 if path=='/ui-probe' and c['service'] in ('counter','dispatcher','recovery'):
  if value!={}:raise Denied('probe_shape')
  if base.epoch(c)!=c['epoch']:raise Denied('probe_epoch')
  with connection(c,'witness' if c['service']=='recovery' else 'database') as db:
   db.execute('SET TRANSACTION READ ONLY');db.execute('SELECT 1')
  return {'available':True}
 if c['service']=='factory' and path=='/ordinary':
  try:return Factory(c).ordinary(value)
  except Exception as error:
   import traceback,json
   chain=[];current=error
   while current is not None and len(chain)<4:
    chain.append(dict(category=type(current).__name__,reason=getattr(current,'code',None),sqlstate=getattr(current,'sqlstate',None),frames=[(f.filename.rsplit('/',1)[-1],f.name,f.lineno) for f in traceback.extract_tb(current.__traceback__)]));current=current.__context__
   print(json.dumps(dict(event='ordinary_ui_refused',chain=chain)),flush=True);raise
 return original(c,path,value,owner)
def main():
 from experiments.ordinary_ui.identity import verify
 identity.verify=verify;request_auth.PATHS=PATHS;base.handler=handler
 from experiments.ordinary_hosted import dispatcher_server
 from experiments.service_isolation import synthetic
 synthetic.outputs=dispatcher_server.outputs
 check=host.Auth.check
 def audited(self,*args,**kwargs):
  try:return check(self,*args,**kwargs)
  except Exception as error:
   import json
   print(json.dumps(dict(event='ui_auth_refused',service=self.c['service'],reason=getattr(error,'code',None),category=type(error).__name__,sqlstate=getattr(error.__context__,'sqlstate',None))),flush=True);raise
 host.Auth.check=audited
 host.main()
if __name__=='__main__':main()
