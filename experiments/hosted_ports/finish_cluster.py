"""Versioned closed-entry verification using the existing seven role composition."""
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
import json,subprocess,time,hashlib,inspect,marshal
from experiments.hosted_ports.native_cluster import Cluster
from experiments.hosted_ports.fault_contract import assert_state,EXPECTED
class FinishCluster(Cluster):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs)
  evidence=Path(__import__('os').environ['TASK52_PINNED_EVIDENCE']);manifest=json.loads((evidence/'run-manifest.json').read_text());roles=(evidence/'role-images.json').read_bytes()
  if hashlib.sha256(roles).hexdigest()!=manifest['roleImagesSHA256'] or self.images!=json.loads(roles):raise RuntimeError('Pinned image inventory changed')
  self.images=json.loads(roles)
 def configuration(self,name):
  role,c=super().configuration(name);c['identityEnvironment']='private-staging';c['localFixtureIdentity']='52-closed-frontend-local-v1';return role,c
 def start(self,name):
  original=Path.read_bytes
  def bootstrap(p):return original(Path('experiments/hosted_ports/finish_start_role.py')) if str(p)=='experiments/hosted_ports/start_role.py' else original(p)
  with patch.object(Path,'read_bytes',bootstrap):return super().start(name)
 def probe(self):
  # Private local transcript: exact generated fixture config, never committed.
  self.evidence=Path(__import__('os').environ['TASK52_PINNED_EVIDENCE']);self.evidence.mkdir(exist_ok=True,mode=0o700)
  p=self.evidence/'sealed-generated-inputs.json';p.write_text(json.dumps({'original':self.private,'roleConfigurations':{p.parent.name:json.loads(p.read_text()) for p in self.root.glob('*/config.json')},'cohort':self.cohort}));p.chmod(0o600)
  for c in self.configs.values():c['identityEnvironment']='private-staging'
  return super().probe()
 def bootstrap_volume(self,directory,uid=0):
  import secrets
  volume='whereto-finish-'+secrets.token_hex(10);self.run(['volume','create',volume],stdout=subprocess.DEVNULL);self.volumes.append(volume)
  helper=self.output(['run','-d','--platform','linux/amd64','--network','none','--user','0:0','--mount','type=volume,src='+volume+',dst=/material','--entrypoint','sleep',self.images['counter']['id'],'60'],text=True).strip()
  try:
   self.run(['cp',str(directory)+'/.',helper+':/material/']);self.run(['exec',helper,'python','-c',"import pathlib,os;root=pathlib.Path('/material');\nfor p in root.rglob('*'):\n os.chown(p,"+str(uid)+","+str(uid)+");os.chmod(p,0o555 if p.is_dir() else 0o444)"])
  finally:subprocess.run(self.D+['rm','-fv',helper],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  return volume
 def closed_frontend(self):
  from experiments.ordinary_network.fixture import Fixture
  from experiments.shared_state.run_grants import BACKEND
  from hashlib import sha256
  images=json.loads(Path(__import__('os').environ['TASK52_CLOSED_IMAGES']).read_text());front=images['fixture'];assert front['FIXTURE'] is True and front['manifest']['cohort']==self.cohort
  c=self.configs['frontend'];identity=self.certificate('identity',['identity.task52.invalid']);(identity/'metadata.json').write_text(json.dumps({'workload':c['googleKeys']['workload'],'iap':c['googleKeys']['iap'],'audience':c['audiences']['backend'],'token':c['oidcTokens'][c['audiences']['backend']]}));(identity/'identity_server.py').write_bytes(Path('experiments/hosted_ports/identity_server.py').read_bytes())
  volume=self.bootstrap_volume(identity,10001)
  d=json.loads(self.output(['inspect',self.private['roles']['worker-a']],text=True))[0];mount=next(x['Name'] for x in d['Mounts'] if x['Destination']=='/app')
  md=self.output(['run','-d','--platform','linux/amd64','--network',self.network,'--network-alias','identity.task52.invalid','--read-only','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','128m','--cpus','.25','--mount','type=volume,src='+volume+',dst=/identity,readonly','--mount','type=volume,src='+mount+',dst=/app,readonly','-e','PYTHONPATH=/app/_deps:/app','--entrypoint','python',BACKEND,'/identity/identity_server.py'],text=True).strip();self.extras.append(md)
  secrets=self.root/'frontend-secrets';secrets.mkdir()
  config={'version':'52-closed-private-frontend-v1','origin':'https://frontend-task52-offline.run.app','backendEndpoint':'https://backend-a.task52.invalid:8080','backendAudience':c['audiences']['backend'],'iapAudience':c['iapAudience'],'serviceSubject':c['enrollment']['frontend']['sub'],'serviceEmail':c['enrollment']['frontend']['email'],'testers':c['testers'],'build':self.cohort,'environment':'private-staging','epoch':c['epoch'],'signingKey':c['signingKey']}
  raw=(json.dumps(config,separators=(',',':'))+'\n').encode();(secrets/'whereto-frontend.json').write_bytes(raw)
  (secrets/'whereto-frontend-enrollment.json').write_text(json.dumps({'version':'52-private-frontend-enrollment-v1','artifact':front['PIN'],'configurationSHA256':sha256(raw).hexdigest(),'purpose':'private-synthetic-ordinary-only','publicTraffic':False,'financialAuthorization':False}))
  (secrets/'local-fixture-ca.crt').write_bytes((self.root/'cert.pem').read_bytes());volume=self.bootstrap_volume(secrets)
  frontend=self.output(['run','-d','--platform','linux/amd64','--network',self.network,'--network-alias','network-frontend.task52.invalid','--read-only','--user','1000:1000','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','512m','--cpus','1','--mount','type=volume,src='+volume+',dst=/run/secrets,readonly','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=32m,uid=1000,gid=1000,mode=0700',front['id']],text=True).strip();self.extras.append(frontend)
  # Existing independent fake IAP edge; frontend receives no signer or controller.
  fixture=Fixture.__new__(Fixture);fixture.D=self.D;fixture.temp=self.root;fixture.image=BACKEND;fixture.mount=mount;fixture.network=self.network;fixture.processes=[];fixture.helpers=self.extras;fixture.volumes=self.volumes;fixture.ingress=None
  (self.root/'iap.pem').write_text(self.private['fixtureSigners']['iap']);(self.root/'iap.pem').chmod(0o600)
  (self.root/'iap.json').write_text(json.dumps({'alice':{'claims':dict(iss='https://cloud.google.com/iap',aud=c['iapAudience'],sub='accounts.google.com:synthetic-alice',email='alice@example.invalid'),'headers':{'kid':'task52-offline-iap'}}}));(self.root/'iap.json').chmod(0o600)
  fixture.start_ingress(None);self.frontend=frontend;return fixture.browser_url
 def browser(self):
  url=self.closed_frontend();done=self.root/'browser-done';Path('/tmp/task52-finish-browser.json').write_text(json.dumps({'url':url,'finishSignal':str(done),'cohort':self.cohort}))
  print('CLOSED_FRONTEND_BROWSER_AVAILABLE',flush=True)
  for _ in range(600):
   if done.exists():return self.probe_crash()
   time.sleep(1)
  raise RuntimeError('Bounded closed frontend browser window ended')
 def probe_crash(self):
  # Record actual loaded assertion code, not a traceback's mutable linecache view.
  code={'source':inspect.getsource(assert_state),'bytecodeSHA256':hashlib.sha256(marshal.dumps(assert_state.__code__)).hexdigest(),'expected':EXPECTED,'operationScenario':'committed reservation and INTENT, before owner callback/delivery','cohort':self.cohort}
  (self.evidence/'loaded-assertion.json').write_text(json.dumps(code,indent=2))
  dispatcher=self.containers['dispatcher'];factory=self.containers['factory-r1'];process=None
  self.run(['exec',dispatcher,'python','-c',"from pathlib import Path;Path('/tmp/block-next-send').write_text('timing barrier')"])
  self.write_control("import json;from pathlib import Path;p=Path('/tmp/native-probe-control.json');v=json.loads(p.read_text());v['onlyInitial']=True;p.write_text(json.dumps(v))")
  try:
   process=subprocess.Popen(self.D+['exec',self.private['client'],'python','/tmp/application_probe.py'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
   op=None
   for _ in range(100):
    r=subprocess.run(self.D+['exec',dispatcher,'cat','/tmp/reserved-operation.json'],capture_output=True,text=True)
    if not r.returncode:op=json.loads(r.stdout)['operation'];break
    if process.poll() is not None:raise RuntimeError('Operation refused before committed barrier')
    time.sleep(.1)
   if op is None:raise RuntimeError('No committed barrier')
   from uuid import UUID
   assert str(UUID(op))==op
   statement="SELECT jsonb_build_object('operation',to_jsonb(o),'facts',(SELECT jsonb_agg(to_jsonb(f) ORDER BY sequence) FROM synthetic_state.facts f WHERE operation=o.id),'financialDispatch',(SELECT jsonb_agg(to_jsonb(d) ORDER BY ordinal) FROM synthetic_state.financial_dispatch d WHERE operation=o.id),'deliveries',(SELECT count(*) FROM synthetic_state.app_witness_facts WHERE id='deliver:'||o.id::text||':1')) FROM synthetic_state.operations o WHERE id=%s"
   def snapshot(label):
    query="import json;from experiments.shared_state.test_store import admin\nwith admin() as c:print(json.dumps(c.execute("+repr(statement)+",("+repr(op)+",)).fetchone()[0]))"
    value=json.loads(self.write_control(query));(self.evidence/(label+'.json')).write_text(json.dumps(value,indent=2));return value
   def triple(v):return (v['operation']['charge'],sum(x['kind']=='INTENT' for x in v['facts']),v['deliveries'])
   before=snapshot('before-interruption');assert tuple(triple(before))==EXPECTED
   oldboot=self.output(['exec',factory,'cat','/tmp/factory-boot.json'],text=True).strip()
   payload=self.output(['exec',dispatcher,'cat','/tmp/reserved-request.json'],text=True);private=self.evidence/'sealed-dispatch-request.json';private.write_text(payload);private.chmod(0o600)
   self.run(['kill','--signal','KILL',factory],stdout=subprocess.DEVNULL);self.run(['exec',dispatcher,'python','-c',"from pathlib import Path;Path('/tmp/block-next-send').unlink()"])
   stdout,stderr=process.communicate(timeout=40)
   if process.returncode or json.loads(stdout)['status']==200:raise RuntimeError('Interrupted request accepted')
   self.run(['start',factory],stdout=subprocess.DEVNULL)
   for _ in range(40):
    r=subprocess.run(self.D+['exec',factory,'cat','/tmp/factory-boot.json'],capture_output=True,text=True)
    if not r.returncode and r.stdout.strip()!=oldboot:break
    time.sleep(.1)
   else:raise RuntimeError('Replacement boot not established')
   # Use a fresh proof from the same trusted role, but the consumed old action.
   target='/tmp/old-request.json';self.run(['exec','-i',factory,'python','-c',"import os,sys;f=os.open('/tmp/old-request.json',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.write(f,sys.stdin.buffer.read());os.close(f)"],input=payload.encode())
   attempt="import sys,json;sys.path.insert(0,'/tests');from start_role import FixtureIdentity;from private_runtime.service_client import ServiceClient;from private_runtime.https import HTTPS;from experiments.shared_state.contracts import Denied,Unavailable\nc=json.load(open('/tests/config.json'))\ntry:ServiceClient(c,FixtureIdentity(c),HTTPS(ca_file='/tests/ca.crt')).request('dispatcher','/send',json.load(open('/tmp/old-request.json')))\nexcept (Denied,Unavailable):print('old_action_refused')\nelse:raise RuntimeError('Old action accepted')"
   r=self.output(['exec',factory,'python','-c',attempt],text=True);assert r.strip()=='old_action_refused'
   after=snapshot('after-restart-and-replay');assert_state(triple(before),triple(after));assert before==after
   result=dict(cohort=self.cohort,before=triple(before),after=triple(after),newBoot=True,oldActionRefused=True,financialStateUnchanged=True,loadedAssertion=code)
   (self.evidence/'fault-result.json').write_text(json.dumps(result,indent=2));print('PINNED_POST_BROWSER_FAULT_PASS',flush=True)
  finally:
   subprocess.run(self.D+['exec',dispatcher,'python','-c',"from pathlib import Path;Path('/tmp/block-next-send').unlink(missing_ok=True)"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   if process is not None and process.poll() is None:process.terminate();process.wait(timeout=5)
