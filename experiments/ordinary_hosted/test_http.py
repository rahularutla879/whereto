"""Actual application HTTP acceptance; every identity/provider/store is synthetic."""
import json,subprocess,unittest
TEXT='Coffee and museum in Baltimore on November 7, 2026'
PENDING='Coffee and museum in Baltimore'
ORIGIN={'point':{'id':'authorized-start','place_id':'Fixture_origin_0'},'explicitly_authorized':True,'source':'manual','precision':'address_or_place'}
def cases(call,private,client,extras,D,data):
 def post(path,value,user='alice'):return call(path,{'X-Goog-IAP-JWT-Assertion':private['users'][user]},json.dumps(value).encode())
 def interpret(text=TEXT,user='alice'):return post('/api/interpret',{'text':text,'calendarTimezone':'America/New_York'},user)
 def plan(v,user='alice',**changes):return post('/api/plans/generate',{**v['request'],'startingLocation':ORIGIN,'privateOuting':v['privateOuting'],**changes},user)
 def stats():
  # Query schema-independent protected ledger through synthetic bootstrap admin only.
  code="from experiments.shared_state.test_store import admin\nwith admin() as c:print(c.execute('SELECT count(*),sum(charge) FROM synthetic_state.operations').fetchone())"
  r=subprocess.run(D+['exec',client,'python','-c',code],check=True,capture_output=True,text=True);return r.stdout.strip()
 class Tests(unittest.TestCase):
  def test_01_actual_interpret_plan_and_duplicate_refusal(self):
   status,v=interpret();self.assertEqual(status,200,v);self.assertEqual(v['privateOuting']['version'],'52-private-ordinary-outing-v1');Tests.first=v
   before=stats()
   from concurrent.futures import ThreadPoolExecutor
   with ThreadPoolExecutor(max_workers=2) as pool:outcomes=list(pool.map(lambda _:plan(v),range(2)))
   self.assertEqual(sorted(status for status,_ in outcomes),[200,503]);result=next(result for status,result in outcomes if status==200);self.assertTrue(result['plans'] or result['provisionalPlans']);self.assertNotEqual(stats(),before)
   self.assertIsNone(result['optionsToken']);self.assertNotEqual(plan(v)[0],200);Tests.planned=result
  def test_02_pending_no_new_inference_and_cross_replica(self):
   status,v=interpret(PENDING);self.assertEqual(status,200,v);self.assertTrue(v['questions']);old=v['privateOuting'];before=stats()
   status,v=post('/api/interpret',{'text':PENDING,'calendarTimezone':'America/New_York','privateOuting':old,'answers':{'date':'2026-11-07'}});self.assertEqual(status,200,v);self.assertEqual(stats(),before);self.assertGreater(v['privateOuting']['revision'],old['revision']);self.assertEqual(v['privateOuting']['expiresMs'],old['expiresMs']);self.assertFalse(v['questions'])
   self.assertEqual(plan(v)[0],200)
  def test_02b_missing_area_and_original_reference_clock(self):
   text='Coffee and museum on November 7, 2026';status,v=interpret(text);self.assertEqual(status,200,v);self.assertIn('location',[q['field'] for q in v['questions']]);before=stats()
   status,v=post('/api/interpret',{'text':text,'calendarTimezone':'America/New_York','privateOuting':v['privateOuting'],'answers':{'location':'Baltimore'}});self.assertEqual(status,200,v);self.assertEqual(stats(),before);self.assertEqual(v['request']['location'],'Baltimore')
   status,v=interpret('Coffee and museum in Baltimore tomorrow');self.assertEqual(status,200,v);self.assertEqual(v['request']['date'],'2026-11-03')
  def test_03_two_tabs_same_user_and_other_user(self):
   _,a=interpret(PENDING);_,b=interpret(PENDING);self.assertNotEqual(a['privateOuting']['handle'],b['privateOuting']['handle'])
   self.assertNotEqual(post('/api/interpret',{'text':PENDING,'calendarTimezone':'America/New_York','privateOuting':a['privateOuting'],'answers':{'date':'2026-11-07'}},'bob')[0],200)
   _,bob=interpret(PENDING,'bob');self.assertEqual(post('/api/interpret',{'text':PENDING,'calendarTimezone':'America/New_York','privateOuting':bob['privateOuting'],'answers':{'date':'2026-11-07'}},'bob')[0],200)
   for v in (a,b):self.assertEqual(post('/api/interpret',{'text':PENDING,'calendarTimezone':'America/New_York','privateOuting':v['privateOuting'],'answers':{'date':'2026-11-07'}})[0],200)
  def test_04_source_edit_revokes_and_wrong_payload_refuses(self):
   _,v=interpret(PENDING);old=v['privateOuting']
   self.assertNotEqual(post('/api/interpret',{'text':TEXT,'calendarTimezone':'America/New_York','privateOuting':old})[0],200)
   self.assertNotEqual(post('/api/interpret',{'text':PENDING,'calendarTimezone':'America/New_York','privateOuting':old,'answers':{'date':'2026-11-07'}})[0],200)
   _,v=interpret();self.assertNotEqual(plan(v,activities=['bowling'])[0],200)
   _,v=interpret(PENDING);self.assertNotEqual(post('/api/interpret',{'text':PENDING,'calendarTimezone':'America/New_York','privateOuting':v['privateOuting'],'answers':{'location':'Philadelphia','date':'2026-11-07'}})[0],200)
  def test_05_forged_missing_handle_and_unreviewed_routes(self):
   for value in ({'activities':['coffee']},{'privateOuting':{'version':'52-private-ordinary-outing-v1','handle':'x'*43,'revision':1,'expiresMs':9999999999999}}):self.assertNotEqual(post('/api/plans/generate',value)[0],200)
   for p in ('plans/advanced','plans/options','starting-places','starting-areas','venues/details','plans/save','plans/reopen','plans/refresh'):self.assertEqual(post('/api/'+p,{})[0],503)
   self.assertEqual(call('/api/development-diagnostics')[0],404)
  def test_07a_expired_sql_session_cannot_continue(self):
   status,v=interpret(PENDING);self.assertEqual(status,200,v);handle=v['privateOuting']['handle']
   code="import json\nfrom experiments.shared_state.test_store import admin\nfrom experiments.shared_state.contracts import digest\nfrom experiments.service_isolation.auth import unb64\np=json.load(open('/tmp/hosted-control.json'));key=digest(unb64(p['configs']['factory']['hashKey']),'service-route',"+repr(handle)+")\nwith admin() as c:c.execute(\"UPDATE synthetic_state.sessions SET expires=clock_timestamp()-interval '1 second' WHERE id=(SELECT session FROM synthetic_state.service_routes WHERE route=%s ORDER BY revision DESC LIMIT 1)\",(key,))"
   before=stats();subprocess.run(D+['exec',client,'python','-c',code],check=True);self.assertNotEqual(post('/api/interpret',{'text':PENDING,'calendarTimezone':'America/New_York','privateOuting':v['privateOuting'],'answers':{'date':'2026-11-07'}})[0],200);self.assertEqual(stats(),before)
  def test_06_identity_body_binding_and_private_service_refusal(self):
   for h in ({'Authorization':'Bearer forged'},{'X-Goog-IAP-JWT-Assertion':'forged'},{'Origin':'https://evil.invalid'}):self.assertNotEqual(call('/api/interpret',h,b'{}')[0],200)
   self.assertEqual(call('/api/health')[0],200)
   # A rejected semantic request still consumed its byte-bound authentication scope.
   post('/api/interpret',{'text':''})
   from pathlib import Path
   captured=json.loads(Path(data['capture']).read_text())
   for changed in (False,True):
    code="import sys,json,base64\nfrom pathlib import Path\nfrom experiments.service_isolation.auth import TLS\np=json.load(open('/tmp/hosted-control.json'));v=json.load(sys.stdin);c=p['configs']['worker-b'];f=Path('/tmp/replay-ca');f.write_text(c['caPem']);raw=base64.urlsafe_b64decode(v['body']+'='*((-len(v['body']))%4));conn=TLS(8099,'worker-b.task52.invalid',str(f),3);conn.request(v['method'],v['path'],b'{}' if "+repr(changed)+" else raw,headers=v['headers']);r=conn.getresponse();assert r.status==403;r.read();conn.close()"
    subprocess.run(D+['exec','-i',client,'python','-c',code],input=json.dumps(captured),text=True,check=True)
  def test_06b_actual_application_client_pending_generation(self):
   r=subprocess.run(['node_modules/.bin/tsx','experiments/ordinary_hosted/client_driver.ts',data['clientFile'],data['frontendBase']],capture_output=True,text=True,timeout=180)
   self.assertEqual(r.returncode,0,r.stderr);self.assertIn('passed',r.stdout)
  def test_06c_optional_flexible_and_contradictory_journeys_never_flatten(self):
   for text in ('Buy groceries and maybe stop for coffee.','Visit the bank and grocery store, whichever is closer first.','Visit the pharmacy before the bank, but the bank before the pharmacy.'):
    status,v=post('/api/interpret',{'text':text,'preferences':{'location':'Baltimore','date':'2026-11-07'},'calendarTimezone':'America/New_York'});self.assertEqual(status,200,v);self.assertIsNone(v['request']);self.assertTrue(v['interpretation']['journey']);self.assertNotEqual(post('/api/plans/generate',{'privateOuting':v['privateOuting'],'activities':['coffee']})[0],200)
  def test_07_store_and_witness_outages_refuse(self):
   for store in ('postgres','redis','witness'):
    status,v=interpret(PENDING);self.assertEqual(status,200,v);before=stats()
    subprocess.run(D+['pause',private['stores'][store]],check=True,stdout=subprocess.DEVNULL)
    try:self.assertNotEqual(post('/api/interpret',{'text':PENDING,'calendarTimezone':'America/New_York','privateOuting':v['privateOuting'],'answers':{'date':'2026-11-07'}})[0],200)
    finally:subprocess.run(D+['unpause',private['stores'][store]],check=True,stdout=subprocess.DEVNULL)
    self.assertEqual(stats(),before)
  def test_06a_factory_and_backend_restart(self):
   _,v=interpret()
   for container,port in ((extras[0],8091),(extras[2],8098)):
    subprocess.run(D+['restart','--time','2',container],check=True,stdout=subprocess.DEVNULL)
    import time
    for _ in range(100):
     r=subprocess.run(D+['exec',client,'python','-c',f"import socket;s=socket.create_connection(('127.0.0.1',{port}),.2);s.close()"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
     if not r.returncode:break
     time.sleep(.2)
    else:raise AssertionError('Restart readiness')
   self.assertEqual(plan(v)[0],200)
  def test_08_financial_reservations_are_protected_and_operator_stop_refuses(self):
   audit="from experiments.shared_state.test_store import admin\nwith admin() as c:\n assert {r[0] for r in c.execute('SELECT DISTINCT provider FROM synthetic_state.operations')}=={'synthetic_ai','synthetic_maps'}\n assert c.execute('SELECT count(*) FROM synthetic_state.financial_dispatch').fetchone()[0]>0\n assert c.execute('SELECT count(*) FROM synthetic_state.token_counts').fetchone()[0]>0\n assert c.execute(\"SELECT count(*) FROM synthetic_state.operations o WHERE EXISTS(SELECT 1 FROM synthetic_state.facts f WHERE f.operation=o.id AND f.kind='SUCCEEDED') AND NOT EXISTS(SELECT 1 FROM synthetic_state.facts f WHERE f.operation=o.id AND f.kind='INTENT')\").fetchone()[0]==0"
   subprocess.run(D+['exec',client,'python','-c',audit],check=True)
   code="import json\nfrom pathlib import Path\nfrom experiments.hosted_identity.auth import Client\np=json.load(open('/tmp/hosted-control.json'));c=p['configs']['operator'];f=Path('/tmp/operator-ca');f.write_text(c['caPem']);c['ca']=str(f);assert Client(c).request('recovery','/recover',{'action':'REVOKED','value':'Synthetic terminal financial-authority refusal test'})=={'stopped':True}"
   before=stats();subprocess.run(D+['exec',client,'python','-c',code],check=True);self.assertNotEqual(interpret()[0],200);self.assertEqual(stats(),before)
 return Tests
