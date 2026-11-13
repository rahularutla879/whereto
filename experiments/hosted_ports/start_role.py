"""External local test bootstrap; never part of an image or hosted command.

Injects fixture verification/metadata only. No signer, admin DB, issuer selection
endpoint or transport fallback exists. Role config contains this role's secrets.
"""
from pathlib import Path
import os,json,sys,ssl,signal,threading,time
if not Path('/.dockerenv').exists() or any(os.environ.get(k) for k in ('K_SERVICE','VERCEL','RENDER')):raise RuntimeError('Local fixture bootstrap only')
import jwt
from experiments.hosted_identity.tokens import Tokens,keyset
from experiments.hosted_identity.auth import _Boundary
from experiments.shared_state.contracts import Denied
class FixtureKeys:
 def __init__(self,docs):self.docs={k:keyset(v,k,offline=True) for k,v in docs.items()}
 def key(self,kind,kid):
  try:return self.docs[kind][kid]
  except KeyError:raise Denied('unknown_fixture_key') from None
class FixtureTokens(Tokens):
 def __init__(self,docs):self.keys=FixtureKeys(docs);self.offline=True
class FixtureAuth(_Boundary):
 def __init__(self,c,consume,epoch):
  if c['identityEnvironment']!='offline-hosted-contract':raise Denied('fixture_environment')
  self.c=c;self.consume=consume;self.epoch=epoch;self.tokens=FixtureTokens(c['googleKeys'])
class FixtureIdentity:
 def __init__(self,c):self.c=c;self.tokens=FixtureTokens(c['googleKeys'])
 def token(self,audience):
  token=self.c['oidcTokens'][audience];value=self.tokens.verify(token,'workload',audience);own=self.c['enrollment'][self.c['principal']]
  if value['sub']!=own['sub'] or value['email']!=own['email'] or value.get('email_verified') is not True:raise Denied('fixture_principal')
  return token

def main():
 from private_runtime.private_service import runtime,privileged_server
 import private_runtime.private_service as service
 def diagnostic(config,error):
  import traceback
  chain=[];seen=set()
  while error is not None and id(error) not in seen and len(chain)<5:
   seen.add(id(error));chain.append(dict(category=type(error).__name__,reason=getattr(error,'code',None),sqlstate=getattr(error,'sqlstate',None),frames=[(Path(f.filename).name,f.name,f.lineno) for f in traceback.extract_tb(error.__traceback__)]));error=error.__context__
  print(json.dumps(dict(event='private_service_refused',role=config['service'],chain=chain)),flush=True)
 service.audit=diagnostic
 original_handle=service.handle
 def controlled_handle(config,path,value):
  block=Path('/tmp/block-next-send')
  if config['service']=='dispatcher' and path=='/send' and block.exists():
   Path('/tmp/reserved-operation.json').write_text(json.dumps({'operation':value['operation'],'ordinal':value['ordinal']}))
   end=time.monotonic()+20
   while block.exists() and time.monotonic()<end:time.sleep(.02)
   if block.exists():raise Denied('fixture_barrier_timeout')
  return original_handle(config,path,value)
 service.handle=controlled_handle
 from private_runtime.https import HTTPS
 c=json.loads(Path('/tests/config.json').read_text())
 from metrics import install
 install(c['service'])
 tls=('/tests/server.crt','/tests/server.key')
 # These are exact application/runtime libraries from the real role image.
 with runtime(c,identity=FixtureIdentity(c),authentication_factory=FixtureAuth,transport=HTTPS(ca_file='/tests/ca.crt')):
  if c['service']=='backend':
   from private_runtime.private_service import backend_app
   import uvicorn
   uvicorn.run(backend_app(c),host='0.0.0.0',port=8080,ssl_certfile=tls[0],ssl_keyfile=tls[1],access_log=False,log_level='warning')
  else:
   server=privileged_server(c,tls=tls)
   def stop(*_):
    if c['service']=='factory':
     from private_runtime.owned_dispatch import owner
     owner().drain(1)
    threading.Thread(target=server.shutdown,daemon=True).start()
   signal.signal(signal.SIGTERM,stop);server.serve_forever(poll_interval=.2);server.server_close()
if __name__=='__main__':main()
