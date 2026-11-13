"""Non-billable authenticated mode, revocation and controlled SQL failure matrix."""
import json,subprocess,unittest
from pathlib import Path
from experiments.ordinary_hosted.test_http import TEXT

def verify(call,private,client,D,extras):
 def control(code):
  import textwrap
  safe='import json\ntry:\n'+textwrap.indent(code,' ')+'\nexcept Exception as e:\n print(json.dumps(dict(category=type(e).__name__,sqlstate=getattr(e,\'sqlstate\',None))));raise SystemExit(1)'
  r=subprocess.run(D+['exec',client,'python','-c',safe],capture_output=True,text=True,timeout=30)
  if r.returncode:raise AssertionError('Synthetic control failed: '+r.stdout[-200:])
  return r.stdout.strip()
 def snapshot(skip_clock=False):
  code=("""from experiments.shared_state.test_store import admin
from hashlib import sha256
from psycopg import sql
with admin() as c:
 tables=[r[0] for r in c.execute("SELECT tablename FROM pg_tables WHERE schemaname='synthetic_state' ORDER BY tablename")]
 TABLES_FILTER
 values=[c.execute(sql.SQL("SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb)::text FROM synthetic_state.{} t").format(sql.Identifier(t))).fetchone()[0] for t in tables]
 print(sha256(str(values).encode()).hexdigest())
""")
  return control(code.replace('TABLES_FILTER',"tables=[t for t in tables if t!='finance_time']" if skip_clock else 'pass'))
 class Tests(unittest.TestCase):
  def test_01_readiness_is_readonly_nonbillable_and_not_global_readiness(self):
   before=snapshot();status,v=call('/api/planning-mode');self.assertEqual(status,200,v);self.assertEqual(v['enabled'],False);self.assertTrue(v['privateOrdinary']['dependencyReady']);self.assertFalse(v['privateOrdinary']['financialAuthorization']);self.assertFalse(v['privateOrdinary']['productionReady']);self.assertEqual(snapshot(),before)
  def test_02_restricted_sql_principal_cannot_probe_or_mutate_policy(self):
   control("from experiments.service_isolation.runtime import connection\nimport psycopg,json\np=json.load(open('/tmp/hosted-control.json'))\nworker=lambda:connection(p['configs']['factory'])\nfor query in [\"SELECT synthetic_state.ui_snapshot('x','x')\",\"UPDATE grant_rules.configuration SET grant_doc='{}'\"]:\n with worker() as c:\n  try:c.execute(query);raise AssertionError('Forbidden authority')\n  except psycopg.errors.InsufficientPrivilege:pass")
  def test_03_owner_revocation_is_nonbillable_and_rejects_old_handle(self):
   def post(path,v,user='alice'):return call(path,{'X-Goog-IAP-JWT-Assertion':private['users'][user]},json.dumps(v).encode())
   status,v=post('/api/interpret',{'text':TEXT,'calendarTimezone':'America/New_York'});self.assertEqual(status,200,v);before=snapshot(True) # Existing finance_guard reads advance only finance_time; readiness compares that clock too.
   self.assertNotEqual(post('/api/private-ordinary/revoke',{'privateOuting':v['privateOuting']},'bob')[0],200);self.assertEqual(snapshot(True),before)
   status,_=post('/api/private-ordinary/revoke',{'privateOuting':v['privateOuting']});self.assertEqual(status,200)
   self.assertNotEqual(post('/api/plans/generate',{**v['request'],'privateOuting':v['privateOuting']})[0],200)
  def test_04_dependency_outages_do_not_change_operational_state(self):
   for name in ('postgres','redis','witness'):
    before=snapshot();subprocess.run(D+['pause',private['stores'][name]],check=True,stdout=subprocess.DEVNULL)
    try:
     status,v=call('/api/planning-mode');self.assertNotEqual(status,200);self.assertFalse(v['privateOrdinary']['dependencyReady'])
    finally:subprocess.run(D+['unpause',private['stores'][name]],check=True,stdout=subprocess.DEVNULL)
    self.assertEqual(snapshot(),before)
  def test_05_reproducible_sql_categories_and_lock_timeout(self):
   result=control("""import json,traceback
from experiments.service_isolation.runtime import make_broker
from experiments.shared_state.test_store import admin
from experiments.shared_state.contracts import Denied,Unavailable
p=json.load(open('/tmp/hosted-control.json'));s=make_broker(p['configs']['factory']).store
cases=[]
try:s._call('native_ready',session='0'*64,revision=1,worker=s._worker,fence=1);raise AssertionError('Missing session passed')
except Denied as error:
 assert error.code=='database_protocol';assert error.__context__.sqlstate in ('P0001','P0002');cases.append(dict(reason=error.code,category=type(error.__context__).__name__,sqlstate=error.__context__.sqlstate,scenario='missing_owned_evidence',frames=[(f.filename.rsplit('/',1)[-1],f.name,f.lineno) for f in traceback.extract_tb(error.__context__.__traceback__)]))
with admin() as lock:
 lock.execute('SELECT * FROM synthetic_state.finance_time WHERE id=1 FOR UPDATE')
 try:s._call('evidence_clock');raise AssertionError('Lock timeout bypassed')
 except Unavailable as error:
  assert error.__context__.sqlstate=='55P03';cases.append(dict(reason='unavailable',category=type(error.__context__).__name__,sqlstate=error.__context__.sqlstate,scenario='protected_lock_contention',frames=[(f.filename.rsplit('/',1)[-1],f.name,f.lineno) for f in traceback.extract_tb(error.__context__.__traceback__)]))
 lock.rollback()
assert s._call('evidence_clock')['now_ms']>0
print(json.dumps(cases))
""")
   Path('/tmp/ui-sql-reliability.json').write_text(result+'\n');self.assertEqual(len(json.loads(result)),2)
  def test_06_fixture_signing_cannot_run_in_production_or_worker(self):
   for module in ('experiments.ordinary_ui.bootstrap','experiments.ordinary_ui.iap_fixture'):
    r=subprocess.run(D+['exec','-e','WHERETO_ENV=production',client,'python','-m',module,'alice'],capture_output=True,text=True)
    self.assertNotEqual(r.returncode,0);self.assertEqual(r.stdout,'')
   for worker in extras[2:4]:
    r=subprocess.run(D+['exec',worker,'python','-m','experiments.ordinary_ui.iap_fixture','alice'],capture_output=True,text=True)
    self.assertNotEqual(r.returncode,0);self.assertEqual(r.stdout,'')
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
 if not result.wasSuccessful():raise RuntimeError('UI authority checks failed')
