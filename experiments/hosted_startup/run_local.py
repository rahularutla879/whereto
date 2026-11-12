"""Reuse exact disposable authority, with actual Next and FastAPI liveness only."""
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from unittest.mock import patch
import subprocess,json,secrets,os,time,socket,unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from experiments.hosted_identity import run_local as parent,test_local
D=parent.D
def checked(args):
    # Bypass the frozen harness's image-creation interception: public workers
    # must not inherit bootstrap Redis credentials or duplicate source mounts.
    r=subprocess.run(D+args,capture_output=True,text=True)
    if r.returncode:raise RuntimeError('Explicit local fixture command refused') from None
    return r.stdout

def main():
    extras=[];volumes=[];helpers=[]
    def verify(private,*_):
        try:
            client=private['client'];configs=private['configs']
            from experiments.hosted_startup.identity import verify as identity
            build=identity()
            inspection=json.loads(checked(['inspect',private['roles']['worker-a']]))[0]
            old_mount=next(x['Name'] for x in inspection['Mounts'] if x['Destination']=='/app');network=inspection['HostConfig']['NetworkMode']
            mount='whereto-startup-code-'+secrets.token_hex(10);volumes.append(mount);subprocess.run(D+['volume','create',mount],check=True,stdout=subprocess.DEVNULL)
            helper=checked(['run','-d','--platform','linux/amd64','--user','0:0','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','128m','--cpus','.25','--network','none','--mount','type=volume,src='+old_mount+',dst=/source,readonly','--mount','type=volume,src='+mount+',dst=/snapshot','--entrypoint','sleep',parent.parent.run_grants.BACKEND,'300']).strip();helpers.append(helper)
            subprocess.run(D+['exec',helper,'sh','-c','cp -R /source/. /snapshot/'],check=True)
            sources=json.loads(Path('experiments/hosted_startup/build.json').read_text())['sources']
            for file in [*sources,'experiments/hosted_startup/build.json','experiments/hosted_startup/identity.py']:
                subprocess.run(D+['exec',helper,'mkdir','-p','/snapshot/'+str(Path(file).parent)],check=True)
                subprocess.run(D+['cp',file,helper+':/snapshot/'+file],check=True)
            subprocess.run(D+['rm','-fv',helper],check=True,stdout=subprocess.DEVNULL);helpers.clear()
            with TemporaryDirectory(prefix='whereto-startup-private-') as temp:
                os.chmod(temp,0o700)
                for i,name in enumerate(('worker-a','worker-b')):
                    c=deepcopy(configs[name]);c['identityBuild']=build;c['port']=8098+i
                    env=Path(temp)/(name+'.env');env.write_text('TASK52_SERVICE_CONFIG='+json.dumps(c));env.chmod(0o600)
                    args=['run','-d','--platform','linux/amd64','--network',network,'--read-only','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','256m','--cpus','.5','--mount','type=volume,src='+mount+',dst=/app,readonly','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=32m,uid=10001,gid=10001,mode=0700','--env-file',str(env),'-e','WHERETO_ENV=development','-e','PYTHONPATH=/app/_deps:/app','-e','PYTHONDONTWRITEBYTECODE=1','--entrypoint','python',parent.parent.run_grants.BACKEND,'-m','experiments.hosted_startup.public_server']
                    extras.append(checked(args).strip())
                    actual=json.loads(checked(['inspect',extras[-1]]))[0]['Config']['Env'];assert not any(v.startswith(('SYNTHETIC_FACTORY_REDIS_PASSWORD=','SYNTHETIC_DELIVERY_REDIS_PASSWORD=')) for v in actual)
                for port in (8098,8099):
                    for _ in range(80):
                        r=subprocess.run(D+['exec',client,'python','-c',"import socket;s=socket.create_connection(('127.0.0.1',"+str(port)+"),.2);s.close()"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                        if r.returncode==0:break
                        time.sleep(.2)
                    else:
                        for container in extras:subprocess.run(D+['logs',container]);raise RuntimeError('Public status fixture unavailable')
                # Host receives only frontend's own fixture credential/public keys;
                # never SQL/Redis, factory, recovery or fake Google signing keys.
                front=deepcopy(configs['frontend']);front['identityBuild']=build
                data=dict(frontend=front,client=client,ingress=secrets.token_hex(32),capture=str(Path(temp)/'last-proof.json'));file=Path(temp)/'frontend.json';file.write_text(json.dumps(data));file.chmod(0o600)
                with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
                log=open('/tmp/startup-next-runtime.log','w');child=subprocess.Popen(['node_modules/.bin/tsx','experiments/hosted_startup/next_fixture.ts',str(file),str(port)],stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'NEXT_TELEMETRY_DISABLED':'1','BACKEND_URL':'http://127.0.0.1:9'})
                try:
                    def call(path,headers=None,body=None):
                        h={'X-Task52-Local-Ingress':data['ingress'],'X-Goog-IAP-JWT-Assertion':private['users']['alice'],**(headers or {})};req=Request('http://127.0.0.1:'+str(port)+path,headers=h,data=body)
                        try:
                            with urlopen(req,timeout=8) as r:return r.status,json.load(r)
                        except HTTPError as e:return e.code,json.load(e)
                    for _ in range(120):
                        if child.poll() is not None:raise RuntimeError('Next fixture refused startup')
                        try:call('/api/health');break
                        except OSError:time.sleep(.25)
                    else:raise RuntimeError('Next startup deadline')
                    class Tests(unittest.TestCase):
                        def test_actual_next_to_two_fastapi_replicas(self):
                            for _ in range(4):self.assertEqual(call('/api/health'),(200,{'status':'ok','backend':'ok'}))
                        def test_identity_and_forged_header_refusals(self):
                            for h in ({'Authorization':'Bearer forged'},{'X-Goog-IAP-JWT-Assertion':'forged'},{'X-Goog-IAP-JWT-Assertion':private['users']['revoked']}):self.assertNotEqual(call('/api/health',h)[0],200)
                            self.assertEqual(call('/api/health',{'X-Goog-Authenticated-User-Id':'bob'})[0],200)
                        def test_actual_routes_block_before_provider_or_local_fallback(self):
                            for p in ('interpret','plans/generate','plans/advanced','plans/options','starting-places','starting-areas','venues/details','plans/save','plans/reopen','plans/refresh'):
                                self.assertEqual(call('/api/'+p,body=b'{}')[1]['code'],'hosted_route_unavailable')
                            self.assertEqual(call('/api/planning-mode')[0],503);self.assertEqual(call('/api/development-diagnostics')[0],404)
                        def test_replay_wrong_audience_and_unsigned_forwarding(self):
                            h=json.loads(Path(data['capture']).read_text())
                            variants=[h,{**h,'authorization':'Bearer '+front['oidcTokens'][front['audiences']['counter']]},{**h,'x-goog-authenticated-user-id':'forged'}]
                            for headers in variants:
                                code="import json,sys\nfrom pathlib import Path\nfrom experiments.service_isolation.auth import TLS\np=json.load(open('/tmp/hosted-control.json'));f=Path('/tmp/replay-ca');f.write_text(p['configs']['worker-b']['caPem']);c=TLS(8099,'worker-b.task52.invalid',str(f),3);c.request('GET','/health',headers=json.load(sys.stdin));r=c.getresponse();assert r.status==403;r.read();c.close()"
                                subprocess.run(D+['exec','-i',client,'python','-c',code],input=json.dumps(headers),text=True,check=True)
                        def test_operational_sql_and_redis_loss_never_open_business_fallback(self):
                            for store in ('postgres','redis'):
                                subprocess.run(D+['pause',private['stores'][store]],check=True,stdout=subprocess.DEVNULL)
                                try:self.assertEqual(call('/api/plans/generate',body=b'{}')[1]['code'],'hosted_route_unavailable')
                                finally:subprocess.run(D+['unpause',private['stores'][store]],check=True,stdout=subprocess.DEVNULL)
                        def test_worker_restart_and_witness_outage(self):
                            subprocess.run(D+['restart','--time','2',extras[0]],check=True,stdout=subprocess.DEVNULL)
                            for _ in range(80):
                                r=subprocess.run(D+['exec',client,'python','-c',"import socket;s=socket.create_connection(('127.0.0.1',8098),.2);s.close()"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                                if r.returncode==0:break
                                time.sleep(.2)
                            else:raise AssertionError('Restart did not become ready')
                            self.assertEqual(call('/api/health')[0],200)
                            subprocess.run(D+['pause',private['stores']['witness']],check=True,stdout=subprocess.DEVNULL)
                            try:self.assertNotEqual(call('/api/health')[0],200)
                            finally:subprocess.run(D+['unpause',private['stores']['witness']],check=True,stdout=subprocess.DEVNULL)
                        def test_no_real_provider_operations(self):
                            code="from experiments.shared_state.test_store import admin\nwith admin() as c:assert c.execute('SELECT count(*) FROM synthetic_state.operations').fetchone()[0]==0\nprint('No financial/provider operation')"
                            subprocess.run(D+['exec',client,'python','-c',code],check=True)
                        def test_z_independent_operator_epoch_invalidates_status_proof(self):
                            code="import json\nfrom pathlib import Path\nfrom experiments.hosted_identity.auth import Client\np=json.load(open('/tmp/hosted-control.json'));c=p['configs']['operator'];f=Path('/tmp/epoch-ca');f.write_text(c['caPem']);c['ca']=str(f);assert Client(c).request('recovery','/recover',{'action':'epoch','value':'e'*64})=={'stopped':True}"
                            subprocess.run(D+['exec',client,'python','-c',code],check=True)
                            self.assertNotEqual(call('/api/health')[0],200)
                    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
                    if not result.wasSuccessful():raise RuntimeError('Next/FastAPI status contracts failed')
                finally:
                    child.terminate()
                    try:child.wait(timeout=10)
                    except subprocess.TimeoutExpired:child.kill();child.wait()
                    log.close()
                    for container in extras:subprocess.run(D+['rm','-fv',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                    extras.clear()
        finally:
            for container in extras:subprocess.run(D+['rm','-fv',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            extras.clear()
            for helper in helpers:subprocess.run(D+['rm','-fv',helper],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            helpers.clear()
            for volume in volumes:subprocess.run(D+['volume','rm',volume],check=True,stdout=subprocess.DEVNULL)
            volumes.clear()
    try:
        with patch.object(test_local,'verify',verify):parent.main()
    finally:
        for container in extras:subprocess.run(D+['rm','-fv',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
if __name__=='__main__':main()
