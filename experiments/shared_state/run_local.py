"""Explicit disposable local harness. No host ports/mounts, owner DB or provider I/O.

Run with repository Python: backend/.venv/bin/python experiments/shared_state/run_local.py
This creates/removes only its own named Docker volume and two local containers.
"""
import json
from pathlib import Path
import secrets
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
D = ['docker','--context','colima-whereto-task52']
PG = 'postgres:17-bookworm@sha256:665dc7b37ac52a17e298511414c21d23ffa4e6a6ef6225b3e5d59c7afb35e994'
BACKEND = json.loads((ROOT/'docs/task52-container-security-verification.json').read_text())['images']['backend']['imageIndexID']


def run(*args, **kwargs):
    return subprocess.run(D+list(args),check=True,**kwargs)


def main():
    suffix='whereto-shared-'+secrets.token_hex(6)
    volume=suffix+'-data';pg=client=None
    admin_password,worker_password=secrets.token_hex(24),secrets.token_hex(24)
    try:
        run('volume','create',volume,stdout=subprocess.DEVNULL)
        pg=subprocess.check_output(D+['run','-d','--network','none','--memory','512m','--cpus','1',
            '--mount','type=volume,src='+volume+',dst=/var/lib/postgresql/data',
            '-e','POSTGRES_USER=whereto_synthetic_admin','-e','POSTGRES_DB=whereto_synthetic',
            '-e','POSTGRES_PASSWORD='+admin_password,PG],text=True).strip()
        for _ in range(60):
            if subprocess.run(D+['exec',pg,'pg_isready','-h','127.0.0.1','-U','whereto_synthetic_admin','-d','whereto_synthetic'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
            time.sleep(.5)
        else:raise RuntimeError('Synthetic PostgreSQL startup deadline')
        # Hex-only generated password; no credential loader and no real role exists.
        sql="CREATE ROLE whereto_synthetic_owner NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS; CREATE ROLE whereto_synthetic_worker LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD '"+worker_password+"'; REVOKE ALL ON DATABASE whereto_synthetic FROM PUBLIC; GRANT CONNECT ON DATABASE whereto_synthetic TO whereto_synthetic_worker; GRANT CREATE ON DATABASE whereto_synthetic TO whereto_synthetic_owner; REVOKE CREATE ON SCHEMA public FROM PUBLIC;"
        run('exec','-i',pg,'psql','-v','ON_ERROR_STOP=1','-U','whereto_synthetic_admin','-d','whereto_synthetic',input=sql,text=True,stdout=subprocess.DEVNULL)
        client=subprocess.check_output(D+['run','-d','--platform','linux/amd64','--network','container:'+pg,
            '--memory','768m','--cpus','1','--cap-drop','ALL','--security-opt','no-new-privileges',
            '-e','WHERETO_ENV=test','-e','PYTHONPATH=/app','-e','PYTHONDONTWRITEBYTECODE=1',
            '-e','SYNTHETIC_ADMIN_PASSWORD='+admin_password,'-e','SYNTHETIC_WORKER_PASSWORD='+worker_password,
            '--entrypoint','sleep',BACKEND,'1800'],text=True).strip()
        run('cp',str(ROOT/'experiments'),client+':/app/experiments')
        for name in ['testing_clock.py','journey_fixtures.py','hours_fixtures49.py','test_journey.py',
                     'test_stop_resolution.py','test_advanced_routing.py','test_advanced_timing.py','test_advanced_planning.py']:
            run('cp',str(ROOT/'backend'/name),client+':/app/backend/'+name)
        print('Running real PostgreSQL synthetic state tests; no production integration.',flush=True)
        run('exec',client,'python','-m','unittest','experiments.shared_state.test_store','-v')
        run('exec',client,'python','-m','experiments.shared_state.test_store','seed')
        run('kill','--signal','KILL',pg,stdout=subprocess.DEVNULL)
        run('exec',client,'python','-m','experiments.shared_state.test_store','unavailable')
        run('start',pg,stdout=subprocess.DEVNULL)
        for _ in range(60):
            if subprocess.run(D+['exec',pg,'pg_isready','-h','127.0.0.1','-U','whereto_synthetic_admin','-d','whereto_synthetic'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:break
            time.sleep(.5)
        else:raise RuntimeError('Synthetic PostgreSQL recovery deadline')
        # Docker network=container uses the old namespace after a database restart.
        # Restart the test worker too; files/key remain, and it joins the new namespace.
        run('stop','--time','2',client,stdout=subprocess.DEVNULL)
        run('start',client,stdout=subprocess.DEVNULL)
        run('exec',client,'python','-m','experiments.shared_state.test_store','after_crash')
        print('Synthetic process/database crash checks passed; no live adapter is enabled.',flush=True)
    finally:
        for container in [client,pg]:
            if container:subprocess.run(D+['rm','-f',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        subprocess.run(D+['volume','rm',volume],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)


if __name__=='__main__':main()
