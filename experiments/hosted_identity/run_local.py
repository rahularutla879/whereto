"""Minimal composition over the frozen service harness; no parent file modifications."""
import json,subprocess,tempfile,zipfile,time,re
from pathlib import Path
from hashlib import sha256
from unittest.mock import patch
from experiments.service_isolation import run_local as parent,test_local
D=parent.D

def main():
    original=parent.run_grants.subprocess.check_output;controller={};extra=[];code_volumes=set()
    with tempfile.TemporaryDirectory(prefix='whereto-hosted-private-') as tmp:
        Path(tmp).chmod(0o700)
        def check(command,**kwargs):
            command=list(command)
            if command[:len(D)+1]==D+['exec'] and 'experiments.service_isolation.bootstrap' in command:
                client=command[len(D)+1];doc=json.loads(Path(__file__).with_name('dependency.json').read_text());wheel=Path('/tmp/whereto-evidence-wheels')/doc['file'];assert sha256(wheel.read_bytes()).hexdigest()==doc['sha256']
                with tempfile.TemporaryDirectory() as deps:
                    with zipfile.ZipFile(wheel) as z:z.extractall(deps)
                    original(D+['cp',deps+'/.',client+':/tmp/evidence-deps'])
                command[command.index('experiments.service_isolation.bootstrap')]='experiments.hosted_identity.bootstrap'
                data=json.loads(original(command,**kwargs));controller.update(data)
                return json.dumps(data['configs'])
            if command[:len(D)+2]==D+['run','-d'] and '--env-file' in command:
                env=Path(command[command.index('--env-file')+1]);c=json.loads(env.read_text().split('=',1)[1])
                if c['service'] in ('factory','counter','dispatcher','recovery','backend'):
                    pos=command.index('--entrypoint');command[pos+1]='python'
                    i=command.index(parent.run_grants.BACKEND);command[i+1:]=['-m','experiments.hosted_identity.server']
                result=original(command,**kwargs)
                if c['service']=='factory':
                    file=Path(tmp)/'frontend.env';file.write_text('TASK52_SERVICE_CONFIG='+json.dumps(controller['configs']['frontend'])+'\n');file.chmod(0o600)
                    clone=list(command);clone[clone.index('--env-file')+1]=str(file);clone[clone.index('--memory')+1]='256m';clone[clone.index('--cpus')+1]='.5'
                    # The extra frontend outlives the parent's cleanup. Remember
                    # only its exact newly created code mount, never prune volumes.
                    for i,arg in enumerate(clone[:-1]):
                        if arg=='--mount':
                            m=re.fullmatch(r'type=volume,src=(whereto-services-code-[a-f0-9]{20}),dst=/app,readonly',clone[i+1])
                            if m:code_volumes.add(m[1])
                    extra.append(original(clone,text=True).strip())
                return result
            return original(command,**kwargs)
        def verify(private,directory,mode):
            private.update(users=controller['users'],fixtureSigners=controller['fixtureSigners'],ingress=controller['ingress']);private['roles']['frontend']=extra[0]
            r=subprocess.run(D+['exec','-i',private['client'],'python','-c',"import os,sys;f=os.open('/tmp/hosted-control.json',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.write(f,sys.stdin.buffer.read());os.close(f)"],input=json.dumps(private).encode(),check=True)
            for name in ('frontend','worker-a','worker-b'):
                port=private['configs']['frontend' if name=='frontend' else name]['port']
                for _ in range(60):
                    q=subprocess.run(D+['exec',private['client'],'python','-c',"import socket;s=socket.create_connection(('127.0.0.1',"+str(port)+"),.2);s.close()"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                    if q.returncode==0:break
                    time.sleep(.25)
                else:raise RuntimeError('Hosted fixture startup')
            from experiments.hosted_identity.test_local import verify as actual
            actual(private)
        try:
            with patch.object(parent.run_grants.subprocess,'check_output',check),patch.object(test_local,'verify',verify):parent.main()
        finally:
            for c in extra:subprocess.run(D+['rm','-fv',c],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            for v in code_volumes:subprocess.run(D+['volume','rm',v],check=True,stdout=subprocess.DEVNULL)

if __name__=='__main__':main()
