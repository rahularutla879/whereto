"""Disposable TLS ports over the existing signed-service harness; no live adapter."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import subprocess,json,os,secrets
from experiments.hosted_identity import run_local as parent
from experiments.ordinary_network.resources import inventory
from experiments.hosted_identity import test_local as hosted_tests
D=parent.D

def main():
 original=hosted_tests.verify
 def verify(private,*_):
  client=private['client'];stores=private['stores']
  with TemporaryDirectory(prefix='whereto-ports-') as tmp:
   root=Path(tmp);root.chmod(0o700)
   subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(root/'key.pem'),'-out',str(root/'cert.pem'),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,umask=0o077)
   (root/'cert.pem').chmod(0o644)
   for name,port,admin,db in [('postgres',5432,'whereto_synthetic_admin','whereto_synthetic'),('witness',5433,'synthetic_witness_admin','whereto_witness')]:
    c=stores[name]
    subprocess.run(D+['cp',str(root/'cert.pem'),c+':/tmp/cert.pem'],check=True)
    subprocess.run(D+['exec','-i','--user','postgres',c,'sh','-c','umask 077; cat > /tmp/hosted-server.key'],input=(root/'key.pem').read_bytes(),check=True)
    sql="ALTER SYSTEM SET ssl='on'; ALTER SYSTEM SET ssl_cert_file='/tmp/cert.pem'; ALTER SYSTEM SET ssl_key_file='/tmp/hosted-server.key'; SELECT pg_reload_conf();"
    subprocess.run(D+['exec','-i',c,'psql','-v','ON_ERROR_STOP=1','-p',str(port),'-U',admin,'-d',db],input=sql,text=True,check=True,stdout=subprocess.DEVNULL)
   rd=stores['redis']
   subprocess.run(D+['cp',str(root/'cert.pem'),rd+':/tmp/cert.pem'],check=True)
   subprocess.run(D+['exec','-i','--user','redis',rd,'sh','-c','umask 077; cat > /tmp/hosted-server.key'],input=(root/'key.pem').read_bytes(),check=True)
   # Root password remains solely in the trusted bootstrap client.
   password=subprocess.check_output(D+['exec',client,'python','-c',"import os;print(os.environ['SYNTHETIC_REDIS_PASSWORD'])"],text=True).strip()
   subprocess.run(D+['exec','-d',rd,'redis-server','--bind','127.0.0.1','--port','0','--tls-port','6380','--tls-cert-file','/tmp/cert.pem','--tls-key-file','/tmp/hosted-server.key','--tls-ca-cert-file','/tmp/cert.pem','--tls-auth-clients','no','--requirepass',password,'--save','','--appendonly','no','--maxmemory','16mb','--maxmemory-policy','noeviction'],check=True)
   subprocess.run(D+['cp',str(root/'cert.pem'),client+':/tmp/hosted-ports-ca.pem'],check=True)
   for folder in ('private_runtime','deployment/sql'):
    subprocess.run(D+['exec',client,'mkdir','-p','/app/'+str(Path(folder).parent)],check=True)
    subprocess.run(D+['cp',folder,client+':/app/'+folder],check=True)
   subprocess.run(D+['cp','experiments/hosted_ports',client+':/app/experiments/hosted_ports'],check=True)
   code="import os,sys;fd=os.open('/tmp/ports-control.json',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.write(fd,sys.stdin.buffer.read());os.close(fd)"
   subprocess.run(D+['exec','-i',client,'python','-c',code],input=json.dumps(private).encode(),check=True)
   subprocess.run(D+['exec',client,'python','-m','unittest','experiments.hosted_ports.test_connections','-v'],check=True)
   subprocess.run(D+['cp',client+':/tmp/hosted-port-pool-timing.json','/tmp/continuation-pool-timing.json'],check=True)
   subprocess.run(D+['exec',client,'python','-m','unittest','private_runtime.test_identity','-v'],check=True)
   from deployment.prepare_private_services import prepare
   project=root/'projection';prepare(project)
   subprocess.run(D+['cp',str(project),client+':/app/private-role-projection'],check=True)
   for role in ('backend','factory','counter','dispatcher','recovery'):
    command='cd /app/private-role-projection/'+role+' && PYTHONPATH=.:/tmp/evidence-deps python -c '+__import__('shlex').quote('from private_runtime.image_identity import verify;print(verify());from private_runtime.private_service import runtime,privileged_server,backend_app' if role in ('backend','factory','dispatcher') else 'from private_runtime.image_identity import verify;print(verify());from private_runtime.private_service import runtime,privileged_server')
    subprocess.run(D+['exec',client,'sh','-c',command],check=True)
   from experiments.hosted_ports.native_cluster import Cluster
   cluster=Cluster(D,private,root)
   try:
    cluster.init();print('SEVEN_ROLE_TLS_STARTUP_PASS',flush=True);cluster.probe()
    if os.environ.get('TASK52_HOSTED_PORTS_CRASH')=='1':cluster.probe_crash()
    elif os.environ.get('TASK52_HOSTED_PORTS_BROWSER_HOLD')=='1':cluster.browser()
   finally:cluster.close()
 try:
  with inventory(D),patch.object(hosted_tests,'verify',verify):parent.main()
 finally:hosted_tests.verify=original
if __name__=='__main__':main()
