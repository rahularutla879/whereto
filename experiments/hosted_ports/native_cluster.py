"""Disposable private bridge and per-role injected fixture data. No host mounts."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json,subprocess,secrets,os,time
from copy import deepcopy
from experiments.shared_state.contracts import Denied

class Cluster:
 def __init__(self,D,private,root):
  self.D=D;self.private=private;self.root=Path(root);self.containers={};self.extras=[];self.volumes=[];self.network='whereto-native-ports-'+secrets.token_hex(8)
  self.images=json.loads(Path('/tmp/continuation-private-images.json').read_text());self.cohort=None
 def run(self,args,**kw):return subprocess.run(self.D+args,check=True,**kw)
 def output(self,args,**kw):return subprocess.check_output(self.D+args,**kw)
 def write_control(self,code):
  result=subprocess.run(self.D+['exec',self.private['client'],'python','-c',code],capture_output=True,text=True)
  if result.returncode:
   # Never interpolate private control code or credentials into exception output.
   reason=next((line.split(':')[0] for line in reversed(result.stderr.splitlines()) if 'Error:' in line or 'Exception:' in line),'control_refused')
   raise RuntimeError('Synthetic control refused: '+reason)
  return result.stdout
 def init(self):
  for c in self.private['roles'].values():subprocess.run(self.D+['stop','--time','2',c],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  self.cohort=self.run(['run','--rm','--platform','linux/amd64','--network','none','--entrypoint','python',self.images['factory']['id'],'-c','from private_runtime.image_identity import verify;print(verify())'],text=True,capture_output=True).stdout.strip()
  # Begin a NEW fictional dataset, only before any operation. Never reset recovery state.
  code="""import json
from pathlib import Path
from unittest.mock import patch
from experiments.shared_state import test_native_sessions as n,test_store as t,test_application_grants as g
from experiments.service_isolation.auth import unb64
p=json.load(open('/tmp/ports-control.json'))
with t.admin() as c:assert c.execute('SELECT count(*) FROM synthetic_state.operations').fetchone()[0]==0;c.execute('DROP SCHEMA private_runtime CASCADE')
with g.witness_admin() as c:c.execute('DROP SCHEMA private_runtime CASCADE')
with patch.object(t,'KEY',unb64(p['configs']['factory']['hashKey'])):n.fixture()
with t.admin() as c:
 c.execute('SET LOCAL ROLE whereto_synthetic_owner');c.execute(Path('/app/experiments/service_isolation/protocol.sql').read_text(),prepare=False)
 c.execute('INSERT INTO synthetic_state.service_profile VALUES(1,%s,%s)',(COHORT,g.EPOCH))
 c.execute(Path('/app/experiments/ordinary_ui/readiness.sql').read_text(),prepare=False)
with g.witness_admin() as c:
 c.execute('SET LOCAL ROLE whereto_synthetic_owner');c.execute(Path('/app/experiments/service_isolation/witness.sql').read_text(),prepare=False);c.execute(Path('/app/experiments/hosted_identity/nonce.sql').read_text(),prepare=False);c.execute(Path('/app/experiments/ordinary_ui/witness_readiness.sql').read_text(),prepare=False)
from experiments.hosted_ports.test_connections import Tests
Tests.setUpClass();Path('/tmp/native-contracts.json').write_text(json.dumps(Tests.contracts))
""".replace('COHORT',repr(self.cohort))
  self.write_control(code)
  self.contracts=json.loads(self.write_control("from pathlib import Path;print(Path('/tmp/native-contracts.json').read_text())"))
  self.make_secondary()
  self.run(['network','create','--opt','com.docker.network.bridge.enable_ip_masquerade=false',self.network],stdout=subprocess.DEVNULL)
  self.run(['network','disconnect','none',self.private['stores']['postgres']])
  self.run(['network','connect','--alias','postgres.task52.invalid','--alias','witness.task52.invalid','--alias','redis.task52.invalid',self.network,self.private['stores']['postgres']])
  self.database_certificates()
  self.redis_acl()
  for name in ('counter','recovery','dispatcher','factory-r1','factory-r2','backend-a','backend-b'):self.start(name)
  return self
 def make_secondary(self):
  code="""import json,time
