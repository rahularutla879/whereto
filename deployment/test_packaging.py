"""Packaging and native assembled-payload checks; never Docker/Cloud/provider proof."""
from contextlib import contextmanager
from datetime import date,timedelta
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
from tempfile import TemporaryDirectory,TemporaryFile
from threading import Thread
import time
import unittest
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from unittest.mock import patch

from deployment.prepare_backend import prepare
from deployment.backend_entry import validate

ROOT=Path(__file__).resolve().parent.parent


def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));return s.getsockname()[1]


def http(base,path,body=None):
    req=Request(base+path,data=None if body is None else json.dumps(body).encode(),
                headers={'Content-Type':'application/json'})
    try:
        with urlopen(req,timeout=5) as response:
            data=response.read();status=response.status
    except HTTPError as e:data=e.read();status=e.code
    try:return status,json.loads(data)
    except ValueError:return status,None


@contextmanager
def running(command,cwd,env,path):
    with TemporaryFile() as log:
        child=subprocess.Popen(command,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:
            for _ in range(200):
                if child.poll() is not None:raise AssertionError('Assembled runtime refused startup')
                try:
                    if http('http://127.0.0.1:'+env['PORT'],path)[0]==200:break
                except OSError:pass
                time.sleep(.05)
            else:raise AssertionError('Assembled runtime failed startup deadline')
            yield child,log
        finally:
            if child.poll() is None:
                child.terminate()
                try:child.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    child.kill();child.wait();raise AssertionError('Graceful shutdown exceeded deadline')


class PackagingTests(unittest.TestCase):
    def test_immutable_bases_and_non_root_no_embedded_secrets(self):
        bases=json.loads((ROOT/'deployment/base-images.json').read_text())
        for role,key,user in [('frontend','node','USER node'),('backend','python','USER app')]:
            docker=(ROOT/f'deployment/Dockerfile.{role}').read_text()
            self.assertIn(bases['images'][key]['reference'],docker)
            self.assertRegex(bases['images'][key]['reference'],r'@sha256:[a-f0-9]{64}$')
            self.assertIn(user,docker)
            self.assertNotIn('COPY . ',docker)
        ignore=(ROOT/'.dockerignore').read_text()
        self.assertTrue(ignore.splitlines()[2]=='**')
        self.assertIn('**/.env*',ignore);self.assertIn('**/test_*.py',ignore)
        self.assertNotIn('!scripts',ignore);self.assertNotIn('!docs',ignore)

    def test_assembly_excludes_evaluation_fixtures_admin_and_credentials(self):
        with TemporaryDirectory() as d:
            target=Path(d)/'runtime';prepare(ROOT,target)
            files={str(p.relative_to(target)) for p in target.rglob('*') if p.is_file()}
            expected=set(json.loads((ROOT/'deployment/backend-files.json').read_text())['files'])
            self.assertEqual(files,expected)
            self.assertIn('backend/main.py',files);self.assertIn('data/mock-venues.json',files)
            for name in files:
                self.assertNotIn('fixture',name);self.assertNotIn('test_',name)
                self.assertNotIn('evaluation',name);self.assertNotIn('.env',name)
                self.assertFalse(name.startswith(('scripts/','docs/')))
            self.assertNotIn('backend/database_migrate.py',files)
            with self.assertRaises(ValueError):prepare(ROOT,target)

    def test_linux_hash_lock_retains_original_versions_and_binary_dependency(self):
        historical=(ROOT/'backend/requirements.txt').read_bytes()
        self.assertEqual(hashlib.sha256(historical).hexdigest(),'29a4d46bb7b8b62f5aad5b14d138545292b00160d0fc08f7a1427cd073585983')
        original=historical.decode().splitlines()
        lock=(ROOT/'deployment/requirements-linux-amd64.lock').read_text().splitlines()[1:]
        pins={line.split(' --hash=')[0].casefold() for line in lock}
        # Only this reviewed deployment security patch may differ from historical evidence.
        expected={p.casefold() for p in original}
        self.assertIn('pyasn1==0.6.4',expected)
        expected.remove('pyasn1==0.6.4');expected.add('pyasn1==0.6.5')
        self.assertEqual(pins,expected|{'psycopg-binary==3.3.3'})
        self.assertIn('pyasn1==0.6.5 --hash=sha256:4017b0fce125096b8573b39c989fdb1a4b19cf761e683398184550fea0e66587',lock)
        self.assertIn('psycopg-binary==3.3.3',pins)
        self.assertTrue(all(' --hash=sha256:' in line and len(line.rsplit(':',1)[1])==64 for line in lock))

    def test_launchers_reject_hosted_mode_and_development_flags(self):
        with patch.dict(os.environ,{'WHERETO_ENV':'production'},clear=True):
            with self.assertRaises(RuntimeError):validate(os.environ)
        for env in ({'WHERETO_ENV':'test','K_SERVICE':'synthetic'},
                    {'PORT':'private-value'}, {'WHERETO_REAL_DEV':'1'},
                    {'VENUE_DATA_MODE':'real'},{'AI_PROVIDER':'openai'},
                    {'AI_BASE_URL':'https://example.invalid'}):
            with patch.dict(os.environ,env,clear=True):
                with self.assertRaises((ValueError,RuntimeError)):validate(os.environ)
        with patch.dict(os.environ,{'WHERETO_ENV':'test'},clear=True):self.assertEqual(validate(os.environ),'8080')

    def test_frontend_missing_or_unsafe_environment_refuses_without_echo(self):
        for settings in ({},{'BACKEND_URL':'https://private-canary@backend.invalid'},
                         {'BACKEND_URL':'https://backend.invalid','NEXT_PUBLIC_DB_PASSWORD':'private-canary'},
                         {'BACKEND_URL':'https://backend.invalid','WHERETO_DIAGNOSTICS_DEV':'1'}):
            env={'PATH':os.environ['PATH'],**settings}
            r=subprocess.run(['node',str(ROOT/'deployment/frontend-entry.mjs')],env=env,capture_output=True,timeout=5)
            self.assertEqual(r.returncode,78)
            self.assertNotIn(b'private-canary',r.stderr+r.stdout)

    def test_restart_loses_receipts_and_local_admission_is_not_shared(self):
        from backend.admission import LocalAdmission
        from backend.saved_plans import Receipts,PersistenceError
        from backend.test_saved_plans import request_for
        from backend.testing_clock import calendar_clock
        with calendar_clock():
            first=Receipts();request=request_for(first)
            first.select(request)
            with self.assertRaises(PersistenceError):Receipts().select(request)
        first,second=LocalAdmission(capacity=1),LocalAdmission(capacity=1)
        one=first.acquire(b'synthetic','test');two=second.acquire(b'synthetic','test')
        one.release();two.release()  # two processes can each admit: a cloud blocker

    def test_native_assembled_backend_proxy_outage_and_shutdown(self):
        if not (ROOT/'.next/standalone/server.js').is_file():
            self.fail('Build standalone output before packaging smoke')
        calls=[]
        class FakeAI(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers.get('Content-Length','0')));calls.append('synthetic')
                self.send_response(503);self.end_headers();self.wfile.write(b'{"error":"private-canary"}')
            def log_message(self,*args):pass
        fake=ThreadingHTTPServer(('127.0.0.1',0),FakeAI)
        thread=Thread(target=fake.serve_forever,daemon=True);thread.start()
        try:
            with TemporaryDirectory() as d:
                root=Path(d);payload=root/'backend';prepare(ROOT,payload)
                (payload/'deployment').mkdir()
                shutil.copyfile(ROOT/'deployment/backend_entry.py',payload/'deployment/backend_entry.py')
                env={'PATH':os.environ['PATH'],'PYTHONPATH':str(payload),'PORT':str(port()),
                     'WHERETO_ENV':'test','VENUE_DATA_MODE':'mock',
                     'AI_BASE_URL':f'http://127.0.0.1:{fake.server_port}','AI_TIMEOUT_SECONDS':'1'}
                refused=subprocess.run([sys.executable,str(payload/'deployment/backend_entry.py')],cwd=payload,
                    env={**env,'WHERETO_ENV':'production'},capture_output=True,timeout=5)
                self.assertEqual(refused.returncode,78);self.assertFalse(calls)
                with running([sys.executable,'deployment/backend_entry.py'],payload,env,'/health') as (_child,log):
                    base='http://127.0.0.1:'+env['PORT']
                    self.assertEqual(http(base,'/health'),(200,{'status':'ok'}));self.assertFalse(calls)
                    self.assertIn(http(base,'/api/development-diagnostics')[0],(403,404))
                    source='Synthetic private-source-canary outing'
                    response=http(base,'/api/interpret',{'text':source})
                    self.assertEqual(response[0],503);self.assertEqual(len(calls),1)
                    self.assertNotIn('private-canary',json.dumps(response[1]))
                    generated=http(base,'/api/plans/generate',{'activities':['food','bowling'],
                        'location':'Baltimore','date':(date.today()+timedelta(days=10)).isoformat(),'planningMode':'surprise'})
                    self.assertEqual(generated[0],200)
                    value=generated[1];options=value['plans']+value['provisionalPlans'];self.assertTrue(options)
                    save={'receipt':value['saveReceipt'],'accessToken':value['saveAccessToken'],
                          'candidateIds':[o['candidate']['id'] for o in options],'selectedId':options[0]['candidate']['id']}
                    self.assertEqual(http(base,'/api/plans/save',save)[0],503) # missing SQL settings, no DNS/connect
                    front=root/'frontend';shutil.copytree(ROOT/'.next/standalone',front)
                    shutil.copytree(ROOT/'.next/static',front/'.next/static',dirs_exist_ok=True)
                    (front/'deployment').mkdir(exist_ok=True)
                    shutil.copyfile(ROOT/'deployment/frontend-entry.mjs',front/'deployment/frontend-entry.mjs')
                    self.assertFalse((front/'scripts').exists());self.assertFalse((front/'backend').exists())
                    frontenv={'PATH':os.environ['PATH'],'PORT':str(port()),'BACKEND_URL':base,'NEXT_TELEMETRY_DISABLED':'1'}
                    with running(['node','deployment/frontend-entry.mjs'],front,frontenv,'/'):
                        frontbase='http://127.0.0.1:'+frontenv['PORT']
                        self.assertEqual(http(frontbase,'/api/health')[0],200)
                        self.assertEqual(http(frontbase,'/dev/diagnostics')[0],404)
                        self.assertIn(http(frontbase,'/api/development-diagnostics')[0],(403,404))
                        self.assertEqual(len(calls),1)
                        # Stop only the synthetic backend: dependency health must fail.
                        _child.terminate();_child.wait(timeout=8)
                        self.assertEqual(http(frontbase,'/api/health')[0],503)
                    log.seek(0);text=log.read().decode()
                    self.assertNotIn(source,text);self.assertNotIn('private-canary',text)
                with running([sys.executable,'deployment/backend_entry.py'],payload,env,'/health'):
                    self.assertEqual(http(base,'/api/plans/save',save)[0],409) # receipt lost on process restart
        finally:
            fake.shutdown();fake.server_close();thread.join(timeout=3)
