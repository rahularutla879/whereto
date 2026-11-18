"""Explicit frozen-source lab only: no real credentials, approval or API peer."""
import unittest,sys
OPT_IN=__name__=='_task52b_generation_tests'
if OPT_IN:
 from pathlib import Path
 from datetime import datetime,timezone,timedelta
 from copy import deepcopy
 from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
 from contextlib import closing
 import json,os,ssl,multiprocessing,socket,tempfile,sqlite3
 import _task52b_first_slot_tests as old
 from scripts import task52b_generation_candidate as g
 from scripts import task52b_generation_policy as p
 fake=old.fake;evidence=old.evidence


@unittest.skipUnless(OPT_IN,'Use explicit source-pinned generation test driver')
class GenerationTests(unittest.TestCase):
 setUpClass=classmethod(old.FirstSlotTests.setUpClass.__func__) if OPT_IN else classmethod(lambda cls:None)
 tearDownClass=classmethod(old.FirstSlotTests.tearDownClass.__func__) if OPT_IN else classmethod(lambda cls:None)
 def packet(self):
  now=datetime.now(timezone.utc);end=min(now+timedelta(hours=1),now.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1));stamp={'observedAt':now.isoformat(),'expiresAt':end.isoformat()}
  out={'project':p.PROJECT,'model':p.MODEL,'slot':p.SLOT,'operation':p.OPERATION,'payloadSHA256':p.PAYLOAD_SHA,'countSHA256':p.COUNT_SHA,'endpoint':p.ENDPOINT,'method':'POST','operationMaximum':1,'retries':0,'planningAuthorized':False,'semanticReview':'deferred','independentlyCorrect':None,'reservationNanodollars':p.CEILING,'fictionalOnly':True,'quotedMaximumNanodollars':1969000,'extraFeesNanodollars':{'tools':0,'separate_reasoning':0,'other_fees':0},'premiumBps':0}
  for k in ('ownerOperationApproved','technicalPurposeApproved','securityReviewApproved','writerEnrollmentApproved','independentPostAppendVerifier','accountTermsAndFeesApproved','modelAliasDiagnosticApproved'):out[k]=True
  for k in ('operationID','credentialIdentity','countBundleSHA256','modelGETBundleSHA256','writerIdentity'):out[k]='a'*64
  out['sourceBuildSHA256']=g.build_sha();out['writerIdentity']=json.loads(g.MANIFEST.read_bytes())['loadedCodeIdentities']['writer'];out['credentialIdentity']=p.digest(b'fictional-generation')
  for k in ('modelEvidence','countEvidence','permissionEvidence','priceEvidence','authorization'):out[k]=deepcopy(stamp)
  out['countEvidence'].update(inputTokens=5704,generationSHA256=p.PAYLOAD_SHA,countSHA256=p.COUNT_SHA);out['priceEvidence']['ratesNanoPerMillion']=deepcopy(p.RATES)
  return out
 def fixture(self,status=200,mode='ok',response=None):
  if response is None:response=self.responses[0]
  raw=json.dumps(response).encode();ctx=multiprocessing.get_context('fork');calls=ctx.Value('i',0);project=ctx.Array('c',80);request_hash=ctx.Array('c',65)
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*a):pass
   def do_POST(self):
    data=self.rfile.read(int(self.headers['Content-Length']))
    calls.value+=1;project.value=self.headers.get('OpenAI-Project','').encode();request_hash.value=p.digest(data).encode()
    assert self.path=='/v1/responses' and self.headers['Authorization']=='Bearer FICTIONAL-OPENAI-LOCAL-SECRET-ONLY'
    if mode=='missing':self.close_connection=True;return
    self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('openai-project','OTHER' if mode=='project' else p.PROJECT);self.send_header('Content-Length',str(1048577 if mode=='oversize' else len(raw)+(10 if mode=='truncated' else 0)));self.end_headers()
    try:self.wfile.write(raw[:20] if mode=='truncated' else b'{' if mode=='malformed' else raw);self.wfile.flush()
    except (OSError,ssl.SSLError):pass
    self.close_connection=True
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(self.root/'good.pem',self.root/'good.key');server.socket=context.wrap_socket(server.socket,server_side=True)
  process=ctx.Process(target=server.serve_forever);process.start();server.socket.close()
  self.addCleanup(lambda:(process.terminate(),process.join()))
  with evidence.original_evidence():fixture=g.kernel.SyntheticExecution(self.keys.trust)
  self.addCleanup(fixture.close);packet=self.packet();engine=g.PreparedEngine(fixture.fixture.directory,self.keys.trust,packet);packets=fake.scope(self.keys,fixture.fixture);engine.activate_synthetic_scope(packets,fake.NOW)
  permission=fake.execute(self.keys,fixture.fixture,packets)
  with engine.lock():
   _,facts,_,_=engine.state();packet['operationID']=g.q.q1.digest([engine.journal_hash,facts[0]['hash'],11,g.q.protocol.auth.digest(permission)])
  engine.packet=deepcopy(packet)
  transport=g.lab_transport(server.server_port,self.root/'good.pem',g.q.ServerSecretFD(self.secret_fd,'fictional-generation'),packet)
  return fixture,engine,permission,transport,calls,project,request_hash
 def run_case(self,f,point=None):
  # Guard every outbound socket; independent child inherits loopback guard.
  original=socket.socket.connect;port=g._BINDINGS[f[3]].port
  def loopback(sock,address):
   if address!=('127.0.0.1',port):raise AssertionError('No real provider peer')
   return original(sock,address)
  from unittest.mock import patch
  with patch.object(socket.socket,'connect',loopback):return g.supervise(f[1],f[2],f[3],fake.NOW,crash_at=point)
 def test_supervised_success_committed_reservation_capture_and_replay(self):
  f=self.fixture();report=self.run_case(f);d=f[0].fixture.directory
  self.assertEqual(report['workerExit'],0,json.loads((d/'generation-refusal.json').read_bytes()) if (d/'generation-refusal.json').exists() else report);self.assertEqual(report['childConservativeExposureNanodollars'],2500000);self.assertEqual(f[4].value,1);self.assertEqual(f[5].value.decode(),p.PROJECT);self.assertEqual(f[6].value.decode(),p.PAYLOAD_SHA)
  self.assertTrue(list(d.glob('raw-*')));self.assertTrue(list(d.glob('decoded-*')));self.assertTrue(list(d.glob('grading-*')))
  with self.assertRaises(FileExistsError):self.run_case(f)
  self.assertEqual(f[4].value,1)
 def test_financial_and_purpose_gates_refuse_before_reservation(self):
  f=self.fixture();original=deepcopy(f[1].packet)
  for key,value in [('project','OTHER'),('model','OTHER'),('payloadSHA256','b'*64),('technicalPurposeApproved',False),('writerEnrollmentApproved',False),('securityReviewApproved',False),('reservationNanodollars',0),('ownerOperationApproved',False),('premiumBps',None),('quotedMaximumNanodollars',1),('endpoint','https://example.com'),('sourceBuildSHA256','b'*64),('credentialIdentity','b'*64),('writerIdentity','b'*64),('operationID','b'*64)]:
   with self.subTest(key=key):
    f[1].packet=deepcopy(original);f[1].packet[key]=value
    with self.assertRaises((p.Refused,g.Denied)):self.run_case(f)
  self.assertEqual(len(p.journal_snapshot(f[0].fixture.directory)['rows']),10);self.assertEqual(f[4].value,0)
 def test_stale_missing_count_and_wrong_prices_refuse(self):
  f=self.fixture();original=deepcopy(f[1].packet)
  for name in ('modelEvidence','countEvidence','permissionEvidence','priceEvidence','authorization'):
   f[1].packet=deepcopy(original);f[1].packet[name]['expiresAt']=f[1].packet[name]['observedAt']
   with self.assertRaises((p.Refused,g.Denied)):self.run_case(f)
  for change in ('missing','prices','output'):
   f[1].packet=deepcopy(original)
   if change=='missing':del f[1].packet['countEvidence']
   elif change=='prices':f[1].packet['priceEvidence']['ratesNanoPerMillion']['output']=1
   else:f[1].packet['countEvidence']['inputTokens']=999999
   with self.assertRaises((p.Refused,g.Denied)):self.run_case(f)
  self.assertEqual(f[4].value,0)
 def test_payload_and_endpoint_substitution_refuse(self):
  f=self.fixture();f[3].payload=b'{}'
  with self.assertRaises(g.Denied):self.run_case(f)
  f[3].payload=p.payload();f[3].endpoint='/v1/models/gpt-6-luna'
  with self.assertRaises(g.Denied):self.run_case(f)
  self.assertEqual(f[4].value,0)
 def test_http_errors_preserve_full_charge_and_no_replay(self):
  for status in (400,401,403):
   with self.subTest(status=status):
    f=self.fixture(status=status,response={'error':{'type':'FICTIONAL'}});r=self.run_case(f)
    self.assertEqual(r['childConservativeExposureNanodollars'],2500000);self.assertEqual(f[4].value,1)
    with self.assertRaises(FileExistsError):self.run_case(f)
 def test_wrong_model_project_and_bad_responses_are_terminal(self):
  for mode in ('model','project','missing','malformed','truncated','oversize'):
   with self.subTest(mode=mode):
    response=deepcopy(self.responses[0]);response['model']='OTHER' if mode=='model' else p.MODEL
    f=self.fixture(mode=mode,response=response);r=self.run_case(f)
    self.assertEqual(r['childConservativeExposureNanodollars'],2500000);self.assertEqual(f[4].value,1)
    self.assertNotEqual(r['workerExit'],0)
    with self.assertRaises(FileExistsError):self.run_case(f)
 def test_crash_reservation_intent_and_uncertain_send_never_reset(self):
  for point in ('after_reserve','after_intent','after_send'):
   with self.subTest(point=point):
    f=self.fixture();r=self.run_case(f,point);self.assertEqual(r['workerExit'],73);self.assertEqual(r['childConservativeExposureNanodollars'],2500000)
    self.assertEqual(f[4].value,int(point=='after_send'))
    with self.assertRaises(FileExistsError):self.run_case(f)
 def test_real_constructor_and_unsigned_approvals_never_open(self):
  from unittest.mock import patch
  with patch('socket.socket',side_effect=AssertionError('No network')):
   for packet in (None,self.packet(),{'approved':True}):
    with self.assertRaises(g.Denied):g.PreparedTransport(packet)
 def test_source_identity_and_financial_boundary(self):
  self.assertEqual(g.identities(),g.verify_build()['loadedCodeIdentities'])
  self.assertEqual(p.quote(5704,p.RATES,{'tools':0,'separate_reasoning':0,'other_fees':0},0)['maximumNanodollars'],1969000)
  self.assertEqual(p.quote(5704,p.RATES,{'tools':0,'separate_reasoning':0,'other_fees':0},1000)['maximumNanodollars'],2165900)
  for args in [(5704,p.RATES,{'tools':0,'separate_reasoning':0,'other_fees':None},0),(5704,p.RATES,{'tools':0,'separate_reasoning':0,'other_fees':0},3000)]:
   with self.assertRaises(p.Refused):p.quote(*args)

 def test_no_unbound_wire_or_policy_globals(self):
  import dis,builtins,types
  def check(code,namespace):
   for ins in dis.get_instructions(code):
    if ins.opname=='LOAD_GLOBAL':self.assertTrue(ins.argval in namespace or hasattr(builtins,ins.argval),(code.co_name,ins.argval))
   for value in code.co_consts:
    if isinstance(value,types.CodeType):check(value,namespace)
  for _,(fn,namespace,_,_) in g.targets().items():check(fn.__code__,namespace)
 def test_competing_supervisors_cannot_both_send(self):
  f=self.fixture();ctx=multiprocessing.get_context('fork')
  def attempt():
   try:self.run_case(f)
   except (FileExistsError,g.Denied,BlockingIOError):os._exit(3)
  processes=[ctx.Process(target=attempt) for _ in range(2)]
  for proc in processes:proc.start()
  for proc in processes:proc.join(150)
  self.assertEqual(sorted(proc.exitcode for proc in processes),[0,3]);self.assertEqual(f[4].value,1)
 def test_attempted_second_slot_or_new_operation_refuses(self):
  f=self.fixture();f[1].packet['slot']=['openai','journey-04',2]
  with self.assertRaises((p.Refused,g.Denied)):self.run_case(f)
  self.assertEqual(f[4].value,0)
 def test_independent_fold_detects_prefix_change(self):
  f=self.fixture();d=f[0].fixture.directory;before=p.journal_snapshot(d)
  # Disposable fictional schema only. Protected real journal is never writable.
  with sqlite3.connect(d/'journal.sqlite') as db:db.execute('UPDATE attempts SET charge=charge+1 WHERE rowid=1');db.commit()
  with self.assertRaises(p.Refused):p.post_append(d,before,'none')

 def test_loaded_wire_substitution_refuses(self):
  from unittest.mock import patch
  with patch.object(g.PreparedTransport,'exchange',lambda *args:None):
   with self.assertRaises(g.code_identity.IdentityRefused):g.verify_build()
 def test_credential_echo_is_not_persisted_or_retried(self):
  response=deepcopy(self.responses[0]);response['FICTIONAL_echo']='FICTIONAL-OPENAI-LOCAL-SECRET-ONLY'
  f=self.fixture(response=response);result=self.run_case(f);self.assertNotEqual(result['workerExit'],0);self.assertEqual(result['childConservativeExposureNanodollars'],2500000)
  for path in f[0].fixture.directory.glob('raw-*'):self.assertNotIn(b'FICTIONAL-OPENAI-LOCAL-SECRET-ONLY',path.read_bytes())
  with self.assertRaises(FileExistsError):self.run_case(f)

 def test_independent_supervisor_restart_after_intent_refuses(self):
  f=self.fixture();before=self.run_case(f,'after_intent')
  self.assertEqual(before['workerExit'],73);self.assertEqual(f[4].value,0)
  def restart():
   try:self.run_case(f)
   except (FileExistsError,g.Denied,BlockingIOError):os._exit(0)
   os._exit(99)
  proc=multiprocessing.get_context('fork').Process(target=restart);proc.start();proc.join(130)
  if proc.is_alive():proc.kill();proc.join();self.fail('Restart refusal deadline')
  self.assertEqual(proc.exitcode,0);self.assertEqual(f[4].value,0)
  rows=p.journal_snapshot(f[0].fixture.directory)['rows'];self.assertEqual(rows[10][5],2500000)