from pathlib import Path
from copy import deepcopy
import jwt
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from experiments.service_isolation.auth import b64
p=json.load(open('/tmp/ports-control.json'));a=deepcopy(p['configs']['factory']);k=ed25519.Ed25519PrivateKey.generate();principal='factory-secondary'
a['principal']=principal;a['signingKey']=b64(k.private_bytes(serialization.Encoding.Raw,serialization.PrivateFormat.Raw,serialization.NoEncryption()))
trust=deepcopy(a['trust']);trust[principal]={'role':'factory','publicKey':b64(k.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw))}
enrollment=deepcopy(a['enrollment']);enrollment[principal]={'sub':'10000000000000000999','email':'factory-secondary@offline-project.iam.gserviceaccount.com'}
now=int(time.time());own=enrollment[principal];a['oidcTokens']={aud:jwt.encode(dict(iss='https://accounts.google.com',aud=aud,sub=own['sub'],email=own['email'],email_verified=True,iat=now,exp=now+3600),p['fixtureSigners']['workload'],algorithm='RS256',headers={'kid':'task52-offline-workload'}) for aud in a['audiences'].values()}
a['trust']=trust;a['enrollment']=enrollment
print(json.dumps({'secondary':a,'trust':trust,'enrollment':enrollment}))
"""
  data=json.loads(self.write_control(code));self.configs=deepcopy(self.private['configs']);self.configs['factory-secondary']=data['secondary']
  for c in self.configs.values():c['trust']=data['trust'];c['enrollment']=data['enrollment']
 def certificate(self,name,hostnames):
  directory=self.root/name;directory.mkdir(exist_ok=True)
  self.run_openssl(['req','-new','-newkey','rsa:2048','-nodes','-keyout',str(directory/'server.key'),'-out',str(directory/'server.csr'),'-subj','/CN='+name])
  (directory/'extensions').write_text('subjectAltName='+','.join('DNS:'+h for h in hostnames)+'\nbasicConstraints=critical,CA:FALSE\n')
  self.run_openssl(['x509','-req','-in',str(directory/'server.csr'),'-CA',str(self.root/'cert.pem'),'-CAkey',str(self.root/'key.pem'),'-CAcreateserial','-out',str(directory/'server.crt'),'-days','1','-extfile',str(directory/'extensions')])
  (directory/'server.crt').chmod(0o644)
  return directory
 def run_openssl(self,args):subprocess.run(['openssl',*args],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,umask=0o077)
 def database_certificates(self):
  for key,port,admin,db in [('postgres',5432,'whereto_synthetic_admin','whereto_synthetic'),('witness',5433,'synthetic_witness_admin','whereto_witness')]:
   directory=self.certificate('db-'+key,[key+'.task52.invalid','localhost']);c=self.private['stores'][key]
   self.run(['cp',str(directory/'server.crt'),c+':/tmp/hosted-leaf.crt'])
   self.run(['exec','-i','--user','postgres',c,'sh','-c','umask 077; cat > /tmp/hosted-leaf.key'],input=(directory/'server.key').read_bytes())
   query="ALTER SYSTEM SET ssl_cert_file='/tmp/hosted-leaf.crt'; ALTER SYSTEM SET ssl_key_file='/tmp/hosted-leaf.key'; SELECT pg_reload_conf();"
   self.run(['exec','-i',c,'psql','-p',str(port),'-U',admin,'-d',db],input=query,text=True,stdout=subprocess.DEVNULL)
  # TLS Redis keeps its original localhost certificate, so add a reviewed TCP alias
  # only via a fresh TLS endpoint process with its own non-root leaf identity.
  rd=self.private['stores']['redis'];directory=self.certificate('db-redis',['redis.task52.invalid','localhost'])
  self.run(['cp',str(directory/'server.crt'),rd+':/tmp/hosted-leaf.crt'])
  self.run(['exec','-i','--user','redis',rd,'sh','-c','umask 077; cat > /tmp/hosted-leaf.key'],input=(directory/'server.key').read_bytes())
  # Fresh TLS-only instance; no persistent/user data, no automatic financial retry.
  password=self.write_control("import os;print(os.environ['SYNTHETIC_REDIS_PASSWORD'])").strip()
  self.run(['exec','-d',rd,'redis-server','--bind','0.0.0.0','--port','0','--tls-port','6381','--tls-cert-file','/tmp/hosted-leaf.crt','--tls-key-file','/tmp/hosted-leaf.key','--tls-ca-cert-file','/tmp/cert.pem','--tls-auth-clients','no','--requirepass',password,'--save','','--appendonly','no','--maxmemory','16mb','--maxmemory-policy','noeviction','--logfile','/tmp/hosted-redis.log'])
  for _ in range(50):
   result=subprocess.run(self.D+['exec',self.private['client'],'python','-c',"import socket;s=socket.create_connection(('localhost',6381),.2);s.close()"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   if not result.returncode:break
   time.sleep(.1)
  else:
   log=self.output(['exec',rd,'cat','/tmp/hosted-redis.log'],text=True)
   raise RuntimeError('Synthetic TLS Redis startup refused: '+log[-1200:])
 def redis_acl(self):
  factory=self.configs['factory'];delivery=self.configs['dispatcher']
  code="""import redis,os
