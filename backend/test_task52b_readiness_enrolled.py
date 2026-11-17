"""Local TLS/canned records only. Never loads the owner credential or real scope."""
from base64 import b64encode
from copy import deepcopy
from contextlib import nullcontext
from hashlib import sha256
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import ast
import json,multiprocessing,os,socket,ssl,subprocess,tempfile,threading,time,unittest
from unittest.mock import patch,Mock
from scripts import task52b_readiness_enrolled as e
from backend.provider_responses import HTTPResult

KEY='FICTIONAL-ONLY-NOT-A-REAL-KEY'

def replies(status=200,model=None):
 return (HTTPResult(status,json.dumps({'object':'model','id':model or e.q.MODEL,'created':1,'owned_by':'FICTIONAL'}).encode()),
         HTTPResult(200,b'{"object":"response.input_tokens","input_tokens":100}'))

def scope():
 return {'operation':e.OPERATION,'project':e.PROJECT,'model':e.q.MODEL,'countSHA256':e.q.COUNT_SHA,
         'buildSHA256':sha256(e.MANIFEST.read_bytes()).hexdigest(),'credentialIdentity':'FICTIONAL-METADATA'}

def setup(directory):
 directory.chmod(0o700);s=scope();e.private_create(directory/'scope.json',s);return s

class Canned:
 def __init__(self,directory,values=None,crash=False):self.directory=directory;self.values=values or replies();self.crash=crash;self.sent=[]
 def exchange(self,index,pair,key):
  e.verify_intent(self.directory,index,pair)
  e.private_create(self.directory/f'wire-consumed-{index}.json',{'fixtureOnly':True})
  if self.crash is not False and self.crash==index:os._exit(73)
  self.sent.append(index);v=self.values[index-1]
  e.private_create(self.directory/f'response-{index}.json',{'status':v.status,'bodyBase64':b64encode(v.body).decode(),'bodySHA256':v.digest,'complete':v.complete,'contentType':v.content_type,'sendStarted':True})
  return v

def process_run(path,crash,queue):
 try:
  s=e.record(Path(path)/'scope.json')
  def key():
   if type(crash)is int and crash==0:os._exit(73)
   return KEY
  v=e.run_scope(Path(path),s,key,Canned(Path(path),crash=crash));queue.put(v['result'])
 except e.q.Refused:queue.put('replay_refused')

class ProtocolTests(unittest.TestCase):
 def fixture(self):
  t=tempfile.TemporaryDirectory(prefix='readiness-offline-');self.addCleanup(t.cleanup);d=Path(t.name);return d,setup(d)
 def test_single_dial_is_exact_reviewed_class_without_evaluator_import(self):
  def node(path):return next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='_SingleDial')
  self.assertEqual(ast.dump(node(e.ROOT/'scripts/task52b_first_slot.py')),ast.dump(node(e.ROOT/'scripts/task52b_readiness_enrolled.py')))
 def test_success_exact_pair_immutable_and_replay_refused(self):
  d,s=self.fixture();wire=Canned(d);v=e.run_scope(d,s,lambda:KEY,wire)
  self.assertEqual((v['result'],v['inputTokens'],wire.sent),('completed',100,[1,2]))
  with self.assertRaises(e.q.Refused):e.run_scope(d,s,Mock(side_effect=AssertionError()),wire)
  self.assertEqual(wire.sent,[1,2]);self.assertEqual(e.private_read(d/'scope.json'),e.private_read(d/'scope.json'))
 def test_get_permission_or_model_refusal_never_posts(self):
  for values in (replies(401),replies(403),replies(model='different'),(HTTPResult(200,b'{}'),replies()[1])):
   d,s=self.fixture();w=Canned(d,values);v=e.run_scope(d,s,lambda:KEY,w)
   self.assertEqual(v['result'],'stopped');self.assertEqual(w.sent,[1]);self.assertFalse((d/'intent-2.json').exists())
 def test_post_permission_malformed_and_incomplete_terminal(self):
  for r in (HTTPResult(403,b'{}'),HTTPResult(400,b'{}'),HTTPResult(200,b'{}'),HTTPResult(200,b'{',False)):
   d,s=self.fixture();w=Canned(d,(replies()[0],r));v=e.run_scope(d,s,lambda:KEY,w)
   self.assertEqual(v['result'],'stopped');self.assertEqual(w.sent,[1,2]);self.assertIsNone(v['inputTokens'])
   with self.assertRaises(e.q.Refused):e.run_scope(d,s,lambda:KEY,w)
 def test_changed_scope_and_missing_precondition_refuse(self):
  d,s=self.fixture();changed={**s,'project':'other'}
  with self.assertRaises(e.q.Refused):e.run_scope(d,changed,Mock(),Mock())
  pair=e.q.requests();e.private_create(d/'consumed.json',{'scopeSHA256':e.digest(e.private_read(d/'scope.json'))})
  e.private_create(d/'intent-2.json',e.intent_value(s,2,pair[1]))
  with self.assertRaises((FileNotFoundError,e.q.Refused)):e.verify_intent(d,2,pair)
 def test_real_process_crash_after_consumption_get_or_post_intent_never_replays(self):
  for point in (0,1,2):
   d,s=self.fixture();c=multiprocessing.get_context('spawn');q=c.Queue();p=c.Process(target=process_run,args=(str(d),point,q));p.start();p.join(15)
   self.assertEqual(p.exitcode,73);self.assertTrue((d/'consumed.json').exists())
   if point:self.assertTrue((d/f'intent-{point}.json').exists())
   p=c.Process(target=process_run,args=(str(d),False,q));p.start();p.join(15);self.assertEqual(p.exitcode,0);self.assertEqual(q.get(timeout=2),'replay_refused');q.close()
 def test_competing_processes_only_one_scope(self):
  d,s=self.fixture();c=multiprocessing.get_context('spawn');q=c.Queue();ps=[c.Process(target=process_run,args=(str(d),False,q)) for _ in range(2)]
  for p in ps:p.start()
  for p in ps:p.join(15);self.assertEqual(p.exitcode,0)
  self.assertEqual(sorted([q.get(timeout=2),q.get(timeout=2)]),['completed','replay_refused']);q.close()
 def test_source_tamper_refuses_and_fixed_bootstrap_has_no_inference_option(self):
  with self.assertRaises(e.q.Refused):e.verify_build('0'*64)
  b=json.loads(e.MANIFEST.read_bytes());self.assertIn('scripts/task52_q4a.py',b['filesSHA256'])
  text=(e.ROOT/'scripts/task52b_run_readiness_once.py').read_text();self.assertIn("['--execute-authorized-readiness-once']",text)
  with patch.dict(os.environ,{'SSLKEYLOGFILE':'FICTIONAL'}):
   with self.assertRaises(e.q.Refused):e.verify_build(e.digest(e.MANIFEST.read_bytes()))

