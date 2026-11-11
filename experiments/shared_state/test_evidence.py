"""Real local Redis/PG, invented evidence and fake transports only."""
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime,timezone
from hashlib import sha256
import json
import multiprocessing as mp
import os
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import patch
from uuid import uuid4
import psycopg
from psycopg.types.json import Jsonb

from experiments.shared_state import test_store as core,test_financial as f,test_bridge as b
from experiments.shared_state.contracts import Kind,Denied,Unavailable
from experiments.shared_state.bridge_models import ProviderAction
from experiments.shared_state.redis_evidence import EvidenceStore,EvidenceIssuer,EvidenceVerifier,RedisEvidence,Keys
from experiments.shared_state.evidence_models import VERSION,Membership,pack,unpack,model_types,data_view

EPOCH='a'*64
EPOCH_FILE=Path('/tmp/synthetic-restore-epoch')
KEY=bytes(reversed(range(32)))  # Synthetic ephemeral fixture, not real enrollment.


def epoch():return EPOCH_FILE.read_text()


def set_epoch(value):
    EPOCH_FILE.write_text(value);EPOCH_FILE.chmod(0o600)


def fixture():
    set_epoch(EPOCH)
    def install(c):
        c.execute(Path(__file__).with_name('bridge.sql').read_text(),prepare=False)
        c.execute(Path(__file__).with_name('evidence.sql').read_text(),prepare=False)
        c.execute('INSERT INTO synthetic_state.evidence_policy VALUES(1,%s,%s,%s)',('synthetic',EPOCH,VERSION))
        # Real absolute wall clock for Redis and SQL; original fixtures remain unchanged.
        c.execute('UPDATE synthetic_state.test_clock SET value=NULL')
    f.fixture(extension=install)
    e=cache();e.client.flushdb()  # Only this fresh isolated disposable Redis.


def cache(keys=None,maximum=128*1024*1024):
    return RedisEvidence(os.environ['SYNTHETIC_REDIS_PASSWORD'],keys or Keys('k1',{'k1':KEY}),maximum=maximum)


def store(e=None):
    return EvidenceStore(evidence=e or cache(),current_epoch=epoch,verifier=EvidenceVerifier(b.issuer_connection),key=core.KEY,
         password=os.environ['SYNTHETIC_WORKER_PASSWORD'],limits=f.LIMITS)


def ready(s,publish=True,ttl=600):
    action=ProviderAction(purpose='ordinary',sourceDigest='b'*64,interpretationDigest='c'*64,requestRevision=1)
    h=s.create(Kind.ACTION,action,ttl=ttl);l=s.claim(h,1)
    http=sha256(str(uuid4()).encode()).hexdigest()
    s._call('admit',id=http,worker=s._worker,domain='http',fingerprint=http)
    with b.issuer_connection() as c:c.execute('SELECT synthetic_state.register_action(%s,%s,NULL,NULL)',(s._hash(h.token,'session'),http))
    f.enroll(s,h);cap=s.issue(l,'provider_action',str(uuid4()));f.approve(s,cap,[f.item(key=h.token)])
    if publish:s.publish(l,{'ordinary':core.ordinary()},'synthetic_fresh',b.issuer_connection)
    return h,l,cap


def child_read(h,q):
    try:
        s=store();l=s.claim(h,1);q.put(s.recover(l)[0]['ordinary'].activities)
    except Exception as e:q.put(type(e).__name__)


def child_crash(h,cap):
    s=store();l=s.claim(h,1)
    # Existing HTTP lease belongs to the old worker; new worker cannot borrow it.
    try:s.reserve(l,cap,str(uuid4()))
    except Denied:os._exit(42)
    os._exit(43)