r=redis.Redis(host='localhost',port=6381,ssl=True,ssl_ca_certs='/tmp/hosted-ports-ca.pem',ssl_cert_reqs='required',ssl_check_hostname=True,password=os.environ['SYNTHETIC_REDIS_PASSWORD'])
from experiments.shared_state.evidence_models import VERSION
for name,password,commands in DATA:
 r.execute_command('ACL','SETUSER',name,'on','>'+password,'~'+VERSION+':*','-@all',*commands)
assert r.config_get('maxmemory-policy')['maxmemory-policy']=='noeviction'
""".replace('DATA',repr([(factory['redisUsername'],factory['redisPassword'],['+ping','+get','+set','+eval','+time','+zrangebyscore','+zcard','+zscore','+hlen','+zrem','+hdel','+hvals','+hget','+hset','+zadd','+zrevrange','+pexpireat']),(delivery['redisUsername'],delivery['redisPassword'],['+ping','+get','+time'])]))
  self.write_control(code)
 def configuration(self,name):
  role='factory' if name.startswith('factory-') else 'backend' if name.startswith('backend-') else name
  key={'factory-r1':'factory','factory-r2':'factory-secondary','backend-a':'worker-a','backend-b':'worker-b'}.get(name,name)
  c=deepcopy(self.configs[key]);c.update(service=role,build=self.cohort,identityBuild=self.cohort,ordinaryBuild=self.cohort,providerMode='synthetic',realProviderTransport=False,port=8080)
  for field in ('referenceTime','savedRecords','certificate','tlsKey','caPem','targets','database','issuer','witness'):c.pop(field,None)
  import ast
  declarations={x.targets[0].id:ast.literal_eval(x.value) for x in ast.parse(Path('private_runtime/registry.py').read_text()).body if isinstance(x,ast.Assign) and isinstance(x.targets[0],ast.Name) and x.targets[0].id in ('ROLES','PURPOSES')}
  ROLES=declarations['ROLES'];PURPOSES=declarations['PURPOSES']
  original=self.configs[key];c['sql']={}
  for purpose in ROLES[role]:
   d=original[purpose];domain='operational' if d['port']==5432 else 'witness'
   membership=('whereto_synthetic_issuer',) if purpose=='issuer' else ('synthetic_token_counter',) if role=='counter' and purpose=='database' else ()
   c['sql'][purpose]=dict(host='postgres.task52.invalid' if domain=='operational' else 'witness.task52.invalid',port=d['port'],database=d['dbname'],user=d['user'],password=d['password'],ca_file='/tests/ca.crt',contract=self.contracts[domain],memberships=membership,maximum=2,purpose=PURPOSES[role][purpose])
  if 'database' in original:c['database']={'password':original['database']['password']}
  if role in ('factory','dispatcher'):
   c['redis']=dict(host='redis.task52.invalid',port=6381,username=original['redisUsername'],password=original['redisPassword'],ca_file='/tests/ca.crt',environment='private-staging',epoch=c['epoch'],protocol_alias='synthetic')
   c['evidenceKeyId']='private-k1'
  owner=lambda slot,principal:dict(slot=slot,build=self.cohort,epoch=c['epoch'],principal=principal)
  if role=='factory':c['factoryOwner']=owner(name,c['principal'])
  if role=='dispatcher':c['factoryOwners']={n:owner(n,p) for n,p in [('factory-r1','factory'),('factory-r2','factory-secondary')]}
  allowed={'factory':{'/ordinary':['worker-a','worker-b'],'/dispatch-check':['dispatcher']},'backend':{},'counter':{'/count':['factory','factory-secondary'],'/ui-probe':['factory','factory-secondary']},'dispatcher':{'/send':['factory','factory-secondary'],'/ui-probe':['factory','factory-secondary']},'recovery':{'/recover':['operator'],'/ui-probe':['factory','factory-secondary']}}
  c['allow']=allowed[role]
  targets={'backend':['factory'],'factory':['counter','dispatcher','recovery'],'dispatcher':['factory-r1','factory-r2'],'counter':[],'recovery':[]}[role]
  c['networkTargets']={n:dict(url='https://'+(('factory-r2' if name=='backend-b' else 'factory-r1') if role=='backend' else n)+'.task52.invalid:8080',audience=c['audiences']['factory' if n.startswith('factory-') else n],service='factory' if n.startswith('factory-') else n) for n in targets}
  c['networkMethods']={n:(['/ordinary'] if role=='backend' else ['/dispatch-check'] if role=='dispatcher' else ['/count','/ui-probe'] if n=='counter' else ['/send','/ui-probe'] if n=='dispatcher' else ['/ui-probe']) for n in targets}
  return role,c
 def start(self,name):
  role,c=self.configuration(name);directory=self.certificate(name,[name+'.task52.invalid']);(directory/'config.json').write_text(json.dumps(c));(directory/'config.json').chmod(0o600)
  (directory/'ca.crt').write_bytes((self.root/'cert.pem').read_bytes());(directory/'start_role.py').write_bytes(Path('experiments/hosted_ports/start_role.py').read_bytes());(directory/'metrics.py').write_bytes(Path('experiments/hosted_ports/metrics.py').read_bytes())
  volume='whereto-role-fixture-'+secrets.token_hex(10);self.run(['volume','create',volume],stdout=subprocess.DEVNULL);self.volumes.append(volume)
  helper=self.output(['run','-d','--platform','linux/amd64','--network','none','--user','0:0','--mount','type=volume,src='+volume+',dst=/tests','--entrypoint','sleep',self.images[role]['id'],'60'],text=True).strip()
  try:
   self.run(['cp',str(directory)+'/.',helper+':/tests/'])
   self.run(['exec',helper,'chown','-R','10001:10001','/tests'])
   self.run(['exec',helper,'chmod','0600','/tests/config.json','/tests/server.key'])
  finally:subprocess.run(self.D+['rm','-fv',helper],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  args=['run','-d','--platform','linux/amd64','--network',self.network,'--network-alias',name+'.task52.invalid','--read-only','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','384m' if role in ('factory','dispatcher') else '192m','--cpus','.5','--mount','type=volume,src='+volume+',dst=/tests,readonly','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=32m,uid=10001,gid=10001,mode=0700','--entrypoint','python',self.images[role]['id'],'/tests/start_role.py']
  container=self.output(args,text=True).strip();self.containers[name]=container
  for _ in range(80):
   result=subprocess.run(self.D+['exec',self.private['client'],'python','-c',"import socket;s=socket.create_connection(('"+name+".task52.invalid',8080),.2);s.close()"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   if result.returncode==0:return container
   if self.output(['inspect','--format','{{.State.Running}}',container],text=True).strip()!='true':break
   time.sleep(.25)
  log=self.output(['logs',container],text=True,stderr=subprocess.STDOUT);raise RuntimeError('Role startup refused '+name+'\n'+log)
 def probe(self):
  control=dict(frontend=self.configs['frontend'],cohort=self.cohort,signer=self.private['fixtureSigners']['iap'])
  code="import os,sys;fd=os.open('/tmp/native-probe-control.json',os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.write(fd,sys.stdin.buffer.read());os.close(fd)"
  self.run(['exec','-i',self.private['client'],'python','-c',code],input=json.dumps(control).encode())
  self.run(['cp','experiments/hosted_ports/application_probe.py',self.private['client']+':/tmp/application_probe.py'])
  try:result=self.output(['exec',self.private['client'],'python','/tmp/application_probe.py'],text=True)
  finally:subprocess.run(self.D+['cp',self.private['client']+':/tmp/native-probe-attempt.json','/tmp/continuation-application-attempt.json'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  Path('/tmp/continuation-application-probe.json').write_text(result)
  print('ACTUAL_PRIVATE_HTTPS_APPLICATION_PROBE_PASS',flush=True)
 def browser(self):
  # Reuse the existing external Next/IAP fixture. No fixture enters a role image.
  from experiments.ordinary_network.fixture import Fixture
  fixture=Fixture.__new__(Fixture);fixture.D=self.D;fixture.client=self.private['client'];fixture.temp=self.root;fixture.ingress=None;fixture.processes=[];fixture.helpers=self.extras;fixture.volumes=self.volumes;fixture.network=self.network
  from experiments.shared_state.run_grants import BACKEND
  fixture.image=BACKEND
  d=json.loads(self.output(['inspect',self.private['roles']['worker-a']],text=True))[0]
  fixture.mount=next(x['Name'] for x in d['Mounts'] if x['Destination']=='/app')
  c=deepcopy(self.configs['frontend']);c['ordinaryBuild']=self.cohort;c['caPem']=(self.root/'cert.pem').read_text()
  data={'frontend':c,'network':{'endpoints':['https://backend-a.task52.invalid:8080','https://backend-b.task52.invalid:8080']}}
  (self.root/'iap.pem').write_text(self.private['fixtureSigners']['iap']);(self.root/'iap.pem').chmod(0o600)
  (self.root/'iap.json').write_text(json.dumps({'alice':{'claims':dict(iss='https://cloud.google.com/iap',aud=c['iapAudience'],sub='accounts.google.com:synthetic-alice',email='alice@example.invalid'),'headers':{'kid':'task52-offline-iap'}}}));(self.root/'iap.json').chmod(0o600)
  fixture.start_frontend(data);fixture.start_ingress(None)
  Path('/tmp/continuation-browser.json').write_text(json.dumps({'url':fixture.browser_url,'cohort':self.cohort,'finishSignal':str(self.root/'browser-done')}))
  print('ACTUAL_NEXT_BROWSER_AVAILABLE',flush=True)
  done=self.root/'browser-done'
  for _ in range(600):
   if done.exists():self.probe_crash();return
   time.sleep(1)
  raise RuntimeError('Bounded local browser verification window ended')
 def probe_crash(self):
  dispatcher=self.containers['dispatcher'];factory=self.containers['factory-r1'];process=None
  self.run(['exec',dispatcher,'python','-c',"from pathlib import Path;Path('/tmp/block-next-send').write_text('synthetic timing barrier')"])
  self.write_control("import json;from pathlib import Path;p=Path('/tmp/native-probe-control.json');v=json.loads(p.read_text());v['onlyInitial']=True;p.write_text(json.dumps(v))")
  try:
   process=subprocess.Popen(self.D+['exec',self.private['client'],'python','/tmp/application_probe.py'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
   operation=None
   for _ in range(100):
    r=subprocess.run(self.D+['exec',dispatcher,'cat','/tmp/reserved-operation.json'],capture_output=True,text=True)
    if not r.returncode:operation=json.loads(r.stdout)['operation'];break
    if process.poll() is not None:raise RuntimeError('Crash probe failed before reserved callback barrier')
    time.sleep(.1)
   if operation is None:raise RuntimeError('Reserved callback barrier not reached')
   from uuid import UUID
   assert str(UUID(operation))==operation
   # Static SQL with an exact synthetic UUID; never record payloads/capabilities.
   query="from experiments.shared_state.test_store import admin\nwith admin() as c:print(c.execute(\"SELECT charge,(SELECT count(*) FROM synthetic_state.facts WHERE operation=o.id AND kind='INTENT'),(SELECT count(*) FROM synthetic_state.app_witness_facts WHERE id='deliver:'||o.id::text||':1') FROM synthetic_state.operations o WHERE id=%s\",("+repr(operation)+",)).fetchone())"
   before=self.write_control(query).strip()
   self.run(['kill','--signal','KILL',factory],stdout=subprocess.DEVNULL)
   self.run(['exec',dispatcher,'python','-c',"from pathlib import Path;Path('/tmp/block-next-send').unlink()"])
   stdout,stderr=process.communicate(timeout=40)
   if process.returncode or json.loads(stdout)['status']==200:raise RuntimeError('Killed-owner operation did not refuse')
   self.run(['start',factory],stdout=subprocess.DEVNULL)
   after=self.write_control(query).strip()
   if before!=after:raise RuntimeError('Killed owner changed conservative reservation exposure')
   from ast import literal_eval
   charge,intents,deliveries=literal_eval(after)
   Path('/tmp/continuation-owner-crash-attempt.json').write_text(json.dumps(dict(cohort=self.cohort,before=literal_eval(before),after=literal_eval(after),operationRefused=True,factoryKilled=True,restarted=True))+'\n')
   assert charge>0 and intents==1 and deliveries==0
   Path('/tmp/continuation-owner-crash.json').write_text(json.dumps(dict(cohort=self.cohort,twoFactoryProcesses=True,factoryKilledBeforeCallback=True,reservationChargeRetained=True,chargeInteger=charge,committedIntentCount=intents,providerDeliveryCount=deliveries,restartWithoutRetry=True,operationRefused=True))+'\n')
   print('RESERVED_SEND_FACTORY_TERMINATION_PASS',flush=True)
  finally:
   subprocess.run(self.D+['exec',dispatcher,'python','-c',"from pathlib import Path;Path('/tmp/block-next-send').unlink(missing_ok=True)"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   if process is not None and process.poll() is None:process.terminate();process.wait(timeout=5)
 def close(self):
  audits={};spans=[]
  for name,c in self.containers.items():
   r=subprocess.run(self.D+['logs',c],capture_output=True,text=True)
   rows=[]
   for line in r.stdout.splitlines():
    try:
     value=json.loads(line)
     if type(value) is dict and value.get('event')=='private_service_refused':rows.append(value)
    except ValueError:pass
   audits[name]=rows
   metric=subprocess.run(self.D+['exec',c,'cat','/tmp/private-role-spans.jsonl'],capture_output=True,text=True)
   if metric.returncode==0:
    for line in metric.stdout.splitlines():
     value=json.loads(line)
     if set(value)=={'stage','nanoseconds','ok'}:spans.append(dict(value,role=name))
  if spans:
   from statistics import median
   groups={}
   for stage in sorted({v['stage'] for v in spans}):
    rows=[v for v in spans if v['stage']==stage];values=sorted(v['nanoseconds']/1e6 for v in rows);groups[stage]=dict(samples=len(rows),failed=sum(not v['ok'] for v in rows),p50Milliseconds=round(median(values),3),p95Milliseconds=round(values[min(len(values)-1,int(len(values)*.95))],3),maxMilliseconds=round(max(values),3))
   Path('/tmp/continuation-role-latency.json').write_text(json.dumps(dict(scope='Inclusive overlapping synthetic local spans; do not sum; not cloud or LLM latency',stages=groups),indent=2)+'\n')
  if audits:Path('/tmp/continuation-role-refusals.json').write_text(json.dumps(audits,indent=2)+'\n')
  for c in [*self.extras,*self.containers.values()]:subprocess.run(self.D+['rm','-fv',c],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  for v in self.volumes:subprocess.run(self.D+['volume','rm',v],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  if self.network:subprocess.run(self.D+['network','disconnect',self.network,self.private['stores']['postgres']],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);subprocess.run(self.D+['network','rm',self.network],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
