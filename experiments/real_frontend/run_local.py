"""Test-only loopback IAP edge and backend bridge for the packaged Next server.

Docker access belongs ONLY to this disposable controller, never the frontend.
No real identities, provider credentials, APIs or journal are loaded.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from threading import Thread
from hashlib import sha256
import base64,http.client,json,os,secrets,shutil,socket,ssl,subprocess,time
D=['docker','--context','colima-whereto-task52']

def main():
    marker=Path('/tmp/task52-six-browser-container.json')
    for _ in range(120):
        if marker.exists():break
        time.sleep(.5)
    else:raise RuntimeError('Local service marker unavailable')
    client=json.loads(marker.read_text())['client']
    def execute(code,raw=None):return subprocess.check_output(D+['exec',*(['-i'] if raw is not None else []),client,'python','-c',code],input=raw)
    for _ in range(120):
        if execute("from pathlib import Path;print(Path('/tmp/real-browser-control.json').is_file())").strip()==b'True':break
        time.sleep(.5)
    else:raise RuntimeError('Local browser services unavailable')
    control=json.loads(execute("from pathlib import Path;import sys;sys.stdout.buffer.write(Path('/tmp/real-browser-control.json').read_bytes())"));front=control['frontend']
    # Fresh test artifact only; original build and historical artifacts untouched.
    source=Path('/tmp/task52-six-real-front');root=Path(__import__('tempfile').mkdtemp(prefix='task52-six-browser-app-'));root.rmdir();shutil.copytree(source/'.next/standalone',root)
    shutil.copytree(source/'.next/static',root/'.next/static');shutil.copytree(source/'private-runtime',root/'private-runtime');shutil.copytree(source/'node_modules/jose',root/'node_modules/jose',dirs_exist_ok=True)
    secret=root/'secrets';secret.mkdir(mode=0o700)
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(secret/'server.key'),'-out',str(secret/'local-fixture-ca.crt'),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    bridge_code="""import sys,json,base64
from private_runtime.https import HTTPS,Endpoint
v=json.loads(sys.stdin.buffer.read());allowed={'/health':'GET','/api/planning-mode':'GET','/api/interpret':'POST','/api/plans/generate':'POST','/api/private-ordinary/revoke':'POST'}
assert allowed.get(v['path'])==v['method']
body=base64.b64decode(v['body']);assert len(body)<=65536
try:
 data=HTTPS(ca_file=CA).request(Endpoint(URL,AUDIENCE),v['method'],v['path'],body,v['headers']);sys.stdout.buffer.write(data)
