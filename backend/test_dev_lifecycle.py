"""Opt-in real local process/PTY tests; no provider calls. Run with both ports stopped."""
import json
import os
from pathlib import Path
import select
import signal
import socket
import subprocess
import sys
import time
import unittest
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parent.parent
ENABLED=os.environ.get('WHERETO_LIFECYCLE_TESTS')=='1'

def wait(check,timeout=20):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if check():return
        time.sleep(.05)
    raise AssertionError('Timed out waiting for local process lifecycle')

def free(port):
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        try:sock.bind(('127.0.0.1',port));return True
        except OSError:return False

def health(port,path='/health'):
    try:
        with urlopen(f'http://127.0.0.1:{port}{path}',timeout=3) as response:return response.status==200
    except Exception:return False

def processes():
    lines=subprocess.check_output(['ps','-axo','pid=,ppid='],text=True).splitlines()
    return {int(pid):int(parent) for pid,parent in (line.split() for line in lines)}

def descendants(pid):
    parents=processes();found={pid}
    while True:
        expanded=found|{child for child,parent in parents.items() if parent in found}
        if expanded==found:return found
        found=expanded

class Terminal:
    def __init__(self,service,*args):
        import pty
        slave=None
        self.service=service;self.output=b''
        self.fd,slave=pty.openpty()
        bootstrap="import os,fcntl,termios;os.setsid();fcntl.ioctl(0,termios.TIOCSCTTY,0);os.execvp('npm',"+repr(['npm','run','dev:backend' if service=='backend' else 'dev',*(['--',*args] if args else [])])+")"
        self.process=subprocess.Popen([sys.executable,'-c',bootstrap],cwd=ROOT,stdin=slave,stdout=slave,stderr=slave,close_fds=True)
        os.close(slave);self.pid=self.process.pid;self.code=None
    def drain(self):
        if self.fd is None:return
        while select.select([self.fd],[],[],0)[0]:
            try:data=os.read(self.fd,65536)
            except OSError:break
            if not data:break
            self.output+=data
    def exited(self):
        self.drain()
        if self.code is None:
            self.code=self.process.poll()
        return self.code is not None
    def stop(self):
        owned=descendants(self.pid)
        os.write(self.fd,b'\x03') # Actual terminal interrupt character, not just startup-log inspection.
        wait(self.exited,15)
        wait(lambda:not (owned & set(processes())),15)
        os.close(self.fd);self.fd=None
    def cleanup(self):
        if not self.exited():
            try:os.killpg(self.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            wait(self.exited,15)
        if self.fd is not None:
            os.close(self.fd);self.fd=None

@unittest.skipUnless(ENABLED and os.name=='posix','Opt-in local process tests (POSIX PTY)')
class Lifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not free(8000) or not free(3000):raise RuntimeError('Stop existing development terminals before lifecycle tests; tests never kill an unknown listener.')
    def launch(self,service,*args):
        terminal=Terminal(service,*args);self.addCleanup(terminal.cleanup)
        port=8000 if service=='backend' else 3000
        wait(lambda:health(port,'/health' if service=='backend' else '/api/health'),60)
        self.assertFalse(terminal.exited())
        return terminal
    def test_01_five_backend_terminal_interrupt_cycles_and_reload(self):
        for cycle in range(5):
            terminal=self.launch('backend','--mock')
            if cycle==0:
                # Trigger StatReload without editing application source.
                source=ROOT/'backend/main.py';before=source.stat()
                time.sleep(1.1);os.utime(source,None)
                wait(lambda:(terminal.drain() or b'Reloading' in terminal.output),10)
                wait(lambda:health(8000),15)
                os.utime(source,ns=(before.st_atime_ns,before.st_mtime_ns))
            terminal.stop();self.assertTrue(free(8000))
        print('LIFECYCLE: five backend PTY Control+C cycles; all descendants gone and port 8000 released; reload observed.')
    def test_02_five_frontend_terminal_interrupt_cycles_and_proxy(self):
        backend=self.launch('backend','--mock')
        for cycle in range(5):
            terminal=self.launch('frontend')
            self.assertTrue(health(3000,'/'))
            terminal.stop();self.assertTrue(free(3000))
        backend.stop();self.assertTrue(free(8000))
        print('LIFECYCLE: five frontend PTY Control+C cycles; proxy and page 200; all descendants gone and port 3000 released.')
    def test_03_healthy_duplicate_and_parent_loss(self):
        for service,port in [('backend',8000),('frontend',3000)]:
            companion=self.launch('backend','--mock') if service=='frontend' else None
            terminal=self.launch(service,*(['--mock'] if service=='backend' else []))
            duplicate=subprocess.run(['node','scripts/dev-server.mjs',service],cwd=ROOT,capture_output=True,text=True,timeout=5)
            self.assertEqual(duplicate.returncode,1);self.assertIn('already running',duplicate.stderr)
            self.assertTrue(health(port,'/health' if service=='backend' else '/api/health'))
            # Abruptly lose only the direct launcher. Its IPC worker must clean its tree.
            parent_map=processes();npm_children=[pid for pid,parent in parent_map.items() if parent==terminal.pid]
            self.assertEqual(len(npm_children),1)
            os.kill(npm_children[0],signal.SIGKILL)
            wait(lambda:free(port),15);wait(terminal.exited,15)
            hangup=self.launch(service,*(['--mock'] if service=='backend' else []))
            os.killpg(hangup.pid,signal.SIGHUP);wait(lambda:free(port),15);wait(hangup.exited,15)
            if companion:companion.stop()
        print('LIFECYCLE: healthy duplicates refused; abrupt launcher loss and terminal hangup released both ports.')
    def test_04_unrelated_listeners_never_terminated(self):
        for service,port in [('backend',8000),('frontend',3000)]:
            with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
                listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);listener.bind(('127.0.0.1',port));listener.listen()
                duplicate=subprocess.run(['node','scripts/dev-server.mjs',service],cwd=ROOT,capture_output=True,text=True,timeout=5)
                self.assertEqual(duplicate.returncode,1);self.assertIn('unverified',duplicate.stderr)
                with socket.create_connection(('127.0.0.1',port),timeout=1):pass
            self.assertTrue(free(port))
        print('LIFECYCLE: unrelated listeners on 8000 and 3000 untouched; no alternate ports.')
    def test_05_owner_profile_and_repeated_signal_rapid_restart(self):
        terminal=self.launch('backend')
        terminal.drain();self.assertIn(b'starting in real mode',terminal.output)
        frontend=self.launch('frontend');self.assertTrue(health(3000,'/api/health'));frontend.stop()
        with urlopen('http://127.0.0.1:8000/health') as response:self.assertTrue(json.load(response))
        os.write(terminal.fd,b'\x03\x03');wait(terminal.exited,15);wait(lambda:free(8000),15)
        second=self.launch('backend','--mock')
        from urllib.request import Request
        payload={'activities':['food','drinks'],'location':'Baltimore','date':'2026-11-07','people':2,'startingLocation':{'point':{'id':'Mock_origin_0','coordinates':{'latitude':0,'longitude':0}},'explicitly_authorized':True,'source':'mock'}}
        with urlopen(Request('http://127.0.0.1:8000/api/plans/generate',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'}),timeout=10) as response:
            planned=json.load(response);self.assertEqual(planned['dataMode'],'mock');self.assertEqual(len(planned['plans']+planned['provisionalPlans']),3)
        second.stop();self.assertTrue(free(8000))
        print('LIFECYCLE: owner real profile healthy, repeated interrupt and rapid explicit-mock restart passed; zero Google planning calls.')

    def test_06_legacy_abrupt_supervisor_loss_reproduces_inherited_socket(self):
        runtime=subprocess.Popen([sys.executable,'-m','backend.dev_start','--mock'],cwd=ROOT,start_new_session=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            wait(lambda:health(8000),15)
            os.kill(runtime.pid,signal.SIGKILL);runtime.wait(timeout=5)
            self.assertFalse(free(8000));self.assertTrue(health(8000))
            print('BASELINE: killing the old unsupervised reloader leaves its child listening and healthy on 8000.')
        finally:
            try:os.killpg(runtime.pid,signal.SIGTERM)
            except ProcessLookupError:pass
            wait(lambda:free(8000),15)
            try:os.killpg(runtime.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            runtime.wait(timeout=5)
    def test_07_authentication_stale_metadata_and_explicit_stop(self):
        from urllib.request import Request
        from urllib.error import HTTPError
        terminal=self.launch('backend','--mock')
        path=ROOT/'backend/.local/dev-servers/backend.json';owner=json.loads(path.read_text())
        self.assertEqual(path.stat().st_mode&0o777,0o600)
        with self.assertRaises(HTTPError) as error:urlopen(Request(f"http://127.0.0.1:{owner['controlPort']}/stop",method='POST'),timeout=1)
        self.assertEqual(error.exception.code,404);self.assertTrue(health(8000))
        stopped=subprocess.run(['node','scripts/dev-server.mjs','backend','--stop'],cwd=ROOT,capture_output=True,text=True,timeout=5)
        self.assertEqual(stopped.returncode,0);wait(terminal.exited,15);wait(lambda:free(8000),15)
        # A stale control port reused by an unrelated HTTP service must never receive /stop.
        from http.server import BaseHTTPRequestHandler,HTTPServer
        from threading import Thread
        calls=[]
        class OtherService(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                calls.append(self.path);self.send_response(200);self.end_headers();self.wfile.write(b'{}')
        other=HTTPServer(('127.0.0.1',0),OtherService)
        thread=Thread(target=other.serve_forever,daemon=True);thread.start()
        try:
            path.write_text(json.dumps({**owner,'controlPort':other.server_port}));path.chmod(0o600)
            rejected=subprocess.run(['node','scripts/dev-server.mjs','backend','--stop'],cwd=ROOT,capture_output=True,text=True,timeout=5)
            self.assertEqual(rejected.returncode,1);self.assertEqual(calls,['/status'])
        finally:other.shutdown();other.server_close();thread.join(timeout=2)
        # An old private file has no live identity authority and never causes PID-based killing.
        path.write_text(json.dumps(owner));path.chmod(0o600)
        second=self.launch('backend','--mock');second.stop();self.assertFalse(path.exists())
        print('LIFECYCLE: unauthenticated stop denied; authenticated stop works; stale metadata safely replaced without PID kills.')
    def test_08_hung_owned_worker_has_bounded_cleanup(self):
        terminal=self.launch('backend','--mock');parents=processes()
        npm_child=next(pid for pid,parent in parents.items() if parent==terminal.pid)
        guard=next(pid for pid,parent in parents.items() if parent==npm_child)
        runtime=next(pid for pid,parent in parents.items() if parent==guard)
        # Freeze only our runtime supervisor, not an unrelated process.
        os.kill(runtime,signal.SIGSTOP)
        started=time.monotonic();terminal.stop()
        self.assertLess(time.monotonic()-started,13);self.assertTrue(free(8000))
        self.assertIn(b'grace period elapsed',terminal.output)
        print('LIFECYCLE: deliberately frozen owned supervisor was boundedly cleaned; no child or listener survived.')
