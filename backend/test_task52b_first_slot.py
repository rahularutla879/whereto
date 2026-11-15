"""Opt-in local TLS provider tests; fictional keys, responders and journals only."""
from contextlib import closing
from hashlib import sha256
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import multiprocessing
import os
from pathlib import Path
import socket
import subprocess
import ssl
import tempfile
import time
import unittest
from unittest.mock import patch

OPT_IN=__name__=='_task52b_first_slot_tests'
if OPT_IN:
    from backend import test_task52_diagnostic_progression as fake
    from scripts import task52b_evidence_access as evidence
    from scripts import task52b_first_slot as q
    from scripts import task52b_first_slot_identity as identity


def serve(cert,key,body,mode,pipe,count,request_hash):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def do_POST(self):
            raw=self.rfile.read(int(self.headers['Content-Length']))
            with count.get_lock():count.value+=1
            with request_hash.get_lock():request_hash.value=sha256(raw).hexdigest().encode()
            if (self.path!='/v1/responses' or self.headers.get('Authorization')!='Bearer FICTIONAL-OPENAI-LOCAL-SECRET-ONLY' or
                    self.headers.get('Content-Type')!='application/json'):
                self.send_error(403);return
            if mode=='missing':self.close_connection=True;return
            if mode=='late':time.sleep(.7)
            status=307 if mode=='redirect' else 429 if mode=='error' else 200
            self.send_response(status)
            self.send_header('Content-Type','application/json')
            self.send_header('x-request-id','FICTIONAL-LOCAL-REQUEST')
            if mode=='redirect':self.send_header('Location','https://api.openai.com/v1/responses')
            self.send_header('Content-Length',str(len(body)+(20 if mode=='truncated' else 0)))
            self.end_headers()
            if mode=='late_body':time.sleep(.7)
            try:self.wfile.write(body[:20] if mode=='truncated' else body);self.wfile.flush()
            except (OSError,ssl.SSLError):pass
            self.close_connection=True
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);server.daemon_threads=True
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.minimum_version=ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(cert,key);server.socket=context.wrap_socket(server.socket,server_side=True)
    pipe.send(server.server_port);pipe.close();server.serve_forever()


def crash_worker(directory,trust,permission,transport,point):
    q.FirstSlotEngine(directory,trust).simulate_one(permission,transport,fake.NOW,crash_at=point)


