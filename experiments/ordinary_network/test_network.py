"""Network-specific checks use the restricted ordinary UI and frozen algorithms."""
import subprocess,json,time,unittest
from pathlib import Path
from experiments.ordinary_hosted.test_http import PENDING,ORIGIN
from experiments.ordinary_network.profile import collect

def verify(call,private,client,D,extras,helpers,data):
 def post(path,v):return call(path,{'X-Goog-IAP-JWT-Assertion':private['users']['alice']},json.dumps(v).encode())
 def stats():
  code="import json\nfrom experiments.shared_state.test_store import admin\nwith admin() as c:print(json.dumps(dict(operations=c.execute('SELECT count(*) FROM synthetic_state.operations').fetchone()[0],charge=c.execute('SELECT coalesce(sum(charge),0)::bigint FROM synthetic_state.operations').fetchone()[0],inference=c.execute(\"SELECT count(*) FROM synthetic_state.operations WHERE provider='synthetic_ai'\").fetchone()[0])))"
  r=subprocess.run(D+['exec',client,'python','-c',code],capture_output=True,text=True,check=True);return json.loads(r.stdout)
 class Tests(unittest.TestCase):
  def test_01_no_application_docker_or_privileged_credentials(self):
   source=Path('experiments/ordinary_network/preload.ts').read_text()
   for x in ('child_process','execFile','spawn(',"['docker'",'iap.pem','iap.json'):self.assertNotIn(x,source)
   for c in extras+[helpers[-1]]:
    d=json.loads(subprocess.check_output(D+['inspect',c],text=True))[0]
    self.assertTrue(d['HostConfig']['ReadonlyRootfs']);self.assertFalse(d['HostConfig']['Privileged']);self.assertFalse(any(m['Destination']=='/var/run/docker.sock' or m['Type']=='bind' for m in d['Mounts']))
   r=subprocess.run(D+['exec',helpers[-1],'sh','-c','! command -v docker && test ! -S /var/run/docker.sock'],capture_output=True);self.assertEqual(r.returncode,0)
  def test_02_complete_ordinary_network_latency_and_no_repeat_inference(self):
   for c in extras+helpers:subprocess.run(D+['exec',c,'sh','-c',': > /tmp/network-spans.jsonl'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   node=data['capture']+'.timing.jsonl';Path(node).write_text('');start=time.perf_counter_ns();before=stats()
   status,v=post('/api/interpret',{'text':PENDING,'calendarTimezone':'America/New_York'});self.assertEqual(status,200,v);after_ai=stats();self.assertEqual(after_ai['inference'],before['inference']+1);old=v['privateOuting']
   status,v=post('/api/interpret',{'text':PENDING,'calendarTimezone':'America/New_York','privateOuting':old,'answers':{'date':'2026-11-07'}});self.assertEqual(status,200,v);self.assertEqual(stats(),after_ai);self.assertEqual(v['privateOuting']['expiresMs'],old['expiresMs']);self.assertGreater(v['privateOuting']['revision'],old['revision'])
   status,result=post('/api/plans/generate',{**v['request'],'startingLocation':ORIGIN,'privateOuting':v['privateOuting']});self.assertEqual(status,200,result);self.assertTrue(result['plans'] or result['provisionalPlans']);elapsed=(time.perf_counter_ns()-start)/1e6
   collect(D,extras+helpers,node,'/tmp/network-ordinary-latency.json');p=json.loads(Path('/tmp/network-ordinary-latency.json').read_text());p['controllerInclusiveMilliseconds']=elapsed;p['countsBefore']=before;p['countsAfter']=stats();p['note']='Inclusive nested spans; controller includes fictional IAP fixture setup and read-only diagnostic queries, not cloud/LLM latency.';Path('/tmp/network-ordinary-latency.json').write_text(json.dumps(p,indent=2)+'\n')
   for key in ('frontendHTTPS','frontendIdentity','identity','sessionLookup','redisRead','sqlExecute','witnessProtocol','admission','reservation','fakeProvider','providerDispatch'):self.assertGreater(p['stages'][key]['samples'],0,key)
  def test_03_backend_and_frontend_cannot_call_counter_or_dispatcher(self):
   subprocess.run(D+['cp','private_runtime',client+':/app/private_runtime'],check=True)
   before=stats()
   code="import json\nfrom experiments.ordinary_network.client import Client\nfrom experiments.ordinary_network.dns import install\nfrom experiments.shared_state.contracts import Denied,Unavailable\ninstall();p=json.load(open('/tmp/hosted-control.json'))\nfor actor,target,path in [('frontend','factory','/ordinary'),('worker-a','counter','/count'),('worker-a','dispatcher','/send')]:\n c=p['configs'][actor];c['ca']='/tmp/network-negative-ca';open(c['ca'],'w').write(c['caPem'])\n try:Client(c).request(target,path,{});raise AssertionError('Role bypass')\n except (Denied,Unavailable):pass"
   # Control-plane negative principal, not an application-side privilege switch.
   r=subprocess.run(D+['exec',client,'python','-c',code],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr[-1000:]);self.assertEqual(stats(),before)
  def test_04_factory_and_dispatcher_disconnect_are_nonbillable_readiness_refusals(self):
   before=stats()
   for container in extras[:2]:
    subprocess.run(D+['pause',container],check=True,stdout=subprocess.DEVNULL)
    try:self.assertNotEqual(call('/api/planning-mode')[0],200)
    finally:subprocess.run(D+['unpause',container],check=True,stdout=subprocess.DEVNULL)
   self.assertEqual(stats(),before);self.assertEqual(call('/api/planning-mode')[0],200)
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 if not result.wasSuccessful():raise RuntimeError('Network application tests failed')
