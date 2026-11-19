"""Host-side TLS setup limited to this disposable cohort's exact containers."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json,subprocess

def setup(D,client):
    def output(*args):return subprocess.check_output(D+list(args),text=True)
    def run(*args,**kw):return subprocess.run(D+list(args),check=True,stdout=subprocess.DEVNULL,**kw)
    info=json.loads(output('inspect',client))[0];mode=info['HostConfig']['NetworkMode']
    if not mode.startswith('container:'):raise ValueError('Isolated fixture required')
    op=mode.split(':',1)[1];peers=[]
    for id in output('ps','-q','--no-trunc').split():
        v=json.loads(output('inspect',id))[0]
        if v['HostConfig']['NetworkMode'] not in (mode,'none'):continue
        if id!=client and id!=op and v['HostConfig']['NetworkMode']==mode:peers.append(v)
    witness=next(v['Id'] for v in peers if v['Config']['Cmd']==['postgres','-p','5433'])
    redis=next(v['Id'] for v in peers if v['Config']['Cmd'][0]=='redis-server')
    with TemporaryDirectory(prefix='real-store-tls-') as temp:
        p=Path(temp)
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(p/'key.pem'),'-out',str(p/'cert.pem'),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        run('cp',str(p/'cert.pem'),client+':/tmp/real-store-ca.pem')
        for id,port,user,db in ((op,5432,'whereto_synthetic_admin','whereto_synthetic'),(witness,5433,'synthetic_witness_admin','whereto_witness')):
            run('cp',str(p/'cert.pem'),id+':/tmp/real-store.crt')
            run('exec','-i','--user','postgres',id,'sh','-c','umask 077; cat > /tmp/real-store.key',input=(p/'key.pem').read_bytes())
            run('exec','-i',id,'psql','-v','ON_ERROR_STOP=1','-p',str(port),'-U',user,'-d',db,input="ALTER SYSTEM SET ssl='on'; ALTER SYSTEM SET ssl_cert_file='/tmp/real-store.crt'; ALTER SYSTEM SET ssl_key_file='/tmp/real-store.key'; SELECT pg_reload_conf();",text=True)
        run('cp',str(p/'cert.pem'),redis+':/tmp/real-store.crt')
        run('exec','-i','--user','redis',redis,'sh','-c','umask 077; cat > /tmp/real-store.key',input=(p/'key.pem').read_bytes())
        code="import os,redis;r=redis.Redis(host='127.0.0.1',password=os.environ['SYNTHETIC_REDIS_PASSWORD']);r.config_set('tls-cert-file','/tmp/real-store.crt');r.config_set('tls-key-file','/tmp/real-store.key');r.config_set('tls-ca-cert-file','/tmp/real-store.crt');r.config_set('tls-auth-clients','no');r.config_set('tls-port','6380')"
        run('exec',client,'python','-c',code)
