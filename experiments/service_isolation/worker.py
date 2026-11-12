"""Ordinary worker: own workload key/TLS CA only. No database or provider authority."""
import json,os,sys
from pathlib import Path
from experiments.service_isolation.auth import Client,sign
from experiments.shared_state.evidence_models import canonical

def load():
    c=json.loads(os.environ['TASK52_SERVICE_CONFIG'])
    directory=Path('/tmp/task52-worker');directory.mkdir(mode=0o700,exist_ok=True)
    ca=directory/'ca.pem';ca.write_text(c['caPem']);ca.chmod(0o600);c['ca']=str(ca)
    return c

def main():
    c=load();command=json.loads(sys.stdin.read());action=command.pop('action','request')
    if action=='mint':
        for key in ('role','build','epoch'):
            if key in command:c[key]=command[key]
        print(json.dumps({'token':sign(c,command['service'],command['path'],canonical(command['body']),now=command.get('now'),nonce=command.get('nonce'))}));return
    if action=='inventory':
        print(json.dumps(dict(configKeys=sorted(c),environmentKeys=sorted(os.environ),uid=os.getuid(),dockerSocket=Path('/var/run/docker.sock').exists(),visibleProcesses=len(list(Path('/proc').glob('[0-9]*/environ'))))));return
    try:
        result=Client(c).request(command['service'],command['path'],command['body'],token=command.get('token'))
        print(json.dumps({'ok':result}))
    except Exception as e:print(json.dumps({'denied':type(e).__name__,'reason':getattr(e,'code',None)}))

if __name__=='__main__':main()
