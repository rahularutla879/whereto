"""Two independent disposable PG volumes + Redis. No owner/cloud/provider access."""
from hashlib import sha256
import json
from pathlib import Path
import secrets
import re
import subprocess
from tempfile import TemporaryDirectory
import time
import zipfile
from experiments.shared_state.run_evidence import D,PG,BACKEND,ROOT,REDIS,run


def main(tests=(),recovery=True):
    # Select focused synthetic tests only; never a paid-dispatch parameter.
    if type(tests) is not tuple or any(type(x) is not str or re.fullmatch(r'(GrantTests|InferenceTests|ApplicationGrantTests)(\.test_[a-z_0-9]+)?',x) is None for x in tests):raise ValueError('Synthetic test selection')
    containers=[];volumes=[]
    credentials=[secrets.token_hex(24) for _ in range(8)]
    admin,worker,wadmin,service,reader,redis_password,issuer,counter=credentials
    def create(*args):
        c=subprocess.check_output(D+['run','-d',*args],text=True).strip();containers.append(c);return c
    def volume():
        name='whereto-grants-'+secrets.token_hex(12);run('volume','create',name,stdout=subprocess.DEVNULL);volumes.append(name);return name
    def ready(c,port,user):
        for _ in range(60):
            if subprocess.run(D+['exec',c,'pg_isready','-h','127.0.0.1','-p',str(port),'-U',user],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:return
            time.sleep(.5)
        raise RuntimeError('Synthetic PG startup')
    try:
        pg=create('--network','none','--memory','512m','--cpus','.5','--mount','type=volume,src='+volume()+',dst=/var/lib/postgresql/data',
            '-e','POSTGRES_USER=whereto_synthetic_admin','-e','POSTGRES_DB=whereto_synthetic','-e','POSTGRES_PASSWORD='+admin,PG)
        ready(pg,5432,'whereto_synthetic_admin')
        wit=create('--network','container:'+pg,'--memory','512m','--cpus','.5','--mount','type=volume,src='+volume()+',dst=/var/lib/postgresql/data',
            '-e','POSTGRES_USER=synthetic_witness_admin','-e','POSTGRES_DB=whereto_witness','-e','POSTGRES_PASSWORD='+wadmin,PG,'postgres','-p','5433')
        ready(wit,5433,'synthetic_witness_admin')
        sql="CREATE ROLE whereto_synthetic_owner NOLOGIN; CREATE ROLE whereto_synthetic_issuer NOLOGIN; CREATE ROLE synthetic_token_counter NOLOGIN; CREATE ROLE whereto_synthetic_worker LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '"+worker+"'; REVOKE ALL ON DATABASE whereto_synthetic FROM PUBLIC; GRANT CONNECT ON DATABASE whereto_synthetic TO whereto_synthetic_worker; GRANT CREATE ON DATABASE whereto_synthetic TO whereto_synthetic_owner; REVOKE CREATE ON SCHEMA public FROM PUBLIC;"
        sql+=" CREATE ROLE synthetic_issuer_client LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS IN ROLE whereto_synthetic_issuer PASSWORD '"+issuer+"'; CREATE ROLE synthetic_counter_client LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS IN ROLE synthetic_token_counter PASSWORD '"+counter+"'; GRANT CONNECT ON DATABASE whereto_synthetic TO synthetic_issuer_client,synthetic_counter_client;"
        run('exec','-i',pg,'psql','-v','ON_ERROR_STOP=1','-U','whereto_synthetic_admin','-d','whereto_synthetic',input=sql,text=True,stdout=subprocess.DEVNULL)
        sql="CREATE ROLE whereto_synthetic_owner NOLOGIN; CREATE ROLE synthetic_grant_operator NOLOGIN; CREATE ROLE synthetic_witness_service LOGIN PASSWORD '"+service+"'; CREATE ROLE synthetic_witness_reader LOGIN PASSWORD '"+reader+"'; REVOKE ALL ON DATABASE whereto_witness FROM PUBLIC; GRANT CONNECT ON DATABASE whereto_witness TO synthetic_witness_service,synthetic_witness_reader; GRANT CREATE ON DATABASE whereto_witness TO whereto_synthetic_owner; REVOKE CREATE ON SCHEMA public FROM PUBLIC;"
        run('exec','-i',wit,'psql','-v','ON_ERROR_STOP=1','-p','5433','-U','synthetic_witness_admin','-d','whereto_witness',input=sql,text=True,stdout=subprocess.DEVNULL)
        create('--network','container:'+pg,'--memory','128m','--cpus','.1','--user','redis','--cap-drop','ALL','--security-opt','no-new-privileges',REDIS,'redis-server','--bind','127.0.0.1','--requirepass',redis_password,'--save','','--appendonly','no','--maxmemory','64mb','--maxmemory-policy','noeviction')
        env={'SYNTHETIC_ISSUER_PASSWORD':issuer,'SYNTHETIC_COUNTER_PASSWORD':counter,'SYNTHETIC_ADMIN_PASSWORD':admin,'SYNTHETIC_WORKER_PASSWORD':worker,'SYNTHETIC_WITNESS_ADMIN_PASSWORD':wadmin,'SYNTHETIC_WITNESS_SERVICE_PASSWORD':service,'SYNTHETIC_WITNESS_READER_PASSWORD':reader,'SYNTHETIC_REDIS_PASSWORD':redis_password,'WHERETO_ENV':'test','PYTHONPATH':'/tmp/evidence-deps:/app','PYTHONDONTWRITEBYTECODE':'1'}
        args=[x for k,v in env.items() for x in ['-e',k+'='+v]]
        client=create('--platform','linux/amd64','--network','container:'+pg,'--memory','768m','--cpus','1','--cap-drop','ALL','--security-opt','no-new-privileges',*args,'--entrypoint','sleep',BACKEND,'3600')
        with TemporaryDirectory(prefix='whereto-grant-deps-') as tmp:
            Path(tmp).chmod(0o755)
            for item in json.loads((ROOT/'experiments/shared_state/evidence-dependencies.json').read_text())['wheels']:
                p=Path('/tmp/whereto-evidence-wheels')/item['file'];assert sha256(p.read_bytes()).hexdigest()==item['sha256']
                with zipfile.ZipFile(p) as z:z.extractall(tmp)
            run('cp',tmp+'/.',client+':/tmp/evidence-deps')
        run('cp',str(ROOT/'experiments'),client+':/app/experiments')
        run('cp',str(ROOT/'deployment/backend-files.json'),client+':/app/deployment/backend-files.json')
        for f in json.loads((ROOT/'deployment/backend-files.json').read_text())['files']:run('cp',str(ROOT/f),client+':/app/'+f)
        for name in ['test_real_planning.py','real_fixtures.py','location_fixtures.py','testing_clock.py','journey_fixtures.py','hours_fixtures49.py','test_journey.py','test_stop_resolution.py','test_advanced_routing.py','test_advanced_timing.py','test_advanced_planning.py']:
            run('cp',str(ROOT/'backend'/name),client+':/app/backend/'+name)
        run('exec',client,'python','-m','unittest',*['experiments.shared_state.test_application_grants'+('.'+x if x else '') for x in (tests or ('',))],'-v','-f')
        if not recovery:return
        # Backups contain only newly authored synthetic state, never the real journal.
        run('exec',client,'python','-m','experiments.shared_state.test_application_grants','seed_restore')
        op_dump=subprocess.check_output(D+['exec',pg,'pg_dump','-U','whereto_synthetic_admin','-d','whereto_synthetic','--schema=synthetic_state','--schema=grant_rules','--clean','--if-exists'])
        run('exec',client,'python','-m','experiments.shared_state.test_application_grants','consume_restore')
        run('exec','-i',pg,'psql','-v','ON_ERROR_STOP=1','-U','whereto_synthetic_admin','-d','whereto_synthetic',input=op_dump,stdout=subprocess.DEVNULL)
        run('exec',client,'python','-m','experiments.shared_state.test_application_grants','detect_op_restore')
        run('exec',client,'python','-m','experiments.shared_state.test_application_grants','seed_restore')
        witness_dump=subprocess.check_output(D+['exec',wit,'pg_dump','-p','5433','-U','synthetic_witness_admin','-d','whereto_witness','--schema=witness','--schema=grant_rules','--clean','--if-exists'])
        run('exec',client,'python','-m','experiments.shared_state.test_application_grants','consume_restore')
        run('exec','-i',wit,'psql','-p','5433','-v','ON_ERROR_STOP=1','-U','synthetic_witness_admin','-d','whereto_witness',input=witness_dump,stdout=subprocess.DEVNULL)
        run('exec',client,'python','-m','experiments.shared_state.test_application_grants','detect_witness_restore')
        # Operational database and worker restart: witness has its own volume.
        run('exec',client,'python','-m','experiments.shared_state.test_application_grants','seed_crash')
        run('kill','--signal','KILL',pg,stdout=subprocess.DEVNULL)
        run('exec',client,'python','-m','experiments.shared_state.test_application_grants','op_down')
        run('start',pg,stdout=subprocess.DEVNULL);ready(pg,5432,'whereto_synthetic_admin')
        # All participants rejoin the new namespace; durable witness volume survives.
        for c in containers[1:]:run('stop','--time','2',c,stdout=subprocess.DEVNULL);run('start',c,stdout=subprocess.DEVNULL)
        ready(wit,5433,'synthetic_witness_admin')
        run('exec',client,'python','-m','experiments.shared_state.test_application_grants','after_crash')
        print('Independent synthetic restore and crash drills passed.',flush=True)
    finally:
        for c in reversed(containers):subprocess.run(D+['rm','-f',c],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for v in volumes:subprocess.run(D+['volume','rm',v],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


if __name__=='__main__':main()