class EvidenceTests(unittest.TestCase):
    def setUp(self):fixture();self.s=store()

    def test_encrypted_typed_restart_no_sql_private_payload(self):
        h,l,_=ready(self.s);m=self.s.meta(l);blob=self.s.evidence.get(self.s.evidence.path('synthetic',EPOCH,m['session']))
        self.assertNotIn(b'Baltimore',blob);self.assertNotIn(b'coffee',blob)
        self.assertEqual(self.s.recover(l)[0]['ordinary'],core.ordinary())
        with core.admin() as c:
            payload=str(c.execute('SELECT payload FROM synthetic_state.evidence').fetchone()[0])
            self.assertNotIn('Baltimore',payload);self.assertNotIn('coffee',payload)
        ctx=mp.get_context('spawn');q=ctx.Queue();p=ctx.Process(target=child_read,args=(h,q));p.start();p.join(15)
        self.assertEqual(p.exitcode,0);self.assertEqual(q.get(timeout=2),['coffee','museum'])
        with self.assertRaises(Denied):self.s.recover(l)  # old worker fence lost

    def test_ciphertext_substitution_corruption_wrong_key_environment(self):
        _,l,_=ready(self.s);m=self.s.meta(l);path=self.s.evidence.path('synthetic',EPOCH,m['session']);blob=self.s.evidence.get(path)
        self.s.evidence.client.set(path,b'x'+blob[1:])
        with self.assertRaises(Denied):self.s.recover(l)
        self.s.evidence.client.set(path,blob)
        self.s.evidence.keys=Keys('k1',{'k1':b'0'*32})
        with self.assertRaises(Denied):self.s.recover(l)
        with self.assertRaises(Denied):self.s.evidence.path('production',EPOCH,m['session'])
        set_epoch('d'*64)
        with self.assertRaises(Denied):self.s.recover(l)

    def test_absolute_expiry_and_key_rotation_no_extension(self):
        _,l,_=ready(self.s);before=self.s.meta(l)['anchor']['expires_ms']
        self.s.evidence.keys=Keys('k2',{'k1':KEY,'k2':b'2'*32})
        self.assertEqual(self.s.publish(l,{'ordinary':core.ordinary()},'synthetic_fresh',b.issuer_connection,previous=1),2)
        self.assertLessEqual(self.s.meta(l)['anchor']['expires_ms'],before)
        self.s.evidence.keys=Keys('k2',{'k2':b'2'*32});self.s.recover(l)
        with self.assertRaises(Denied):self.s.publish(l,{'ordinary':core.ordinary()},'synthetic_fresh',b.issuer_connection,previous=1)
        fixture();s=store();_,l,_=ready(s);s.evidence.keys=Keys('k2',{'k2':b'2'*32})
        with self.assertRaises(Denied):s.recover(l)  # revoked old key

    def test_missing_redis_cannot_reserve_and_no_refund_after_loss(self):
        _,l,cap=ready(self.s);self.s.evidence.client.flushdb()
        with self.assertRaises(Denied):self.s.reserve(l,cap,str(uuid4()))
        self.assertEqual(self.s.snapshot()['attempts'],0)
        fixture();s=store();_,l,cap=ready(s);r=s.reserve(l,cap,str(uuid4()));s.transition(r,'INTENT')
        before=s.snapshot();s.evidence.client.flushdb()
        with self.assertRaises(Denied):f.dispatch(s,r,1)
        self.assertEqual(s.snapshot(),before)
        s.transition(r,'UNCERTAIN');self.assertGreater(s.snapshot()['gross'],0)
        with self.assertRaises(Denied):s.reserve(l,cap,str(uuid4()))

    def test_restore_older_snapshot_epoch_mismatch_never_reuses_capability(self):
        _,l,cap=ready(self.s);r=self.s.reserve(l,cap,str(uuid4()));self.s.transition(r,'INTENT');self.s._call('dispatch',**self.s._lease(l),capability=self.s._hash(cap.token,'cap'),operation=r.operation,ordinal=1,payload_digest=sha256(l.session.token.encode()).hexdigest())
        # Real SQL export before reserve is separately exercised by harness below.
        # Mandatory external epoch changes on restore, old SQL epoch cannot enroll itself.
        set_epoch('e'*64)
        for fn in [lambda:self.s.recover(l),lambda:self.s.reserve(l,cap,str(uuid4())),lambda:self.s.snapshot()]:
            with self.assertRaises(Denied):fn()
        with core.admin() as c:self.assertGreater(c.execute('SELECT sum(charge) FROM synthetic_state.operations').fetchone()[0],0)

    def test_runtime_cannot_modify_anchors_epoch_or_call_old_front_doors(self):
        _,l,_=ready(self.s)
        for sql in ['DELETE FROM synthetic_state.evidence_anchors','UPDATE synthetic_state.evidence_policy SET epoch=repeat(\'e\',64)',
                    "SELECT synthetic_state.bridge_protocol('snapshot','{}')","SELECT synthetic_state.financial_protocol('snapshot','{}')",
                    "SELECT synthetic_state.protocol('snapshot','{}')","SET ROLE whereto_synthetic_owner",
                    "SELECT synthetic_state.evidence_anchor('',1,0,'','',0,'','')"]:
            with self.subTest(sql=sql),self.assertRaises(psycopg.Error),psycopg.connect(**self.s._connection) as c:c.execute(sql)
        for payload in [dict(purpose=None,sourceDigest='b'*64,interpretationDigest='c'*64,requestRevision=1),dict(purpose='ordinary',sourceDigest=10**63,interpretationDigest='c'*64,requestRevision=1)]:
            with self.assertRaises(psycopg.Error),psycopg.connect(**self.s._connection) as c:
                args=dict(session='e'*64,kind='provider_action',binding='f'*64,payload=payload,ttl=1800)
                c.execute("SELECT synthetic_state.evidence_protocol('create',%s,'synthetic',%s,NULL)",(Jsonb(args),EPOCH))
        # Even direct wrapper calls cannot omit the committed proof.
        with self.assertRaises(psycopg.Error),psycopg.connect(**self.s._connection) as c:
            c.execute("SELECT synthetic_state.evidence_protocol('reserve',%s,'synthetic',%s,NULL)",
                (Jsonb(dict(**self.s._lease(l),capability='f'*64,operation=str(uuid4()))),EPOCH))

    def test_competing_publications_cas_and_torn_commit_fail_closed(self):
        _,l,_=ready(self.s);results=[];barrier=threading.Barrier(2)
        def publish():
            try:
                barrier.wait();self.s.publish(l,{'ordinary':core.ordinary()},'synthetic_fresh',b.issuer_connection,previous=1);results.append('ok')
            except Denied:results.append('denied')
        threads=[threading.Thread(target=publish) for _ in range(2)]
        for t in threads:t.start()
        for t in threads:t.join(5)
        self.assertEqual(sorted(results),['denied','ok']);self.s.recover(l)
        @contextmanager
        def broken():raise RuntimeError('fictional commit failure');yield
        with self.assertRaises(Denied):self.s.publish(l,{'ordinary':core.ordinary()},'synthetic_fresh',broken,previous=2)
        with self.assertRaises(Denied):self.s.recover(l)

    def test_capacity_and_unsupported_objects_or_real_content_refuse(self):
        _,l,_=ready(self.s)
        for records,provenance in [({'ordinary':threading.Lock()},'synthetic_fresh'),({'ordinary':core.ordinary()},'google'),
                                   ({'raw':__import__('backend.ai',fromlist=['Interpretation']).Interpretation(activities=['coffee'],budget_per_person=None,date=None,location=None,preferences=[])},'synthetic_pending_effective')]:
            with self.assertRaises(Denied):pack(records,provenance)
        raw=pack({'ordinary':core.ordinary()},'synthetic_fresh')
        with self.assertRaises(Denied):unpack(raw.replace(b'"records":',b'"version":"duplicate","records":'))
        # Global namespace byte budget, not a per-process counter.
        s=store(cache(maximum=65536));_,l,_=ready(s)
        path=s.evidence.path('synthetic',EPOCH,'f'*64)
        with self.assertRaises(Denied):s.evidence.publish(path,None,b'x'*65536,int(time.time()*1000)+600000)

    def test_expiry_revision_revocation_and_duplicate_capability(self):
        h,l,cap=ready(self.s,ttl=1);time.sleep(1.05)
        with self.assertRaises(Denied):self.s.recover(l)
        fixture();s=store();h,l,cap=ready(s);r=s.reserve(l,cap,str(uuid4()))
        with self.assertRaises(Denied):s.reserve(l,cap,str(uuid4()))
        s.transition(r,'UNCERTAIN');s.revoke(h,1)
        with self.assertRaises(Denied):s.recover(l)
        fixture();s=store();h,l,_=ready(s);s.revise(h,1,Kind.ACTION,ProviderAction(purpose='ordinary',sourceDigest='b'*64,interpretationDigest='d'*64,requestRevision=2))
        with self.assertRaises(Denied):s.recover(l)
        l2=s.claim(h,2)
        with self.assertRaises(Denied):s.recover(l2)

    def test_process_death_cannot_borrow_admission_or_erase_charge(self):
        h,l,cap=ready(self.s);r=self.s.reserve(l,cap,str(uuid4()));self.s.transition(r,'INTENT');before=self.s.snapshot()['gross']
        ctx=mp.get_context('spawn');p=ctx.Process(target=child_crash,args=(h,cap));p.start();p.join(15)
        self.assertEqual(p.exitcode,42);self.assertEqual(self.s.snapshot()['gross'],before)
        self.assertEqual(self.s.snapshot()['states'],{'UNCERTAIN':1})

    def test_persistent_checkpoint_revalidates_pending_after_action_completion(self):
        from experiments.shared_state.evidence_recovery import CheckpointIssuer,restore_interpretation
        from backend.interpretation import InterpretationInput,ClarificationAnswers
        from backend.testing_clock import calendar_clock
        from backend.provider_budget import ProviderBudget
        from experiments.shared_state.action_bridge import Broker,LocalIssuer
        with calendar_clock(b.NOW),patch.dict(os.environ,b.ENV,clear=False),patch('requests.sessions.Session.send',side_effect=AssertionError('No provider')):
            model=b.Model(dict(activities=['coffee','museum'],location='Baltimore',date=None,budget_per_person=None,preferences=[]))
            broker=Broker(self.s,LocalIssuer(b.issuer_connection,f.ROOT),model,ProviderBudget(),None,now=b.NOW)
            token,result=broker.interpret(InterpretationInput(text='Coffee and museum in Baltimore',calendarTimezone='America/New_York'))
            self.assertIsNotNone(result.pending)
            original=broker._source(token)
            with patch('experiments.shared_state.evidence_recovery.monotonic',return_value=original.created+590):
                h=CheckpointIssuer(b.issuer_connection,f.ROOT,str(uuid4())).capture(self.s,broker,token,b.NOW)
            restarted=store();l=restarted.claim(h,1)
            self.assertLessEqual(restarted.meta(l)['anchor']['expires_ms'],int(time.time()*1000)+10000)
            restored=restore_interpretation(restarted,l,answers=ClarificationAnswers(date='2026-11-07'))
            self.assertIsNotNone(restored.request);self.assertEqual(model.calls,1)
            cap=restarted.issue(l,'provider_action',str(uuid4()))
            with self.assertRaises(Denied):restarted.reserve(l,cap,str(uuid4()))
            self.assertEqual(restarted.snapshot()['attempts'],0)

    def test_route_observation_cannot_gain_freshness_by_republication_or_clock_skew(self):
        from backend.routes import RouteResult,RouteLeg
        _,l,_=ready(self.s,publish=False)
        now=self.s._call('evidence_clock')['now_ms']
        leg=RouteLeg(origin_id='synthetic_a',destination_id='synthetic_b',mode='walk',status='unreachable',estimate_type='walking',observed_at=datetime.fromtimestamp((now-1000)/1000,timezone.utc))
        route=RouteResult(legs=[leg],matrix_elements=1,matrix_requests=1)
        self.s.publish(l,{'route':route},'synthetic_fresh',b.issuer_connection)
        self.assertLessEqual(self.s.meta(l)['anchor']['expires_ms'],now+299000)
        for stamp in [None,datetime(2020,1,1),datetime.fromtimestamp((now-400000)/1000,timezone.utc),datetime.fromtimestamp((now+600000)/1000,timezone.utc)]:
            altered=route.model_copy(update={'legs':[leg.model_copy(update={'observed_at':stamp})]})
            with self.assertRaises(Denied):self.s.publish(l,{'route':altered},'synthetic_fresh',b.issuer_connection,previous=1)

    def test_unknown_source_build_and_manifest_refuse_before_authority(self):
        from experiments.shared_state import evidence_identity as identity
        self.assertEqual(identity.verify()['identity'],VERSION)
        with patch.object(identity,'MANIFEST_SHA','0'*64),self.assertRaises(Denied):store()

    def test_noeviction_memory_error_refuses_publication_without_financial_reset(self):
        _,l,cap=ready(self.s);r=self.s.reserve(l,cap,str(uuid4()));before=self.s.snapshot()
        self.s.evidence.client.config_set('maxmemory',1)
        try:
            with self.assertRaises(Unavailable):self.s.publish(l,{'ordinary':core.ordinary()},'synthetic_fresh',b.issuer_connection,previous=1)
            self.assertEqual(self.s.snapshot(),before)
        finally:self.s.evidence.client.config_set('maxmemory',64*1024*1024)
        self.s.transition(r,'UNCERTAIN');self.assertEqual(self.s.snapshot()['gross'],before['gross'])

    def test_contact_and_refresh_membership_keep_native_1800_second_boundary(self):
        action=ProviderAction(purpose='details',sourceDigest='b'*64,interpretationDigest='c'*64,requestRevision=1)
        h=self.s.create(Kind.ACTION,action,ttl=1800);l=self.s.claim(h,1)
        membership=Membership(purpose='details',documentDigest='d'*64,selectedId='selected',allowedIds=['synthetic_venue'])
        self.s.publish(l,{'membership':membership},'synthetic_refresh',b.issuer_connection)
        before=self.s.meta(l)['anchor']['expires_ms']
        self.assertGreater(before,int(time.time()*1000)+1700000)
        self.s.recover(l)
        self.s.publish(l,{'membership':membership},'synthetic_refresh',b.issuer_connection,previous=1)
        self.assertLessEqual(self.s.meta(l)['anchor']['expires_ms'],before)
        # Stored membership is not a current refresh/Details provider grant.
        cap=self.s.issue(l,'provider_action',str(uuid4()))
        with self.assertRaises(Denied):self.s.reserve(l,cap,str(uuid4()))
        with self.assertRaises(Denied):self.s.create(Kind.ACTION,action.model_copy(update={'purpose':'ordinary'}),ttl=1800)
        EPOCH_FILE.unlink()
        with self.assertRaises(Unavailable):self.s.snapshot()

    def test_local_tls_auth_hostname_and_noeviction_configuration(self):
        import redis
        options=dict(retry=redis.retry.Retry(redis.backoff.NoBackoff(),0),port=6380,password=os.environ['SYNTHETIC_REDIS_PASSWORD'],ssl=True,
            ssl_cert_reqs='required',ssl_check_hostname=True,ssl_ca_certs='/tmp/synthetic-redis-ca.crt',socket_timeout=1,socket_connect_timeout=1)
        adapter=RedisEvidence(os.environ['SYNTHETIC_REDIS_PASSWORD'],Keys('k1',{'k1':KEY}),tls_ca='/tmp/synthetic-redis-ca.crt')
        client=adapter.client
        self.assertTrue(client.ping());self.assertEqual(client.config_get('maxmemory-policy')['maxmemory-policy'],'noeviction')
        self.assertEqual(client.config_get('appendonly')['appendonly'],'no')
        with self.assertRaises(redis.RedisError):redis.Redis(host='localhost',**options).ping()
        with self.assertRaises(redis.RedisError):redis.Redis(host='127.0.0.1',**{**options,'password':'fictional-wrong-password'}).ping()
        with self.assertRaises(redis.RedisError):redis.Redis(host='127.0.0.1',**{**options,'ssl_ca_certs':None}).ping()
        client.close()

    def test_exact_single_use_attestation_not_digest_expiry_or_worker_forgery(self):
        _,l,cap=ready(self.s)
        args=dict(**self.s._lease(l),capability=self.s._hash(cap.token,'cap'),operation=str(uuid4()))
        nonce=self.s._verifier.authorize(self.s,l,'reserve',args)
        def raw(p,proof):
            with psycopg.connect(**self.s._connection) as c:
                return c.execute("SELECT synthetic_state.evidence_protocol('reserve',%s,'synthetic',%s,%s)",(Jsonb(p),EPOCH,proof)).fetchone()
        with self.assertRaises(psycopg.Error):raw({**args,'operation':str(uuid4())},nonce)
        with self.assertRaises(psycopg.Error):raw(args,self.s.meta(l)['anchor']['commitment'])
        raw(args,nonce)
        with self.assertRaises(psycopg.Error):raw(args,nonce)
        self.assertEqual(self.s.snapshot()['attempts'],1)
        with self.assertRaises(psycopg.Error),psycopg.connect(**self.s._connection) as c:
            c.execute("SELECT synthetic_state.evidence_attest(%s,'reserve',%s,%s,'synthetic',%s)",('1'*64,Jsonb(args),self.s.meta(l)['anchor']['commitment'],EPOCH))
        fixture();s=store();_,l,cap=ready(s);args=dict(**s._lease(l),capability=s._hash(cap.token,'cap'),operation=str(uuid4()))
        nonce=s._verifier.authorize(s,l,'reserve',args);time.sleep(5.05)
        with self.assertRaises(psycopg.Error),psycopg.connect(**s._connection) as c:
            c.execute("SELECT synthetic_state.evidence_protocol('reserve',%s,'synthetic',%s,%s)",(Jsonb(args),EPOCH,nonce))
        self.assertEqual(s.snapshot()['attempts'],0)

    def test_actual_pending_options_selected_and_route_dtos_roundtrip(self):
        from backend.interpretation import InterpretationInput,ClarificationAnswers,interpret_request
        from backend.real_planning import PlannerInput
        from backend.saved_plans import Receipts,SaveRequest
        from backend.ranking import recommend_plans
        from backend.models import PlanningRequest
        from backend.testing_clock import calendar_clock
        from backend.ai import Interpretation
        from backend.routes import RouteResult
        class Fake:
            calls=0
            def interpret(self,text):
                self.calls+=1
                return Interpretation(activities=['coffee','museum'],location='Baltimore',date=None,budget_per_person=None,preferences=[])
        model=Fake()
        with calendar_clock():
            result=interpret_request(InterpretationInput(text='Coffee and museum in Baltimore',calendarTimezone='America/New_York'),model,now=b.NOW)
            _,l,_=ready(self.s,publish=False)
            self.s.publish(l,{'pending_effective':result.pending},'synthetic_pending_effective',b.issuer_connection)
            pending=self.s.recover(l)[0]['pending_effective']
            answer=interpret_request(InterpretationInput(text=pending.text,pending=pending,answers=ClarificationAnswers(date='2026-11-07'),calendarTimezone='America/New_York'),model,now=b.NOW)
            self.assertEqual(model.calls,1)
            request=PlannerInput.model_validate(answer.request.model_dump())
            ranked=recommend_plans(PlanningRequest.model_validate(request.model_dump(exclude={'locationFirst','searchRadius'})))
            receipts=Receipts();issued=receipts.issue(ranked);plans=issued.plans+issued.provisionalPlans
            selected=receipts.select(SaveRequest(receipt=issued.saveReceipt,accessToken=issued.saveAccessToken,candidateIds=[x.candidate.id for x in plans],selectedId=plans[0].candidate.id))
            records={'ordinary':request,'options':ranked,'selected':selected,'route':RouteResult(legs=[],matrix_elements=0,matrix_requests=0)}
            _,l2,_=ready(self.s,publish=False)
            self.s.publish(l2,records,'synthetic_fresh',b.issuer_connection)
            got,_=self.s.recover(l2)
            self.assertEqual(pack(got,'synthetic_fresh'),pack(records,'synthetic_fresh'))
            self.assertLessEqual(self.s.meta(l2)['anchor']['expires_ms'],int(time.time()*1000)+300000)
            self.assertEqual(got['selected'].selectedId,plans[0].candidate.id)
            with self.assertRaises(Denied):pack({'pending_effective':pending},'synthetic_fresh')
            with self.assertRaises(Denied):self.s.create(Kind.PENDING,pending)

    def test_actual_advanced_result_and_handoff_are_evidence_not_planning_authority(self):
        from backend.test_advanced_planning import IntegrationTests
        from backend.test_advanced_routing import start
        from backend.ai import Interpretation
        from backend.journey import Journey
        from backend.interpretation import InterpretationResult,InterpretationContext
        fixture_test=IntegrationTests('test_named_roundtrip_dto_and_receipt');fixture_test.setUp()
        try:
            session=fixture_test.session(endpoint={'kind':'origin','source':'return to start'})
            result=fixture_test.run_session(session,startingLocation=start())
            handoff=InterpretationResult(interpretation=Interpretation(activities=['coffee'],budget_per_person=None,date=None,location=None,preferences=[],journey=Journey(stops=[{'source':'coffee'}])),request=None,notes=[],issues=[],executionStatus='advanced_unavailable',context=InterpretationContext())
            _,l,_=ready(self.s,publish=False)
            with self.assertRaises(Denied):pack({'advanced_results':result},'synthetic_fresh')
            records={'advanced_handoff':handoff,'advanced_results':data_view(result)}
            self.s.publish(l,records,'synthetic_fresh',b.issuer_connection)
            self.assertEqual(pack(self.s.recover(l)[0],'synthetic_fresh'),pack(records,'synthetic_fresh'))
            self.assertEqual(self.s.snapshot()['attempts'],0)
            with self.assertRaises(Denied):pack({'options':session},'synthetic_fresh')
        finally:fixture_test.doCleanups()


