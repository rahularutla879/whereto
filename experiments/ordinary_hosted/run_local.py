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
            from experiments.ordinary_hosted.identity import verify as identity
            build=identity()
            inspection=json.loads(checked(['inspect',private['roles']['worker-a']]))[0]
            old_mount=next(x['Name'] for x in inspection['Mounts'] if x['Destination']=='/app');network=inspection['HostConfig']['NetworkMode']
            mount='whereto-ordinary-code-'+secrets.token_hex(10);volumes.append(mount);subprocess.run(D+['volume','create',mount],check=True,stdout=subprocess.DEVNULL)
            helper=checked(['run','-d','--platform','linux/amd64','--user','0:0','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','128m','--cpus','.25','--network','none','--mount','type=volume,src='+old_mount+',dst=/source,readonly','--mount','type=volume,src='+mount+',dst=/snapshot','--entrypoint','sleep',parent.parent.run_grants.BACKEND,'300']).strip();helpers.append(helper)
            subprocess.run(D+['exec',helper,'sh','-c','cp -R /source/. /snapshot/'],check=True)
            sources=json.loads(Path('experiments/ordinary_hosted/build.json').read_text())['sources']
            for file in [*sources,'experiments/ordinary_hosted/build.json','experiments/ordinary_hosted/identity.py']:
                subprocess.run(D+['exec',helper,'mkdir','-p','/snapshot/'+str(Path(file).parent)],check=True)
                subprocess.run(D+['cp',file,helper+':/snapshot/'+file],check=True)
            subprocess.run(D+['rm','-fv',helper],check=True,stdout=subprocess.DEVNULL);helpers.clear()
            with TemporaryDirectory(prefix='whereto-ordinary-private-') as temp:
                os.chmod(temp,0o700)
                # Replace only the disposable factory process. Original source/SQL algorithms stay frozen.
                subprocess.run(D+['stop','--time','2',private['roles']['factory']],check=True,stdout=subprocess.DEVNULL)
                fc=deepcopy(configs['factory']);fc['ordinaryBuild']=build;fc['allow']['/ordinary']=['worker-a','worker-b']
                env=Path(temp)/'factory.env';env.write_text('TASK52_SERVICE_CONFIG='+json.dumps(fc));env.chmod(0o600)
                factory=checked(['run','-d','--platform','linux/amd64','--network',network,'--read-only','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','384m','--cpus','1','--mount','type=volume,src='+mount+',dst=/app,readonly','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=32m,uid=10001,gid=10001,mode=0700','--env-file',str(env),'-e','WHERETO_ENV=development','-e','VENUE_DATA_MODE=real','-e','WHERETO_REAL_DEV=1','-e','WHERETO_ROUTES_DEV=1','-e','PYTHONPATH=/app/_deps:/app','-e','PYTHONDONTWRITEBYTECODE=1','--entrypoint','python',parent.parent.run_grants.BACKEND,'-m','experiments.ordinary_hosted.factory_server']).strip()
                extras.append(factory)
                # Same dispatcher role/credentials, with two additional fixed fake replies.
                subprocess.run(D+['stop','--time','2',private['roles']['dispatcher']],check=True,stdout=subprocess.DEVNULL)
                dc=deepcopy(configs['dispatcher']);dc['ordinaryBuild']=build
                de=Path(temp)/'dispatcher.env';de.write_text('TASK52_SERVICE_CONFIG='+json.dumps(dc));de.chmod(0o600)
                dispatcher=checked(['run','-d','--platform','linux/amd64','--network',network,'--read-only','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','384m','--cpus','.5','--mount','type=volume,src='+mount+',dst=/app,readonly','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=32m,uid=10001,gid=10001,mode=0700','--env-file',str(de),'-e','WHERETO_ENV=development','-e','PYTHONPATH=/app/_deps:/app','-e','PYTHONDONTWRITEBYTECODE=1','--entrypoint','python',parent.parent.run_grants.BACKEND,'-m','experiments.ordinary_hosted.dispatcher_server']).strip()
                extras.append(dispatcher)
                for i,name in enumerate(('worker-a','worker-b')):
                    c=deepcopy(configs[name]);c['ordinaryBuild']=build;c['port']=8098+i
                    env=Path(temp)/(name+'.env');env.write_text('TASK52_SERVICE_CONFIG='+json.dumps(c));env.chmod(0o600)
                    args=['run','-d','--platform','linux/amd64','--network',network,'--read-only','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','256m','--cpus','.5','--mount','type=volume,src='+mount+',dst=/app,readonly','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=32m,uid=10001,gid=10001,mode=0700','--env-file',str(env),'-e','WHERETO_ENV=development','-e','PYTHONPATH=/app/_deps:/app','-e','PYTHONDONTWRITEBYTECODE=1','--entrypoint','python',parent.parent.run_grants.BACKEND,'-m','experiments.ordinary_hosted.public_server']
                    extras.append(checked(args).strip())
                    actual=json.loads(checked(['inspect',extras[-1]]))[0]['Config']['Env'];assert not any(v.startswith(('SYNTHETIC_FACTORY_REDIS_PASSWORD=','SYNTHETIC_DELIVERY_REDIS_PASSWORD=')) for v in actual)
                for port in (8091,8093,8098,8099):
                    for _ in range(80):
                        r=subprocess.run(D+['exec',client,'python','-c',"import socket;s=socket.create_connection(('127.0.0.1',"+str(port)+"),.2);s.close()"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                        if r.returncode==0:break
                        time.sleep(.2)
                    else:
                        for container in extras:subprocess.run(D+['logs',container]);raise RuntimeError('Public status fixture unavailable')
                # Host receives only frontend's own fixture credential/public keys;
                # never SQL/Redis, factory, recovery or fake Google signing keys.
                front=deepcopy(configs['frontend']);front['ordinaryBuild']=build
                data=dict(frontend=front,client=client,ingress=secrets.token_hex(32),capture=str(Path(temp)/'last-proof.json'));file=Path(temp)/'frontend.json';file.write_text(json.dumps(data));file.chmod(0o600)
                client_file=Path(temp)/'application-client.json';client_file.write_text(json.dumps({'ingress':data['ingress'],'user':private['users']['alice']}));client_file.chmod(0o600);data['clientFile']=str(client_file)
                with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
                log=open('/tmp/ordinary-next-runtime.log','w');child=subprocess.Popen(['node_modules/.bin/tsx','experiments/ordinary_hosted/next_fixture.ts',str(file),str(port)],stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'NEXT_TELEMETRY_DISABLED':'1','BACKEND_URL':'http://127.0.0.1:9'})
                try:
                    def call(path,headers=None,body=None):
                        h={'Origin':'https://frontend-task52-offline.run.app','Content-Type':'application/json','X-Task52-Local-Ingress':data['ingress'],'X-Goog-IAP-JWT-Assertion':private['users']['alice'],**(headers or {})};req=Request('http://127.0.0.1:'+str(port)+path,headers=h,data=body)
                        try:
                            with urlopen(req,timeout=130 if body is not None else 8) as r:return r.status,json.load(r)
                        except HTTPError as e:return e.code,json.load(e)
                    for _ in range(120):
                        if child.poll() is not None:raise RuntimeError('Next fixture refused startup')
                        try:call('/api/health');break
                        except OSError:time.sleep(.25)
                    else:raise RuntimeError('Next startup deadline')
                    subprocess.run(D+['exec',client,'python','-m','unittest','experiments.ordinary_hosted.test_reliability','-v'],check=True)
                    from experiments.ordinary_hosted.test_http import cases
                    data['frontendBase']='http://127.0.0.1:'+str(port)
                    Tests=cases(call,private,client,extras,D,data)
                    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
                    if not result.wasSuccessful():
                        for container in extras:subprocess.run(D+['logs',container])
                        raise RuntimeError('Ordinary hosted contracts failed')
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
