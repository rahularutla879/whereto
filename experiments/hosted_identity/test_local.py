"""Actual TLS service processes, owned native workflows and offline signed assertions."""
import json,subprocess,time,unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from experiments.service_isolation.test_local import D

def verify(private):
    client=private['client'];roles=private['roles']
    def control(code):
        r=subprocess.run(D+['exec',client,'python','-c',code],capture_output=True,text=True)
        if r.returncode:raise AssertionError(r.stderr[-1200:])
        return r.stdout.strip()
    unit=subprocess.run(D+['exec',client,'python','-m','experiments.hosted_identity.test_tokens'],check=True)
    def call(path,body,user='alice',target='frontend',headers=None):
        code="""import json,time
from pathlib import Path
from experiments.service_isolation.auth import TLS
from experiments.shared_state.evidence_models import canonical,strict_json
from experiments.hosted_identity.auth import Client
p=json.load(open('/tmp/hosted-control.json'));c=p['configs']['frontend'];f=Path('/tmp/client-ca');f.write_text(c['caPem']);c['ca']=str(f)
"""
        if target=='frontend':
            code+="""import jwt
from experiments.hosted_identity.tokens import ISSUERS
now=int(time.time());iap=jwt.encode(dict(iss=ISSUERS['iap'],aud=c['iapAudience'],sub='accounts.google.com:synthetic-"""+user+"""',iat=now,exp=now+600),p['fixtureSigners']['iap'],algorithm='ES256',headers={'kid':'task52-offline-iap'})
headers={'Content-Type':'application/json','Origin':'https://frontend-task52-offline.run.app','X-Goog-IAP-JWT-Assertion':iap,'X-Task52-Offline-Ingress':p['ingress']};headers.update("""+repr(headers or {})+""" )
t=c['targets']['frontend'];conn=TLS(t['port'],t['hostname'],c['ca'],120)
conn.request('POST',"""+repr(path)+","+repr(json.dumps(body,sort_keys=True,separators=(',',':')).encode())+""",headers);r=conn.getresponse();assert 'Python' not in r.getheader('Server','');wire=r.read(1048577);print(json.dumps({'status':r.status,'data':strict_json(wire)}));conn.close()
"""
        else:
            code+="""c=p['configs']["""+repr(target)+"""];c['ca']=str(f)
try:print(json.dumps({'status':200,'data':{'result':Client(c).request('factory',"""+repr(path)+","+repr(body)+""" )}}))
except Exception:print(json.dumps({'status':403}))
"""
        return json.loads(control(code))
    def value(r):
        if r['status']!=200:raise AssertionError(r)
        return r['data']['result']
    def counts():return control("from experiments.shared_state.test_store import admin\nwith admin() as c:print(c.execute('SELECT count(*),sum(charge) FROM synthetic_state.operations').fetchone())")
    def route(v):return {k:v[k] for k in ('ticket','revision')}
    class Tests(unittest.TestCase):
        def test_01_frontend_backend_two_workers_user_owned_pending(self):
            r=value(call('/interpret',dict(request={'text':'Coffee and museum in Baltimore','calendarTimezone':'America/New_York'},execution={'startingLocation':{'point':{'id':'authorized-start','place_id':'Fixture_origin_0'},'explicitly_authorized':True,'source':'manual','precision':'address_or_place'}},requestId=str(__import__('uuid').uuid4()))));self.assertIsNotNone(r['result']['pending']);before=counts()
            self.assertEqual(call('/lookup',route(r),user='bob')['status'],403)
            r=value(call('/continue',dict(route=route(r),method='answer',arguments={'date':'2026-11-07'})));self.assertEqual(counts(),before)
            self.assertEqual(value(call('/lookup',route(r)))['status'],'owned_current_session');Tests.current=r
        def test_02_forwarded_headers_and_unenrolled_iap(self):
            for h in ({'Authorization':'Bearer forged'},{'X-Whereto-User':'alice'},{'X-Goog-IAP-JWT-Assertion':'invalid'},{'X-Goog-IAP-JWT-Assertion':''},{'Origin':'https://evil.invalid'},{'X-Task52-Offline-Ingress':''}):self.assertEqual(call('/lookup',route(Tests.current),headers=h)['status'],403)
            self.assertEqual(call('/lookup',route(Tests.current),user='revoked')['status'],403)
            self.assertEqual(call('/lookup',route(Tests.current),headers={'X-Goog-Authenticated-User-Id':'forged-bob','X-Goog-Authenticated-User-Email':'bob@example.invalid'})['status'],200)
            self.assertEqual(call('/lookup',route(Tests.current),user='bob',headers={'X-Goog-Authenticated-User-Id':'forged-alice'})['status'],403)
        def test_03_direct_worker_issuer_without_user_scope_refuses(self):
            before=counts()
            for n in ('worker-a','worker-b','worker-other'):self.assertEqual(call('/lookup',route(Tests.current),target=n)['status'],403)
            self.assertEqual(counts(),before)
        def test_035_service_oidc_substitution_and_direct_privileged_access(self):
            code="""import json,time,copy,jwt
from pathlib import Path
from experiments.hosted_identity.auth import Auth,Client
p=json.load(open('/tmp/hosted-control.json'));front=p['configs']['frontend'];ca=Path('/tmp/ca');ca.write_text(front['caPem']);front['ca']=str(ca)
body="""+repr(route(Tests.current))+""";from experiments.shared_state.evidence_models import canonical
ctx={'iap':p['users']['alice'],'forward':Auth(front,None,None).forward('/lookup',canonical(body),p['users']['alice'])}
c=copy.deepcopy(p['configs']['worker-a']);c['ca']=str(ca);aud=c['audiences']['factory'];now=int(time.time());e=c['enrollment']['worker-a']
base=dict(iss='https://accounts.google.com',aud=aud,sub=e['sub'],email=e['email'],email_verified=True,iat=now,exp=now+3600)
for delta in [dict(aud=c['audiences']['backend']),dict(sub='different'),dict(email='forged@offline-project.iam.gserviceaccount.com'),dict(iat=now+120,exp=now+3600),dict(iat=now-4000,exp=now-1)]:
 v=base|delta;c['oidcTokens'][aud]=jwt.encode(v,p['fixtureSigners']['workload'],algorithm='RS256',headers={'kid':'task52-offline-workload'})
 try:Client(c).request('factory','/lookup',body,context=ctx)
 except Exception:pass
 else:raise AssertionError('Google-shaped claim accepted')
c=copy.deepcopy(p['configs']['worker-a']);c['ca']=str(ca)
for target,path in [('counter','/count'),('dispatcher','/send'),('recovery','/recover')]:
 try:Client(c).request(target,path,{})
 except Exception:pass
 else:raise AssertionError('direct privileged access')
from experiments.service_isolation.auth import sign
legacy=sign(c,'factory','/lookup',canonical(body))
try:Client(c).request('factory','/lookup',body,context=ctx,auth_override={'Authorization':'Bearer '+legacy})
except Exception:pass
else:raise AssertionError('legacy synthetic identity accepted as Google')
for field,bad in [('identityBuild','0'*64),('epoch','e'*64),('identityEnvironment','wrong-environment'),('signingKey',p['configs']['worker-other']['signingKey'])]:
 c=copy.deepcopy(p['configs']['worker-a']);c['ca']=str(ca);c[field]=bad
 try:Client(c).request('factory','/lookup',body,context=ctx)
 except Exception:pass
 else:raise AssertionError('request build/epoch/environment/key accepted')
from experiments.service_isolation.auth import TLS
t=c['targets']['factory'];conn=TLS(t['port'],t['hostname'],c['ca'],120)
conn.request('POST','/lookup',canonical(body),{'Content-Type':'application/json'});response=conn.getresponse();assert response.status==403;response.read();conn.close()
print('claims and direct/legacy bypasses refused')"""
            self.assertIn('refused',control(code))
        def test_04_signed_scope_replay_body_and_user_substitution(self):
            code="""import json
from pathlib import Path
from experiments.hosted_identity.auth import Auth,Client,proof
from experiments.service_isolation.auth import b64
from experiments.shared_state.evidence_models import canonical
p=json.load(open('/tmp/hosted-control.json'));c=p['configs']['frontend'];f=Path('/tmp/ca');f.write_text(c['caPem']);c['ca']=str(f)
body="""+repr(route(Tests.current))+""";wire=canonical(body);iap=p['users']['alice'];forward=Auth(c,None,None).forward('/lookup',wire,iap);ctx={'iap':iap,'forward':forward}
Client(c).request('worker-a','/lookup',body,context=ctx)
for b,u in [(body,ctx),(dict(body,revision=999),ctx),(body,dict(ctx,iap=p['users']['bob']))]:
 try:Client(c).request('worker-b','/lookup',b,context=u)
 except Exception:pass
 else:raise AssertionError('replay/body/user substitution')
print('bound/replay refused')"""
            self.assertIn('refused',control(code))
        def test_045_competing_backends_consume_one_forward_scope(self):
            before=counts()
            code="""import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from experiments.hosted_identity.auth import Auth,Client
from experiments.shared_state.evidence_models import canonical
p=json.load(open('/tmp/hosted-control.json'));c=p['configs']['frontend'];f=Path('/tmp/ca');f.write_text(c['caPem']);c['ca']=str(f)
body="""+repr(route(Tests.current))+""";ctx={'iap':p['users']['alice'],'forward':Auth(c,None,None).forward('/lookup',canonical(body),p['users']['alice'])}
def send(target):
 try:Client(c).request(target,'/lookup',body,context=ctx);return True
 except Exception:return False
with ThreadPoolExecutor(2) as pool:assert sum(pool.map(send,['worker-a','worker-b']))==1
print('one scoped request')"""
            self.assertIn('one scoped',control(code));self.assertEqual(counts(),before)
        def test_05_actual_plan_receipt_and_capability_refresh(self):
            r=value(call('/continue',dict(route=route(Tests.current),method='plan',arguments={})));self.assertTrue(r['result']['provisionalPlans'])
            r=value(call('/continue',dict(route=route(r),method='receipt',arguments={})));d=r['result'];ids=[x['candidate']['id'] for x in d['plans']+d['provisionalPlans']];body=dict(route=r['selection'],request=dict(receipt=d['saveReceipt'],accessToken=d['saveAccessToken'],candidateIds=ids,selectedId=ids[0]));a=value(call('/select',body));self.assertEqual(value(call('/select',body)),a)
            self.assertEqual(call('/select',body,user='bob')['status'],403);Tests.current=r
            f=dict(accessToken='A'*43,candidateId='chosen',refreshId=str(__import__('uuid').uuid4()));self.assertTrue(value(call('/refresh',f))['venues']);before=counts();self.assertTrue(all(x['status']=='already_attempted' for x in value(call('/refresh',f))['venues'].values()));self.assertEqual(counts(),before)
            self.assertTrue(all(x['status']=='already_attempted' for x in value(call('/refresh',f,user='bob'))['venues'].values()));self.assertEqual(counts(),before)
            self.assertEqual(call('/refresh',dict(f,accessToken='B'*43))['status'],403)
        def test_051_backend_nonce_role_is_not_financial_authority(self):
            code="""import json,psycopg
p=json.load(open('/tmp/hosted-control.json'));assert not set(p['configs']['frontend']) & {'witness','database','issuer','redisPassword','encryptionKey','hashKey'};c=p['configs']['worker-a']['witness']
for sql,state in [("DELETE FROM witness.hosted_nonces",'42501'),("SELECT witness.operator('epoch','{}')",'42501'),("SELECT witness.service_protocol('reserve','{}')",'42501'),("CREATE TABLE witness.forged(x int)",'42501'),("SELECT witness.hosted_nonce('factory','worker-a',repeat('a',32),repeat('b',64),0)",'P0001')]:
 try:
  with psycopg.connect(host='127.0.0.1',**c) as db:db.execute(sql)
 except psycopg.Error as e:assert e.sqlstate==state,e.sqlstate
 else:raise AssertionError('nonce role escalation')
print('five SQL authority bypasses refused')"""
            self.assertIn('five SQL',control(code))
        def test_055_advanced_source_through_authenticated_workers(self):
            r=value(call('/interpret',dict(request={'text':'Go to SUNY College of Optometry and then get coffee.','calendarTimezone':'America/New_York'},execution={},requestId=str(__import__('uuid').uuid4()))))
            r=value(call('/continue',dict(route=route(r),method='plan',arguments={})));self.assertEqual(r['result']['status'],'advanced_ready')
            origin={'point':{'id':'private_start','coordinates':{'latitude':40.75,'longitude':-73.98}},'explicitly_authorized':True,'source':'manual','precision':'address_or_place'}
            r=value(call('/continue',dict(route=route(r),method='advance',arguments=dict(date='2026-11-07',destination='New York',startingLocation=origin))));self.assertTrue(r['result']['options'])
            self.assertEqual(call('/lookup',route(r),user='bob')['status'],403)
        def test_06_restarts_outages_epoch_and_expired_ownership(self):
            before=counts()
            for n in ('worker-a','worker-b','factory'):
                subprocess.run(D+['restart','--time','2',roles[n]],check=True,stdout=subprocess.DEVNULL)
            time.sleep(2);self.assertEqual(value(call('/lookup',route(Tests.current)))['status'],'owned_current_session');self.assertEqual(counts(),before)
            for n in ('postgres','redis'):
                subprocess.run(D+['pause',private['stores'][n]],check=True,stdout=subprocess.DEVNULL)
                try:self.assertNotEqual(call('/lookup',route(Tests.current))['status'],200)
                finally:subprocess.run(D+['unpause',private['stores'][n]],check=True,stdout=subprocess.DEVNULL)
                self.assertEqual(counts(),before)
            control("from experiments.shared_state.test_store import admin\nwith admin() as c:c.execute(\"UPDATE synthetic_state.sessions SET expires=clock_timestamp()-interval '1 second'\")")
            self.assertNotEqual(call('/lookup',route(Tests.current))['status'],200)
            fresh=value(call('/interpret',dict(request={'text':'Coffee and museum in Baltimore','calendarTimezone':'America/New_York'},execution={},requestId=str(__import__('uuid').uuid4()))));before=counts()
            control("from experiments.shared_state.test_store import admin\nwith admin() as c:c.execute(\"UPDATE synthetic_state.sessions SET revoked=true\")")
            self.assertNotEqual(call('/lookup',route(fresh))['status'],200)
            self.assertNotEqual(call('/lookup',route(Tests.current))['status'],200)
            self.assertIn('operator stopped',control("import json\nfrom pathlib import Path\nfrom experiments.hosted_identity.auth import Client\np=json.load(open('/tmp/hosted-control.json'));c=p['configs']['operator'];f=Path('/tmp/operator-ca');f.write_text(c['caPem']);c['ca']=str(f)\nassert Client(c).request('recovery','/recover',{'action':'epoch','value':'e'*64})=={'stopped':True}\nprint('operator stopped')"))
            self.assertNotEqual(call('/lookup',route(Tests.current))['status'],200);self.assertEqual(counts(),before)
    result=unittest.TextTestRunner(verbosity=2,failfast=True).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    if not result.wasSuccessful():raise RuntimeError('Hosted local identity contracts failed')
    print('Hosted identity process suite passed.',flush=True)
