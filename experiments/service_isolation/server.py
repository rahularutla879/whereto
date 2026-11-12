"""Private loopback TLS servers. Explicit disposable config only, never FastAPI startup."""
from contextlib import ExitStack
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json,os,ssl,sys,traceback
from pathlib import Path
from threading import BoundedSemaphore
from unittest.mock import patch
import psycopg
from pydantic import ValidationError
from experiments.service_isolation.auth import Verify,Client,MAX_BODY,MAX_RESPONSE,unb64
from experiments.service_isolation.runtime import connection,dispatch,witness
from experiments.shared_state.contracts import Denied,Unavailable
from experiments.shared_state.evidence_models import canonical,strict_json


def config():
    from experiments.service_isolation.identity import verify
    if not Path('/.dockerenv').exists() or {p.name for p in Path('/sys/class/net').iterdir()}!={'lo'}:raise Denied('fixture_only')
    c=json.loads(os.environ['TASK52_SERVICE_CONFIG'])
    if c['environment']!='synthetic-isolated-services' or c['build']!=verify():raise Denied('service_build')
    return c


def epoch(c):
    with connection(c,'witness') as db:return db.execute('SELECT witness.epoch()').fetchone()[0]


def consume(c,*args):
    with connection(c,'witness') as db:db.execute('SELECT witness.service_nonce(%s,%s,%s,%s,%s)',args)


def handler(c,path,value,owner):
    if c['service']=='factory':
        if path=='/dispatch-check':
            from experiments.service_isolation.runtime import current_dispatch
            return current_dispatch(value)
        from experiments.service_isolation.factory import Factory
        return Factory(c).handle(path,value,owner)
    if c['service']=='counter' and path=='/count':
        if set(value)!={'capability','wire'} or len(value['capability'])!=64:raise Denied('counter_shape')
        raw=unb64(value['wire'])
        if len(raw)>100000 or canonical(json.loads(raw))!=raw:raise Denied('counter_payload')
        with connection(c) as db:db.execute('SELECT synthetic_state.app_count_input(%s,%s)',(value['capability'],raw))
        return dict(counted=True,units=len(raw),profile='fictional-utf8-bytes-not-provider-tokens')
    if c['service']=='dispatcher' and path=='/send':return dispatch(c,value)
    if c['service']=='recovery' and path=='/recover':
        if set(value)!={'action','value'}:raise Denied('recovery_shape')
        a=value['action']
        if a not in ('epoch','RECONCILED_STOPPED','REVOKED','QUARANTINED'):raise Denied('recovery_method')
        arg={'epoch':value['value']} if a=='epoch' else {'reason':value['value']}
        with connection(c,'witness') as db:db.execute('SELECT witness.operator(%s,%s)',(a,__import__('psycopg.types.json',fromlist=['Jsonb']).Jsonb(arg)))
        return dict(stopped=True) # No endpoint can unquarantine, refund or renew a grant.
    raise Denied('service_method')


def main():
    c=config();directory=Path('/tmp/task52-tls');directory.mkdir(mode=0o700)
    for k in ('certificate','tlsKey','caPem'):
        f=directory/k;f.write_text(c[k]);f.chmod(0o600)
    c['ca']=str(directory/'caPem')
    verify=Verify(c,lambda *a:consume(c,*a),lambda:epoch(c));gate=BoundedSemaphore(4);callback_gate=BoundedSemaphore(4)
    class Handler(BaseHTTPRequestHandler):
        server_version='';sys_version=''
        def log_message(self,*args):pass # Never log source/body/tokens or database errors.
        def do_GET(self):self.send_error(405)
        def do_POST(self):
            active_gate=callback_gate if c['service']=='factory' and self.path=='/dispatch-check' else gate
            if not active_gate.acquire(blocking=False):self.send_error(503);return
            status=200;stage='decode'
            def audit(error):
                print(json.dumps(dict(event='service_refused',service=c['service'],stage=stage,reason=getattr(error,'code',type(error).__name__),sqlstate=getattr(error,'sqlstate',None),frames=[(Path(f.filename).name,f.name,f.lineno) for f in traceback.extract_tb(error.__traceback__)])),file=sys.stderr,flush=True)
            try:
                self.connection.settimeout(5)
                if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length',[]))!=1 or len(self.headers.get_all('Authorization',[]))!=1:raise Denied('http_shape')
                n=int(self.headers['Content-Length'])
                if not 0<n<=MAX_BODY or self.headers.get('Content-Type')!='application/json':raise Denied('http_body')
                raw=self.rfile.read(n)
                if len(raw)!=n:raise Denied('http_body')
                value=strict_json(raw);auth=self.headers['Authorization']
                if not auth.startswith('Bearer '):raise Denied('service_authentication')
                stage='authenticate'
                principal,owner=verify.check(auth[7:],self.path,raw)
                # Only the role-specific handler sees its own credentials.
                stage='action'
                result={'result':handler(c,self.path,value,owner)}
            except (Denied,ValidationError,ValueError,KeyError,TypeError) as error:audit(error);status=403;result={'error':'request_refused'}
            except (Unavailable,psycopg.Error,OSError) as error:audit(error);status=503;result={'error':'authority_unavailable'}
            except Exception as error:audit(error);status=500;result={'error':'authority_stopped'}
            finally:active_gate.release()
            wire=canonical(result)
            if len(wire)>MAX_RESPONSE:
                stage='encode';audit(Denied('response_bound'));status=503;wire=canonical({'error':'response_bound'})
            try:
                self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(wire)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(wire)
            except OSError:pass # Never repeat provider work after a lost response.
    server=ThreadingHTTPServer(('127.0.0.1',c['port']),Handler);server.daemon_threads=True
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(directory/'certificate',directory/'tlsKey');server.socket=context.wrap_socket(server.socket,server_side=True)
    with ExitStack() as stack:
        from backend.testing_clock import calendar_clock
        reference=datetime.fromisoformat(c['referenceTime']);stack.enter_context(calendar_clock(reference))
        clock=stack.enter_context(patch('backend.advanced_planning.datetime',wraps=datetime));clock.now.side_effect=lambda tz=None:reference.astimezone(tz or timezone.utc)
        stack.enter_context(patch('requests.sessions.Session.send',side_effect=AssertionError('External provider transport forbidden')))
        if c['service']=='factory':
            from backend.saved_plans import PersistenceError
            def reopen(request):
                doc=c.get('savedRecords',{}).get(request.accessToken)
                if doc is None:raise PersistenceError(404)
                return json.loads(json.dumps(doc))
            stack.enter_context(patch('backend.saved_plans.reopen',side_effect=reopen));stack.enter_context(patch('backend.saved_refresh.reopen',side_effect=reopen))
        server.serve_forever(poll_interval=.2)

if __name__=='__main__':main()