@unittest.skipUnless(OPT_IN,'Use the explicit first-slot frozen-B2 TLS test driver')
class FirstSlotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.keys=fake.SyntheticKeys();cls.responses=fake.fake_responses()
        cls.temp=tempfile.TemporaryDirectory(prefix='whereto-first-slot-fictional-')
        cls.root=Path(cls.temp.name);os.chmod(cls.root,0o700)
        for name,address in [('good','127.0.0.1'),('wrong','127.0.0.2')]:
            subprocess.run(['/opt/homebrew/bin/openssl','req','-x509','-newkey','rsa:2048','-nodes',
                '-keyout',str(cls.root/(name+'.key')),'-out',str(cls.root/(name+'.pem')),
                '-days','1','-subj','/CN=FICTIONAL-LOOPBACK','-addext','subjectAltName=IP:'+address],
                check=True,timeout=15,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,umask=0o077)
        (cls.root/'secret').write_text('FICTIONAL-OPENAI-LOCAL-SECRET-ONLY');os.chmod(cls.root/'secret',0o600)
        cls.secret_fd=os.open(cls.root/'secret',os.O_RDONLY)

    @classmethod
    def tearDownClass(cls):os.close(cls.secret_fd);cls.temp.cleanup();cls.keys.close()

    def setup(self,mode='success',*,wrong_host=False,wrong_ca=False,response=None,crash=False):
        if response is None:
            response={'error':{'type':'fictional_rate_limit'}} if mode=='error' else self.responses[0]
        raw=json.dumps(response,indent=2).encode()
        context=multiprocessing.get_context('fork');parent,child=context.Pipe()
        count=context.Value('i',0);request_hash=context.Array('c',65)
        certificate=self.root/('wrong.pem' if wrong_host else 'good.pem')
        process=context.Process(target=serve,args=(certificate,self.root/('wrong.key' if wrong_host else 'good.key'),raw,mode,child,count,request_hash))
        process.start()
        if not parent.poll(5):process.terminate();process.join();self.fail('TLS fixture startup timeout')
        port=parent.recv();parent.close()
        def cleanup():process.terminate();process.join(5)
        self.addCleanup(cleanup)
        with evidence.original_evidence():fixture=q.kernel.SyntheticExecution(self.keys.trust)
        self.addCleanup(fixture.close)
        engine=q.FirstSlotEngine(fixture.fixture.directory,self.keys.trust)
        packets=fake.scope(self.keys,fixture.fixture);engine.activate_synthetic_scope(packets,fake.NOW)
        secret=q.ServerSecretFD(self.secret_fd,'fictional-first-slot-key')
        transport=q.local_fixture_transport(port,self.root/'wrong.pem' if wrong_ca else certificate,secret,deadline=.2 if mode.startswith('late') else 2,
                                           crash_before_capture=crash)
        return fixture,engine,packets,transport,count,request_hash,raw,port

    def send(self,setup,*,permission=None,point=None):
        f,e,p,t,*_,port=setup
        connect=socket.socket.connect
        def only_loopback(sock,address):
            if address!=('127.0.0.1',port):raise AssertionError('External network forbidden')
            return connect(sock,address)
        with patch.object(socket.socket,'connect',only_loopback):
            return e.simulate_one(permission or fake.execute(self.keys,f.fixture,p),t,fake.NOW,crash_at=point)

    def state(self,e):
        with e.lock():return e.state()

    def test_exact_payload_over_verified_tls_and_immutable_capture(self):
        s=self.setup();outcome=self.send(s);f,e,p,t,count,request_hash,raw,port=s
        self.assertEqual(count.value,1);self.assertEqual(request_hash.value.decode(),q.PAYLOAD_SHA)
        self.assertEqual(outcome['data']['assessment']['raw']['mechanicalFailures'],[])
        self.assertEqual(q._BINDINGS[t].secret.reads,1)
        self.assertEqual(self.state(e)[3],2500000)
        op=outcome['operation'];capture=json.loads((f.fixture.directory/f'raw-{op}.json').read_bytes())
        self.assertEqual(q.b64decode(capture['bytesBase64']),raw)
        self.assertIsNone(outcome['data']['assessment']['raw']['fullyCorrectIndependent'])
        self.assertFalse(outcome['data']['assessment']['diagnostic']['planningAuthorized'])
        with self.assertRaises(q.Denied):self.send(s)
        self.assertEqual(count.value,1)
        metadata_path=f.fixture.directory/f'http-{op}.json'
        metadata=json.loads(metadata_path.read_bytes());metadata['headers']['x-request-id']='altered'
        metadata_path.write_text(json.dumps(metadata))
        with self.assertRaises(q.Denied):self.state(e)

    def test_mutation_after_validation_cannot_change_wire_bytes(self):
        s=self.setup();connect=q._SingleDial.connect
        def changed(connection):
            connect(connection);s[3].payload=b'{}'
        with patch.object(q._SingleDial,'connect',changed):self.send(s)
        self.assertEqual(s[5].value.decode(),q.PAYLOAD_SHA)
        self.assertEqual(s[4].value,1)

    def test_refusal_and_http_error_keep_charges_and_raw_evidence(self):
        for mode,response in [('success',{'model':'gpt-6-luna','output':[{'content':[{'type':'refusal'}]}]}),('error',None)]:
            s=self.setup(mode,response=response);o=self.send(s)
            self.assertEqual(self.state(s[1])[1][-1]['kind'],'HALT')
            self.assertEqual(self.state(s[1])[3],2500000)
            self.assertEqual(s[4].value,1)
            self.assertTrue((s[0].fixture.directory/f'http-{o["operation"]}.json').exists())

    def test_redirect_is_not_followed(self):
        s=self.setup('redirect');self.send(s)
        self.assertEqual(s[4].value,1);self.assertEqual(self.state(s[1])[1][-1]['kind'],'HALT')
        with self.assertRaises(q.Denied):self.send(s)
        self.assertEqual(s[4].value,1)

    def test_missing_late_and_truncated_responses_never_retry(self):
        for mode in ('missing','late','late_body','truncated'):
            with self.subTest(mode=mode):
                s=self.setup(mode)
                with self.assertRaises(q.Denied):self.send(s)
                self.assertEqual(self.state(s[1])[3],2500000)
                self.assertEqual(self.state(s[1])[1][-1]['kind'],'HALT')
                captures=list(s[0].fixture.directory.glob('http-*.json'))
                metadata=[json.loads(p.read_bytes()) for p in captures if not p.name.startswith('http-intent')]
                self.assertEqual(len(metadata),1);self.assertFalse(metadata[0]['complete'])
                with self.assertRaises(q.Denied):self.send(s)
                self.assertEqual(s[4].value,1)

    def test_hostname_verification_failure_never_sends_post(self):
        for options in ({'wrong_host':True},{'wrong_ca':True}):
            with self.subTest(options=options):
                s=self.setup(**options)
                with self.assertRaises(q.Denied):self.send(s)
                self.assertEqual(s[4].value,0);self.assertEqual(self.state(s[1])[3],2500000)
                with self.assertRaises(q.Denied):self.send(s)

    def test_no_second_slot_even_after_synthetic_review(self):
        s=self.setup();o=self.send(s);f,e,p,*_=s
        e.record_review(fake.review(self.keys,f.fixture,o),fake.NOW)
        permission=fake.execute(self.keys,f.fixture,p,1,self.state(e)[1][-1]['hash'])
        with self.assertRaises(q.Denied):self.send(s,permission=permission)
        self.assertEqual(s[4].value,1)

    def test_changed_payload_and_second_slot_refuse_before_reservation(self):
        s=self.setup()
        with self.assertRaises(q.Denied):s[3].exchange(s[0].fixture.directory,'0'*64,q.PAYLOAD_SHA)
        self.assertEqual(s[4].value,0)
        s[3].payload=b'{}'
        with self.assertRaises(q.Denied):self.send(s)
        self.assertEqual(len(self.state(s[1])[0]),10);self.assertEqual(s[4].value,0)
        s[3].payload=identity.first_request()
        with self.assertRaises(q.Denied):self.send(s,permission=fake.execute(self.keys,s[0].fixture,s[2],1))
        self.assertEqual(len(self.state(s[1])[0]),10)

    def test_operational_constructor_never_reads_credentials_or_opens_socket(self):
        secret=q.ServerSecretFD(self.secret_fd,'fictional-first-slot-key')
        with patch('socket.getaddrinfo',side_effect=AssertionError('No network')):
            for packet in (None,{'approved':True},json.loads((identity.ROOT/'docs/task52b-diagnostic-purpose-amendment-PROPOSED-v1.json').read_text())):
                with self.assertRaises(q.Denied):q.OpenAIResponsesTransport(packet,credential=secret)
        self.assertEqual(secret.reads,0)

    def test_real_process_crashes_do_not_erase_reservation_or_resend(self):
        for point,crash,expected in [('after_intent',False,0),(None,True,1),('after_send',False,1)]:
            with self.subTest(point=point,crash=crash):
                s=self.setup(crash=crash);f,e,p,t,count,*_=s
                process=multiprocessing.get_context('fork').Process(target=crash_worker,
                    args=(f.fixture.directory,self.keys.trust,fake.execute(self.keys,f.fixture,p),t,point))
                process.start();process.join(45)
                if process.is_alive():process.terminate();process.join();self.fail('Crash worker timeout')
                self.assertEqual(process.exitcode,73);self.assertEqual(count.value,expected)
                self.assertEqual(self.state(e)[3],2500000)
                with self.assertRaises(q.Denied):self.send(s)
                self.assertEqual(count.value,expected)

    def test_conditional_quote_and_unknown_or_over_cap_refuse(self):
        self.assertEqual(q.quote(9952,125,500,0)['calculatedNanodollars'],2500000)
        self.assertFalse(q.quote(9952,125,500,0)['approved'])
        for args in [(None,125,500,0),(9953,125,500,0),(9952,126,500,0),
                     (9952,125,500,1),(True,125,500,0),(9952,125,500,None),
                     (9952,-1,500,0),(9952,125,501,0)]:
            with self.assertRaises(q.Denied):q.quote(*args)
