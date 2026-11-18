"""Integrated actual supervisor/worker/gates/loader/exchange over local TLS."""
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
import json,os,ssl,subprocess,sys,tempfile,threading,unittest
from backend.task52b_get_tls_fixture import build_fixture,KEY
from scripts import task52b_model_get as g

class IntegratedTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
  subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(cls.root/'key'),'-out',str(cls.root/'ca'),'-days','1','-subj','/CN=api.openai.com','-addext','subjectAltName=DNS:api.openai.com'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def fixture(self,mode='ok',status=200,raw=None):
  calls=[]
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*_):pass
   def do_GET(self):
    calls.append((self.command,self.path,self.headers.get('OpenAI-Project')))
    assert self.headers.get('Authorization')=='Bearer '+KEY
    assert self.headers.get('Content-Length','0')=='0'
    assert self.headers.get('OpenAI-Project')==g.PROJECT
    body=raw if raw is not None else json.dumps({'object':'model','id':g.q.MODEL,'created':1,'owned_by':'FICTIONAL'}).encode()
    self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(self.root/'ca',self.root/'key');server.socket=ctx.wrap_socket(server.socket,server_side=True)
  threading.Thread(target=server.serve_forever,daemon=True).start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);cfg,driver=build_fixture(Path(t.name)/'source',server.server_address[1],self.root/'ca',mode)
  return cfg,driver,calls
 def run_driver(self,driver):
  env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','TMPDIR')}
  return subprocess.run([sys.executable,'-I','-B',str(driver)],env=env,capture_output=True,text=True,timeout=30)
 def test_actual_supervised_tls_success(self):
  cfg,driver,calls=self.fixture();p=self.run_driver(driver);d=Path(cfg['state'])
  self.assertEqual(p.returncode,0,p.stderr+p.stdout)
  result=json.loads(p.stdout);self.assertEqual(result['result'],'completed',json.dumps({'result':result,'diagnostic':json.loads(Path(cfg['diagnostic']).read_text()) if Path(cfg['diagnostic']).exists() else None}))
  self.assertEqual(calls,[('GET','/v1/models/gpt-6-luna',g.PROJECT)])
  self.assertTrue(list(Path(cfg['root']).glob('key-boundary-*.json')));self.assertTrue((d/'intent.json').exists());self.assertTrue((d/'validated.json').exists())
  repeat=self.run_driver(driver);self.assertNotEqual(repeat.returncode,0);self.assertEqual(len(calls),1)

 def test_original_defect_is_reproduced_by_the_same_supervised_tls_harness(self):
  cfg,driver,calls=self.fixture('original_defect');p=self.run_driver(driver)
  self.assertEqual(p.returncode,0,p.stderr);result=json.loads(p.stdout)
  self.assertEqual(result['result'],'stopped');self.assertIsNone(result['status']);self.assertEqual(calls,[])
  diagnostic=json.loads(Path(cfg['diagnostic']).read_bytes())
  self.assertEqual((diagnostic['code'],diagnostic['function'],diagnostic['wireClaim']),('get_worker_identity','verify_supervision',True))
  raw=json.loads((Path(cfg['state'])/'response-1.json').read_bytes());self.assertFalse(raw['sendStarted'])
 def test_repeated_fresh_clean_supervisors_have_identical_wire_identity(self):
  hashes=[]
  for _ in range(3):
   cfg,driver,calls=self.fixture();p=self.run_driver(driver);self.assertEqual(p.returncode,0,p.stderr)
   self.assertEqual(json.loads(p.stdout)['result'],'completed');self.assertEqual(len(calls),1)
   hashes.append(json.loads((Path(cfg['state'])/'runtime.json').read_bytes())['loadedWireIdentitySHA256'])
  self.assertEqual(len(set(hashes)),1)
 def test_source_build_bootstrap_metadata_and_transport_mutations_refuse(self):
  for mode in ('changed_source','bad_build','bad_bootstrap','bad_metadata','monkeypatch_wire','changed_constant','monkeypatch_dial','monkeypatch_class','monkeypatch_constructor','missing_authorization','expired_authorization'):
   with self.subTest(mode=mode):
    cfg,driver,calls=self.fixture(mode);p=self.run_driver(driver)
    self.assertNotEqual(p.returncode,0,p.stdout);self.assertEqual(calls,[])
    self.assertFalse(list(Path(cfg['root']).glob('key-boundary-*.json')))
    self.assertFalse((Path(cfg['state'])/'consumed.json').exists())
 def test_http_401_403_and_malformed_model_responses_are_terminal(self):
  for status,raw in ((401,b'{}'),(403,b'{}'),(200,b'{'),(200,b'{"object":"model","id":"other","created":1,"owned_by":"FICTIONAL"}')):
   with self.subTest(status=status,raw=raw):
    cfg,driver,calls=self.fixture(status=status,raw=raw);p=self.run_driver(driver)
    self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout)['result'],'stopped');self.assertEqual(len(calls),1)
    repeat=self.run_driver(driver);self.assertNotEqual(repeat.returncode,0);self.assertEqual(len(calls),1)
 def test_crash_before_after_intent_and_after_tls_send_never_replays(self):
  for mode in ('before_intent','after_intent','after_send'):
   with self.subTest(mode=mode):
    cfg,driver,calls=self.fixture(mode);p=self.run_driver(driver);d=Path(cfg['state'])
    self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout)['result'],'stopped')
    self.assertTrue((d/'consumed.json').exists());self.assertEqual((d/'intent.json').exists(),mode!='before_intent')
    self.assertEqual(len(calls),int(mode=='after_send'))
    repeat=self.run_driver(driver);self.assertNotEqual(repeat.returncode,0);self.assertEqual(len(calls),int(mode=='after_send'))
 def test_competing_independent_supervisors_can_only_send_once(self):
  cfg,driver,calls=self.fixture();env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','TMPDIR')}
  processes=[subprocess.Popen([sys.executable,'-I','-B',str(driver)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
  results=[p.communicate(timeout=30) for p in processes]
  self.assertEqual(sum(p.returncode==0 for p in processes),1,results);self.assertEqual(len(calls),1)
  self.assertTrue((Path(cfg['state'])/'consumed.json').exists())
