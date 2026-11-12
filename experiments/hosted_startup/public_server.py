"""Local-only FastAPI liveness fixture; production refusal remains untouched."""
import os,json,ssl
from email.message import Message
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
import uvicorn
from starlette.responses import JSONResponse
from experiments.service_isolation.server import config,epoch
from experiments.service_isolation.runtime import connection
from experiments.hosted_identity.auth import Auth
from experiments.hosted_startup.public_auth import StatusVerifier
from experiments.shared_state.contracts import Denied

def main():
    if os.environ.get('WHERETO_ENV','development')!='development' or os.environ.get('NODE_ENV')=='production' or any(os.environ.get(k) for k in ('K_SERVICE','VERCEL','RENDER')):raise Denied('local_status_only')
    c=config()
    from experiments.hosted_startup.identity import verify
    if c['identityBuild']!=verify():raise Denied('public_status_build')
    def consume(*args):
        with connection(c,'witness') as db:db.execute('SELECT witness.hosted_nonce(%s,%s,%s,%s,%s)',args)
    verifier=StatusVerifier(Auth(c,consume,lambda:epoch(c)))
    from backend.main import app
    class Boundary:
        async def __call__(self,scope,receive,send):
            if scope['type']=='lifespan':return await app(scope,receive,send)
            if scope['type']!='http':return
            if scope['method']!='GET' or scope['path']!='/health':return await JSONResponse({'code':'hosted_route_unavailable'},503)(scope,receive,send)
            try:
                h=Message()
                for k,v in scope['headers']:h[k.decode()]=v.decode()
                if h.get('transfer-encoding') or h.get('content-length') not in (None,'0'):raise Denied('status_body')
                verifier.check(h,'GET','/health',b'')
            except Exception:return await JSONResponse({'status':'error'},403)(scope,receive,send)
            return await app(scope,receive,send)
    d=Path('/tmp/startup-tls');d.mkdir(mode=0o700)
    for name in ('certificate','tlsKey'):(d/name).write_text(c[name]);(d/name).chmod(0o600)
    # Fake preparation only. Neither validate_environment invocation is patched.
    # No backend test mode, provider fallback or production startup claim.
    with ExitStack() as stack:
        stack.enter_context(patch('backend.ai_readiness.start',return_value=None))
        stack.enter_context(patch('requests.sessions.Session.send',side_effect=AssertionError('No providers')))
        uvicorn.run(Boundary(),host='127.0.0.1',port=c['port'],ssl_certfile=str(d/'certificate'),ssl_keyfile=str(d/'tlsKey'),access_log=False,log_level='warning')
if __name__=='__main__':main()
