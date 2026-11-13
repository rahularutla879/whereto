"""Disposable authority with actual ordinary UI/API, read-only probes and browser hold."""
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
    if args[:2]==['run','-d']:
        from experiments.ordinary_network.resources import record
        record(D,r.stdout.strip())
    return r.stdout

def main():
    extras=[];volumes=[];helpers=[];network_fixture=None
    real_check=subprocess.check_output
    def bootstrap(command,**kwargs):
        command=list(command)
        if 'experiments.hosted_identity.bootstrap' in command:command[command.index('experiments.hosted_identity.bootstrap')]='experiments.ordinary_ui.bootstrap'
        return real_check(command,**kwargs)
    def verify(private,*_):
        try:
            nonlocal network_fixture
            client=private['client'];configs=private['configs']
            from experiments.ordinary_network.identity import verify as identity
            build=identity()
            inspection=json.loads(checked(['inspect',private['roles']['worker-a']]))[0]
            old_mount=next(x['Name'] for x in inspection['Mounts'] if x['Destination']=='/app');network=inspection['HostConfig']['NetworkMode']
            mount='whereto-ordinary-code-'+secrets.token_hex(10);volumes.append(mount);subprocess.run(D+['volume','create',mount],check=True,stdout=subprocess.DEVNULL)
            helper=checked(['run','-d','--platform','linux/amd64','--user','0:0','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','128m','--cpus','.25','--network','none','--mount','type=volume,src='+old_mount+',dst=/source,readonly','--mount','type=volume,src='+mount+',dst=/snapshot','--entrypoint','sleep',parent.parent.run_grants.BACKEND,'300']).strip();helpers.append(helper)
            subprocess.run(D+['exec',helper,'sh','-c','cp -R /source/. /snapshot/'],check=True)
            sources={**json.loads(Path('experiments/ordinary_ui/build.json').read_text())['sources'],**json.loads(Path('experiments/ordinary_network/build.json').read_text())['sources']}
            for file in [*sources,*map(str,Path('private_runtime').glob('test_*.py')),'experiments/ordinary_network/build.json','experiments/ordinary_network/identity.py']:
                subprocess.run(D+['exec',helper,'mkdir','-p','/snapshot/'+str(Path(file).parent)],check=True)
                subprocess.run(D+['cp',file,helper+':/snapshot/'+file],check=True)
            subprocess.run(D+['rm','-fv',helper],check=True,stdout=subprocess.DEVNULL);helpers.clear()
            with TemporaryDirectory(prefix='whereto-ordinary-private-') as temp:
                os.chmod(temp,0o700)
                # Replace only the disposable factory process. Original source/SQL algorithms stay frozen.
                subprocess.run(D+['stop','--time','2',private['roles']['factory']],check=True,stdout=subprocess.DEVNULL)
                fc=deepcopy(configs['factory']);fc['ordinaryBuild']=build;fc['allow']['/ordinary']=['worker-a','worker-b']
                env=Path(temp)/'factory.env';env.write_text('TASK52_SERVICE_CONFIG='+json.dumps(fc));env.chmod(0o600)
                factory=checked(['run','-d','--platform','linux/amd64','--network',network,'--read-only','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','384m','--cpus','1','--mount','type=volume,src='+mount+',dst=/app,readonly','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=32m,uid=10001,gid=10001,mode=0700','--env-file',str(env),'-e','WHERETO_ENV=development','-e','VENUE_DATA_MODE=real','-e','WHERETO_REAL_DEV=1','-e','WHERETO_ROUTES_DEV=1','-e','PYTHONPATH=/app/_deps:/app','-e','PYTHONDONTWRITEBYTECODE=1','--entrypoint','python',parent.parent.run_grants.BACKEND,'-m','experiments.ordinary_network.server']).strip()
                extras.append(factory)
                # Same dispatcher role/credentials, with two additional fixed fake replies.
                subprocess.run(D+['stop','--time','2',private['roles']['dispatcher']],check=True,stdout=subprocess.DEVNULL)
                dc=deepcopy(configs['dispatcher']);dc['ordinaryBuild']=build;dc['allow']['/ui-probe']=['factory']
                de=Path(temp)/'dispatcher.env';de.write_text('TASK52_SERVICE_CONFIG='+json.dumps(dc));de.chmod(0o600)
                dispatcher=checked(['run','-d','--platform','linux/amd64','--network',network,'--read-only','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','384m','--cpus','.5','--mount','type=volume,src='+mount+',dst=/app,readonly','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=32m,uid=10001,gid=10001,mode=0700','--env-file',str(de),'-e','WHERETO_ENV=development','-e','PYTHONPATH=/app/_deps:/app','-e','PYTHONDONTWRITEBYTECODE=1','--entrypoint','python',parent.parent.run_grants.BACKEND,'-m','experiments.ordinary_network.server']).strip()
                extras.append(dispatcher)
                # Install new read-only probes only in disposable stores using bootstrap credentials.
                probe="from pathlib import Path\nfrom experiments.shared_state.test_store import admin\nfrom experiments.shared_state.test_application_grants import witness_admin\nwith admin() as c:c.execute(Path('/app/experiments/ordinary_ui/readiness.sql').read_text())\nwith witness_admin() as c:c.execute(Path('/app/experiments/ordinary_ui/witness_readiness.sql').read_text())"
                subprocess.run(D+['cp','experiments/ordinary_ui',client+':/tmp/ui-source'],check=True)
                probe=probe.replace('/app/experiments/ordinary_ui/','/tmp/ui-source/')
                subprocess.run(D+['exec',client,'python','-c',probe],check=True)
                for name in ('counter','recovery'):
                    subprocess.run(D+['stop','--time','2',private['roles'][name]],check=True,stdout=subprocess.DEVNULL)
                    rc=deepcopy(configs[name]);rc['ordinaryBuild']=build;rc['allow']['/ui-probe']=['factory']
                    re=Path(temp)/(name+'.env');re.write_text('TASK52_SERVICE_CONFIG='+json.dumps(rc));re.chmod(0o600)
                    clone=['run','-d','--platform','linux/amd64','--network',network,'--read-only','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','192m','--cpus','.25','--mount','type=volume,src='+mount+',dst=/app,readonly','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=32m,uid=10001,gid=10001,mode=0700','--env-file',str(re),'-e','WHERETO_ENV=development','-e','PYTHONPATH=/app/_deps:/app','-e','PYTHONDONTWRITEBYTECODE=1','--entrypoint','python',parent.parent.run_grants.BACKEND,'-m','experiments.ordinary_network.server']
                    helpers.append(checked(clone).strip())
                for i,name in enumerate(('worker-a','worker-b')):
                    c=deepcopy(configs[name]);c['ordinaryBuild']=build;c['port']=8098+i
                    env=Path(temp)/(name+'.env');env.write_text('TASK52_SERVICE_CONFIG='+json.dumps(c));env.chmod(0o600)
                    args=['run','-d','--platform','linux/amd64','--network',network,'--read-only','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','256m','--cpus','.5','--mount','type=volume,src='+mount+',dst=/app,readonly','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=32m,uid=10001,gid=10001,mode=0700','--env-file',str(env),'-e','WHERETO_ENV=development','-e','PYTHONPATH=/app/_deps:/app','-e','PYTHONDONTWRITEBYTECODE=1','--entrypoint','python',parent.parent.run_grants.BACKEND,'-m','experiments.ordinary_network.public_server']
                    extras.append(checked(args).strip())
                    actual=json.loads(checked(['inspect',extras[-1]]))[0]['Config']['Env'];assert not any(v.startswith(('SYNTHETIC_FACTORY_REDIS_PASSWORD=','SYNTHETIC_DELIVERY_REDIS_PASSWORD=')) for v in actual)
                for port in (8091,8092,8093,8094,8098,8099):
                    for _ in range(80):
                        r=subprocess.run(D+['exec',client,'python','-c',"import socket;s=socket.create_connection(('127.0.0.1',"+str(port)+"),.2);s.close()"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                        if r.returncode==0:break
                        time.sleep(.2)
                    else:
                        for container in extras+helpers:subprocess.run(D+['logs',container])
                        raise RuntimeError('Public status fixture unavailable at '+str(port))
                # Host receives only frontend's own fixture credential/public keys;
                # never SQL/Redis, factory, recovery or fake Google signing keys.
                front=deepcopy(configs['frontend']);front['ordinaryBuild']=build
                data=dict(frontend=front,client=client,ingress=secrets.token_hex(32),capture=str(Path(temp)/'last-proof.json'),user=private['users']['alice']);from experiments.ordinary_network.fixture import Fixture
                network_fixture=Fixture(D,client,network,mount,parent.parent.run_grants.BACKEND,configs,extras,helpers,volumes,temp)
                network_fixture.configure(data)
                file=Path(temp)/'frontend.json';file.write_text(json.dumps(data));file.chmod(0o600)
                client_file=Path(temp)/'application-client.json';client_file.write_text(json.dumps({'ingress':data['ingress'],'user':private['users']['alice']}));client_file.chmod(0o600);data['clientFile']=str(client_file)
                with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
                port=network_fixture.start_frontend(data)
                try:
                    def call(path,headers=None,body=None):
                        supplied=(headers or {}).get('X-Goog-IAP-JWT-Assertion',private['users']['alice'])
                        who=next((name for name,token in private['users'].items() if token==supplied),None)
                        refreshed=checked(['exec',client,'python','-m','experiments.ordinary_ui.iap_fixture',who]).strip() if who else supplied
                        h={'Origin':'https://frontend-task52-offline.run.app','Content-Type':'application/json','X-Task52-Local-Ingress':data['ingress'],'X-Goog-IAP-JWT-Assertion':private['users']['alice'],**(headers or {}),'X-Goog-IAP-JWT-Assertion':refreshed};req=Request('http://127.0.0.1:'+str(port)+path,headers=h,data=body)
                        try:
                            with urlopen(req,timeout=130 if body is not None else 8) as r:
                                result=(r.status,json.load(r));network_fixture.capture(data);return result
                        except HTTPError as e:return e.code,json.load(e)
                    for _ in range(120):
                        try:call('/api/health');break
                        except OSError:time.sleep(.25)
                    else:raise RuntimeError('Next startup deadline')
                    subprocess.run(D+['exec',extras[0],'python','-m','unittest','private_runtime.test_identity','-v'],check=True)
                    subprocess.run(D+['exec',client,'python','-m','unittest','experiments.ordinary_hosted.test_reliability','-v'],check=True)
                    from experiments.ordinary_ui.test_local import verify as extra
                    try:
                        extra(call,private,client,D,extras)
                        from experiments.ordinary_network.test_network import verify as network_tests
                        network_tests(call,private,client,D,extras,helpers,data)
                    except Exception:
                        for container in extras+helpers:subprocess.run(D+['logs',container])
                        raise
                    if '--browser' in __import__('sys').argv:
                        marker=Path('/tmp/whereto-network-ready.json');network_fixture.start_ingress(port)
                        marker.write_text(json.dumps({'url':network_fixture.browser_url,'synthetic':True}));marker.chmod(0o600)
                        for _ in range(3600):
                            if Path('/tmp/whereto-network-browser-done').exists():break
                            time.sleep(.5)
                        else:raise RuntimeError('Bounded browser review not completed')
                        marker.unlink(missing_ok=True)
                    network_fixture.stop_ingress()
                    if '--browser-only' in __import__('sys').argv:return
                    from experiments.ordinary_hosted.test_http import cases
                    data['frontendBase']='http://127.0.0.1:'+str(port)
                    Tests=cases(call,private,client,extras,D,data)
                    # The unchanged client-driver case needs a CURRENT tester
                    # assertion after a long manual browser hold. Never renew a
                    # native deadline/capability or accept an expired assertion.
                    original_driver=Tests.test_06b_actual_application_client_pending_generation
                    def current_driver(test):
                        fresh=checked(['exec',client,'python','-m','experiments.ordinary_ui.iap_fixture','alice']).strip()
                        client_file.write_text(json.dumps({'ingress':data['ingress'],'user':fresh}));client_file.chmod(0o600)
                        return original_driver(test)
                    Tests.test_06b_actual_application_client_pending_generation=current_driver
                    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
                    if not result.wasSuccessful():
                        for container in extras+helpers:subprocess.run(D+['logs',container])
                        raise RuntimeError('Ordinary hosted contracts failed')
                finally:
                    from experiments.ordinary_network.profile import collect
                    collect(D,extras+helpers,data['capture']+'.timing.jsonl')
                    with open('/tmp/network-next-runtime.log','w') as frontlog:subprocess.run(D+['logs',network_fixture.frontend],stdout=frontlog,stderr=subprocess.STDOUT)
                    network_fixture.close()
                    for container in extras+helpers:subprocess.run(D+['rm','-fv',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                    extras.clear()
        finally:
            for container in extras:subprocess.run(D+['rm','-fv',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            extras.clear()
            for helper in helpers:subprocess.run(D+['rm','-fv',helper],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            helpers.clear()
            for volume in volumes:subprocess.run(D+['volume','rm',volume],check=True,stdout=subprocess.DEVNULL)
            volumes.clear()
    try:
        from experiments.ordinary_network.resources import inventory
        with patch.object(parent.parent.run_grants.subprocess,'check_output',bootstrap),patch.object(test_local,'verify',verify):parent.main()
    finally:
        for container in extras:subprocess.run(D+['rm','-fv',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
if __name__=='__main__':
 from experiments.ordinary_network.resources import inventory
 with inventory(D):main()