class CredentialTests(unittest.TestCase):
 def fixture(self,first=b'OPENAI_API_KEY=',project=None):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);root=Path(t.name);backend=root/'backend';backend.mkdir()
  f=backend/'.env.cloud-evaluation.openai-replacement-FICTIONAL';key=b'sk-proj-'+b'FICTIONAL'*6
  f.write_bytes(first+key+b'\nUNRELATED=DO-NOT-LOAD\n');f.chmod(0o600)
  p=f.with_name(f.name+'.metadata.json');m={'projectId':project or e.PROJECT,'projectName':'WhereTo Model Evaluation','credentialFile':str(f),'trackingId':'FICTIONAL','permissions':{'listModels':'Read','responses':'Read','unrelated':'None'},'expiresOn':'2099-01-01'};p.write_text(json.dumps(m));p.chmod(0o600);s=f.stat()
  return root,{'metadataPath':str(p),'credentialPath':str(f),'trackingId':'FICTIONAL','credentialDevice':s.st_dev,'credentialInode':s.st_ino,'credentialSize':s.st_size,'credentialMtimeNS':s.st_mtime_ns},e.digest(p.read_bytes()),key
 def test_only_first_openai_line_read_no_unrelated_bytes(self):
  root,c,h,key=self.fixture();original=os.read;read=[]
  def observe(fd,n):
   data=original(fd,n);read.append(data);return data
  # Metadata reads are separate; check the credential descriptor bytes only.
  f=Path(c['credentialPath']);orig_open=os.open;ids=[]
  def opened(path,*args,**kw):
   fd=orig_open(path,*args,**kw)
   if Path(path)==f:ids.append(fd)
   return fd
  def read_only_key(fd,n):
   data=original(fd,n)
   if fd in ids:read.append(data)
   return data
  with patch.object(e,'ROOT',root),patch('os.open',side_effect=opened),patch('os.read',side_effect=read_only_key):value=e.read_openai_only(c,h)
  self.assertEqual(value.encode(),key);self.assertNotIn(b'UNRELATED',b''.join(read))
 def test_wrong_project_permissions_identity_symlink_and_mode_refuse(self):
  root,c,h,key=self.fixture(project='other')
  with patch.object(e,'ROOT',root):
   with self.assertRaises(e.q.Refused):e.read_openai_only(c,h)
  root,c,h,key=self.fixture();Path(c['credentialPath']).chmod(0o644)
  with patch.object(e,'ROOT',root):
   with self.assertRaises(e.q.Refused):e.read_openai_only(c,h)
  for change in ('permissions','expiresOn','trackingId'):
   root,c,h,key=self.fixture();p=Path(c['metadataPath']);m=json.loads(p.read_bytes())
   m[change]={'listModels':'Read','responses':'Write','unrelated':'None'} if change=='permissions' else '2000-01-01' if change=='expiresOn' else 'OTHER'
   p.write_text(json.dumps(m));h=e.digest(p.read_bytes())
   with patch.object(e,'ROOT',root):
    with self.assertRaises(e.q.Refused):e.read_openai_only(c,h)
  root,c,h,key=self.fixture();f=Path(c['credentialPath']);other=f.with_name('fictional-original');f.rename(other);f.symlink_to(other)
  with patch.object(e,'ROOT',root):
   with self.assertRaises(e.q.Refused):e.read_openai_only(c,h)
 def test_non_openai_first_line_refuses_without_alternate_key(self):
  root,c,h,key=self.fixture(first=b'UNRELATED_KEY=')
  with patch.object(e,'ROOT',root):
   with self.assertRaises(e.q.Refused):e.read_openai_only(c,h)

class TLSTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
  for host,name in [('api.openai.com','good'),('wrong.invalid','wrong')]:
   subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(cls.root/(name+'.key')),'-out',str(cls.root/(name+'.crt')),'-days','1','-subj','/CN='+host,'-addext','subjectAltName=DNS:'+host],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def run_tls(self,mode='ok',wrong=False):
  t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);d=Path(t.name);s=setup(d);calls=[];name='wrong' if wrong else 'good';cert=self.root/(name+'.crt')
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*_):pass
   def do_GET(self):self.answer()
   def do_POST(self):self.answer()
   def answer(self):
    data=self.rfile.read(int(self.headers.get('Content-Length',0)))
    calls.append((self.command,self.path,e.digest(data),self.headers.get('OpenAI-Project')))
    if self.headers.get('Authorization')!='Bearer '+KEY:self.send_error(403);return
    i=1 if self.command=='GET' else 2;v=replies()[i-1];status=403 if mode=='deny' else 307 if mode=='redirect' else v.status
    raw=b'{"error":"sk-proj-FICTIONAL-MASKED-***"}' if mode=='echo' else v.body
    if mode=='missing':self.close_connection=True;return
    self.send_response(status);
    if mode=='project':self.send_header('OpenAI-Project','OTHER')
    self.send_header('Content-Type','text/plain' if mode=='badmedia' else 'application/json');self.send_header('Content-Length',str(65537 if mode=='oversize' else len(raw)+(10 if mode=='truncated' else 0)));self.end_headers()
    if mode=='late':time.sleep(.15)
    try:self.wfile.write(raw);self.wfile.flush()
    except OSError:pass
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(cert,self.root/(name+'.key'));server.socket=ctx.wrap_socket(server.socket,server_side=True)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
  context=ssl.create_default_context(cafile=str(cert));wire=e.FixedReadinessHTTPS(d,context)
  original=socket.getaddrinfo
  def local(host,port,**kw):
   if host!='api.openai.com' or port!=443:raise AssertionError('Unexpected network destination')
   return original('127.0.0.1',server.server_address[1],**kw)
  with patch('socket.getaddrinfo',side_effect=local), (patch.object(e,'DEADLINE',.05) if mode=='late' else nullcontext()):value=e.run_scope(d,s,lambda:KEY,wire)
  return value,calls,d
 def test_real_single_dial_code_local_tls_exact_pair(self):
  v,c,d=self.run_tls();self.assertEqual(v['result'],'completed');self.assertEqual(len(c),2)
  self.assertEqual([x[:2] for x in c],[('GET','/v1/models/gpt-6-luna'),('POST','/v1/responses/input_tokens')]);self.assertEqual(c[1][2],e.q.COUNT_SHA);self.assertTrue(all(x[3]==e.PROJECT for x in c))
  self.assertTrue((d/'wire-consumed-1.json').exists());self.assertTrue((d/'wire-consumed-2.json').exists())
 def test_permission_redirect_truncation_and_hostname_refuse_no_post(self):
  for mode,wrong in [('deny',False),('redirect',False),('truncated',False),('missing',False),('late',False),('oversize',False),('badmedia',False),('project',False),('echo',False),('ok',True)]:
   with self.subTest(mode=mode,wrong=wrong):
    v,c,d=self.run_tls(mode,wrong);self.assertEqual(v['result'],'stopped');self.assertLessEqual(len(c),1);self.assertFalse((d/'intent-2.json').exists())

 def test_completed_wire_claim_cannot_resend(self):
  v,c,d=self.run_tls();self.assertEqual(v['result'],'completed')
  with patch('socket.socket',side_effect=AssertionError('Network forbidden')):
   wire=e.FixedReadinessHTTPS(d)
   with self.assertRaises(FileExistsError):wire.exchange(1,e.q.requests(),KEY)
  self.assertEqual(len(c),2)
