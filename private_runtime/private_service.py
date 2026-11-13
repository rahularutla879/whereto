"""Narrow private role composition. No test clocks, signers, bootstrap or live APIs."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from email.message import Message
from threading import BoundedSemaphore
from copy import deepcopy
import json,ssl,signal,threading
from psycopg.types.json import Jsonb
from experiments.shared_state.contracts import Denied,Unavailable
from experiments.shared_state.evidence_models import canonical,strict_json
from experiments.hosted_identity.auth import HostedAuth,USER,verify_proof,PROOF
from experiments.ordinary_hosted.request_auth import RequestVerifier
from experiments.service_isolation.auth import MAX_BODY,MAX_RESPONSE,b64
from private_runtime.registry import Ports,install,current
from private_runtime import owned_dispatch
from private_runtime.image_identity import verify

CALLERS={'factory':{'/ordinary':'backend','/dispatch-check':'dispatcher'},'counter':{'/count':'factory','/ui-probe':'factory'},'dispatcher':{'/send':'factory','/ui-probe':'factory'},'recovery':{'/recover':'operator','/ui-probe':'factory'},'backend':{}}

def enrollment(config):
    required=CALLERS.get(config.get('service'))
    if required is None or set(config.get('allow',{}))!=set(required):raise Denied('service_methods')
    for path,role in required.items():
        principals=config['allow'][path]
        if type(principals) is not list or not principals or len(principals)>8 or len(set(principals))!=len(principals):raise Denied('service_callers')
        if any(config['trust'].get(p,{}).get('role')!=role or p not in config['enrollment'] for p in principals):raise Denied('service_callers')

PATHS={'/health':'GET','/api/interpret':'POST','/api/plans/generate':'POST','/api/planning-mode':'GET','/api/private-ordinary/revoke':'POST'}

def authentication(config,auth_factory=None):
    def nonce(*args):
        with current().connection('witness') as c:c.execute('SELECT witness.hosted_nonce(%s,%s,%s,%s,%s)',args)
    from private_runtime.auth_port import authenticated
    return (auth_factory or authenticated)(config,nonce,current().epoch)

def handle(config,path,value):
    p=current()
    if path=='/ui-probe':
        if value!={} or p.epoch()!=config['epoch']:raise Denied('readiness')
        return {'available':True}
    if p.role=='factory':
        if path=='/dispatch-check':return owned_dispatch.owner().check(value)
        if path=='/ordinary':
            from experiments.ordinary_ui.server import Factory
            with owned_dispatch.owner().action():return Factory(config).ordinary(value)
    if p.role=='counter' and path=='/count':
        if set(value)!={'capability','wire'} or type(value['capability']) is not str or len(value['capability'])!=64:raise Denied('counter_shape')
        from experiments.service_isolation.auth import unb64
        raw=unb64(value['wire'])
        if len(raw)>100000 or canonical(strict_json(raw))!=raw:raise Denied('counter_payload')
        with p.connection() as c:c.execute('SELECT synthetic_state.app_count_input(%s,%s)',(value['capability'],raw))
        return dict(counted=True,units=len(raw),profile='fictional-utf8-bytes-not-provider-tokens')
    if p.role=='dispatcher' and path=='/send':
        from private_runtime.simulation import respond
        return owned_dispatch.dispatch(config,value,respond)
    if p.role=='recovery' and path=='/recover':
        if set(value)!={'action','value'} or value['action'] not in ('epoch','RECONCILED_STOPPED','REVOKED','QUARANTINED'):raise Denied('recovery_method')
        args={'epoch':value['value']} if value['action']=='epoch' else {'reason':value['value']}
        with p.connection('witness') as c:c.execute('SELECT witness.operator(%s,%s)',(value['action'],Jsonb(args)))
        return {'stopped':True}
    raise Denied('role_method')

def backend_app(config,auth_factory=None):
    """Same public/native envelope and actual middleware; no legacy startup override."""
    import asyncio
    from fastapi import FastAPI
    from starlette.responses import JSONResponse
    from backend.request_middleware import RequestManagement
    from experiments.ordinary_hosted import request_auth
    request_auth.PATHS=PATHS
    verifier=RequestVerifier(authentication(config,auth_factory))
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    @app.get('/health')
    async def health():return {'status':'ok'}
    class Boundary:
        async def __call__(self,scope,receive,send):
            if scope['type']=='lifespan':return await app(scope,receive,send)
            if scope['type']!='http':return
            path=scope['path'];method=scope['method']
            if PATHS.get(path)!=method:return await JSONResponse({'code':'hosted_route_unavailable'},503)(scope,receive,send)
            try:
                body=b''
                async with asyncio.timeout(5):
                    while True:
                        message=await receive()
                        if message['type']!='http.request':raise Denied('request_disconnected')
                        body+=message.get('body',b'')
                        if len(body)>65536:raise Denied('request_bound')
                        if not message.get('more_body'):break
                headers=Message()
                for k,v in scope['headers']:headers[k.decode()]=v.decode()
                if headers.get('transfer-encoding'):raise Denied('request_shape')
                await asyncio.to_thread(verifier.check,headers,method,path,body)
                if path=='/health':return await app(scope,receive,send)
                if method!='GET':
                    from experiments.ordinary_hosted.public_json import decode
                    decode(body)
                envelope=dict(path=path,body=b64(body),headers={k:headers[k] for k in ('Authorization','X-Whereto-Context')})
                result=await asyncio.to_thread(current().client.request,'factory','/ordinary',envelope)
                response=JSONResponse(result,headers={'Cache-Control':'no-store'})
            except Exception as error:
                audit(config,error)
                response=JSONResponse({'code':'private_action_refused','message':'This outing could not continue safely. Do not repeat an uncertain operation.'},403,headers={'Cache-Control':'no-store'})
            return await response(scope,receive,send)
    return RequestManagement(Boundary())

def audit(config,error):
    print(json.dumps(dict(event='private_service_refused',role=config['service'],category=type(error).__name__,reason=getattr(error,'code',None),sqlstate=getattr(error.__context__,'sqlstate',None))),flush=True)

def privileged_server(config,*,auth_factory=None,tls=None):
    auth=authentication(config,auth_factory);gate=BoundedSemaphore(4);callbacks=BoundedSemaphore(4)
    class Handler(BaseHTTPRequestHandler):
        server_version='';sys_version=''
        def log_message(self,*_):pass
        def do_GET(self):
            if self.path!='/health':self.send_error(405);return
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length','15');self.end_headers();self.wfile.write(b'{"status":"ok"}')
        def do_POST(self):
            g=callbacks if self.path=='/dispatch-check' else gate
            if not g.acquire(False):self.send_error(503);return
            context=None;caller=None;status=200
            try:
                self.connection.settimeout(5)
                if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length',[]))!=1 or self.headers.get('Content-Type')!='application/json':raise Denied('http_shape')
                n=int(self.headers['Content-Length'])
                if not 0<n<=MAX_BODY:raise Denied('request_bound')
                raw=self.rfile.read(n)
                if len(raw)!=n:raise Denied('request_bound')
                value=strict_json(raw);_,ctx=auth.check(self.headers,self.path,raw);context=USER.set(ctx)
                principal,_=verify_proof(config,ctx['proof'],PROOF,config['service']);caller=owned_dispatch.CALLER.set(principal)
                result=handle(config,self.path,value);wire=canonical({'result':result})
                if len(wire)>MAX_RESPONSE:raise Denied('response_bound')
            except Denied as error:audit(config,error);status=403;wire=canonical({'error':'request_refused'})
            except Exception as error:audit(config,error);status=503;wire=canonical({'error':'authority_unavailable'})
            finally:
                if caller is not None:owned_dispatch.CALLER.reset(caller)
                if context is not None:USER.reset(context)
                g.release()
            try:
                self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(wire)));self.end_headers();self.wfile.write(wire)
            except OSError:pass # Never resend/reconcile uncertain work from a socket result.
    server=ThreadingHTTPServer(('0.0.0.0',config['port']),Handler);server.daemon_threads=True
    if tls:
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2;context.load_cert_chain(*tls);server.socket=context.wrap_socket(server.socket,server_side=True)
    return server

@contextmanager
def runtime(config,*,identity=None,authentication_factory=None,transport=None):
    from private_runtime.image_build import ROLE
    build=verify();enrollment(config)
    if any(k in config for k in ('referenceTime','savedRecords','certificate','tlsKey','admin','bootstrap')):raise Denied('fixture_configuration')
    if config.get('service')!=ROLE or config.get('build')!=build or config.get('identityBuild')!=build or config.get('ordinaryBuild')!=build or config.get('providerMode')!='synthetic' or config.get('realProviderTransport') is not False:raise Denied('private_configuration')
    with Ports(ROLE,config,identity=identity,authentication_factory=authentication_factory,transport=transport) as ports:
        install(ports);owned_dispatch.configure(config)
        yield ports
