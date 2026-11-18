"""Explicit source-pinned offline harness; full historical COPY, fictional keys."""
import unittest
OPT_IN=__name__=='_task52b_original_enrollment_tests'
if OPT_IN:
 from pathlib import Path
 from datetime import datetime,timezone,timedelta
 from contextlib import closing
 from copy import deepcopy
 from unittest.mock import patch
 import json,os,tempfile,sqlite3,uuid,fcntl,multiprocessing,socket,ssl
 import _task52b_first_slot_tests as old
 from scripts import task52b_original_journal as j
 from scripts import task52b_real_enrollment as a
 from scripts import task52b_enrolled_transport as w
 from scripts import task52b_generation_policy as p
 from scripts import task52b_generation_candidate as g
 from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler

@unittest.skipUnless(OPT_IN,'Explicit frozen-source original-enrollment driver required')
class OriginalEnrollmentTests(unittest.TestCase):
 setUpClass=classmethod(old.FirstSlotTests.setUpClass.__func__) if OPT_IN else classmethod(lambda cls:None)
 tearDownClass=classmethod(old.FirstSlotTests.tearDownClass.__func__) if OPT_IN else classmethod(lambda cls:None)
 def packet(self):
  now=a.now();end=min(now+timedelta(hours=1),now.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1));stamp={'observedAt':now.isoformat(),'expiresAt':end.isoformat()}
  out={'project':p.PROJECT,'model':p.MODEL,'slot':p.SLOT,'operation':p.OPERATION,'payloadSHA256':p.PAYLOAD_SHA,'countSHA256':p.COUNT_SHA,'endpoint':p.ENDPOINT,'method':'POST','operationMaximum':1,'retries':0,'planningAuthorized':False,'semanticReview':'deferred','independentlyCorrect':None,'reservationNanodollars':p.CEILING,'fictionalOnly':True,'quotedMaximumNanodollars':1969000,'extraFeesNanodollars':{'tools':0,'separate_reasoning':0,'other_fees':0},'premiumBps':0}
  for k in ('ownerOperationApproved','technicalPurposeApproved','securityReviewApproved','writerEnrollmentApproved','independentPostAppendVerifier','accountTermsAndFeesApproved','modelAliasDiagnosticApproved'):out[k]=True
  for k in ('operationID','credentialIdentity','countBundleSHA256','modelGETBundleSHA256','writerIdentity'):out[k]='a'*64
  out['sourceBuildSHA256']=j.build_sha();out['writerIdentity']=json.loads(g.MANIFEST.read_bytes())['loadedCodeIdentities']['writer']
  for name in ('modelEvidence','countEvidence','permissionEvidence','priceEvidence','authorization'):out[name]=deepcopy(stamp)
  out['countEvidence'].update(inputTokens=5704,generationSHA256=p.PAYLOAD_SHA,countSHA256=p.COUNT_SHA);out['priceEvidence']['ratesNanoPerMillion']=deepcopy(p.RATES)
  return out
 def fixture(self,status=200,mode='ok'):
  temp=tempfile.TemporaryDirectory(prefix='whereto-original-copy-');self.addCleanup(temp.cleanup);d=Path(temp.name).resolve();os.chmod(d,0o700)
  # Read ONLY canonical original journal under its ORIGINAL lock. No write/create
  # of WAL, replacement history or copied private provider records.
  lock=os.open(a.ORIGINAL/'experiment.lock',os.O_RDONLY|os.O_NOFOLLOW)
  try:
   fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
   raw=(a.ORIGINAL/'journal.sqlite').read_bytes()
   self.assertEqual(p.digest(raw),'241af59ffa81553c98feb1e093c75194d908191504a9e67a6ad16fcc13e49028')
   self.write(d/'journal.sqlite',raw);self.write(d/'experiment.lock',b'FICTIONAL COPY LOCK')
  finally:os.close(lock)
  child=Path(tempfile.mkdtemp(prefix='whereto-child-copy-')).resolve();os.chmod(child,0o700);self.addCleanup(lambda:__import__('shutil').rmtree(child))
  cr=d/'fixture';(cr/'backend').mkdir(parents=True,mode=0o700)
  key=cr/'backend/.env.cloud-evaluation.openai-replacement-FICTIONAL';self.write(key,('OPENAI_API_KEY='+'sk-proj-'+('FICTIONAL'*6)+'\nDO_NOT_READ=FICTIONAL\n').encode());st=key.stat()
  meta={'projectId':p.PROJECT,'projectName':'WhereTo Model Evaluation','credentialFile':str(key),'trackingId':'FICTIONAL','permissions':{'listModels':'Read','responses':'Read','unrelated':'None'},'expiresOn':'2099-01-01'}
  mp=key.with_name(key.name+'.metadata.json');self.write(mp,json.dumps(meta).encode())
  cred={'metadataPath':str(mp),'credentialPath':str(key),'trackingId':'FICTIONAL','credentialDevice':st.st_dev,'credentialInode':st.st_ino,'credentialSize':st.st_size,'credentialMtimeNS':st.st_mtime_ns}
  cp=d/'credential.json';self.write(cp,json.dumps(cred).encode())
  trust={'version':a.VERSION,'fixtureOnly':True,'roles':{r:{'principal':'q4c-'+r,'key':self.keys.public['reviewer' if r=='security' else r]} for r in ('owner','security','operator')},'journal':str(d/'journal.sqlite'),'lock':str(d/'experiment.lock'),'facts':str(child),'authority':str(d/'authority.json'),'credentialEnrollment':str(cp),'credentialMetadataSHA256':p.digest(mp.read_bytes()),'epoch':'e'*64,'minimumSequence':1}
  snap=p.journal_snapshot(d)
  with closing(sqlite3.connect('file:'+str(d/'journal.sqlite')+'?mode=ro',uri=True)) as db:root=db.execute('SELECT config FROM metadata').fetchone()[0]
  marker={'scope':uuid.uuid4().hex+uuid.uuid4().hex,'root':a.digest(root),'prefix':[a.digest(row) for row in snap['rows']],'prefixHash':j.PREFIX}
  financial=self.packet();financial['credentialIdentity']=p.digest(cp.read_bytes())
  spec={'sourceBuildSHA256':j.build_sha(),'scope':marker['scope'],'journalHash':a.digest({'root':marker['root'],'prefix':marker['prefix']}),'journalIdentity':a.file_identity(d/'journal.sqlite'),'lockIdentity':a.file_identity(d/'experiment.lock'),'marker':marker,'epoch':trust['epoch'],'financialPacket':financial,'credentialIdentity':financial['credentialIdentity'],'credentialEnrollmentSHA256':p.stable(cred),'fixtureCredentialRoot':str(cr),'processingCategories':{'serviceTier':'default','cache12hRequested':False,'toolsRequested':False,'separateReasoningFees':False,'otherFeesKnown':True}}
  package={'fixtureOnly':True,'spec':spec,'packets':{}}
  bh=p.stable(spec);at=a.now().replace(microsecond=0);end=min(at+timedelta(hours=1),at.replace(hour=0,minute=0,second=0)+timedelta(days=1))
  def sign(role,data):
   group='security' if role=='authority' else a.GROUP[role];ns='whereto.task52b.original-firstslot.'+role+'.v1'
   e={'version':a.VERSION,'audience':'52b-original-firstslot-LAB','purpose':a.PURPOSE,'role':role,'principal':trust['roles'][group]['principal'],'namespace':ns,'scope':spec['scope'],'journal':spec['journalHash'],'nonce':uuid.uuid4().hex+uuid.uuid4().hex,'issuedAt':a.utc(at),'expiresAt':a.utc(end),'trustHash':p.stable(trust),'bindingHash':bh,'data':data}
   return self.keys.sign_bytes(a.canonical(e),role,signer='reviewer' if group=='security' else group,namespace=ns)
  self.write(d/'authority.json',json.dumps(sign('authority',{'epoch':trust['epoch'],'sequence':1,'revokedKeyHashes':[]})).encode())
  packets=package['packets']
  packets['owner']=sign('owner',{'bindingHash':bh,'technicalPurposeApproved':True,'reservationMaximum':2500000,'operationMaximum':1,'semanticReview':'deferred','planningAuthorized':False})
  packets['rubric']=sign('rubric',{'bindingHash':bh,'independentSecurityApproved':True,'realWriterApproved':True,'postAppendApproved':True,'semanticReview':'deferred','planningAuthorized':False})
  packets['readiness_permission']=sign('readiness_permission',{'bindingHash':bh,'additionalReadinessRequests':0})
  packets['readiness']=sign('readiness',{'bindingHash':bh,'permissionHash':a.digest(packets['readiness_permission']),'accountTermsAndFeesReviewed':True,'modelAliasCountApplicabilityReviewed':True})
  packets['execute']=sign('execute',{'slot':p.SLOT,'sourceHash':g.q.identity.requests()[0]['sourceSHA256'],'payloadHash':p.PAYLOAD_SHA,'inputBound':7752,'outputBound':2000,'reservation':2500000,'ownerHash':a.digest(packets['owner']),'readinessHash':a.digest(packets['readiness']),'previousReviewHash':'0'*64})
  receipt=a.enroll_fixture(trust,package);engine=j.OriginalEngine(receipt);engine.activate_scope()
  ctx=multiprocessing.get_context('fork');calls=ctx.Value('i',0);response=deepcopy(self.responses[0]);raw=json.dumps(response).encode()
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_POST(self):
    body=self.rfile.read(int(self.headers['Content-Length']));calls.value+=1
    assert body==p.payload() and self.path=='/v1/responses'
    assert self.headers['Authorization']=='Bearer '+'sk-proj-'+('FICTIONAL'*6)
    if mode=='missing':self.close_connection=True;return
    self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw if mode!='malformed' else b'{');self.close_connection=True
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);sc=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);sc.load_cert_chain(self.root/'good.pem',self.root/'good.key');server.socket=sc.wrap_socket(server.socket,server_side=True)
  proc=ctx.Process(target=server.serve_forever);proc.start();server.socket.close();self.addCleanup(lambda:(proc.terminate(),proc.join()))
  transport=w.fixture_transport(receipt,server.server_port,self.root/'good.pem')
  return engine,transport,calls,sign,package,trust
 def write(self,path,raw):
  fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  try:os.write(fd,raw);os.fsync(fd)
  finally:os.close(fd)
 def run_case(self,f,crash=None):
  original=socket.socket.connect;port=w.binding(f[1]).port
  def local(sock,address):
   if address!=('127.0.0.1',port):raise AssertionError('No remote endpoint in offline test')
   return original(sock,address)
  with patch.object(socket.socket,'connect',local):return j.supervise(f[0],f[1],crash=crash)
 def test_success_original_prefix_separate_facts_and_replay(self):
  f=self.fixture();r=self.run_case(f)
  refusal=f[0].directory/'refusal.json'
  self.assertEqual(r['workerExit'],0,refusal.read_text() if refusal.exists() else r)
  self.assertEqual(r['childExposureNanodollars'],2500000);self.assertEqual(f[2].value,1)
  self.assertNotEqual(f[0].directory,f[0].receipt.journal.parent)
  self.assertEqual(len(list(f[0].directory.glob('grading-*'))),1)
  self.assertNotEqual(p.digest(f[0].receipt.journal.read_bytes()),'241af59ffa81553c98feb1e093c75194d908191504a9e67a6ad16fcc13e49028')
  with self.assertRaises((j.Denied,FileExistsError)):self.run_case(f)
  self.assertEqual(f[2].value,1)
 def test_crashes_and_worker_replacement(self):
  for point in ('before_start','before_reserve','before_commit','after_reserve','after_intent','after_send','after_outcome'):
   with self.subTest(point=point):
    f=self.fixture();r=self.run_case(f,point);self.assertEqual(r['workerExit'],73)
    self.assertEqual(r['childExposureNanodollars'],0 if point in ('before_start','before_reserve','before_commit') else 2500000)
    self.assertEqual(f[2].value,int(point in ('after_send','after_outcome')))
    with self.assertRaises((j.Denied,FileExistsError)):self.run_case(f)
 def test_terminal_http_and_capture_failure(self):
  for status,mode in ((400,'ok'),(401,'ok'),(403,'ok'),(200,'missing'),(200,'malformed')):
   with self.subTest(status=status,mode=mode):
    f=self.fixture(status,mode);r=self.run_case(f);self.assertEqual(r['childExposureNanodollars'],2500000);self.assertEqual(f[2].value,1)
    with self.assertRaises((j.Denied,FileExistsError)):self.run_case(f)
 def test_signed_binding_mutations_and_closed_real_entry(self):
  f=self.fixture()
  for field,value in (('epoch','f'*64),('credentialIdentity','b'*64),('sourceBuildSHA256','b'*64)):
   package=deepcopy(f[4]);package['spec'][field]=value
   with self.assertRaises((j.Denied,p.Refused)):a.enroll_fixture(f[5],package)
  with self.assertRaises(j.Denied):a.enroll_real()
  with self.assertRaises(j.Denied):w.EnrolledTransport()
  self.assertEqual(f[2].value,0)
 def test_concurrent_operators(self):
  f=self.fixture();ctx=multiprocessing.get_context('fork')
  def attempt():
   try:self.run_case(f)
   except (j.Denied,FileExistsError):os._exit(3)
  procs=[ctx.Process(target=attempt) for _ in range(2)]
  for proc in procs:proc.start()
  for proc in procs:proc.join(150)
  self.assertEqual(sorted(proc.exitcode for proc in procs),[0,3]);self.assertEqual(f[2].value,1)
 def test_prefix_tamper_and_original_path_refusal(self):
  f=self.fixture()
  with sqlite3.connect(f[0].receipt.journal) as db:db.execute('UPDATE attempts SET charge=charge+1 WHERE rowid=1');db.commit()
  with self.assertRaises(j.Denied):j.independent_verify(f[0])
  trust=deepcopy(f[5]);trust['journal']=str(a.ORIGINAL/'journal.sqlite');trust['lock']=str(a.ORIGINAL/'experiment.lock')
  with self.assertRaises(j.Denied):a.enroll_fixture(trust,f[4])
 def test_loaded_code_and_unknown_cost_refusal(self):
  with patch.object(w.EnrolledTransport,'exchange',lambda *args:None):
   with self.assertRaises((g.code_identity.IdentityRefused,j.Denied)):j.verify_build()
  with self.assertRaises(p.Refused):p.quote(5704,p.RATES,{'tools':0,'separate_reasoning':0,'other_fees':None},0)

 def test_sql_surface_and_canonical_identity(self):
  f=self.fixture();engine=f[0]
  with self.assertRaises(j.Denied):engine.db()
  with engine.lock():
   with closing(engine.db()) as db:
    for sql in ('DELETE FROM attempts','UPDATE attempts SET charge=0','CREATE TABLE unsafe(x)'):
     with self.assertRaises(j.Denied):db.execute(sql)
    with self.assertRaises(j.Denied):db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?)',('google','journey-04',2,'reserved_uncertain',0,'{}'))
  self.assertEqual(len(p.journal_snapshot(engine.receipt.journal.parent)['rows']),10)
  oldlock=engine.receipt.lock;oldlock.rename(oldlock.with_name('retained-lock'))
  self.write(oldlock,b'FICTIONAL replacement inode')
  with self.assertRaises(j.Denied):j.OriginalEngine(engine.receipt)
 def test_credential_metadata_and_source_substitution_refuse(self):
  f=self.fixture();receipt=f[0].receipt;loader=w.credential_loader(receipt)
  cred=json.loads(a.private(Path(receipt.trust['credentialEnrollment'])))
  # Metadata validation stats the fictional key but never opens its bytes.
  self.assertEqual(loader['metadata'](cred,receipt.trust['credentialMetadataSHA256']),Path(cred['credentialPath']))
  changed=deepcopy(cred);changed['credentialInode']+=1
  with self.assertRaises(j.Denied):loader['metadata'](changed,receipt.trust['credentialMetadataSHA256'])
  with patch.object(w,'_SingleDial',object):
   with self.assertRaises(j.Denied):j.verify_build()
  with patch.object(j,'_state',lambda *args:None):
   with self.assertRaises(j.Denied):j.verify_build()
 def test_unsigned_approval_stale_evidence_and_additional_diagnostic(self):
  f=self.fixture();package=deepcopy(f[4]);package['packets']['owner']['envelope']=package['packets']['owner']['envelope'].replace('2500000','1')
  with self.assertRaises(j.Denied):a.enroll_fixture(f[5],package)
  packet=self.packet()
  for name in ('modelEvidence','countEvidence','permissionEvidence','priceEvidence','authorization'):
   changed=deepcopy(packet);changed[name]['expiresAt']=changed[name]['observedAt']
   with self.assertRaises(p.Refused):p.validate_packet(changed,a.now(),expected_build=j.build_sha())
  for key,value in (('slot',['openai','journey-04',2]),('ownerOperationApproved',False),('premiumBps',None),('quotedMaximumNanodollars',0),('endpoint','https://example.com')):
   changed=deepcopy(packet);changed[key]=value
   with self.assertRaises(p.Refused):p.validate_packet(changed,a.now(),expected_build=j.build_sha())
  self.assertEqual(f[2].value,0)
 def test_crash_before_response_capture_retains_full_reservation(self):
  f=self.fixture();old=w.binding(f[1]);transport=w.fixture_transport(old.receipt,old.port,self.root/'good.pem',crash=True)
  f=(f[0],transport,*f[2:]);result=self.run_case(f)
  self.assertEqual(result['workerExit'],73);self.assertEqual(result['childExposureNanodollars'],2500000);self.assertEqual(f[2].value,1)
  self.assertFalse(list(f[0].directory.glob('raw-*')))
  with self.assertRaises((j.Denied,FileExistsError)):self.run_case(f)
