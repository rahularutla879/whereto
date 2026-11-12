"""Host-side orchestration: each worker request runs in its own restricted container."""
import json,subprocess,time,unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

D=['docker','--context','colima-whereto-task52']

def verify(private,directory,mode='normal'):
    roles=private['roles'];client=private['client'];configs=private['configs']
    def worker(name,path,body,service='factory',**extra):
        if path=='/interpret' and 'requestId' not in body:body=dict(body,requestId=str(__import__('uuid').uuid4()))
        command=dict(action='request',service=service,path=path,body=body,**extra)
        result=subprocess.run(D+['exec','-i',roles[name],'python','-m','experiments.service_isolation.worker'],input=json.dumps(command),text=True,capture_output=True)
        if result.returncode:raise AssertionError('Worker process failed: '+result.stderr[-300:])
        return json.loads(result.stdout)
    def control(code):
        r=subprocess.run(D+['exec',client,'python','-c',code],capture_output=True,text=True)
        if r.returncode:raise AssertionError('Synthetic control failed: '+r.stderr[-500:])
        return r.stdout.strip()
    def privileged(service,path,body,principal='factory'):
        code=("import json\nfrom pathlib import Path\nfrom experiments.service_isolation.auth import Client\n"
              "c=json.load(open('/tmp/service-control.json'))['configs']["+repr(principal)+"]\n"
              "p=Path('/tmp/test-client-ca.pem');p.write_text(c['caPem']);c['ca']=str(p)\n"
              "try: print(json.dumps({'ok':Client(c).request("+repr(service)+","+repr(path)+","+repr(body)+")}))\n"
              "except Exception as e:print(json.dumps({'denied':type(e).__name__}))")
        return json.loads(control(code))
    def counts():return json.loads(control("from experiments.shared_state.test_store import admin\nimport json\nwith admin() as c: print(json.dumps(c.execute('SELECT count(*),coalesce(sum(charge),0)::bigint FROM synthetic_state.operations').fetchone()))"))
    def route(result):return {k:result[k] for k in ('ticket','revision')}
    def cont(name,current,method,args=None):return worker(name,'/continue',dict(route=route(current),method=method,arguments=args or {}))
    def mint(name,path,body,service='factory',**changes):
        r=subprocess.run(D+['exec','-i',roles[name],'python','-m','experiments.service_isolation.worker'],input=json.dumps(dict(action='mint',service=service,path=path,body=body,**changes)),capture_output=True,text=True,check=True)
        return json.loads(r.stdout)['token']
    class Tests(unittest.TestCase):
        def ok(self,result):self.assertIn('ok',result,result);return result['ok']
        def no(self,result):self.assertIn('denied',result,result)
        def test_01_actual_pending_cross_workers_and_selected_receipt(self):
            current=self.ok(worker('worker-a','/interpret',dict(request=dict(text='Coffee and museum in Baltimore',calendarTimezone='America/New_York'),execution={'startingLocation':{'point':{'id':'authorized-start','place_id':'Fixture_origin_0'},'explicitly_authorized':True,'source':'manual','precision':'address_or_place'}})))
            self.assertIsNotNone(current['result']['pending']);before=counts()
            # Fresh credentials/new workers cannot retry a lost initial response.
            repeated=dict(request=dict(text='Coffee and museum in Baltimore',calendarTimezone='America/New_York'),execution={},requestId=str(__import__('uuid').uuid4()))
            self.ok(worker('worker-a','/interpret',repeated));spent=counts()
            self.no(worker('worker-b','/interpret',repeated));self.assertEqual(counts(),spent)
            self.no(worker('worker-b','/interpret',dict(repeated,execution={'searchRadius':900})));self.assertEqual(counts(),spent)
            before=counts()
            after=self.ok(cont('worker-b',current,'answer',{'date':'2026-11-07'}));self.assertEqual(counts(),before)
            self.no(cont('worker-a',current,'plan')) # old revision
            self.no(worker('worker-other','/lookup',route(after)))
            self.no(worker('worker-a','/lookup',dict(ticket='x'*43,revision=1)))
            planned=self.ok(cont('worker-a',after,'plan'));self.assertTrue(planned['result']['optionsToken'])
            venue=(planned['result']['plans']+planned['result']['provisionalPlans'])[0]['candidate']['venues'][0]
            identity=venue.get('providerPlaceId') or venue['id']
            contact=self.ok(cont('worker-b',planned,'contact',{'id':identity}));self.assertEqual(contact['result']['placeId'],identity)
            more=self.ok(cont('worker-a',contact,'more'));self.assertTrue(more['result']['provisionalPlans'])
            issued=self.ok(cont('worker-a',more,'receipt'));data=issued['result'];plans=data['plans']+data['provisionalPlans'];ids=[x['candidate']['id'] for x in plans]
            request=dict(receipt=data['saveReceipt'],accessToken=data['saveAccessToken'],candidateIds=ids,selectedId=ids[0])
            before=counts();one=self.ok(worker('worker-a','/select',dict(route=issued['selection'],request=request)));two=self.ok(worker('worker-b','/select',dict(route=issued['selection'],request=request)))
            self.assertEqual(one,two);self.assertEqual(counts(),before)
            self.no(worker('worker-b','/select',dict(route=issued['selection'],request=dict(request,selectedId='forged'))))
            Tests.current=issued
        def test_02_actual_advanced_factory_across_restart(self):
            source=self.ok(worker('worker-b','/interpret',dict(request=dict(text='Go to SUNY College of Optometry and then get coffee.',calendarTimezone='America/New_York'),execution={})))
            handoff=self.ok(cont('worker-a',source,'plan'));self.assertEqual(handoff['result']['status'],'advanced_ready')
            origin={'point':{'id':'private_start','coordinates':{'latitude':40.75,'longitude':-73.98}},'explicitly_authorized':True,'source':'manual','precision':'address_or_place'}
            result=self.ok(cont('worker-b',handoff,'advance',dict(date='2026-11-07',destination='New York',startingLocation=origin)))
            self.assertTrue(result['result']['options']);before=counts()
            subprocess.run(D+['restart','--time','2',roles['factory']],check=True,stdout=subprocess.DEVNULL);time.sleep(2)
            owned=self.ok(worker('worker-a','/lookup',route(result)));self.assertEqual(owned['revision'],result['revision']);self.assertEqual(counts(),before)
            result=self.ok(cont('worker-b',result,'advance',dict(action='different',startingLocation=origin)))
            self.assertIn(result['result']['status'],('results','no_results','unsupported'))
        def test_03_authentication_body_role_audience_replay_and_methods(self):
            body={'ticket':'z'*43,'revision':1}
            for changes in [dict(service='counter'),dict(role='factory'),dict(build='0'*64),dict(epoch='1'*64),dict(now=int(time.time())-120),dict(now=int(time.time())+120)]:
                audience=changes.pop('service','factory');token=mint('worker-a','/lookup',body,service=audience,**changes)
                self.no(worker('worker-a','/lookup',body,token=token))
            import base64
            original=mint('worker-a','/lookup',body);h,p,sig=original.split('.');wire=bytearray(base64.urlsafe_b64decode(sig+'=='));wire[0]^=1
            forged=h+'.'+p+'.'+base64.urlsafe_b64encode(wire).decode().rstrip('=')
            self.no(worker('worker-a','/lookup',body,token=forged))
            self.no(worker('worker-a','/lookup',body,token='invalid'))
            self.no(worker('worker-a','/lookup',body,token=''))
            token=mint('worker-a','/lookup',body);self.no(worker('worker-a','/lookup',dict(body,revision=2),token=token))
            # First valid authentication consumes a nonce even when the fake ticket refuses.
            self.no(worker('worker-a','/lookup',body,token=token));self.no(worker('worker-b','/lookup',body,token=token))
            for service,path in [('counter','/count'),('dispatcher','/send'),('recovery','/recover'),('factory','/dispatch-check'),('factory','/sql'),('factory','/sign'),('factory','/pricing')]:self.no(worker('worker-a',path,{},service=service))
            self.no(worker('worker-a','/interpret',dict(request={'text':'x'},execution={},graph={},grant=999)))
        def test_035_strict_wire_and_tls_server_authentication(self):
            code="""import json
from experiments.service_isolation.worker import load
from experiments.service_isolation.auth import TLS,Client,sign
c=load();target=c['targets']['factory'];wire=b'{"ticket":"x","ticket":"y","revision":1}'
for headers in ({'Content-Type':'application/json'},{'Content-Type':'application/json','Authorization':'Bearer '+sign(c,'factory','/lookup',wire)}):
 t=TLS(target['port'],target['hostname'],c['ca'],5);t.request('POST','/lookup',wire,headers);r=t.getresponse();assert r.status==403;r.read();t.close()
c['targets']['factory']['hostname']='counter.task52.invalid'
try:Client(c).request('factory','/lookup',{'ticket':'x','revision':1})
except Exception:pass
else:raise AssertionError('wrong TLS service accepted')
print('wire/TLS refused')"""
            r=subprocess.run(D+['exec',roles['worker-a'],'python','-c',code],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr);self.assertIn('wire/TLS refused',r.stdout)
        def test_04_worker_credential_and_os_isolation(self):
            for name in ('worker-a','worker-b','worker-other'):
                r=subprocess.run(D+['exec','-i',roles[name],'python','-m','experiments.service_isolation.worker'],input=json.dumps({'action':'inventory'}),capture_output=True,text=True,check=True);v=json.loads(r.stdout)
                self.assertFalse(set(v['configKeys'])&set('database issuer witness redisPassword encryptionKey hashKey tlsKey'.split()))
                self.assertFalse(any(k.startswith('SYNTHETIC_') for k in v['environmentKeys']));self.assertEqual(v['uid'],10001);self.assertFalse(v['dockerSocket'])
                info=json.loads(subprocess.check_output(D+['inspect',roles[name]],text=True))[0];h=info['HostConfig']
                self.assertTrue(h['ReadonlyRootfs']);self.assertEqual(h['CapDrop'],['ALL']);self.assertNotIn(h['PidMode'],('host','container:'+roles['factory']))
                self.assertTrue(all(m.get('RW') is False for m in info['Mounts'] if m['Destination']=='/app'))
        def test_045_no_loopback_passwordless_admin_or_redis_access(self):
            code="""import psycopg,redis
for port,db,user in [(5432,'whereto_synthetic','whereto_synthetic_admin'),(5433,'whereto_witness','synthetic_witness_admin'),(5432,'whereto_synthetic','synthetic_issuer_client'),(5432,'whereto_synthetic','synthetic_counter_client')]:
 try:psycopg.connect(host='127.0.0.1',port=port,dbname=db,user=user,password='incorrect-synthetic-password',connect_timeout=2)
 except psycopg.OperationalError as e:assert 'password authentication failed' in str(e)
 else:raise AssertionError('loopback authentication bypass')
try:redis.Redis(host='127.0.0.1',socket_timeout=1).ping()
except redis.AuthenticationError:pass
else:raise AssertionError('anonymous Redis')
print('loopback SQL/Redis authentication refused')"""
            r=subprocess.run(D+['exec',roles['worker-a'],'python','-c',code],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr);self.assertIn('authentication refused',r.stdout)
            self.assertEqual(control("from experiments.shared_state.test_store import admin\nwith admin() as c:print(c.execute(\"SELECT count(*) FROM pg_hba_file_rules WHERE type LIKE 'host%' AND auth_method<>'scram-sha-256'\").fetchone()[0])"),'0')
        def test_05_duplicate_action_two_workers_no_financial_reset(self):
            current=self.ok(worker('worker-a','/interpret',dict(request=dict(text='Coffee and museum in Baltimore',calendarTimezone='America/New_York'),execution={})));before=counts()
            with ThreadPoolExecutor(2) as pool:
                results=list(pool.map(lambda n:worker(n,'/lookup',route(current)),['worker-a','worker-b']))
            self.assertEqual(counts(),before);self.assertTrue(any('ok' in x for x in results))
            # Same revision on a mutating action can be consumed only once.
            with ThreadPoolExecutor(2) as pool:results=list(pool.map(lambda n:cont(n,current,'answer',{'date':'2026-11-07'}),['worker-a','worker-b']))
            self.assertEqual(sum('ok' in x for x in results),1);Tests.current=next(x['ok'] for x in results if 'ok' in x)
        def test_06_refresh_current_access_and_cross_worker_consumption(self):
            import uuid
            request=dict(accessToken='A'*43,candidateId='chosen',refreshId=str(uuid.uuid4()))
            result=self.ok(worker('worker-a','/refresh',request));self.assertTrue(all(x['status']=='refreshed' for x in result['venues'].values()));before=counts()
            result=self.ok(worker('worker-b','/refresh',request));self.assertTrue(all(x['status']=='already_attempted' for x in result['venues'].values()));self.assertEqual(counts(),before)
            self.no(worker('worker-a','/refresh',dict(request,accessToken='B'*43)))
        def test_07_restricted_database_principals_cannot_escalate(self):
            code="""import json,psycopg
c=json.load(open('/tmp/service-control.json'))['configs']
checks=[('counter',\"UPDATE grant_rules.configuration SET grant_doc='{}'\"),('counter',\"SELECT synthetic_state.app_accept('x','reserve','{}')\"),('dispatcher',\"DELETE FROM synthetic_state.operations\"),('dispatcher',\"SELECT synthetic_state.app_count_input('x','x')\"),('dispatcher',\"SELECT synthetic_state.approve_requests('x','[]')\")]
for name,sql in checks:
 try:
  with psycopg.connect(host='127.0.0.1',**c[name]['database']) as db:db.execute(sql)
 except psycopg.Error as e:assert e.sqlstate=='42501',e.sqlstate
 else:raise AssertionError('privilege bypass')
checks=[('counter',"SELECT witness.operator('epoch','{}')",'42501'),('factory',"SELECT witness.operator('epoch','{}')",'42501'),('dispatcher',"SELECT witness.service_protocol('reserve','{}')",'P0001'),('counter',"SELECT witness.service_nonce('recovery','counter',repeat('a',32),repeat('b',64),0)",'P0001'),('dispatcher',"DELETE FROM witness.service_nonces",'42501')]
for name,sql,state in checks:
 try:
  with psycopg.connect(host='127.0.0.1',**c[name]['witness']) as db:db.execute(sql)
 except psycopg.Error as e:assert e.sqlstate==state,e.sqlstate
 else:raise AssertionError('witness privilege bypass')
import redis
for name,args in [('dispatcher',('SET','52-encrypted-shared-evidence-local-v1:{synthetic:'+('a'*64)+'}:bad','x')),('dispatcher',('GET','outside')),('dispatcher',('FLUSHALL',)),('factory',('CONFIG','SET','maxmemory','0')),('factory',('ACL','LIST'))]:
 client=redis.Redis(host='127.0.0.1',username=c[name]['redisUsername'],password=c[name]['redisPassword'])
 try:client.execute_command(*args)
 except redis.exceptions.NoPermissionError:pass
 else:raise AssertionError('Redis ACL bypass')
print('restricted roles refused5 SQL bypasses,5 witness bypasses and5 Redis bypasses')"""
            self.assertIn('refused5',control(code))
            self.no(privileged('counter','/count',dict(capability='a'*64,wire='e30'))) # {} cannot be model input
            self.no(privileged('dispatcher','/send',dict(operation='x',capability='x',token='x',revision=1,worker='x',fence=1,ordinal=1,payload='e30',permit='x')))
        def test_08_worker_and_authority_restart_preserve_auth_replay(self):
            body=route(Tests.current);token=mint('worker-a','/lookup',body)
            self.ok(worker('worker-a','/lookup',body,token=token));before=counts()
            for name in ('worker-a','counter','dispatcher','factory'):
                subprocess.run(D+['restart','--time','2',roles[name]],check=True,stdout=subprocess.DEVNULL)
            time.sleep(2);self.no(worker('worker-b','/lookup',body,token=token))
            self.ok(worker('worker-b','/lookup',body));self.assertEqual(counts(),before)
        def test_09_outages_refuse_without_spending_or_fallback(self):
            before=counts();body=route(Tests.current)
            for name in ('postgres','redis'):
                subprocess.run(D+['pause',private['stores'][name]],check=True,stdout=subprocess.DEVNULL)
                try:self.no(worker('worker-b','/lookup',body))
                finally:subprocess.run(D+['unpause',private['stores'][name]],check=True,stdout=subprocess.DEVNULL)
                self.assertEqual(counts(),before);self.ok(worker('worker-b','/lookup',body))
            subprocess.run(D+['restart','--time','2',private['stores']['redis']],check=True,stdout=subprocess.DEVNULL);time.sleep(1)
            self.no(worker('worker-a','/lookup',body));self.assertEqual(counts(),before)
        def test_10_restore_and_independent_operator_epoch(self):
            # SQL backup contains only this newly generated fictional experiment.
            snapshot=subprocess.check_output(D+['exec',private['stores']['postgres'],'pg_dump','-U','whereto_synthetic_admin','-d','whereto_synthetic','--schema=synthetic_state','--schema=grant_rules','--clean','--if-exists'])
            source=self.ok(worker('worker-a','/interpret',dict(request=dict(text='Coffee and museum in Baltimore',calendarTimezone='America/New_York'),execution={})))
            subprocess.run(D+['exec','-i',private['stores']['postgres'],'psql','-v','ON_ERROR_STOP=1','-U','whereto_synthetic_admin','-d','whereto_synthetic'],input=snapshot,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            self.no(worker('worker-b','/lookup',route(source)))
            self.no(worker('worker-a','/interpret',dict(request=dict(text='Coffee and museum in Baltimore',calendarTimezone='America/New_York'),execution={})))
            self.assertEqual(control("""from experiments.shared_state.test_application_grants import witness
s=witness().call('status');assert s['quarantined'] and s['quarantineExposure']==2000000;print('quarantined')"""),'quarantined')
            self.no(worker('worker-a','/recover',dict(action='epoch',value='e'*64),service='recovery'))
            self.ok(privileged('recovery','/recover',dict(action='epoch',value='e'*64),principal='operator'))
            self.no(worker('worker-b','/lookup',route(Tests.current)))
    class Failure(unittest.TestCase):
        def test_interrupted_single_use_operation(self):
            self.assertIn(mode,('lost_http','lost_inference','factory_crash','dispatcher_crash','worker_crash'))
            before=counts();request=dict(request=dict(text='Coffee and museum in Baltimore',calendarTimezone='America/New_York'),execution={},requestId=str(__import__('uuid').uuid4()))
            dispatcher=roles['dispatcher'];subprocess.run(D+['pause',dispatcher],check=True,stdout=subprocess.DEVNULL)
            pool=ThreadPoolExecutor(1);future=pool.submit(worker,'worker-a','/interpret',request)
            try:
                for _ in range(160):
                    ready=control("from experiments.shared_state.test_store import admin\nwith admin() as c:print(c.execute('SELECT count(*) FROM synthetic_state.financial_dispatch').fetchone()[0])")
                    if int(ready)>0:break
                    if future.done():raise AssertionError('operation refused before durable intent: '+str(future.result()))
                    time.sleep(.15)
                else:raise AssertionError('reservation deadline')
                reserved=counts();self.assertGreater(reserved[0],before[0]);self.assertGreater(reserved[1],before[1])
                if mode.startswith('lost_'):
                    domain='http' if mode=='lost_http' else 'inference'
                    control("from experiments.shared_state.test_store import admin\nwith admin() as c:c.execute(\"UPDATE synthetic_state.admission_leases SET refs=0 WHERE domain='"+domain+"'\")")
                elif mode=='factory_crash':subprocess.run(D+['kill','--signal','KILL',roles['factory']],check=True,stdout=subprocess.DEVNULL)
                elif mode=='dispatcher_crash':subprocess.run(D+['kill','--signal','KILL',dispatcher],check=True,stdout=subprocess.DEVNULL)
                elif mode=='worker_crash':subprocess.run(D+['kill','--signal','KILL',roles['worker-a']],check=True,stdout=subprocess.DEVNULL)
            finally:
                subprocess.run(D+['unpause',dispatcher],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            # A killed caller can lose its response; no service may automatically retry.
            try:reply=future.result(timeout=150)
            except AssertionError:reply={'denied':'worker_terminated'}
            pool.shutdown(wait=True)
            if mode!='worker_crash':self.assertIn('denied',reply,reply)
            if mode in ('factory_crash','dispatcher_crash'):
                name='factory' if mode=='factory_crash' else 'dispatcher'
                subprocess.run(D+['start',roles[name]],check=True,stdout=subprocess.DEVNULL);time.sleep(2)
            # Fresh JWT on another worker cannot repeat the same consumed input.
            retry=worker('worker-b','/interpret',request);self.assertIn('denied',retry,retry)
            self.assertEqual(counts(),reserved)
            if mode!='worker_crash':
                self.assertEqual(control("from experiments.shared_state.test_store import admin\nwith admin() as c:print(c.execute(\"SELECT count(*) FROM synthetic_state.app_witness_facts WHERE id LIKE 'deliver:%'\").fetchone()[0])"),'0')
            print('Failure cohort '+mode+': committed charge retained; request ID consumed; no automatic retry.',flush=True)
    selected=Tests if mode=='normal' else Failure
    result=unittest.TextTestRunner(verbosity=2,failfast=True).run(unittest.defaultTestLoader.loadTestsFromTestCase(selected))
    if not result.wasSuccessful():raise RuntimeError('Service isolation tests failed')
    print('Service process contract tests passed.',flush=True)