except Exception:sys.stdout.buffer.write(b'{"code":"fixture_upstream_refused"}')
""".replace('CA',repr(control['serviceCA'])).replace('URL',repr('https://localhost:'+str(control['backendPort']))).replace('AUDIENCE',repr(front['audiences']['backend']))
    class Backend(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def do_GET(self):self.request_()
        def do_POST(self):self.request_()
        def request_(self):
            try:
                n=int(self.headers.get('Content-Length','0'))
                if n>65536 or self.path not in ('/health','/api/planning-mode','/api/interpret','/api/plans/generate','/api/private-ordinary/revoke'):raise ValueError()
                raw=json.dumps(dict(method=self.command,path=self.path,body=base64.b64encode(self.rfile.read(n)).decode(),headers={k:v for k,v in self.headers.items() if k.lower() in ('authorization','x-whereto-context','content-type')})).encode()
                started=time.monotonic();body=execute(bridge_code,raw);print(json.dumps(dict(fixtureStage="backend",path=self.path,seconds=round(time.monotonic()-started,3),refused=b"fixture_upstream_refused" in body)),flush=True);status=403 if b'fixture_upstream_refused' in body else 200
            except Exception:body=b'{"code":"fixture_bridge_refused"}';status=503
            self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    backend=ThreadingHTTPServer(('127.0.0.1',0),Backend);tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);tls.minimum_version=ssl.TLSVersion.TLSv1_2;tls.load_cert_chain(secret/'local-fixture-ca.crt',secret/'server.key');backend.socket=tls.wrap_socket(backend.socket,server_side=True);Thread(target=backend.serve_forever,daemon=True).start()
    cfg=dict(version='52-closed-real-frontend-v1',origin='https://frontend-task52-offline.run.app',backendEndpoint='https://localhost:'+str(backend.server_port),backendAudience=front['audiences']['backend'],iapAudience=front['iapAudience'],serviceSubject=front['enrollment']['frontend']['sub'],serviceEmail=front['enrollment']['frontend']['email'],testers=front['testers'],build=front['build'],environment=front['identityEnvironment'],epoch=front['epoch'],signingKey=front['signingKey'])
    raw=json.dumps(cfg,separators=(',',':')).encode();(secret/'whereto-frontend.json').write_bytes(raw)
    manifest=(root/'private-runtime/frontend-build.json').read_bytes();artifact=sha256(manifest).hexdigest()
    approval=dict(version='52-real-frontend-enrollment-v1',artifact=artifact,configurationSHA256=sha256(raw).hexdigest(),purpose='private-real-ordinary-only',publicTraffic=False,financialAuthorization=False)
    message=json.dumps([approval[k] for k in ('version','artifact','configurationSHA256','purpose','publicTraffic','financialAuthorization')],separators=(',',':')).encode()
    approval['signature']=subprocess.check_output(['node','-e',"const fs=require('node:fs'),c=require('node:crypto');process.stdout.write(c.sign(null,fs.readFileSync(0),fs.readFileSync('/tmp/task52-six-front-authority/fixture-private.pem')).toString('base64url'))"],input=message).decode();(secret/'whereto-frontend-enrollment.json').write_text(json.dumps(approval))
    (secret/'identity.json').write_text(json.dumps(dict(workload=front['googleKeys']['workload'],iap=front['googleKeys']['iap'],audience=front['audiences']['backend'],token=front['oidcTokens'][front['audiences']['backend']])))
    for file in root.rglob('*'):
        if file.is_file() and not file.is_symlink():file.chmod(0o400 if secret in file.parents else 0o444)
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));node_port=sock.getsockname()[1]
    log=Path('/tmp/task52-six-next-runtime.log').open('w');process=subprocess.Popen(['node',str(root/'private-runtime/frontend-entry.mjs')],cwd=root,env={'PATH':os.environ['PATH'],'NODE_ENV':'production','NEXT_TELEMETRY_DISABLED':'1','PORT':str(node_port),'HOSTNAME':'127.0.0.1'},stdout=log,stderr=subprocess.STDOUT)
    cookie=secrets.token_hex(24)
    class Edge(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def do_GET(self):self.request_()
        def do_POST(self):self.request_()
        def request_(self):
            if any(self.headers.get(k) for k in ('Authorization','X-Serverless-Authorization','X-Goog-IAP-JWT-Assertion','X-Whereto-Context','X-Whereto-User')):self.send_error(403);return
            if self.path.startswith('/api/') and 'real-ui='+cookie not in self.headers.get('Cookie','').split('; '):self.send_error(403);return
            if self.command=='POST' and self.headers.get('Origin')!='http://'+self.headers.get('Host',''):self.send_error(403);return
            n=int(self.headers.get('Content-Length','0'))
            if n>65536 or self.headers.get('Transfer-Encoding'):self.send_error(413);return
            c=http.client.HTTPConnection('127.0.0.1',node_port,timeout=120)
            try:
                c.request(self.command,self.path,self.rfile.read(n),{'Content-Type':self.headers.get('Content-Type','application/json'),'X-Goog-IAP-JWT-Assertion':control['users']['alice'],**({'Origin':cfg['origin']} if self.command=='POST' else {})});r=c.getresponse();body=r.read(2000001)
                if len(body)>2000000:raise ValueError()
                print(json.dumps(dict(fixtureStage="edge",path=self.path,status=r.status)),flush=True)
                self.send_response(r.status)
                for k,v in r.getheaders():
                    if k.lower() not in ('connection','content-length','transfer-encoding','set-cookie'):self.send_header(k,v)
                self.send_header('Content-Length',str(len(body)))
                if self.path=='/':self.send_header('Set-Cookie','real-ui='+cookie+'; HttpOnly; SameSite=Strict; Path=/')
                self.end_headers();self.wfile.write(body)
            except Exception:self.send_error(503)
            finally:c.close()
    edge=ThreadingHTTPServer(('127.0.0.1',0),Edge);Thread(target=edge.serve_forever,daemon=True).start()
    try:
        for _ in range(100):
            if process.poll() is not None:raise RuntimeError('Packaged frontend refused; inspect sanitized local runtime log')
            try:
                with socket.create_connection(('127.0.0.1',node_port),timeout=.2):break
            except OSError:time.sleep(.1)
        else:raise RuntimeError('Frontend startup timeout')
        ready=Path('/tmp/task52-six-browser-ready.json');ready.write_text(json.dumps(dict(url='http://127.0.0.1:'+str(edge.server_port),client=client,text=control['text'],date=control['answerDate'],artifact=artifact)));ready.chmod(0o600)
        print('Packaged Next.js real-profile fixture ready on loopback',flush=True)
        for _ in range(1200):
            if Path('/tmp/task52-six-browser-result.json').exists():
                result=Path('/tmp/task52-six-browser-result.json').read_bytes();execute("from pathlib import Path;import sys;Path('/tmp/real-browser-done.json').write_bytes(sys.stdin.buffer.read())",result);return
            if process.poll() is not None:raise RuntimeError('Frontend terminated')
            time.sleep(.5)
        raise RuntimeError('Browser window expired')
    finally:process.terminate();process.wait(timeout=10);log.close();edge.shutdown();backend.shutdown()
if __name__=='__main__':main()
