"""Fictional count scopes only; no owner credential or live authorization."""
from base64 import b64encode
from datetime import datetime,timezone,timedelta
from pathlib import Path
from contextlib import nullcontext
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json,multiprocessing,os,socket,ssl,subprocess,tempfile,threading,time,unittest
from unittest.mock import patch,Mock
from scripts import task52b_count_only as c
from backend.provider_responses import HTTPResult

KEY='FICTIONAL-COUNT-ONLY'
NOW=datetime(2026,11,17,21,tzinfo=timezone.utc)
GOOD=HTTPResult(200,b'{"object":"response.input_tokens","input_tokens":100}')

class Canned:
 def __init__(self,d,v=GOOD):self.d=d;self.v=v;self.sent=0
 def exchange(self,key):
  c.verify_intent(self.d);c.private_create(self.d/'wire-consumed.json',{'fixtureOnly':True});self.sent+=1
  c.private_create(self.d/'response-1.json',{'status':self.v.status,'complete':self.v.complete,'bodySHA256':self.v.digest,'bodyBase64':b64encode(self.v.body).decode()})
  return self.v

def child(path,point,queue):
 d=Path(path);c._FIXTURES[path]=('127.0.0.1',1)
 original=c.private_create
 def create(p,value):
  if point=='before_intent' and p.name=='intent.json':os._exit(73)
  original(p,value)
  if point=='after_intent' and p.name=='intent.json':os._exit(73)
  if point=='response' and p.name=='response-1.json':os._exit(73)
 try:
  with patch.object(c,'private_create',side_effect=create):v=c.run_count(d,lambda:KEY,Canned(d));queue.put(v['result'])
 except c.q.Refused:queue.put('replay_refused')

