"""Host-only Docker fixture controller. No production code calls this module."""
from pathlib import Path
from tempfile import TemporaryDirectory
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread,Event
import base64,json,os,subprocess,time,secrets,http.client,shutil
ROOT=Path(__file__).resolve().parents[2];P=Path(__import__('sys').argv[1]).resolve();D=['docker','--context','colima-whereto-task52']
VOLUMES={}
images=json.loads((P/'images.json').read_bytes());cohort=__import__('hashlib').sha256((P/'roles/cohort.json').read_bytes()).hexdigest()
def run(*a,**kw):return subprocess.run(D+list(a),check=True,**kw)
def out(*a,**kw):return subprocess.check_output(D+list(a),**kw)

def fixture_volume(directory):
    volume='whereto-real-image-test-'+secrets.token_hex(8)
    out('volume','create','--label','whereto.task52.checkpoint=real-image-test',volume)
    helper=out('run','-d','--platform','linux/amd64','--network','none','--user','0:0','--cap-drop','ALL','--security-opt','no-new-privileges','--mount','type=volume,src='+volume+',dst=/testing','--entrypoint','sleep',images['backend']['image'],'300').decode().strip()
    try:run('cp',str(directory)+'/.',helper+':/testing',stdout=subprocess.DEVNULL)
    finally:run('rm','-f',helper,stdout=subprocess.DEVNULL)
    return volume

