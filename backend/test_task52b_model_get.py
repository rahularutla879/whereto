"""GET-only preparation: fictional journals/keys, spawned processes and loopback TLS."""
from base64 import b64encode
from datetime import datetime,timezone,timedelta
from pathlib import Path
from functools import partial
from contextlib import redirect_stdout,nullcontext
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import io,json,multiprocessing,os,resource,sys,tempfile,unittest,socket,ssl,subprocess,threading,time
from unittest.mock import patch,Mock
from scripts import task52b_model_get as c
from scripts import task52b_run_model_get_once as b
from backend.provider_responses import HTTPResult

KEY='FICTIONAL-MODEL-GET-ONLY'
GOOD=HTTPResult(200,json.dumps({'object':'model','id':c.q.MODEL,'created':1,'owned_by':'FICTIONAL'}).encode())

class Canned:
 def __init__(self,d,v=GOOD):self.d=d;self.v=v;self.sent=0
 def exchange(self,key):
  c.verify_intent(self.d);c.private_create(self.d/'wire-consumed.json',{'fixtureOnly':True});self.sent+=1
  c.private_create(self.d/'response-1.json',{'at':c.stamp(),'status':self.v.status,'complete':self.v.complete,'bodySHA256':self.v.digest,'bodyBase64':b64encode(self.v.body).decode()})
  return self.v

class ProtocolTests(unittest.TestCase):
 def fixture(self):
  f=c.FictionalGet();self.addCleanup(f.close);return f.directory
 def test_exact_empty_get_and_no_post_authority(self):
  self.assertEqual((c.request().method,c.request().url,c.request().body),('GET',c.ENDPOINT,b''))
  self.assertEqual((c.proposed_scope()['getMaximum'],c.proposed_scope()['postMaximum'],c.proposed_scope()['inferenceMaximum']),(1,0,0))
 def test_success_and_replay(self):
  d=self.fixture();w=Canned(d);v=c.run_get(d,lambda:KEY,w)
  self.assertEqual((v['result'],v['model'],w.sent),('completed',c.q.MODEL,1))
  self.assertEqual(v['expiresAt'],c.previous.fresh(v['observedAt'],datetime.now(timezone.utc)).isoformat())
  with self.assertRaises(c.q.Refused):c.run_get(d,Mock(side_effect=AssertionError()),w)
  self.assertEqual(w.sent,1)
 def test_terminal_denials_malformed_wrong_model_and_incomplete(self):
  bad=HTTPResult(200,b'{"object":"model","id":"other","created":1,"owned_by":"FICTIONAL"}')
  for reply in [HTTPResult(n,b'{}') for n in (400,401,403,307,500)]+[bad,HTTPResult(200,b'{}'),HTTPResult(200,b'{'),HTTPResult(200,GOOD.body,False),HTTPResult(200,b' '*1048577)]:
   d=self.fixture();w=Canned(d,reply);v=c.run_get(d,lambda:KEY,w)
   self.assertEqual((v['result'],w.sent),('stopped',1));self.assertNotIn('expiresAt',v)
   with self.assertRaises(c.q.Refused):c.run_get(d,Mock(),w)
 def test_project_model_method_and_any_post_or_inference_substitution(self):
  for k,v in [('project','other'),('model','other'),('method','POST'),('endpoint','https://api.openai.com/v1/responses/input_tokens'),('getMaximum',2),('postMaximum',1),('inferenceMaximum',1),('retries',1),('bodySHA256','0'*64)]:
   d=self.fixture();s=c.e.record(d/'scope.json');s[k]=v;(d/'scope.json').write_text(json.dumps(s));loader=Mock()
   with self.assertRaises(c.q.Refused):c.run_get(d,loader,Canned(d))
   loader.assert_not_called();self.assertFalse((d/'consumed.json').exists())
 def test_freshness_same_utc_day_and_24h_no_extension(self):
  t='2026-11-18T23:59:00+00:00';now=datetime(2026,11,18,23,59,tzinfo=timezone.utc)
  self.assertEqual(c.previous.fresh(t,now).isoformat(),'2026-11-19T00:00:00+00:00')
  for later in (now+timedelta(minutes=1),now+timedelta(hours=24),now-timedelta(seconds=1)):
   with self.assertRaises(c.q.Refused):c.previous.fresh(t,later)
  with self.assertRaises(c.q.Refused):c.previous.fresh('2026-11-17T19:48:46.517118+00:00',datetime(2026,11,18,0,0,tzinfo=timezone.utc))
 def test_reviewed_network_tail_is_unchanged(self):
  old=(c.ROOT/'scripts/task52b_count_only.py').read_text();new=Path(c.__file__).read_text()
  self.assertEqual(old[old.index('        began=monotonic();'):old.index('\n\ndef run_count')].strip(),new[new.index('        began=monotonic();'):new.index('\n\n\ndef run_get')].strip())
 def test_exact_source_pin_and_closed_real_entry(self):
  c.verify_build(c.digest(c.BUILD.read_bytes()))
  with self.assertRaises(c.q.Refused):c.verify_build('0'*64)
  with patch.object(c.e,'read_openai_only',side_effect=AssertionError('No secret read')),patch('socket.socket',side_effect=AssertionError('No network')):
   with self.assertRaises((FileNotFoundError,c.q.Refused)):c.execute_get_only()
  self.assertFalse(c.STATE.exists());self.assertFalse(c.AUTHORIZATION.exists())