class CountTests(unittest.TestCase):
 def fixture(self):
  f=c.FictionalCount();self.addCleanup(f.close);return f.directory
 def test_exact_request_has_only_count_authority(self):
  r=c.request();self.assertEqual((r.method,r.url,c.digest(r.body)),('POST',c.ENDPOINT,c.q.COUNT_SHA))
  self.assertEqual((c.proposed_scope()['getMaximum'],c.proposed_scope()['inferenceMaximum']),(0,0))
 def test_success_and_replay(self):
  d=self.fixture();w=Canned(d);v=c.run_count(d,lambda:KEY,w)
  self.assertEqual((v['result'],v['count'],w.sent),('completed',100,1))
  with self.assertRaises(c.q.Refused):c.run_count(d,Mock(side_effect=AssertionError()),w)
  self.assertEqual(w.sent,1)
 def test_terminal_http_denials(self):
  for status in (400,401,403):
   with self.subTest(status=status):
    d=self.fixture();w=Canned(d,HTTPResult(status,b'{}'));v=c.run_count(d,lambda:KEY,w)
    self.assertEqual((v['result'],v['status'],w.sent),('stopped',status,1));self.assertIsNone(v['count'])
    with self.assertRaises(c.q.Refused):c.run_count(d,Mock(),w)
 def test_invalid_counts_and_response_shape(self):
  for raw in (b'{}',b'{',b'{"object":"response.input_tokens","input_tokens":0}',b'{"object":"response.input_tokens","input_tokens":true}',b'{"object":"response.input_tokens","input_tokens":9953}',b'{"object":"response.input_tokens","input_tokens":100,"model":"other"}',b' '*1048577):
   d=self.fixture();v=c.run_count(d,lambda:KEY,Canned(d,HTTPResult(200,raw)));self.assertEqual(v['result'],'stopped')
 def test_incomplete_response(self):
  d=self.fixture();v=c.run_count(d,lambda:KEY,Canned(d,HTTPResult(200,GOOD.body,False)));self.assertEqual(v['result'],'stopped')
 def test_scope_substitution_and_inference_refuse_before_loader(self):
  for k,v in [('project','other'),('model','other'),('countSHA256','0'*64),('endpoint','https://api.openai.com/v1/responses'),('getMaximum',1),('postMaximum',2),('inferenceMaximum',1),('retries',1)]:
   d=self.fixture();s=c.e.record(d/'scope.json');s[k]=v
   # Fictional fixture mutation only; never modifies protected original records.
   (d/'scope.json').write_text(json.dumps(s));loader=Mock(side_effect=AssertionError())
   with self.assertRaises(c.q.Refused):c.run_count(d,loader,Canned(d))
   loader.assert_not_called();self.assertFalse((d/'consumed.json').exists())
 def test_crash_before_after_intent_and_response_cannot_replay(self):
  for point in ('before_intent','after_intent','response'):
   d=self.fixture();ctx=multiprocessing.get_context('spawn');queue=ctx.Queue();p=ctx.Process(target=child,args=(str(d),point,queue));p.start();p.join(15)
   self.assertEqual(p.exitcode,73);self.assertTrue((d/'consumed.json').exists());self.assertEqual((d/'intent.json').exists(),point!='before_intent')
   p=ctx.Process(target=child,args=(str(d),None,queue));p.start();p.join(15);self.assertEqual(p.exitcode,0);self.assertEqual(queue.get(timeout=2),'replay_refused');queue.close()
 def test_independent_competing_runners(self):
  d=self.fixture();ctx=multiprocessing.get_context('spawn');queue=ctx.Queue();ps=[ctx.Process(target=child,args=(str(d),None,queue)) for _ in range(2)]
  for p in ps:p.start()
  for p in ps:p.join(15);self.assertEqual(p.exitcode,0)
  self.assertEqual(sorted([queue.get(timeout=2),queue.get(timeout=2)]),['completed','replay_refused']);queue.close()
 def test_modified_or_missing_intent_refuses(self):
  d=self.fixture();w=c.CountOnlyHTTPS(d)
  with patch('socket.socket',side_effect=AssertionError('No network')):
   with self.assertRaises(FileNotFoundError):w.exchange(KEY)
  self.assertFalse((d/'wire-consumed.json').exists())
 def test_build_manifest_exact_hash_and_source_refusal(self):
  c.verify_count_build(c.digest(c.BUILD.read_bytes()))
  with self.assertRaises(c.q.Refused):c.verify_count_build('0'*64)
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'source').write_text('FICTIONAL');b=root/'build.json';b.write_text(json.dumps({'filesSHA256':{'source':'0'*64}}))
   with patch.object(c,'BUILD',b),patch.object(c,'ROOT',root):
    with self.assertRaises(c.q.Refused):c.verify_count_build(c.digest(b.read_bytes()))
 def test_live_entry_remains_closed_no_credential_or_network(self):
  with patch.object(c.e,'read_openai_only',side_effect=AssertionError('No credential read')),patch('socket.socket',side_effect=AssertionError('No network')):
   with self.assertRaises((FileNotFoundError,c.q.Refused)):c.execute_count_only()
  self.assertFalse(c.STATE.exists());self.assertFalse(c.AUTHORIZATION.exists())  # Permission receipt is evidence, never send authority.

