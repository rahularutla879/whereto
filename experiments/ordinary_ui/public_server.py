"""Local FastAPI facade: public contracts forward to the independently authenticated factory."""
from copy import deepcopy
from email.message import Message
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
import os,json,uvicorn
from starlette.responses import JSONResponse
from experiments.service_isolation.server import config,epoch
from experiments.service_isolation.runtime import connection
from experiments.hosted_identity.auth import Auth,Client
from experiments.ordinary_hosted.request_auth import RequestVerifier
from experiments.ordinary_ui.server import PATHS
from experiments.ordinary_hosted import request_auth
request_auth.PATHS=PATHS
from experiments.service_isolation.auth import b64

def main():
 if os.environ.get('WHERETO_ENV','development')!='development' or any(os.environ.get(k) for k in ('K_SERVICE','VERCEL','RENDER')):raise RuntimeError('Local only')
 c=config();from experiments.ordinary_ui.identity import verify
 if c['ordinaryBuild']!=verify():raise RuntimeError('Build mismatch')
 directory=Path('/tmp/ordinary-tls');directory.mkdir(mode=0o700)
 for k in ('certificate','tlsKey','caPem'):(directory/k).write_text(c[k]);(directory/k).chmod(0o600)
 c['ca']=str(directory/'caPem');public=deepcopy(c);public['identityBuild']=c['ordinaryBuild']
 def consume(*args):
  with connection(c,'witness') as db:db.execute('SELECT witness.hosted_nonce(%s,%s,%s,%s,%s)',args)
 verifier=RequestVerifier(Auth(public,consume,lambda:epoch(c)))
 from backend.main import app
 class Boundary:
  async def __call__(self,scope,receive,send):
   if scope['type']=='lifespan':return await app(scope,receive,send)
   if scope['type']!='http':return
   path=scope['path'];method=scope['method']
   if PATHS.get(path)!=method:return await JSONResponse({'code':'hosted_route_unavailable'},503)(scope,receive,send)
   try:
    import asyncio
    body=b''
    async with asyncio.timeout(5):
     while True:
      message=await receive()
      if message['type']!='http.request':raise ValueError()
      body+=message.get('body',b'')
      if len(body)>65536:raise ValueError()
      if not message.get('more_body'):break
    h=Message()
    for k,v in scope['headers']:h[k.decode()]=v.decode()
    if h.get('transfer-encoding'):raise ValueError()
    # Blocking TLS/SQL work runs off-loop; no retry after disconnect or response loss.
    await asyncio.to_thread(verifier.check,h,method,path,body)
    if path=='/health':return await app(scope,receive,send)
    from experiments.ordinary_hosted.public_json import decode
    if method!='GET':decode(body)
    envelope=dict(path=path,body=b64(body),headers={k:h[k] for k in ('Authorization','X-Whereto-Context')})
    result=await asyncio.to_thread(Client(c).request,'factory','/ordinary',envelope)
    response=JSONResponse(result,headers={'Cache-Control':'no-store'})
   except Exception as error:
    print(json.dumps({'event':'ordinary_refused','class':type(error).__name__,'reason':getattr(error,'code',None),'sqlstate':getattr(error.__context__,'sqlstate',None)}),flush=True)
    response=JSONResponse({'code':'private_action_refused','message':'This outing could not continue safely. Start a new request.'},403,headers={'Cache-Control':'no-store'})
   return await response(scope,receive,send)
 d=directory
 with ExitStack() as stack:
  stack.enter_context(patch('backend.ai_readiness.start',return_value=None));stack.enter_context(patch('requests.sessions.Session.send',side_effect=AssertionError('No provider network')))
  from backend.request_middleware import RequestManagement
  uvicorn.run(RequestManagement(Boundary()),host='127.0.0.1',port=c['port'],ssl_certfile=str(d/'certificate'),ssl_keyfile=str(d/'tlsKey'),access_log=False,log_level='warning')
if __name__=='__main__':main()