class ApplicationEvidenceTests(unittest.TestCase):
    fake=b.BridgeTests.fake
    initial=b.BridgeTests.initial
    advanced_fixture=b.BridgeTests.advanced_fixture
    test_ordinary_options=b.BridgeTests.test_actual_ordinary_pipeline_financial_dispatch_and_options
    test_pending_date=b.BridgeTests.test_pending_date_answer_no_new_model_and_no_browser_snapshot_authority
    test_advanced=b.BridgeTests.test_actual_advanced_date_area_origin_and_named_order
    test_optional_flexible=b.BridgeTests.test_optional_flexible_and_origin_advanced_workflows
    test_lookup_area=b.BridgeTests.test_actual_starting_area_resolution
    test_place_lookup=b.BridgeTests.test_lookup_and_starting_area_use_actual_typed_controls
    test_refresh=b.BridgeTests.test_refresh_specific_owner_decision_and_replay
    test_contact=b.BridgeTests.test_contact_membership_and_single_use
    test_uncertain=b.BridgeTests.test_interrupted_fake_transport_no_retry
    test_changed_payload=b.BridgeTests.test_changed_payload_after_reservation_retains_uncertainty
    test_contradiction=b.BridgeTests.test_contradictory_source_never_creates_advanced_session_or_search
    test_edit=b.BridgeTests.test_source_edit_invalidation_and_tampered_internal_snapshot

    # Deliberate limited application-contract composition, not replacement historical tests.
    def setUp(self):
        self.enterContext(patch.object(b,'fixture',fixture));self.enterContext(patch.object(b,'store',store))
        b.BridgeTests.setUp(self)

    def make(self,model):
        from experiments.shared_state.action_bridge import Broker
        from backend.provider_budget import ProviderBudget,ProviderSettings
        broker=None
        def records():
            a=broker._Broker__current
            values=[a['source'],a['interpretation']];out={}
            def add(v):
                if isinstance(v,(list,tuple)):
                    for x in v:add(x)
                else:
                    from backend.interpretation import InterpretationResult
                    if type(v) is InterpretationResult:
                        out['interpretation_result']=v;return
                    for k,t in model_types().items():
                        if type(v) is t:out[k]=v;break
            for v in values:add(v)
            if a['purpose']=='refresh':
                document=a['interpretation'];selected=next(i for i in document['itineraries'] if i['candidateId']==document['selectedId'])
                out={'membership':Membership(purpose='refresh',documentDigest=broker._digest(document),selectedId=str(document['selectedId']),allowedIds=[x['reference'] for x in selected['stops']])}
            if not out:raise Denied('unsupported_session_snapshot')
            pending=out.get('request') is not None and out['request'].pending is not None
            return out,'synthetic_refresh' if a['purpose']=='refresh' else 'synthetic_pending_effective' if pending else 'synthetic_fresh'
        broker=Broker(self.s,EvidenceIssuer(b.issuer_connection,f.ROOT,records),model,
                      ProviderBudget(ProviderSettings(mode='real',candidates_per_activity=3)),self.fake,now=b.NOW)
        return broker