class EvidenceTests(unittest.TestCase):
 def records(self):
  body=json.dumps({'object':'model','id':c.q.MODEL,'created':1,'owned_by':'FICTIONAL'}).encode();h=c.digest(body)
  raw={'status':200,'complete':True,'credentialEchoRefused':False,'bodyBase64':b64encode(body).decode(),'bodySHA256':h,'contentType':'application/json','at':NOW.isoformat()}
  val={'value':c.q.validate_response(c.q.requests()[0],HTTPResult(200,body)),'rawSHA256':h,'at':NOW.isoformat()}
  return raw,val,h
 def test_valid_prior_get_expires_at_midnight(self):
  r,v,h=self.records();proof=c.validate_get_record(r,v,h,NOW);self.assertEqual(proof['expiresAt'],'2026-11-18T00:00:00+00:00')
 def test_stale_future_or_non_utc_evidence_refused(self):
  for t in (NOW+timedelta(days=1),NOW-timedelta(seconds=1),NOW+timedelta(hours=25)):
   r,v,h=self.records()
   with self.assertRaises(c.q.Refused):c.validate_get_record(r,v,h,t)
  with self.assertRaises(c.q.Refused):c.fresh('2026-11-17T21:00:00',NOW)
 def test_get_identity_integrity_and_completeness(self):
  for k,val in [('status',401),('complete',False),('bodySHA256','0'*64),('credentialEchoRefused',True)]:
   r,v,h=self.records();r[k]=val
   with self.assertRaises(c.q.Refused):c.validate_get_record(r,v,h,NOW)
  r,v,h=self.records();r['bodyBase64']=b64encode(b'{"object":"model","id":"other","created":1,"owned_by":"FICTIONAL"}').decode();r['bodySHA256']=c.digest(__import__('base64').b64decode(r['bodyBase64']));v['rawSHA256']=r['bodySHA256']
  with self.assertRaises(c.q.Refused):c.validate_get_record(r,v,r['bodySHA256'],NOW)
 def permission(self):
  return {'project':c.PROJECT,'credentialIdentity':'FICTIONAL','permissions':{'listModels':'Read','responses':'Write','unrelated':'None'},'independentlyEstablished':True,'basis':'verified-permission-receipt','evidenceSHA256':'a'*64,'observer':'FICTIONAL-REVIEWER','observedAt':NOW.isoformat()}
 def test_fictional_verified_permission_record_shape(self):self.assertEqual(len(c.permission_record(self.permission(),'FICTIONAL',NOW)),64)
 def test_owner_statement_old_read_wrong_identity_and_stale_not_proof(self):
  for change in ({'independentlyEstablished':False},{'basis':'owner-confirmation'},{'project':'other'},{'credentialIdentity':'other'},{'permissions':{'listModels':'Read','responses':'Read','unrelated':'None'}},{'observedAt':'2026-11-16T21:00:00+00:00'}):
   with self.assertRaises(c.q.Refused):c.permission_record(self.permission()|change,'FICTIONAL',NOW)

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
   def do_POST(self):
    body=self.rfile.read(int(self.headers.get('Content-Length',0)));calls.append((self.command,self.path,c.digest(body)))
    if mode=='missing':self.close_connection=True;return
    status=403 if mode=='deny' else 307 if mode=='redirect' else 200;raw=b'{"secret":"'+KEY.encode()+b'"}' if mode=='echo' else GOOD.body
    self.send_response(status);self.send_header('Content-Type','text/plain' if mode=='media' else 'application/json');self.send_header('Content-Length',str(65537 if mode=='oversize' else len(raw)+(10 if mode=='truncated' else 0)));self.end_headers()
    if mode=='late':time.sleep(.15)
    try:self.wfile.write(raw);self.wfile.flush()
    except OSError:pass
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(cert,self.root/(name+'.key'));server.socket=ctx.wrap_socket(server.socket,server_side=True)
  threading.Thread(target=server.serve_forever,daemon=True).start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
  f=c.FictionalCount(server.server_address[1]);self.addCleanup(f.close);d=f.directory;wire=c.CountOnlyHTTPS(d,ssl.create_default_context(cafile=str(cert)))
  original=socket.getaddrinfo
  def local(host,port,**kw):
   if host!='127.0.0.1' or port!=server.server_address[1]:raise AssertionError('Unexpected destination')
   return original(host,port,**kw)
  original_intent=c.verify_intent;verified=[]
  def verify(directory):
   verified.append(True)
   if mode=='expire' and len(verified)==2:raise c.q.Refused('prior_evidence_stale')
   return original_intent(directory)
  with patch('socket.getaddrinfo',side_effect=local),patch.object(c,'verify_intent',side_effect=verify),(patch.object(c,'DEADLINE',.05) if mode=='late' else nullcontext()):v=c.run_count(d,lambda:KEY,wire)
  return v,calls,d,wire
 def test_exact_count_bytes_single_send_and_replay(self):
  v,calls,d,w=self.check_tls();self.assertEqual((v['result'],v['count']),('completed',100));self.assertEqual(calls,[('POST','/v1/responses/input_tokens',c.q.COUNT_SHA)])
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
  f=c.FictionalCount();self.addCleanup(f.close);ctx=ssl._create_unverified_context()
  with self.assertRaises(c.q.Refused):c.CountOnlyHTTPS(f.directory,ctx)