def fictional_worker(path,point):
    resource.setrlimit(resource.RLIMIT_CORE,(0,0));d=Path(path);c._FIXTURES[path]=('127.0.0.1',1)
    original=c.private_create
    def create(p,value):
        if point=='before_intent' and p.name=='intent.json':os._exit(73)
        original(p,value)
        if point=='after_intent' and p.name=='intent.json':os._exit(73)
        if point=='response' and p.name=='response-1.json':os._exit(73)
    def exchange(self,key):return Canned(d).exchange(key)
    with patch.object(c,'STATE',d),patch.object(c,'live_preconditions',side_effect=lambda *_:c.e.record(d/'scope.json')),patch.object(c.e,'read_openai_only',return_value=KEY),patch.object(c,'private_create',side_effect=create),patch.object(c.GetOnlyHTTPS,'exchange',exchange):
        # The real prepared worker's supervision/runtime/INTENT ordering executes;
        # only permission/enrollment and provider exchanges are fictional substitutes.
        c.execute_get_only(b.MANIFEST_SHA)


def harness(path,point,queue):
    d=Path(path)
    with patch.object(c,'STATE',d),patch.object(c,'validate_preparation',return_value=None),patch.object(c,'live_preconditions',side_effect=lambda *_:c.e.record(d/'scope.json')),patch.object(b,'child',partial(fictional_worker,path,point)),patch.object(sys,'argv',['count-supervisor','--execute-model-get-once']),redirect_stdout(io.StringIO()):
        try:b.main();queue.put('supervised')
        except SystemExit:queue.put('refused')


class SupervisorTests(unittest.TestCase):
    def fixture(self):
        f=c.FictionalGet();self.addCleanup(f.close);return f.directory
    def test_default_missing_send_authorization_never_claims_or_reads_key(self):
        d=self.fixture()
        with patch.object(c,'STATE',d),patch.object(c,'validate_preparation',return_value=None),patch.object(c,'live_preconditions',side_effect=FileNotFoundError),patch.object(c.e,'read_openai_only',side_effect=AssertionError('No credential read')),patch('socket.socket',side_effect=AssertionError('No network')),patch.object(sys,'argv',['count','--execute-model-get-once']):
            with self.assertRaises(SystemExit):b.main()
        self.assertEqual({p.name for p in d.iterdir()},{'scope.json'})
    def test_wrong_cli_purpose_and_expired_evidence_refuse(self):
        for args in ([],['--get'],['--inference'],['--retry']):
            with patch.object(sys,'argv',['count']+args),patch.object(c,'validate_preparation',side_effect=AssertionError('No enrollment')):
                with self.assertRaises(SystemExit):b.main()
        with patch.object(sys,'argv',['count','--execute-model-get-once']),patch.object(c,'validate_preparation',side_effect=c.q.Refused('prior_evidence_stale')),patch.object(c,'live_preconditions',side_effect=AssertionError('No authorization')):
            with self.assertRaises(SystemExit):b.main()
    def test_supervisor_identity_refuses_wrong_parent_and_worker(self):
        d=self.fixture();s=c.e.record(d/'scope.json')
        c.private_create(d/'launcher-claim.json',{'operation':c.OPERATION,'buildSHA256':s['buildSHA256'],'supervisorPID':-1})
        with patch.object(c,'STATE',d):
            with self.assertRaises(c.q.Refused):c.verify_supervision(s)
        # Fictional mutation solely to test the second guard.
        (d/'launcher-claim.json').write_text(json.dumps({'operation':c.OPERATION,'buildSHA256':s['buildSHA256'],'supervisorPID':os.getppid()}))
        c.private_create(d/'runtime.json',{'workerPID':-1,'buildSHA256':s['buildSHA256']})
        with patch.object(c,'STATE',d):
            with self.assertRaises(c.q.Refused):c.verify_supervision(s,True)
    def test_actual_spawned_supervisor_worker_success_and_crashes_never_replay(self):
        ctx=multiprocessing.get_context('spawn')
        for point in (None,'before_intent','after_intent','response'):
            with self.subTest(point=point):
                d=self.fixture();queue=ctx.Queue();p=ctx.Process(target=harness,args=(str(d),point,queue));p.start();p.join(20)
                self.assertEqual(p.exitcode,0);self.assertEqual(queue.get(timeout=2),'supervised')
                self.assertTrue((d/'consumed.json').exists());self.assertTrue((d/'runtime.json').exists());self.assertTrue((d/'supervisor.json').exists())
                self.assertEqual((d/'intent.json').exists(),point!='before_intent')
                if point is None:self.assertEqual(c.e.record(d/'result.json')['model'],c.q.MODEL)
                p=ctx.Process(target=harness,args=(str(d),None,queue));p.start();p.join(20)
                self.assertEqual(p.exitcode,0);self.assertEqual(queue.get(timeout=2),'refused');queue.close()
    def test_competing_actual_supervisors_single_worker(self):
        d=self.fixture();ctx=multiprocessing.get_context('spawn');queue=ctx.Queue();ps=[ctx.Process(target=harness,args=(str(d),None,queue)) for _ in range(2)]
        for p in ps:p.start()
        for p in ps:p.join(20);self.assertEqual(p.exitcode,0)
        self.assertEqual(sorted([queue.get(timeout=2),queue.get(timeout=2)]),['refused','supervised']);self.assertEqual(c.e.record(d/'result.json')['model'],c.q.MODEL);queue.close()


class TLSTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
  for host,name in [('127.0.0.1','good'),('wrong.invalid','wrong')]:
   subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(cls.root/(name+'.key')),'-out',str(cls.root/(name+'.crt')),'-days','1','-subj','/CN='+host,'-addext','subjectAltName='+('IP:' if name=='good' else 'DNS:')+host],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def check_tls(self,mode='ok',wrong=False):
  calls=[];name='wrong' if wrong else 'good';cert=self.root/(name+'.crt')
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*_):pass
   def do_GET(self):
    body=self.rfile.read(int(self.headers.get('Content-Length',0)));calls.append((self.command,self.path,c.digest(body)))
    if mode=='missing':self.close_connection=True;return
    status=403 if mode=='deny' else 307 if mode=='redirect' else 200;raw=b'{"secret":"'+KEY.encode()+b'"}' if mode=='echo' else GOOD.body
    self.send_response(status);self.send_header('Content-Type','text/plain' if mode=='media' else 'application/json');self.send_header('Content-Length',str(65537 if mode=='oversize' else len(raw)+(10 if mode=='truncated' else 0)));self.end_headers()
    if mode=='late':time.sleep(.15)
    try:self.wfile.write(raw);self.wfile.flush()
    except OSError:pass
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(cert,self.root/(name+'.key'));server.socket=ctx.wrap_socket(server.socket,server_side=True)
  threading.Thread(target=server.serve_forever,daemon=True).start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
  f=c.FictionalGet(server.server_address[1]);self.addCleanup(f.close);d=f.directory;wire=c.GetOnlyHTTPS(d,ssl.create_default_context(cafile=str(cert)))
  original=socket.getaddrinfo
  def local(host,port,**kw):
   if host!='127.0.0.1' or port!=server.server_address[1]:raise AssertionError('Unexpected destination')
   return original(host,port,**kw)
  original_intent=c.verify_intent;verified=[]
  def verify(directory):
   verified.append(True)
   if mode=='expire' and len(verified)==2:raise c.q.Refused('prior_evidence_stale')
   return original_intent(directory)
  with patch('socket.getaddrinfo',side_effect=local),patch.object(c,'verify_intent',side_effect=verify),(patch.object(c,'DEADLINE',.05) if mode=='late' else nullcontext()):v=c.run_get(d,lambda:KEY,wire)
  return v,calls,d,wire
 def test_exact_get_bytes_single_send_and_replay(self):
  v,calls,d,w=self.check_tls();self.assertEqual((v['result'],v['model']),('completed',c.q.MODEL));self.assertEqual(calls,[('GET','/v1/models/gpt-6-luna',c.digest(b''))])
  with patch('socket.socket',side_effect=AssertionError('No resend')):
   with self.assertRaises(FileExistsError):w.exchange(KEY)
 def test_tls_and_response_failures_are_terminal(self):
  for mode,wrong in [('deny',False),('redirect',False),('missing',False),('truncated',False),('late',False),('oversize',False),('media',False),('echo',False),('ok',True)]:
   with self.subTest(mode=mode,wrong=wrong):
    v,calls,d,w=self.check_tls(mode,wrong);self.assertEqual(v['result'],'stopped');self.assertLessEqual(len(calls),1)
    with patch('socket.socket',side_effect=AssertionError('No resend')):
     with self.assertRaises(FileExistsError):w.exchange(KEY)
 def test_evidence_expiring_during_tls_refuses_before_http(self):
  v,calls,d,w=self.check_tls('expire');self.assertEqual(v['result'],'stopped');self.assertEqual(calls,[])
  self.assertFalse(c.e.record(d/'response-1.json')['sendStarted']);self.assertTrue((d/'consumed.json').exists())
 def test_tls_context_cannot_disable_verification(self):
  f=c.FictionalGet();self.addCleanup(f.close);ctx=ssl._create_unverified_context()
  with self.assertRaises(c.q.Refused):c.GetOnlyHTTPS(f.directory,ctx)
