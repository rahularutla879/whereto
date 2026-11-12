"""Reuse disposable parent stores; create separately isolated role containers, not cloud resources."""
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json,os,secrets,subprocess,time
from experiments.shared_state import run_grants
from experiments.shared_state.run_native import local_resources

D=run_grants.D
ROOT=run_grants.ROOT

def main(mode='normal'):
    if mode not in ('normal','lost_http','lost_inference','factory_crash','dispatcher_crash','worker_crash'):raise ValueError('fixture cohort')
    redis_factory=secrets.token_hex(24);redis_delivery=secrets.token_hex(24)
    roles={};stores={};created=[];code_volume='whereto-services-code-'+secrets.token_hex(10)
    original=run_grants.run;check=run_grants.subprocess.check_output
    subprocess.run(D+['volume','create',code_volume],check=True,stdout=subprocess.DEVNULL)
    with TemporaryDirectory(prefix='whereto-services-private-') as tmp:
        Path(tmp).chmod(0o700)
        def create(command,**kwargs):
            command=list(command)
            if command[:len(D)+2]==D+['run','-d'] and run_grants.PG in command:
                pos=command.index(run_grants.PG);command[pos:pos]=['-e','POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256']
            if command[:len(D)+2]==D+['run','-d'] and run_grants.BACKEND in command:
                pos=command.index(run_grants.BACKEND);command[pos:pos]=['--mount','type=volume,src='+code_volume+',dst=/snapshot','-e','SYNTHETIC_FACTORY_REDIS_PASSWORD='+redis_factory,'-e','SYNTHETIC_DELIVERY_REDIS_PASSWORD='+redis_delivery]
            if command[:len(D)+2]==D+['run','-d'] and run_grants.REDIS in command:
                # ACL file is copied into this private container before first start;
                # it survives its restart, never via a host mount or worker volume.
                password=command[command.index('--requirepass')+1]
                prefix='52-encrypted-shared-evidence-local-v1:{synthetic:'+'a'*64+'}:*'
                connection='+auth +hello +ping +client|setinfo +client|setname'
                source='+get +time +eval +zrangebyscore +zcard +hlen +zrem +hdel +hvals +hget +zscore +hset +zadd +zrevrange +pexpireat +set'
                acl=Path(tmp)/'redis.acl';acl.write_text('user default on >'+password+' ~* +@all\nuser source_factory on >'+redis_factory+' ~'+prefix+' -@all '+connection+' '+source+'\nuser source_delivery on >'+redis_delivery+' ~'+prefix+' -@all '+connection+' +get +time\n');acl.chmod(0o444)
                creation=list(command);creation[len(D):len(D)+2]=['create'];creation+=['--aclfile','/tmp/task52-services.acl']
                if '--cpus' in creation:creation[creation.index('--cpus')+1]='.25'
                result=resource_check(creation,**kwargs);identity=result.strip() if isinstance(result,str) else result.decode().strip()
                resource_check(D+['cp',str(acl),identity+':/tmp/task52-services.acl']);resource_check(D+['start',identity])
            else:result=resource_check(command,**kwargs)
            if command[:len(D)+2]==D+['run','-d']:
                identity=result.strip() if isinstance(result,str) else result.decode().strip()
                if 'POSTGRES_DB=whereto_synthetic' in command:stores['postgres']=identity
                elif 'POSTGRES_DB=whereto_witness' in command:stores['witness']=identity
                elif run_grants.REDIS in command:stores['redis']=identity
            return result
        def role(name,c,pg):
            env=Path(tmp)/(name+'.env');env.write_text('TASK52_SERVICE_CONFIG='+json.dumps(c,separators=(',',':'))+'\n');env.chmod(0o600)
            args=['run','-d','--platform','linux/amd64','--network','container:'+pg,'--read-only','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges',
                '--memory','512m' if name=='factory' else '384m' if name=='dispatcher' else '192m','--cpus','1' if name=='factory' else '.5',
                '--mount','type=volume,src='+code_volume+',dst=/app,readonly','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=32m,uid=10001,gid=10001,mode=0700',
                '--env-file',str(env),'-e','PYTHONPATH=/app/_deps:/app','-e','PYTHONDONTWRITEBYTECODE=1','-e','WHERETO_ENV=development',
                '-e','VENUE_DATA_MODE=real','-e','WHERETO_REAL_DEV=1','-e','WHERETO_ADVANCED_DEV=1','-e','WHERETO_STOP_RESOLUTION_DEV=1','-e','WHERETO_ROUTES_DEV=1','-e','WHERETO_CONTACT_DETAILS_DEV=1',
                '--entrypoint','python' if name in ('factory','counter','dispatcher','recovery') else 'sleep',run_grants.BACKEND]
            args+=['-m','experiments.service_isolation.server'] if name in ('factory','counter','dispatcher','recovery') else ['3600']
            try:value=check(D+args,text=True).strip()
            except subprocess.CalledProcessError:raise RuntimeError('Isolated role startup failed') from None
            roles[name]=value;created.append(value)
        def selected(*args,**kwargs):
            if len(args)>5 and args[0]=='exec' and args[2:5]==('python','-m','unittest'):
                client=args[1]
                configs=json.loads(check(D+['exec',client,'python','-m','experiments.service_isolation.bootstrap'],text=True))
                original('exec','--user','0',client,'sh','-c','cp -R /app/. /snapshot/ && cp -R /tmp/evidence-deps /snapshot/_deps && find /snapshot -type d -name __pycache__ -prune -exec rm -r {} +')
                pg=json.loads(check(D+['inspect',client],text=True))[0]['HostConfig']['NetworkMode'].split(':',1)[1]
                for name in ['counter','dispatcher','recovery','factory','worker-a','worker-b','worker-other']:role(name,configs[name],pg)
                # Private test metadata stays in the trusted bootstrap client, never workers.
                private=dict(configs=configs,roles=roles,postgres=pg,client=client,stores=stores)
                f=Path(tmp)/'control.json';f.write_text(json.dumps(private));f.chmod(0o600)
                original('exec','-i',client,'python','-c',"import os,sys;fd=os.open('/tmp/service-control.json',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.write(fd,sys.stdin.buffer.read());os.close(fd)",input=f.read_bytes())
                for name in ['counter','dispatcher','recovery','factory']:
                    for _ in range(80):
                        result=subprocess.run(D+['exec',client,'python','-c',"import socket;s=socket.create_connection(('127.0.0.1',"+str(configs[name]['port'])+"),.2);s.close()"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                        if result.returncode==0:break
                        if subprocess.check_output(D+['inspect','--format','{{.State.Running}}',roles[name]],text=True).strip()!='true':
                            subprocess.run(D+['logs',roles[name]]);raise RuntimeError('Private role refused startup: '+name)
                        time.sleep(.25)
                    else:raise RuntimeError('Private role startup deadline: '+name)
                # Host-side tests can exercise fresh Docker exec workers and controlled crashes.
                from experiments.service_isolation.test_local import verify
                verify(private,tmp,mode)
                return None
            return original(*args,**kwargs)
        try:
            with local_resources():
                resource_check=run_grants.subprocess.check_output
                with patch.object(run_grants.subprocess,'check_output',create),patch.object(run_grants,'run',selected):run_grants.main(recovery=False)
        except BaseException:
            for name in ('factory','counter','dispatcher','recovery'):
                if name in roles:subprocess.run(D+['logs','--tail','30',roles[name]],check=False)
            raise
        finally:
            for c in reversed(created):subprocess.run(D+['rm','-fv',c],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            subprocess.run(D+['volume','rm',code_volume],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

if __name__=='__main__':main()
