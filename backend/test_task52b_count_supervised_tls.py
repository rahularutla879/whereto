"""Actual count supervisor/worker/loader/exchange on guarded local TLS only."""
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
import json,os,ssl,subprocess,sys,tempfile,threading,unittest
from backend.task52b_count_tls_fixture import build_fixture,KEY
from backend import test_task52b_get_supervised_tls as get_tests
from scripts import task52b_count_only as c

class CountIntegratedTests(unittest.TestCase):
 setUpClass=classmethod(get_tests.IntegratedTests.setUpClass.__func__)
 tearDownClass=classmethod(get_tests.IntegratedTests.tearDownClass.__func__)
 run_driver=get_tests.IntegratedTests.run_driver
 def fixture(self,mode='ok',status=200,raw=None):
  calls=[]
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*_):pass
   def do_POST(self):
    body=self.rfile.read(int(self.headers.get('Content-Length',0)));calls.append((self.command,self.path,c.digest(body)))
    assert self.headers.get('Authorization')=='Bearer '+KEY
    assert self.headers.get('OpenAI-Project')==c.PROJECT
    assert c.digest(body)==c.q.COUNT_SHA
    response=raw if raw is not None else b'{"object":"response.input_tokens","input_tokens":100}'
    self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(response)));self.end_headers();self.wfile.write(response)
   def do_GET(self):calls.append(('GET',self.path,None));self.send_error(405)
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(self.root/'ca',self.root/'key');server.socket=ctx.wrap_socket(server.socket,server_side=True)
  threading.Thread(target=server.serve_forever,daemon=True).start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);cfg,driver=build_fixture(Path(t.name)/'source',server.server_address[1],self.root/'ca',mode)
  return cfg,driver,calls
 def test_actual_supervised_count_tls_success(self):
  cfg,driver,calls=self.fixture();p=self.run_driver(driver)
  self.assertEqual(p.returncode,0,p.stderr+p.stdout);result=json.loads(p.stdout)
  self.assertEqual(result['result'],'completed',json.dumps({'result':result,'diagnostic':json.loads(Path(cfg['diagnostic']).read_text()) if Path(cfg['diagnostic']).exists() else None}))
  self.assertEqual(result['count'],100);self.assertEqual(calls,[('POST','/v1/responses/input_tokens',c.q.COUNT_SHA)])
  self.assertTrue(list(Path(cfg['root']).glob('key-boundary-*.json')))
  repeat=self.run_driver(driver);self.assertNotEqual(repeat.returncode,0);self.assertEqual(len(calls),1)
 def test_original_count_defect_is_reproduced(self):
  cfg,driver,calls=self.fixture('original_defect');p=self.run_driver(driver)
  self.assertEqual(p.returncode,0,p.stderr);result=json.loads(p.stdout)
  self.assertEqual(result['result'],'stopped');self.assertEqual(calls,[])
  diagnostic=json.loads(Path(cfg['diagnostic']).read_bytes())
  self.assertEqual((diagnostic['code'],diagnostic['function'],diagnostic['wireClaim']),('count_worker_identity','verify_supervision',True))
 def test_repeated_fresh_clean_count_supervisors_have_stable_identity(self):
  hashes=[]
  for _ in range(3):
   cfg,driver,calls=self.fixture();p=self.run_driver(driver);self.assertEqual(p.returncode,0,p.stderr)
   self.assertEqual(json.loads(p.stdout)['count'],100);self.assertEqual(len(calls),1)
   hashes.append(json.loads((Path(cfg['state'])/'runtime.json').read_bytes())['loadedWireIdentitySHA256'])
  self.assertEqual(len(set(hashes)),1)
 def test_source_bootstrap_metadata_and_transport_substitution_refuse(self):
  for mode in ('changed_source','bad_build','bad_bootstrap','bad_metadata','monkeypatch_wire','changed_constant','monkeypatch_dial','monkeypatch_class','missing_permission','read_permission','stale_get'):
   with self.subTest(mode=mode):
    cfg,driver,calls=self.fixture(mode);p=self.run_driver(driver)
    self.assertNotEqual(p.returncode,0,p.stdout);self.assertEqual(calls,[])
    self.assertFalse(list(Path(cfg['root']).glob('key-boundary-*.json')))
    self.assertFalse((Path(cfg['state'])/'consumed.json').exists())
    if mode in ('stale_get','read_permission'):
     self.assertEqual(json.loads(Path(cfg['diagnostic']).read_bytes())['code'],'prior_evidence_stale' if mode=='stale_get' else 'responses_write_required')
 def test_http_and_count_parse_failures_are_terminal(self):
  for status,raw in ((401,b'{}'),(403,b'{}'),(400,b'{}'),(200,b'{'),(200,b'{"object":"response.input_tokens","input_tokens":0}'),(200,b'{"object":"response.input_tokens","input_tokens":true}'),(200,b'{"object":"response.input_tokens","input_tokens":9953}')):
   with self.subTest(status=status,raw=raw):
    cfg,driver,calls=self.fixture(status=status,raw=raw);p=self.run_driver(driver)
    self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout)['result'],'stopped');self.assertEqual(len(calls),1)
    repeat=self.run_driver(driver);self.assertNotEqual(repeat.returncode,0);self.assertEqual(len(calls),1)
 def test_crash_stages_never_replay(self):
  for mode in ('before_intent','after_intent','after_send'):
   with self.subTest(mode=mode):
    cfg,driver,calls=self.fixture(mode);p=self.run_driver(driver);d=Path(cfg['state'])
    self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout)['result'],'stopped')
    self.assertTrue((d/'consumed.json').exists());self.assertEqual((d/'intent.json').exists(),mode!='before_intent')
    self.assertEqual(len(calls),int(mode=='after_send'))
    repeat=self.run_driver(driver);self.assertNotEqual(repeat.returncode,0);self.assertEqual(len(calls),int(mode=='after_send'))
 def test_competing_count_supervisors_send_once(self):
  cfg,driver,calls=self.fixture();env={k:v for k,v in os.environ.items() if k in ('PATH','LANG','TMPDIR')}
  processes=[subprocess.Popen([sys.executable,'-I','-B',str(driver)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
  results=[p.communicate(timeout=30) for p in processes]
  self.assertEqual(sum(p.returncode==0 for p in processes),1,results);self.assertEqual(len(calls),1)
 def test_both_runners_reject_wrong_operation_and_inference_cli(self):
  from scripts import task52b_run_count_once as count_boot
  from scripts import task52b_run_model_get_once as get_boot
  from unittest.mock import patch
  for boot in (count_boot,get_boot):
   for option in ('--inference','--retry','--execute-count-only-once' if boot is get_boot else '--execute-model-get-once'):
    with patch.object(sys,'argv',['supervisor',option]):
     with self.assertRaises(SystemExit):boot.main()
