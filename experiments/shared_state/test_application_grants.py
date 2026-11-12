"""Synthetic-only two-database financial authority and fake inference tests."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from hashlib import sha256
import json
import multiprocessing as mp
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4
import psycopg
from psycopg.types.json import Jsonb

from experiments.shared_state import test_store as core,test_financial as f,test_bridge as b,test_evidence as e
from experiments.shared_state.contracts import Kind,Denied,Unavailable
from experiments.shared_state.evidence_models import canonical
from experiments.shared_state.application_grants import *

EPOCH=e.EPOCH
MODEL=DEFAULT_MODEL


def rates():
    from backend.ai import Interpretation
    schema=Interpretation.model_json_schema();r={'maps':__import__('backend.development_cost',fromlist=['RATES']).RATES.copy(),'models':{}}
    for model,provider,inp,out in [(MODEL,'fictional_llm_a',1,3),('fictional-other@offline-v1','fictional_llm_b',2,5),('fictional-free@offline-v1','fictional_llm_a',0,0)]:
        r['models'][model]=dict(provider=provider,profile='fake-utf8-complete-v1',input_rate=inp,output_rate=out,max_input=100000,max_output=64,
            rate_version='fictional-a-rate-v1' if provider=='fictional_llm_a' else 'fictional-b-rate-v1',prompt_hash=sha256(PROMPT.encode()).hexdigest(),schema_hash=sha256(canonical(schema)).hexdigest(),schema=schema)
    return r


def grant(**changes):
    return dict(id='11111111-1111-4111-8111-111111111111',version='synthetic-app-grant-v1',domain='synthetic-application-domain-v1',epoch=EPOCH,
        total=2000000,daily=2000000,outing=2000000,providers=dict(synthetic_maps=2000000,fictional_llm_a=2000000,fictional_llm_b=2000000),
        timezone='UTC',expires='2099-01-01T00:00:00Z',roots=[f.ROOT,'00000000-0000-4000-8000-000000000002'],attempts=100,concurrency=4)|changes


def witness_connection(user,password):
    return psycopg.connect(host='127.0.0.1',port=5433,dbname='whereto_witness',user=user,password=password,connect_timeout=2)


def witness_admin():return witness_connection('synthetic_witness_admin',os.environ['SYNTHETIC_WITNESS_ADMIN_PASSWORD'])


def witness():
    return Witness(lambda:witness_connection('synthetic_witness_service',os.environ['SYNTHETIC_WITNESS_SERVICE_PASSWORD']),
                   lambda:witness_connection('synthetic_witness_reader',os.environ['SYNTHETIC_WITNESS_READER_PASSWORD']))


def issuer_connection():
    return psycopg.connect(host='127.0.0.1',port=5432,dbname='whereto_synthetic',user='synthetic_issuer_client',password=os.environ['SYNTHETIC_ISSUER_PASSWORD'],connect_timeout=2)


def counter_connection():
    return psycopg.connect(host='127.0.0.1',port=5432,dbname='whereto_synthetic',user='synthetic_counter_client',password=os.environ['SYNTHETIC_COUNTER_PASSWORD'],connect_timeout=2)


def fixture(g=None):
    g=g or grant();r=rates()
    with witness_admin() as c:
        c.execute('DROP SCHEMA IF EXISTS witness CASCADE');c.execute('DROP SCHEMA IF EXISTS grant_rules CASCADE');c.execute('SET LOCAL ROLE whereto_synthetic_owner')
        c.execute(Path(__file__).with_name('grant_rules.sql').read_text(),prepare=False)
        c.execute('SELECT grant_rules.validate(%s,%s)',(Jsonb(g),Jsonb(r)))
        c.execute('INSERT INTO grant_rules.configuration VALUES(1,%s,%s)',(Jsonb(g),Jsonb(r)))
        c.execute(Path(__file__).with_name('grant_witness.sql').read_text(),prepare=False)
    with witness_admin() as c:
        c.execute('SET LOCAL ROLE synthetic_grant_operator');c.execute("SELECT witness.operator('epoch',%s)",(Jsonb({'epoch':EPOCH}),))
    def install(c):
        c.execute('DROP SCHEMA IF EXISTS grant_rules CASCADE')
        c.execute(Path(__file__).with_name('bridge.sql').read_text(),prepare=False)
        c.execute(Path(__file__).with_name('evidence.sql').read_text(),prepare=False)
        c.execute('INSERT INTO synthetic_state.evidence_policy VALUES(1,%s,%s,%s)',('synthetic',EPOCH,e.VERSION))
        c.execute('UPDATE synthetic_state.test_clock SET value=NULL')
        c.execute(Path(__file__).with_name('grant_rules.sql').read_text(),prepare=False)
        c.execute('SELECT grant_rules.validate(%s,%s)',(Jsonb(g),Jsonb(r)))
        c.execute('INSERT INTO grant_rules.configuration VALUES(1,%s,%s)',(Jsonb(g),Jsonb(r)))
        c.execute(Path(__file__).with_name('application_grants.sql').read_text(),prepare=False)
    f.fixture(extension=install);e.cache().client.flushdb()


def store():
    service=GrantService(witness(),issuer_connection)
    return GrantStore(service=service,issuer_connection=issuer_connection,evidence=e.cache(),key=core.KEY,password=os.environ['SYNTHETIC_WORKER_PASSWORD'],limits=f.LIMITS)


def maps(s,*,root=f.ROOT,key=None,variant='pro',operation='details'):
    action=ProviderAction(purpose='lookup',sourceDigest='b'*64,interpretationDigest='c'*64,requestRevision=1)
    h=s.create(Kind.ACTION,action);l=s.claim(h,1);http=secrets.token_hex(32)
    s._call('admit',id=http,worker=s._worker,domain='http',fingerprint=http)
    with issuer_connection() as c:
        c.execute('SELECT synthetic_state.register_action(%s,%s,NULL,NULL)',(s._hash(h.token,'session'),http))
        c.execute('SELECT synthetic_state.app_enroll_budget(%s,%s,%s)',(s._hash(h.token,'session'),root,str(uuid4())))
    cap=s.issue(l,'provider_action',str(uuid4()));payload=canonical({'synthetic':key or str(uuid4())})
    f.approve(s,cap,[dict(operation=operation,variant=variant,rows=0,cols=0,request_digest=sha256(payload).hexdigest())])
    s.publish(l,{'ordinary':core.ordinary()},'synthetic_fresh',issuer_connection)
    return l,cap,payload


def perform(s,l,cap,payload,callback=lambda _:None):
    r=s.reserve(l,cap,str(uuid4()));s.transition(r,'INTENT')
    s._call('dispatch',**s._lease(l),capability=s._hash(cap.token,'cap'),operation=r.operation,ordinal=1,payload_digest=sha256(payload).hexdigest())
    value=s.service.send(s,r,1,payload,callback);s.transition(r,'SUCCEEDED');return r,value


def reply(payload,data=None,usage=True):
    body=json.loads(payload)
    return dict(output=data or dict(activities=['coffee','museum'],location='Baltimore',date='2026-11-07',budget_per_person=None,preferences=[]),
        usage=dict(provider=body['provider'],model=body['model'],input_tokens=len(payload),output_tokens=2,cached_tokens=0,reasoning_tokens=0,tool_calls=0) if usage else None)


def child_spend(root,barrier,queue):
    try:
        s=store()
        with s.service.witness.serial():l,c,p=maps(s,root=root)
        barrier.wait(15);perform(s,l,c,p);queue.put('accepted')
    except Denied:queue.put('denied')
    except Exception as x:queue.put(type(x).__name__)


def child_crash(phase):
    s=store();l,c,p=maps(s);args=dict(**s._lease(l),capability=s._hash(c.token,'cap'),operation=str(uuid4()))
    if phase=='witness':
        with s.service.witness.serial():s.recover(l);s.service.prepare(s,'reserve',args);os._exit(42)
    r=s.reserve(l,c,args['operation']);s.transition(r,'INTENT')
    os._exit(43)


class GrantTests(unittest.TestCase):
    def setUp(self):fixture();self.s=store()
    def test_legitimate_maps_and_shared_limits_no_refund(self):
        l,c,p=maps(self.s);r,_=perform(self.s,l,c,p)
        self.assertEqual(self.s.service.witness.call('status')['gross'],17000)
        self.assertEqual(self.s.snapshot()['gross'],17000);self.assertFalse(r.planning_authorized)
        with self.assertRaises(Denied):self.s.reserve(l,c,str(uuid4()))

    def test_concurrent_workers_cannot_exceed_one_lifetime_grant(self):
        fixture(grant(total=17000,daily=17000,outing=17000,providers=dict(synthetic_maps=17000,fictional_llm_a=17000,fictional_llm_b=17000)))
        ctx=mp.get_context('spawn');barrier=ctx.Barrier(2);q=ctx.Queue()
        workers=[ctx.Process(target=child_spend,args=(root,barrier,q)) for root in grant()['roots']]
        for p in workers:p.start()
        for p in workers:p.join(30);self.assertEqual(p.exitcode,0)
        self.assertEqual(sorted(q.get(timeout=2) for _ in workers),['accepted','denied'])
        self.assertEqual(witness().call('status')['gross'],17000)

    def test_exhausted_grant_new_worker_root_zero_charge_and_overflow(self):
        fixture(grant(total=17000,daily=17000,outing=17000,providers=dict(synthetic_maps=17000,fictional_llm_a=17000,fictional_llm_b=17000)))
        s=store();perform(s,*maps(s))
        s2=store();l,c,p=maps(s2,root=grant()['roots'][1])
        with self.assertRaises(Denied):s2.reserve(l,c,str(uuid4()))
        l,c,p=maps(s2,operation='route',variant='none');perform(s2,l,c,p)
        self.assertEqual(witness().call('status')['gross'],17000)
        with self.assertRaises(psycopg.Error):maps(store(),root=str(uuid4()))
        with self.assertRaises(psycopg.Error):fixture(grant(total=10**20))

    def test_provider_day_outing_attempt_and_expiry_limits(self):
        for limits in [dict(providers=dict(synthetic_maps=17000,fictional_llm_a=2000000,fictional_llm_b=2000000)),dict(daily=17000),dict(attempts=1)]:
            with self.subTest(limits=limits):
                fixture(grant(**limits));s=store();perform(s,*maps(s))
                l,c,p=maps(s,root=grant()['roots'][1])
                with self.assertRaises(Denied):s.reserve(l,c,str(uuid4()))
                self.assertEqual(witness().call('status')['gross'],17000)
        fixture(grant(outing=17000));s=store();l,c,p=maps(s);perform(s,l,c,p)
        # One source/outgoing scope cannot erase its old charge by issuing a new capability.
        c2=s.issue(l,'provider_action',str(uuid4()));f.approve(s,c2,[f.item(key='second')])
        with self.assertRaises(Denied):s.reserve(l,c2,str(uuid4()))
        fixture(grant(expires='2020-01-01T00:00:00Z'));s=store();l,c,p=maps(s)
        with self.assertRaises(Denied):s.reserve(l,c,str(uuid4()))
        self.assertEqual(witness().call('status')['gross'],0)

    def test_calendar_rollover_never_renews_total_and_revocation_stops(self):
        fixture(grant(total=34000,daily=17000,outing=34000,providers=dict(synthetic_maps=34000,fictional_llm_a=34000,fictional_llm_b=34000)))
        def clock(value):
            for factory in [core.admin,witness_admin]:
                with factory() as c:c.execute('UPDATE grant_rules.test_clock SET value=%s',(value,))
        clock('2030-01-01T23:59:00Z');s=store();perform(s,*maps(s))
        l,c,p=maps(s)
        with self.assertRaises(Denied):s.reserve(l,c,str(uuid4()))
        clock('2030-01-02T00:01:00Z');perform(s,*maps(s));self.assertEqual(witness().call('status')['gross'],34000)
        clock('2030-01-03T00:01:00Z');l,c,p=maps(s)
        with self.assertRaises(Denied):s.reserve(l,c,str(uuid4()))
        fixture();s=store();l,c,p=maps(s)
        with witness_admin() as db:
            db.execute('SET LOCAL ROLE synthetic_grant_operator');db.execute("SELECT witness.operator('REVOKED',%s)",(Jsonb({'reason':'fictional_revocation'}),))
        with self.assertRaises(Denied):s.reserve(l,c,str(uuid4()))

    def test_missing_or_wrong_key_and_stale_fence_refuse_without_charge(self):
        l,c,p=maps(self.s);self.s.evidence.keys=e.Keys('k1',{'k1':b'0'*32})
        with self.assertRaises(Denied):self.s.reserve(l,c,str(uuid4()))
        self.assertEqual(witness().call('status')['gross'],0)
        fixture();s=store();l,c,p=maps(s);other=store();other.claim(l.session,1)
        with self.assertRaises(Denied):s.reserve(l,c,str(uuid4()))
        self.assertEqual(witness().call('status')['gross'],0)

    def test_runtime_and_issuer_cannot_change_grants_rates_epoch_or_counts(self):
        for factory in [lambda:psycopg.connect(**self.s._connection),issuer_connection]:
            for sql in ['UPDATE grant_rules.configuration SET grant_doc=\'{}\'','DELETE FROM synthetic_state.app_operations','SET ROLE whereto_synthetic_owner',"SELECT synthetic_state.app_count_input('x','x'::bytea)"]:
                with self.subTest(sql=sql),self.assertRaises(psycopg.Error),factory() as c:c.execute(sql)
        with self.assertRaises(psycopg.Error):
            with witness_connection('whereto_synthetic_worker',os.environ['SYNTHETIC_WORKER_PASSWORD']):pass
        with self.assertRaises(psycopg.Error),witness_connection('synthetic_witness_service',os.environ['SYNTHETIC_WITNESS_SERVICE_PASSWORD']) as c:
            c.execute("SELECT witness.operator('epoch',%s)",(Jsonb({'epoch':'c'*64}),))

    def test_missing_evidence_before_reserve_and_modified_payload_after_charge(self):
        l,c,p=maps(self.s);self.s.evidence.client.flushdb()
        with self.assertRaises(Denied):self.s.reserve(l,c,str(uuid4()))
        self.assertEqual(witness().call('status')['gross'],0)
        fixture();s=store();l,c,p=maps(s);r=s.reserve(l,c,str(uuid4()));s.transition(r,'INTENT')
        with self.assertRaises(Denied):s._call('dispatch',**s._lease(l),capability=s._hash(c.token,'cap'),operation=r.operation,ordinal=1,payload_digest='f'*64)
        self.assertEqual(witness().call('status')['gross'],17000)
        self.assertTrue(witness().call('status')['quarantined'])

    def test_uncertain_transport_stops_full_grant_and_no_replay(self):
        l,c,p=maps(self.s);r=self.s.reserve(l,c,str(uuid4()));self.s.transition(r,'INTENT')
        self.s._call('dispatch',**self.s._lease(l),capability=self.s._hash(c.token,'cap'),operation=r.operation,ordinal=1,payload_digest=sha256(p).hexdigest())
        self.s.service.send(self.s,r,1,p,lambda _:None)
        with self.assertRaises(Denied):self.s.service.send(self.s,r,1,p,lambda _:self.fail('Replay reached fake I/O'))
        self.s.transition(r,'UNCERTAIN');status=witness().call('status')
        self.assertTrue(status['quarantined']);self.assertEqual(status['quarantineExposure'],grant()['total']);self.assertEqual(status['gross'],17000)

    def test_process_death_retains_external_claim_and_unknown_exposure(self):
        for phase in ['witness','intent']:
            with self.subTest(phase=phase):
                fixture();ctx=mp.get_context('spawn');p=ctx.Process(target=child_crash,args=(phase,));p.start();p.join(20);self.assertIn(p.exitcode,(42,43))
                s=store();self.assertEqual(witness().call('status')['gross'],17000)
                if phase=='witness':
                    with self.assertRaises(Denied):s.service.sync(s)
                    self.assertTrue(witness().call('status')['quarantined'])
                else:self.assertEqual(s.snapshot()['gross'],17000)

    def test_missing_terminal_fact_is_restore_disagreement(self):
        perform(self.s,*maps(self.s))
        # Simulate an administrator restoring an older terminal-fact prefix.
        # Runtime cannot TRUNCATE; this is intentionally outside its privileges.
        with core.admin() as c:
            rows=c.execute("SELECT id,quote FROM synthetic_state.app_witness_facts WHERE id NOT LIKE 'outcome:%'").fetchall()
            c.execute('TRUNCATE synthetic_state.app_witness_facts')
            for identifier,q in rows:c.execute('INSERT INTO synthetic_state.app_witness_facts VALUES(%s,%s)',(identifier,Jsonb(q)))
        with self.assertRaises(Denied):self.s.service.sync(self.s)
        self.assertEqual(witness().call('status')['quarantineExposure'],grant()['total'])

    def test_epoch_rotation_invalidates_old_sql_and_cannot_roll_back(self):
        l,c,p=maps(self.s)
        with witness_admin() as db:
            db.execute('SET LOCAL ROLE synthetic_grant_operator');db.execute("SELECT witness.operator('epoch',%s)",(Jsonb({'epoch':'d'*64}),))
        with self.assertRaises(Denied):self.s.reserve(l,c,str(uuid4()))
        with self.assertRaises(psycopg.Error),witness_admin() as db:
            db.execute('SET LOCAL ROLE synthetic_grant_operator');db.execute("SELECT witness.operator('epoch',%s)",(Jsonb({'epoch':EPOCH}),))
        self.assertEqual(witness().call('status')['quarantineExposure'],grant()['total'])


class InferenceTests(unittest.TestCase):
    def setUp(self):fixture();self.s=store();self.enterContext(__import__('backend.testing_clock',fromlist=['calendar_clock']).calendar_clock(b.NOW))
    def broker(self,data=None,**kwargs):
        from backend.provider_budget import ProviderBudget
        model=FakeInference(self.s,issuer_connection,counter_connection,f.ROOT,lambda p:reply(p,data),**kwargs)
        broker=GrantBroker(self.s,GrantIssuer(issuer_connection,f.ROOT,lambda:({'ordinary':core.ordinary()},'synthetic_fresh')),model,ProviderBudget(),None,now=b.NOW)
        model.broker=broker;return broker,model
    def test_owned_complete_inference_and_pending_no_second_model_charge(self):
        from backend.interpretation import InterpretationInput,ClarificationAnswers
        data=dict(activities=['coffee','museum'],location='Baltimore',date=None,budget_per_person=None,preferences=[])
        broker,model=self.broker(data);token,result=broker.interpret(InterpretationInput(text='Coffee and museum in Baltimore',calendarTimezone='America/New_York'))
        self.assertIsNotNone(result.pending);before=witness().call('status')['gross']
        result=broker.answer(token,ClarificationAnswers(date='2026-11-07'))
        self.assertIsNotNone(result.request);self.assertEqual(model.calls,1);self.assertEqual(witness().call('status')['gross'],before)
    def test_unknown_model_or_output_overflow_never_reserves(self):
        from backend.interpretation import InterpretationInput
        for changes in [dict(model='gpt-not-authorized'),dict(max_output=65),dict(max_output=-1)]:
            with self.subTest(changes=changes):
                fixture();self.s=store();broker,_=self.broker(**changes)
                with self.assertRaises((Denied,psycopg.Error)):broker.interpret(InterpretationInput(text='Coffee and museum in Baltimore on November 7, 2026'))
                self.assertEqual(witness().call('status')['gross'],0)
    def test_malformed_and_substituted_usage_never_refunds(self):
        from backend.interpretation import InterpretationInput
        for change in [dict(output_tokens=65),dict(input_tokens=-1),dict(model='substituted'),dict(provider='substituted'),dict(reasoning_tokens=1),dict(cached_tokens=1),dict(tool_calls=1)]:
            with self.subTest(change=change):
                fixture();self.s=store();broker,model=self.broker()
                def invalid(p):
                    result=reply(p);result['usage'].update(change);return result
                model.reply=invalid
                with self.assertRaises(Denied):broker.interpret(InterpretationInput(text='Coffee and museum in Baltimore on November 7, 2026'))
                status=witness().call('status');self.assertGreater(status['gross'],0);self.assertTrue(status['quarantined'])

    def test_inference_and_maps_share_grant_and_source_outing(self):
        from backend.interpretation import InterpretationInput
        broker,model=self.broker();token,result=broker.interpret(InterpretationInput(text='Coffee and museum in Baltimore on November 7, 2026'))
        llm_charge=witness().call('status')['gross'];self.assertGreater(llm_charge,0)
        perform(self.s,*maps(self.s));self.assertEqual(witness().call('status')['gross'],llm_charge+17000)
        with core.admin() as c:
            self.assertEqual(c.execute("SELECT count(DISTINCT quote->>'provider') FROM synthetic_state.app_operations").fetchone()[0],2)
            source=c.execute('SELECT root,outing,inference,source_digest FROM synthetic_state.app_sources').fetchone();self.assertEqual(str(source[0]),f.ROOT)
            self.assertEqual(c.execute('SELECT count(*) FROM synthetic_state.llm_usage WHERE valid').fetchone()[0],1)
        self.assertFalse(result.request is None)
        # The protected source-to-outing binding also constrains issuer mistakes.
        h=self.s.create(Kind.ACTION,ProviderAction(purpose='ordinary',sourceDigest=source[3],interpretationDigest='c'*64,requestRevision=1))
        lease=self.s.claim(h,1);http=secrets.token_hex(32)
        self.s._call('admit',id=http,worker=self.s._worker,domain='http',fingerprint=http)
        with issuer_connection() as c:
            c.execute('SELECT synthetic_state.register_action(%s,%s,%s,NULL)',(self.s._hash(h.token,'session'),http,source[2]))
            c.execute('SELECT synthetic_state.app_enroll_budget(%s,%s,%s)',(self.s._hash(h.token,'session'),source[0],source[1]))
        for root,outing in [(source[0],str(uuid4())),(grant()['roots'][1],source[1])]:
            with self.assertRaises(psycopg.Error),issuer_connection() as c:
                c.execute('SELECT synthetic_state.app_enroll_budget(%s,%s,%s)',(self.s._hash(h.token,'session'),root,outing))

    def test_maps_consumption_prevents_llm_over_grant_before_fake_send(self):
        from backend.interpretation import InterpretationInput
        value=InterpretationInput(text='Coffee and museum in Baltimore on November 7, 2026')
        cost=len(inference_payload(value))+64*3
        total=17000+cost-1
        fixture(grant(total=total,daily=total,outing=total,providers=dict(synthetic_maps=total,fictional_llm_a=total,fictional_llm_b=total)))
        self.s=store();perform(self.s,*maps(self.s));broker,model=self.broker()
        with self.assertRaises(Denied):broker.interpret(value)
        self.assertEqual(model.calls,0);self.assertEqual(witness().call('status')['gross'],17000)
        self.assertEqual(self.s.snapshot()['attempts'],1)

    def test_zero_price_model_still_consumes_operation(self):
        from backend.interpretation import InterpretationInput
        broker,model=self.broker(model='fictional-free@offline-v1');broker.interpret(InterpretationInput(text='Coffee and museum in Baltimore on November 7, 2026'))
        self.assertEqual(witness().call('status')['gross'],0);self.assertEqual(self.s.snapshot()['attempts'],1)

    def test_changed_inference_payload_and_unbounded_categories_refuse(self):
        from backend.interpretation import InterpretationInput
        from experiments.shared_state import application_grants as module
        original=module.inference_payload
        for change in [dict(provider='forged'),dict(system='altered prompt'),dict(schema={}),dict(reasoning='unknown'),dict(tools=[{'type':'fictional'}]),dict(cache=True)]:
            with self.subTest(change=change):
                fixture();self.s=store();broker,model=self.broker()
                def altered(*args):
                    body=json.loads(original(*args));body.update(change);return canonical(body)
                with patch.object(module,'inference_payload',altered),self.assertRaises((Denied,psycopg.Error)):
                    broker.interpret(InterpretationInput(text='Coffee and museum in Baltimore on November 7, 2026'))
                self.assertEqual(witness().call('status')['gross'],0);self.assertEqual(model.calls,0)
        fixture();self.s=store();broker,model=self.broker()
        def altered_source(*args):
            body=json.loads(original(*args));body['input']='Unauthorized changed source';return canonical(body)
        with patch.object(module,'inference_payload',altered_source),self.assertRaises(Denied):
            broker.interpret(InterpretationInput(text='Coffee and museum in Baltimore on November 7, 2026'))
        self.assertEqual(model.calls,0);self.assertGreater(witness().call('status')['gross'],0)
        self.assertTrue(witness().call('status')['quarantined'])

    def test_unknown_build_refuses_before_database_authority(self):
        from experiments.shared_state import grant_identity
        with patch.object(grant_identity,'MANIFEST_SHA','0'*64),self.assertRaises(Denied):store()
        self.assertEqual(witness().call('status')['gross'],0)

    def test_second_model_rates_and_interrupted_fake_send(self):
        from backend.interpretation import InterpretationInput
        value=InterpretationInput(text='Coffee and museum in Baltimore on November 7, 2026')
        broker,model=self.broker(model='fictional-other@offline-v1');broker.interpret(value)
        self.assertEqual(witness().call('status')['gross'],len(inference_payload(value,'fictional-other@offline-v1'))*2+64*5)
        fixture();self.s=store();broker,model=self.broker()
        def lost(_):raise ConnectionError('fictional_uncertain_send')
        model.reply=lost
        with self.assertRaises(ConnectionError):broker.interpret(value)
        status=witness().call('status');self.assertGreater(status['gross'],0);self.assertTrue(status['quarantined'])
        self.assertEqual(self.s.snapshot()['attempts'],1)

    def test_missing_usage_retains_maximum_and_quarantines(self):
        from backend.interpretation import InterpretationInput
        broker,model=self.broker();model.reply=lambda p:reply(p,usage=False)
        with self.assertRaises(Denied):broker.interpret(InterpretationInput(text='Coffee and museum in Baltimore on November 7, 2026'))
        status=witness().call('status');self.assertGreater(status['gross'],0);self.assertTrue(status['quarantined'])


class ApplicationGrantTests(unittest.TestCase):
    # Existing actual planner/session tests, with only the inactive authority profile changed.
    fake=b.BridgeTests.fake
    initial=b.BridgeTests.initial
    advanced_fixture=b.BridgeTests.advanced_fixture
    test_ordinary_options_selection=b.BridgeTests.test_actual_ordinary_pipeline_financial_dispatch_and_options
    test_pending_date=b.BridgeTests.test_pending_date_answer_no_new_model_and_no_browser_snapshot_authority
    test_advanced_named_origin=b.BridgeTests.test_actual_advanced_date_area_origin_and_named_order
    test_optional_flexible=b.BridgeTests.test_optional_flexible_and_origin_advanced_workflows
    test_lookup=b.BridgeTests.test_lookup_and_starting_area_use_actual_typed_controls
    test_area=b.BridgeTests.test_actual_starting_area_resolution
    test_details=b.BridgeTests.test_contact_membership_and_single_use
    test_refresh=b.BridgeTests.test_refresh_specific_owner_decision_and_replay

    def setUp(self):
        self.enterContext(patch.object(b,'fixture',fixture));self.enterContext(patch.object(b,'store',store))
        b.BridgeTests.setUp(self)

    def make(self,model):
        def charged_response(payload):
            output=model.interpret(json.loads(payload)['input']).model_dump(mode='json')
            return reply(payload,output)
        charged=FakeInference(self.s,issuer_connection,counter_connection,f.ROOT,charged_response)
        broker=e.ApplicationEvidenceTests.make(self,charged)
        # Adapt the existing test composition; retain the same Broker/record closure.
        broker.__class__=GrantBroker
        broker._Broker__issuer=GrantIssuer(issuer_connection,f.ROOT,broker._Broker__issuer._records)
        charged.broker=broker
        return broker


def phase(mode):
    path=Path('/tmp/synthetic-grant-recovery')
    if mode in ('seed_restore','seed_crash'):
        fixture();s=store();l,c,p=maps(s)
        path.write_text(json.dumps({'token':l.session.token,'cap':c.token,'payload':p.decode(),'gross':17000}))
        if mode=='seed_crash':s.reserve(l,c,str(uuid4()))
    elif mode=='consume_restore':
        # The original test process ended: new worker gets new authority only via
        # a newly created server-owned action, never borrowing old HTTP ownership.
        s=store();perform(s,*maps(s));assert witness().call('status')['gross']==17000
    elif mode.startswith('detect_'):
        s=store()
        try:s.service.sync(s)
        except Denied:pass
        else:raise AssertionError('One-component rollback was accepted')
        status=witness().call('status');assert status['quarantined'] and status['quarantineExposure']==grant()['total']
        print(mode+': full grant quarantined, no new dispatch.')
    elif mode=='op_down':
        try:store()
        except Unavailable:print('Operational DB outage refused; external exposure retained.')
        else:raise AssertionError('Outage admitted')
    elif mode=='after_crash':
        s=store();assert s.snapshot()['gross']==17000;assert witness().call('status')['gross']==17000
        s.service.sync(s);assert s.snapshot()['states']=={'RESERVED':1}
        from experiments.shared_state.contracts import SessionHandle
        lease=s.claim(SessionHandle(json.loads(path.read_text())['token']),1)
        try:s.recover(lease)
        except Denied:pass
        else:raise AssertionError('Restart reconstructed lost Redis evidence')
        print('Operational SQL/witness restart retained full reserved exposure; Redis loss cannot reconstruct evidence.')


if __name__=='__main__':
    import sys
    if len(sys.argv)>1:phase(sys.argv[1])
    else:unittest.main()