def main():
    safety=__import__('sys').argv[2:]==['--adversarial']
    if __import__('sys').argv[2:] and not safety:raise ValueError('Unknown image test mode')
    marker=Path('/tmp/task52-six-browser-container.json')
    if marker.exists():raise RuntimeError('Archive prior task marker first')
    (P/'role-logs').mkdir(exist_ok=True);
    identity={str(p.relative_to(ROOT)):__import__('hashlib').sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'experiments/real_images/role.py',ROOT/'experiments/real_images/browser.mjs',ROOT/'private_runtime/real_application/test_image_browser.py',ROOT/'private_runtime/real_application/run_native.py']}
    with (P/('safety-source.json' if safety else 'browser-source.json')).open('x') as f:json.dump(identity,f,sort_keys=True,indent=2)
    owned={};finished=set();stop=Event();client=None
    # Runtime must not need fixture code, Docker, or writable app files.
    def execute(code,raw=None):return out('exec',*(['-i'] if raw is not None else []),client,'python','-c',code,input=raw)
    log=(P/('container-safety-services.log' if safety else 'container-browser-services.log')).open('x')
    env={**os.environ,'PYTHONPATH':str(ROOT)}
    command="from private_runtime.real_application.run_native import main;main(service_only=True,browser_hold="+repr(not safety)+",image_cases="+repr(('test_image_replacement_and_replay','test_image_uncertain','test_image_redis_loss','test_000_count_relay_rejects_substitution_replay_and_generation') if safety else ())+",image_cohort="+repr(cohort)+")"
    controller=subprocess.Popen([str(ROOT/'backend/.venv/bin/python'),'-c',command],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
    def supervisor():
        while not stop.is_set():
            try:
                raw=execute("from pathlib import Path;import json;print(json.dumps({p.stem:json.loads(p.read_bytes()) for p in Path('/tmp/image-role-requests').glob('*.json')}))")
                docs=json.loads(raw)
                for id,v in docs.items():
                    if id in finished:continue
                    if id not in owned:
                        assert v['config']['service'] in images and v['config']['build']==cohort
                        with TemporaryDirectory(prefix='real-image-fixture-') as temp:
                            testing=Path(temp);shutil.copyfile(ROOT/'experiments/real_images/role.py',testing/'role.py');shutil.copyfile(ROOT/'experiments/hosted_identity/tokens.py',testing/'tokens.py')
                            value=dict(v,certificate='/testing/cert.pem',tlsKey='/testing/key.pem')
                            (testing/'config.json').write_text(json.dumps(value))
                            for name,data in v['files'].items():
                                dest='cert.pem' if name==v['certificate'] else 'key.pem' if name==v['tlsKey'] else 'real-store-ca.pem'
                                (testing/dest).write_bytes(base64.b64decode(data))
                            for f in testing.iterdir():f.chmod(0o444)
                            volume=fixture_volume(testing);VOLUMES[id]=volume
                        cid=out('create','--platform','linux/amd64','--network',network,'--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','384m','--cpus','1','--pids-limit','128','--mount','type=volume,src='+volume+',dst=/testing,readonly','--entrypoint','python',images[v['config']['service']]['image'],'/testing/role.py').decode().strip();owned[id]=cid
                        run('start',cid,stdout=subprocess.DEVNULL)
                        for _ in range(120):
                            logs=out('logs',cid,stderr=subprocess.STDOUT)
                            if b'IMAGE_ROLE_READY' in logs:ready=True;break
                            state=json.loads(out('inspect',cid))[0]['State']
                            if not state['Running']:ready=False;break
                            time.sleep(.25)
                        else:ready=False
                        (P/'role-logs'/(id+'.log')).write_bytes(logs)
                        execute("from pathlib import Path;import sys;Path('/tmp/image-role-requests/"+id+".state').write_bytes(sys.stdin.buffer.read())",json.dumps({'ready':ready}).encode())
                    cid=owned[id]
                    requested=execute("from pathlib import Path;print(Path('/tmp/image-role-requests/"+id+".stop').exists())").strip()==b'True'
                    if requested:
                        logs=out('logs',cid,stderr=subprocess.STDOUT);(P/'role-logs'/(id+'.log')).write_bytes(logs)
                        subprocess.run(D+['rm','-f',cid],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                        subprocess.run(D+['volume','rm',VOLUMES.pop(id)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                        execute("from pathlib import Path;Path('/tmp/image-role-requests/"+id+".stopped').touch()");finished.add(id)
            except subprocess.CalledProcessError:
                if controller.poll() is not None:break
            time.sleep(.1)
    try:
        for _ in range(240):
            if marker.exists():break
            if controller.poll() is not None:raise RuntimeError('Disposable controller startup failed')
            time.sleep(.5)
        else:raise RuntimeError('Controller deadline')
        client=json.loads(marker.read_bytes())['client'];network=json.loads(out('inspect',client))[0]['HostConfig']['NetworkMode'];assert network.startswith('container:')
        Thread(target=supervisor,daemon=True).start()
        if safety:
            controller.wait(timeout=900)
            assert controller.returncode==0,'Actual image safety acceptance failed'
            print('CONTAINER_SAFETY_ACCEPTANCE_PASSED',flush=True);return
        for _ in range(480):
            if execute("from pathlib import Path;print(Path('/tmp/real-browser-control.json').exists())").strip()==b'True':break
            if controller.poll() is not None:raise RuntimeError('Image services failed')
            time.sleep(.5)
        else:raise RuntimeError('Image service deadline')
        control=json.loads(execute("from pathlib import Path;import sys;sys.stdout.buffer.write(Path('/tmp/real-browser-control.json').read_bytes())"))
        frontend,edge=start_frontend(control,network,client,execute,owned)
        browser=subprocess.run(['node',str(ROOT/'experiments/real_images/browser.mjs'),str(P)],cwd=ROOT,timeout=480)
        for _ in range(1800):
            result=P/'browser-result.json'
            if result.exists():
                run('rm','-f',frontend,stdout=subprocess.DEVNULL);run('volume','rm',VOLUMES.pop('frontend'),stdout=subprocess.DEVNULL)
                execute("from pathlib import Path;import sys;Path('/tmp/real-browser-done.json').write_bytes(sys.stdin.buffer.read())",result.read_bytes());break
            time.sleep(.5)
        else:raise RuntimeError('Browser deadline')
        controller.wait(timeout=300);assert controller.returncode==0,'Container browser acceptance failed'
        edge.shutdown();print('CONTAINER_BROWSER_ACCEPTANCE_PASSED',flush=True)
    finally:
        if controller.poll() is None:
            try:execute("from pathlib import Path;Path('/tmp/real-browser-done.json').write_text('{\"passed\":false,\"reason\":\"fixture controller stopped\"}')")
            except (subprocess.CalledProcessError,TypeError):pass
            try:controller.wait(timeout=60)
            except subprocess.TimeoutExpired:controller.terminate();controller.wait(timeout=30)
        stop.set()
        for cid in set(owned.values()):subprocess.run(D+['rm','-f',cid],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for volume in VOLUMES.values():subprocess.run(D+['volume','rm',volume],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        if controller.poll() is None:controller.terminate();controller.wait(timeout=30)
        log.close()
        if marker.exists() and client and json.loads(marker.read_bytes()).get("client")==client:
            marker.rename(P/("safety-controller-marker.json" if safety else "browser-controller-marker.json"))

def start_frontend(control,network,client,execute,owned):
    # Source-pinned application/proxy/network run inside the actual frontend image.
    # External fixture identity injection never enters the image or production CMD.
    c=control['frontend'];config=dict(origin='https://frontend-task52-offline.run.app',backendEndpoint='https://localhost:'+str(control['backendPort']),backendAudience=c['audiences']['backend'],iapAudience=c['iapAudience'],serviceSubject=c['enrollment']['frontend']['sub'],serviceEmail=c['enrollment']['frontend']['email'],testers=c['testers'],build=cohort,environment=c['identityEnvironment'],epoch=c['epoch'],signingKey=c['signingKey'])
    cert=execute("from pathlib import Path;import sys;sys.stdout.buffer.write(Path("+repr(control['serviceCA'])+").read_bytes())")
    with TemporaryDirectory(prefix='real-front-image-fixture-') as tmp:
        p=Path(tmp)/'testing';p.mkdir();(p/'ca.pem').write_bytes(cert);(p/'identity.json').write_text(json.dumps(dict(config=config,workload=c['googleKeys']['workload'],iap=c['googleKeys']['iap'],token=c['oidcTokens'][c['audiences']['backend']])))
        # Same reviewed public identity implementation; only module paths differ.
        source=(ROOT/'lib/server-identity.ts').read_text().replace("from 'jose'","from '/app/node_modules/jose/dist/webapi/index.js'").replace("from './identity-json'","from '/app/private-runtime/identity-json.mjs'")
        compilejs="const ts=require('typescript'),fs=require('fs');process.stdout.write(ts.transpileModule(fs.readFileSync(0,'utf8'),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText)"
        (p/'fixture-port.mjs').write_bytes(subprocess.check_output(['node','-e',compilejs],cwd=ROOT,input=source.encode()))
        (p/'frontend.mjs').write_text("import fs from 'node:fs';import {createLocalJWKSet} from '/app/node_modules/jose/dist/webapi/index.js';import {composeIdentityPort} from './fixture-port.mjs';import {createRealOrdinaryUIProfile,installPrivateProfile} from '/app/private-runtime/boundary-v1.mjs';import {createHTTPSChannel} from '/app/private-runtime/network-port-v2.mjs';const d=JSON.parse(fs.readFileSync('/testing/identity.json'));const port=composeIdentityPort(d.config,{fixture:true,workload:createLocalJWKSet(d.workload),iap:createLocalJWKSet(d.iap),metadata:async()=>new Response(d.token,{headers:{'Metadata-Flavor':'Google'}})});installPrivateProfile(createRealOrdinaryUIProfile(d.config.origin,d.config.backendAudience,port,createHTTPSChannel({audience:d.config.backendAudience,endpoint:d.config.backendEndpoint})));await import('/app/server.js');")
        for f in p.iterdir():f.chmod(0o444)
        volume=fixture_volume(p);VOLUMES['frontend']=volume
    cid=out('create','--platform','linux/amd64','--network',network,'--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','512m','--cpus','1','--pids-limit','128','--mount','type=volume,src='+volume+',dst=/testing,readonly','-e','NODE_EXTRA_CA_CERTS=/testing/ca.pem','-e','PORT=8080','--entrypoint','node',images['frontend']['image'],'/testing/frontend.mjs').decode().strip();owned['frontend']=cid
    run('start',cid,stdout=subprocess.DEVNULL)
    for _ in range(60):
        try:
            execute("import socket;s=socket.create_connection(('127.0.0.1',8080),.5);s.close()");break
        except subprocess.CalledProcessError:time.sleep(.5)
    else:raise RuntimeError('Image frontend did not listen')
    cookie=secrets.token_hex(24)
    request_code="""import sys,json,base64,http.client
v=json.loads(sys.stdin.buffer.read());c=http.client.HTTPConnection('127.0.0.1',8080,timeout=120)
c.request(v['method'],v['path'],base64.b64decode(v['body']),v['headers']);r=c.getresponse();raw=r.read(2000001);assert len(raw)<=2000000
print(json.dumps(dict(status=r.status,headers=r.getheaders(),body=base64.b64encode(raw).decode())));c.close()
"""
    class Edge(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def do_GET(self):self.action()
        def do_POST(self):self.action()
        def action(self):
            if any(self.headers.get(k) for k in ('Authorization','X-Goog-IAP-JWT-Assertion','X-Whereto-Context')):self.send_error(403);return
            if self.path.startswith('/api/') and 'image-fixture='+cookie not in self.headers.get('Cookie','').split('; '):self.send_error(403);return
            if self.command=='POST' and self.headers.get('Origin')!='http://'+self.headers['Host']:self.send_error(403);return
            try:
                n=int(self.headers.get('Content-Length','0'));assert n<=65536 and not self.headers.get('Transfer-Encoding')
                value=dict(method=self.command,path=self.path,body=base64.b64encode(self.rfile.read(n)).decode(),headers={'Content-Type':'application/json','X-Goog-IAP-JWT-Assertion':control['users']['alice'],**({'Origin':config['origin']} if self.command=='POST' else {})})
                result=json.loads(execute(request_code,json.dumps(value).encode()));body=base64.b64decode(result['body']);self.send_response(result['status'])
                for k,v in result['headers']:
                    if k.lower()not in ('connection','content-length','transfer-encoding','set-cookie'):self.send_header(k,v)
                if self.path=='/':self.send_header('Set-Cookie','image-fixture='+cookie+'; HttpOnly; SameSite=Strict; Path=/')
                self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            except Exception:self.send_error(503)
    edge=ThreadingHTTPServer(('127.0.0.1',0),Edge);Thread(target=edge.serve_forever,daemon=True).start()
    ready=dict(url='http://127.0.0.1:'+str(edge.server_port),text=control['text'],date=control['answerDate'],containerImage=True,result=str(P/'browser-result.json'))
    (P/'browser-ready.json').write_text(json.dumps(ready));print('ACTUAL_IMAGE_BROWSER_READY',flush=True);return cid,edge
if __name__=='__main__':main()
