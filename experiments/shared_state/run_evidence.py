"""Disposable no-network Redis/PG harness. No cloud, host mounts or real data.

Download requirements-evidence.lock to /tmp/whereto-evidence-wheels first using
pip download --require-hashes --only-binary and Linux amd64 platform selection.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import subprocess
from tempfile import TemporaryDirectory
import time
import zipfile

from experiments.shared_state.run_local import D,PG,BACKEND,ROOT,run
REDIS='redis:7.2-bookworm@sha256:5b816bb37d9707a70f10ef5002ecf8ee431750d397010fc4314c93dca887962f'


def wait(pg):
    for _ in range(60):
        if subprocess.run(D+['exec',pg,'pg_isready','-h','127.0.0.1','-U','whereto_synthetic_admin'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:return
        time.sleep(.5)
    raise RuntimeError('Synthetic startup deadline')


def main(suites=('test_evidence','test_store','test_financial','test_bridge')):
    if any(s not in ('test_evidence','test_store','test_financial','test_bridge') for s in suites):raise ValueError('Unknown fixture suite')
    suffix='whereto-evidence-'+secrets.token_hex(6);volume=suffix+'-data';containers=[]
    a,w,r=(secrets.token_hex(24) for _ in range(3))
    def create(*args):
        value=subprocess.check_output(D+['run','-d',*args],text=True).strip();containers.append(value);return value
    try:
        run('volume','create',volume,stdout=subprocess.DEVNULL)
        pg=create('--network','none','--memory','512m','--cpus','1','--mount','type=volume,src='+volume+',dst=/var/lib/postgresql/data',
          '-e','POSTGRES_USER=whereto_synthetic_admin','-e','POSTGRES_DB=whereto_synthetic','-e','POSTGRES_PASSWORD='+a,PG)
        wait(pg)
        sql="CREATE ROLE whereto_synthetic_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; CREATE ROLE whereto_synthetic_issuer NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; CREATE ROLE whereto_synthetic_worker LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '"+w+"'; REVOKE ALL ON DATABASE whereto_synthetic FROM PUBLIC; GRANT CONNECT ON DATABASE whereto_synthetic TO whereto_synthetic_worker; GRANT CREATE ON DATABASE whereto_synthetic TO whereto_synthetic_owner; REVOKE CREATE ON SCHEMA public FROM PUBLIC;"
        run('exec','-i',pg,'psql','-v','ON_ERROR_STOP=1','-U','whereto_synthetic_admin','-d','whereto_synthetic',input=sql,text=True,stdout=subprocess.DEVNULL)
        rd=create('--network','container:'+pg,'--memory','128m','--cpus','.25','--user','redis','--cap-drop','ALL','--security-opt','no-new-privileges',
             REDIS,'redis-server','--bind','127.0.0.1','--requirepass',r,'--save','','--appendonly','no','--maxmemory','64mb','--maxmemory-policy','noeviction')
        client=create('--platform','linux/amd64','--network','container:'+pg,'--memory','768m','--cpus','1','--cap-drop','ALL','--security-opt','no-new-privileges',
             '-e','WHERETO_ENV=test','-e','PYTHONPATH=/tmp/evidence-deps:/app','-e','PYTHONDONTWRITEBYTECODE=1',
             '-e','SYNTHETIC_ADMIN_PASSWORD='+a,'-e','SYNTHETIC_WORKER_PASSWORD='+w,'-e','SYNTHETIC_REDIS_PASSWORD='+r,
             '--entrypoint','sleep',BACKEND,'3600')
        with TemporaryDirectory(prefix='whereto-evidence-deps-') as tmp:
            Path(tmp).chmod(0o755)  # non-root container test worker must traverse it
            for x in json.loads(Path(__file__).with_name('evidence-dependencies.json').read_text())['wheels']:
                p=Path('/tmp/whereto-evidence-wheels')/x['file']
                if sha256(p.read_bytes()).hexdigest()!=x['sha256']:raise RuntimeError('Wheel identity')
                with zipfile.ZipFile(p) as z:z.extractall(tmp)
            run('cp',tmp+'/.',client+':/tmp/evidence-deps')
        # Synthetic one-day TLS identity; never uses personal keys or enrolls trust.
        with TemporaryDirectory(prefix='whereto-evidence-tls-') as tmp:
            key=Path(tmp)/'server.key';cert=Path(tmp)/'server.crt'
            subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1',
                '-keyout',str(key),'-out',str(cert),'-subj','/CN=synthetic-redis',
                '-addext','subjectAltName=IP:127.0.0.1'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            # Test-only private key, on isolated disposable Redis, never in worker/image/Git.
            key.chmod(0o444);cert.chmod(0o444)
            run('cp',str(key),rd+':/tmp/server.key');run('cp',str(cert),rd+':/tmp/server.crt')
            run('cp',str(cert),client+':/tmp/synthetic-redis-ca.crt')
            run('exec','-d',rd,'redis-server','--bind','127.0.0.1','--port','0','--tls-port','6380',
                '--tls-cert-file','/tmp/server.crt','--tls-key-file','/tmp/server.key','--tls-ca-cert-file','/tmp/server.crt',
                '--tls-auth-clients','no','--requirepass',r,'--save','','--appendonly','no','--maxmemory','16mb','--maxmemory-policy','noeviction')
        run('cp',str(ROOT/'experiments'),client+':/app/experiments')
        run('cp',str(ROOT/'deployment/backend-files.json'),client+':/app/deployment/backend-files.json')
        for f in json.loads((ROOT/'deployment/backend-files.json').read_text())['files']:
            run('cp',str(ROOT/f),client+':/app/'+f)
        for name in ['test_real_planning.py','real_fixtures.py','location_fixtures.py','testing_clock.py','journey_fixtures.py','hours_fixtures49.py','test_journey.py','test_stop_resolution.py','test_advanced_routing.py','test_advanced_timing.py','test_advanced_planning.py']:
            run('cp',str(ROOT/'backend'/name),client+':/app/backend/'+name)
        run('exec',client,'python','-m','unittest',*['experiments.shared_state.'+s for s in suites],'-v','-f')
        # Restore only a newly created synthetic schema, never a real journal/database.
        run('exec',client,'python','-m','experiments.shared_state.test_evidence','restore_seed')
        dump=subprocess.check_output(D+['exec',pg,'pg_dump','-U','whereto_synthetic_admin','-d','whereto_synthetic','--schema=synthetic_state','--clean','--if-exists'])
        run('exec',client,'python','-m','experiments.shared_state.test_evidence','restore_consume')
        run('exec','-i',pg,'psql','-v','ON_ERROR_STOP=1','-U','whereto_synthetic_admin','-d','whereto_synthetic',input=dump,stdout=subprocess.DEVNULL)
        run('exec',client,'python','-m','experiments.shared_state.test_evidence','restored_old_sql')
        # Actual Redis process restart, PostgreSQL SIGKILL, worker restart and refusal.
        run('exec',client,'python','-m','experiments.shared_state.test_evidence','seed')
        run('kill','--signal','KILL',rd,stdout=subprocess.DEVNULL)
        run('exec',client,'python','-m','experiments.shared_state.test_evidence','redis_down')
        run('start',rd,stdout=subprocess.DEVNULL)
        run('exec',client,'python','-m','experiments.shared_state.test_evidence','redis_lost')
        run('kill','--signal','KILL',pg,stdout=subprocess.DEVNULL)
        run('exec',client,'python','-m','experiments.shared_state.test_evidence','sql_down')
        run('start',pg,stdout=subprocess.DEVNULL);wait(pg)
        # Rejoin restarted namespace; Redis intentionally has no persistence.
        for c in [rd,client]:
            run('stop','--time','2',c,stdout=subprocess.DEVNULL);run('start',c,stdout=subprocess.DEVNULL)
        run('exec',client,'python','-m','experiments.shared_state.test_evidence','after_restart')
        print('Actual Redis/SQL/worker restart checks passed; original paid journal untouched.',flush=True)
    finally:
        for c in reversed(containers):subprocess.run(D+['rm','-f',c],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        subprocess.run(D+['volume','rm',volume],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


if __name__=='__main__':main()