def phase(mode):
    path=Path('/tmp/evidence-restart-fixture')
    if mode=='restore_seed':
        fixture();s=store();h,l,cap=ready(s)
        path.write_text(json.dumps({'token':h.token,'cap':cap.token}));path.chmod(0o600)
    elif mode=='restore_consume':
        from experiments.shared_state.contracts import SessionHandle,Capability
        data=json.loads(path.read_text());s=store();l=s.claim(SessionHandle(data['token']),1)
        # Claim fences the former worker: refresh only the synthetic active HTTP owner
        # through fixture admin to simulate the same authorized worker's reservation.
        with core.admin() as c:c.execute('UPDATE synthetic_state.admission_leases SET worker=%s WHERE refs>0',(s._worker,))
        r=s.reserve(l,Capability(data['cap']),str(uuid4()));s.transition(r,'INTENT')
        assert s.snapshot()['gross']>0
        set_epoch('e'*64)  # external protected restore procedure, not the restored SQL
    elif mode=='restored_old_sql':
        with core.admin() as c:assert c.execute('SELECT count(*) FROM synthetic_state.operations').fetchone()[0]==0
        try:store()
        except Denied:print('Actual older synthetic SQL snapshot restored; independent epoch mismatch blocks replay.')
        else:raise AssertionError('Restored old authority accepted')
    elif mode=='seed':
        fixture();s=store();h,l,cap=ready(s);r=s.reserve(l,cap,str(uuid4()));s.transition(r,'INTENT')
        path.write_text(json.dumps({'token':h.token,'gross':s.snapshot()['gross']}));path.chmod(0o600)
        print('Seeded synthetic charged INTENT; no provider used.')
    elif mode=='redis_down':
        s=store();from experiments.shared_state.contracts import SessionHandle
        l=s.claim(SessionHandle(json.loads(path.read_text())['token']),1)
        try:s.recover(l)
        except Unavailable:print('Redis outage refuses with SQL exposure retained.')
        else:raise AssertionError('Redis outage admitted')
    elif mode=='sql_down':
        try:store()
        except Unavailable:print('SQL outage refuses without memory fallback.')
        else:raise AssertionError('SQL outage admitted')
    else:
        s=store();data=json.loads(path.read_text());assert s.snapshot()['gross']==data['gross']
        from experiments.shared_state.contracts import SessionHandle
        l=s.claim(SessionHandle(data['token']),1)
        try:s.recover(l)
        except Denied:print('Evidence loss refuses; restart retained financial charge.')
        else:raise AssertionError('Lost Redis admitted')


if __name__=='__main__':
    import sys
    if len(sys.argv)>1:phase(sys.argv[1])
    else:unittest.main()
