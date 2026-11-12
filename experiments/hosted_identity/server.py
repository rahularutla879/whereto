"""Explicit offline profile. Reuses parent handlers and actual native factories."""
from contextlib import ExitStack
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from threading import BoundedSemaphore,Lock
import ssl,json,os
from unittest.mock import patch
import psycopg
from experiments.shared_state.contracts import Denied,Unavailable
from experiments.shared_state.evidence_models import canonical,strict_json
from experiments.service_isolation import server as parent,runtime
from experiments.service_isolation.auth import MAX_BODY,MAX_RESPONSE
from experiments.hosted_identity.auth import Auth,Client,USER,PRODUCT


def main():
    if any(os.environ.get(k) for k in ('K_SERVICE','VERCEL','RENDER')) or os.environ.get('NODE_ENV')=='production' or os.environ.get('WHERETO_ENV')=='production':raise Denied('offline_only')
    c=parent.config()
    from experiments.hosted_identity.identity import verify
    if c['identityBuild']!=verify():raise Denied('identity_build')
    directory=Path('/tmp/hosted-tls');directory.mkdir(mode=0o700)
    for k in ('certificate','tlsKey','caPem'):
        p=directory/k;p.write_text(c[k]);p.chmod(0o600)
    c['ca']=str(directory/'caPem')
    def epoch():return parent.epoch(c)
    def consume(*args):
        with runtime.connection(c,'witness') as db:db.execute('SELECT witness.hosted_nonce(%s,%s,%s,%s,%s)',args)
    auth=Auth(c,consume,epoch);gate=BoundedSemaphore(4);callbacks=BoundedSemaphore(4);selection=Lock();next_backend=0
    class Handler(BaseHTTPRequestHandler):
        server_version='';sys_version=''
        def log_message(self,*args):pass
        def do_GET(self):self.send_error(405)
        def do_POST(self):
            nonlocal next_backend
            g=callbacks if self.path=='/dispatch-check' else gate
            if not g.acquire(False):self.send_error(503);return
            status=200;context=None
            try:
                self.connection.settimeout(5)
                if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length',[]))!=1 or self.headers.get('Content-Type')!='application/json':raise Denied('http')
                n=int(self.headers['Content-Length'])
                if not 0<n<=MAX_BODY:raise Denied('body')
                raw=self.rfile.read(n);value=strict_json(raw)
                if c['service']=='frontend':
                    if self.path not in PRODUCT or len(self.headers.get_all('X-Goog-IAP-JWT-Assertion',[]))!=1:raise Denied('frontend_auth')
                    if any(self.headers.get(h) for h in ('Authorization','X-Serverless-Authorization','X-Whereto-Context','X-Whereto-User')):raise Denied('browser_identity_header')
                    if self.headers.get('Origin')!='https://frontend-task52-offline.run.app' or self.headers.get('Sec-Fetch-Site') not in (None,'same-origin'):raise Denied('origin')
                    # Local stand-in for Cloud Run's IAP-agent-only Invoker gate.
                    # Never accepted as a production/browser-trusted header.
                    if len(self.headers.get_all('X-Task52-Offline-Ingress',[]))!=1:raise Denied('iap_ingress')
                    ingress=auth.tokens.verify(self.headers['X-Task52-Offline-Ingress'],'workload',c['audiences']['frontend'])
                    if ingress['sub']!=c['ingressIdentity']['sub'] or ingress.get('email')!=c['ingressIdentity']['email'] or ingress.get('email_verified') is not True:raise Denied('iap_ingress')
                    iap=self.headers['X-Goog-IAP-JWT-Assertion'];forward=auth.forward(self.path,raw,iap)
                    with selection:b=c['backends'][next_backend%2];next_backend+=1
                    result=Client(c).request(b,self.path,value,context={'iap':iap,'forward':forward})
                else:
                    owner,ctx=auth.check(self.headers,self.path,raw);context=USER.set(ctx)
                    if c['service']=='backend':
                        if self.path not in PRODUCT:raise Denied('backend_method')
                        result=Client(c).request('factory',self.path,value)
                    else:result=parent.handler(c,self.path,value,owner)
                wire=canonical({'result':result})
                if len(wire)>MAX_RESPONSE:raise Denied('response_bound')
            except (Denied,ValueError,KeyError,TypeError):status=403;wire=canonical({'error':'request_refused'})
            except (OSError,psycopg.Error,Unavailable):status=503;wire=canonical({'error':'authority_unavailable'})
            except Exception as e:
                print(json.dumps({'event':'identity_stopped','service':c['service'],'class':type(e).__name__}),flush=True);status=500;wire=canonical({'error':'authority_stopped'})
            finally:
                if context is not None:USER.reset(context)
                g.release()
            try:
                self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(wire)));self.end_headers();self.wfile.write(wire)
            except OSError:pass
    server=ThreadingHTTPServer(('127.0.0.1',c['port']),Handler);server.daemon_threads=True;tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.minimum_version=ssl.TLSVersion.TLSv1_2;tls.load_cert_chain(directory/'certificate',directory/'tlsKey');server.socket=tls.wrap_socket(server.socket,server_side=True)
    with ExitStack() as stack:
        stack.enter_context(patch.object(runtime,'Client',Client))
        from backend.testing_clock import calendar_clock
        reference=datetime.fromisoformat(c['referenceTime']);stack.enter_context(calendar_clock(reference));clock=stack.enter_context(patch('backend.advanced_planning.datetime',wraps=datetime));clock.now.side_effect=lambda tz=None:reference.astimezone(tz or timezone.utc)
        stack.enter_context(patch('requests.sessions.Session.send',side_effect=AssertionError('No provider network')))
        if c['service']=='factory':
            from backend.saved_plans import PersistenceError
            def reopen(request):
                if request.accessToken not in c['savedRecords']:raise PersistenceError(404)
                return json.loads(json.dumps(c['savedRecords'][request.accessToken]))
            stack.enter_context(patch('backend.saved_plans.reopen',side_effect=reopen));stack.enter_context(patch('backend.saved_refresh.reopen',side_effect=reopen))
        server.serve_forever(poll_interval=.2)

if __name__=='__main__':main()
