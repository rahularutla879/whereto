"""Only executed in a disposable, network-isolated synthetic PostgreSQL fixture."""
from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
import multiprocessing as mp
import os
from pathlib import Path
import unittest
from uuid import uuid4
from unittest.mock import patch

import psycopg
from psycopg.types.json import Jsonb

from experiments.shared_state.contracts import *
from experiments.shared_state.postgres import LocalPostgres

KEY = bytes(range(32))  # Fictional test key. Not a real signer/enrollment.
DEFAULT = Limits(100, 80, 10, 8)


def admin():
    return psycopg.connect(host='127.0.0.1', dbname='whereto_synthetic', user='whereto_synthetic_admin',
                           password=os.environ['SYNTHETIC_ADMIN_PASSWORD'], connect_timeout=2)


def fixture(limits=DEFAULT, extension=None):
    # Reset only between independent synthetic test cases, NEVER recovery.
    with admin() as c:
        c.execute('DROP SCHEMA IF EXISTS synthetic_state CASCADE')
        c.execute('SET LOCAL ROLE whereto_synthetic_owner')
        c.execute(Path(__file__).with_name('schema.sql').read_text(), prepare=False)
        c.execute('INSERT INTO synthetic_state.policy VALUES(1,%s,%s,%s)',
                  (VERSION, digest(KEY,'key',VERSION), Jsonb(asdict(limits))))
        c.execute(Path(__file__).with_name('routines.sql').read_text(), prepare=False)
        if extension is not None:extension(c)  # Atomic synthetic bootstrap; never runtime input.


def store(limits=DEFAULT, key=KEY):
    return LocalPostgres(key=key, password=os.environ['SYNTHETIC_WORKER_PASSWORD'], limits=limits)


def ordinary():
    from backend.real_planning import PlannerInput
    return PlannerInput(activities=['coffee','museum'], location='Baltimore',date='2026-11-17',planningMode='surprise')


def ready(s, payload=None):
    h=s.create(Kind.ORDINARY,payload or ordinary())
    lease=s.claim(h,1)
    return h,lease,s.issue(lease,'ordinary_plan',str(uuid4()))


def child_reserve(lease, cap, limits, barrier, queue):
    try:
        s=store(limits);lease=s.claim(lease.session,lease.revision);barrier.wait(timeout=10)
        s.reserve(lease,cap,str(uuid4()),'synthetic_maps',60)
        queue.put('reserved')
    except Denied:queue.put('denied')
    except Exception as error:queue.put(type(error).__name__)


def child_crash(lease, cap, phase):
    s=store();lease=s.claim(lease.session,lease.revision);op=str(uuid4())
    if phase=='before_commit':
        with s._tx() as c:
            s._invoke(c,'claim',dict(session=s._hash(lease.session.token,'session'),revision=lease.revision,worker=s._worker))
            os._exit(41)  # real open transaction: PostgreSQL must roll back
    r=s.reserve(lease,cap,op,'synthetic_maps',30)
    if phase=='after_intent':s.transition(r,'INTENT')
    if phase=='after_outcome':
        s.transition(r,'INTENT');s.transition(r,'SUCCEEDED')
    os._exit(42)


class SharedPostgresTests(unittest.TestCase):
    def setUp(self):fixture()

    def test_restart_and_all_terminal_costs_are_retained(self):
        s=store();h,l,cap=ready(s);r=s.reserve(l,cap,str(uuid4()),'synthetic_maps',30)
        self.assertFalse(r.planning_authorized)
        restarted=store()
        with self.assertRaises(Denied):restarted.read(l)
        with self.assertRaises(Denied):restarted.transition(r,'INTENT')
        current=restarted.claim(h,1)
        self.assertEqual(restarted.read(current),ordinary())
        self.assertEqual(restarted.snapshot()['states'],{'UNCERTAIN':1})
        self.assertEqual(restarted.snapshot()['gross'],30)
        with self.assertRaises(Denied):restarted.reserve(current,cap,str(uuid4()),'synthetic_maps',1)
        # A known failed attempt is also charged after restart; no refund.
        fixture();s=store();_,l,cap=ready(s);r=s.reserve(l,cap,str(uuid4()),'synthetic_maps',30)
        s.transition(r,'INTENT');s.transition(r,'FAILED')
        self.assertEqual(store().snapshot()['gross'],30)
        with self.assertRaises(Denied):s.transition(r,'INTENT')

    def test_two_actual_processes_cannot_exceed_financial_cap(self):
        limits=Limits(100,100,20,20,2);fixture(limits);s=store(limits)
        _,l1,c1=ready(s);_,l2,c2=ready(s)
        ctx=mp.get_context('spawn');barrier=ctx.Barrier(2);queue=ctx.Queue()
        ps=[ctx.Process(target=child_reserve,args=(l,c,limits,barrier,queue)) for l,c in [(l1,c1),(l2,c2)]]
        for p in ps:p.start()
        for p in ps:
            p.join(15);self.assertEqual(p.exitcode,0)
        self.assertEqual(sorted([queue.get(timeout=2),queue.get(timeout=2)]),['denied','reserved'])
        self.assertEqual(s.snapshot()['gross'],60)

    def test_two_processes_consume_one_capability_once(self):
        limits=Limits(1000,1000,20,20,2);fixture(limits);s=store(limits);_,l,cap=ready(s)
        ctx=mp.get_context('spawn');barrier=ctx.Barrier(2);q=ctx.Queue()
        ps=[ctx.Process(target=child_reserve,args=(l,cap,limits,barrier,q)) for _ in range(2)]
        for p in ps:p.start()
        for p in ps:p.join(15);self.assertEqual(p.exitcode,0)
        self.assertEqual(sorted([q.get(timeout=2),q.get(timeout=2)]),['denied','reserved'])
        self.assertEqual(s.snapshot()['attempts'],1)

    def test_fence_and_uncertainty_never_allow_another_send(self):
        s=store();h,l,cap=ready(s);r=s.reserve(l,cap,str(uuid4()),'synthetic_maps',30);s.transition(r,'INTENT')
        newer=s.claim(h,1)
        for action in [lambda:s.read(l),lambda:s.transition(r,'SUCCEEDED'),lambda:s.issue(l,'ordinary_plan',str(uuid4()))]:
            with self.assertRaises(Denied):action()
        self.assertEqual(s.snapshot()['states'],{'UNCERTAIN':1})
        cap2=s.issue(newer,'ordinary_plan',str(uuid4()))
        with self.assertRaises(Denied):s.reserve(newer,cap2,str(uuid4()),'synthetic_maps',1)
        self.assertEqual(s.snapshot()['gross'],30)

    def test_expiry_revocation_revision_and_absolute_lifetime(self):
        s=store();h,l,cap=ready(s)
        before=None
        with admin() as c:before=c.execute('SELECT expires FROM synthetic_state.sessions').fetchone()[0]
        p=ordinary().model_copy(update={'location':'New York'});self.assertEqual(s.revise(h,1,Kind.ORDINARY,p),2)
        with self.assertRaises(Denied):s.reserve(l,cap,str(uuid4()),'synthetic_maps',1)
        with admin() as c:self.assertEqual(c.execute('SELECT expires FROM synthetic_state.sessions').fetchone()[0],before)
        l2=s.claim(h,2);self.assertEqual(s.read(l2).location,'New York');s.revoke(h,2)
        with self.assertRaises(Denied):s.read(l2)
        h,l,_=ready(s)
        with admin() as c:c.execute("UPDATE synthetic_state.sessions SET expires=clock_timestamp()-interval '1 second'")
        with self.assertRaises(Denied):s.read(l)

    def test_evidence_loss_and_tampering_fail_closed(self):
        s=store();h,l,cap=ready(s);r=s.reserve(l,cap,str(uuid4()),'synthetic_maps',30)
        with admin() as c:c.execute("UPDATE synthetic_state.evidence SET payload=jsonb_set(payload,'{location}','\"other\"')")
        with self.assertRaises(Denied):s.read(l)
        with admin() as c:c.execute('DELETE FROM synthetic_state.evidence')
        with self.assertRaises(Denied):s.transition(r,'INTENT')
        self.assertEqual(s.snapshot()['gross'],30)

    def test_wrong_key_policy_and_remote_configuration_refuse(self):
        with self.assertRaises(Denied):store(key=b'x'*32)
        with self.assertRaises(Denied):store(Limits(101,80,10,8))
        with self.assertRaises(Denied):LocalPostgres(key=KEY,password='synthetic',limits=DEFAULT,host='db.example.invalid')
        with admin() as c:c.execute('DELETE FROM synthetic_state.gate')
        with self.assertRaises(Denied):store()

    def test_forged_cross_session_capability_and_action_replay(self):
        s=store();h,l,cap=ready(s);_,other,_=ready(s)
        for candidate in [Capability('x'*43),cap]:
            with self.assertRaises(Denied):s.reserve(other,candidate,str(uuid4()),'synthetic_maps',1)
        with self.assertRaises(Denied):s.read(replace(l,worker=str(uuid4())))
        action=str(uuid4());s.issue(l,'ordinary_plan',action)
        with self.assertRaises(Denied):s.issue(l,'ordinary_plan',action)
        self.assertEqual(s.snapshot()['attempts'],0)
        operation=str(uuid4())
        r=s.reserve(l,cap,operation,'synthetic_maps',1)
        s.transition(r,'INTENT');s.transition(r,'SUCCEEDED')
        # Current worker and completed operation: refusal must come from durable
        # operation/capability uniqueness, not stale fencing or active capacity.
        with self.assertRaises(Denied):s.reserve(l,cap,str(uuid4()),'synthetic_maps',1)
        cap2=s.issue(l,'ordinary_plan',str(uuid4()))
        with self.assertRaises(Denied):s.reserve(l,cap2,operation,'synthetic_maps',1)
        self.assertEqual(s.snapshot()['attempts'],1)

    def test_invalid_amount_attempt_and_provider_caps(self):
        limits=Limits(100,30,1,1,2);fixture(limits);s=store(limits);_,l,cap=ready(s)
        for charge in [-1,True,10**13]:
            with self.assertRaises(Denied):s.reserve(l,cap,str(uuid4()),'synthetic_maps',charge)
        with self.assertRaises(Denied):s.reserve(l,cap,str(uuid4()),'synthetic_maps',31)
        r=s.reserve(l,cap,str(uuid4()),'synthetic_maps',30);s.transition(r,'INTENT');s.transition(r,'SUCCEEDED')
        _,l,cap=ready(s)
        with self.assertRaises(Denied):s.reserve(l,cap,str(uuid4()),'synthetic_ai',0)
        self.assertEqual(s.snapshot()['gross'],30)

    def test_worker_role_cannot_mutate_immutable_anchors(self):
        s=store();_,l,cap=ready(s);r=s.reserve(l,cap,str(uuid4()),'synthetic_maps',30)
        for table in ['operations','facts','capabilities','policy']:
            with self.assertRaises(psycopg.Error):
                with psycopg.connect(**s._connection) as c:c.execute('DELETE FROM synthetic_state.'+table)
        with self.assertRaises(psycopg.Error):
            with admin() as c:c.execute('UPDATE synthetic_state.operations SET charge=0')
        self.assertEqual(s.snapshot()['gross'],30)

    def test_explicit_isolation_and_missing_facts_cannot_restore_capacity(self):
        s=store()
        with s._tx() as c:self.assertEqual(c.execute('SHOW transaction_isolation').fetchone()['transaction_isolation'],'read committed')
        _,lease,cap=ready(s);s.reserve(lease,cap,str(uuid4()),'synthetic_maps',30)
        # Privileged fixture fault injection only; the application role cannot truncate.
        with self.assertRaises(psycopg.Error):
            with psycopg.connect(**s._connection) as c:c.execute('TRUNCATE synthetic_state.facts')
        with admin() as c:c.execute('TRUNCATE synthetic_state.facts')
        with self.assertRaises(Denied):s.snapshot()
        with self.assertRaises(Denied):store()
        with admin() as c:self.assertEqual(c.execute('SELECT sum(charge) FROM synthetic_state.operations').fetchone()[0],30)

    def test_lock_timeout_is_unavailable_without_fallback(self):
        s=store();_,l,cap=ready(s);s.reserve(l,cap,str(uuid4()),'synthetic_maps',30)
        with admin() as c:
            c.execute('SELECT id FROM synthetic_state.gate FOR UPDATE')
            with self.assertRaises(Unavailable):s.snapshot()
        self.assertEqual(s.snapshot()['gross'],30)

    def test_process_exit_before_and_after_durable_phases(self):
        for phase,state in [('before_commit',None),('after_reservation','RESERVED'),('after_intent','INTENT'),('after_outcome','SUCCEEDED')]:
            with self.subTest(phase=phase):
                fixture();s=store();h,l,cap=ready(s)
                ctx=mp.get_context('spawn');p=ctx.Process(target=child_crash,args=(l,cap,phase));p.start();p.join(15)
                self.assertIn(p.exitcode,(41,42));snap=store().snapshot()
                self.assertEqual(snap['gross'],0 if state is None else 30)
                self.assertEqual(snap['states'],{} if state is None else {state:1})
                if state:
                    with self.assertRaises(Denied):s.reserve(l,cap,str(uuid4()),'synthetic_maps',1)

    def raw(self, s, action, args):
        # Deliberately bypass LocalPostgres validation and its check call.
        with psycopg.connect(**s._connection) as c:
            return c.execute('SELECT synthetic_state.protocol(%s,%s)',
                             (action,Jsonb(args))).fetchone()['protocol']

    def raw_reservation(self, s, lease, cap, **changes):
        args=dict(**s._lease(lease),capability=s._hash(cap.token,'cap'),
                  operation=str(uuid4()),provider='synthetic_maps',charge=30)
        args.update(changes)
        return args

    def test_runtime_has_only_routine_not_table_sequence_or_admin_authority(self):
        s=store();_,lease,cap=ready(s);s.reserve(lease,cap,str(uuid4()),'synthetic_maps',30)
        for table,column in [('policy','id'),('gate','id'),('sessions','id'),('evidence','session'),
                             ('capabilities','id'),('operations','id'),('facts','kind')]:
            for sql in [f'SELECT * FROM synthetic_state.{table}',
                        f'INSERT INTO synthetic_state.{table} DEFAULT VALUES',
                        f'UPDATE synthetic_state.{table} SET {column}={column}',
                        f'DELETE FROM synthetic_state.{table}',
                        f'TRUNCATE synthetic_state.{table}',
                        f'ALTER TABLE synthetic_state.{table} DISABLE TRIGGER ALL']:
                with self.subTest(sql=sql),self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    with psycopg.connect(**s._connection) as c:c.execute(sql)
        attacks=[
            "SELECT nextval('synthetic_state.facts_sequence_seq')",
            "SELECT setval('synthetic_state.facts_sequence_seq',1)",
            'SET ROLE whereto_synthetic_owner',
            'SET ROLE whereto_synthetic_admin',
            'GRANT whereto_synthetic_owner TO whereto_synthetic_worker',
            'ALTER ROLE whereto_synthetic_worker SUPERUSER',
            'CREATE SCHEMA worker_bypass',
            'CREATE TABLE public.worker_bypass(id int)',
            'CREATE TEMP TABLE sessions(id text)',
            'CREATE FUNCTION synthetic_state.bypass() RETURNS int LANGUAGE sql AS $$ SELECT 1 $$',
            'ALTER FUNCTION synthetic_state.protocol(text,jsonb) SECURITY INVOKER',
            "SELECT synthetic_state.abandon('forged')",
            "SELECT synthetic_state.valid_integer('1'::jsonb,0,10)",
            "SET session_replication_role='replica'",
        ]
        for sql in attacks:
            with self.subTest(sql=sql),self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with psycopg.connect(**s._connection) as c:c.execute(sql)
        # Structurally valid forged history, not merely missing DEFAULT fields.
        attempts=[
            ("INSERT INTO synthetic_state.operations(id,capability,session,revision,worker,fence,provider,charge) VALUES(%s,%s,%s,1,%s,%s,'synthetic_maps',0)",
             (str(uuid4()),s._hash(cap.token,'cap'),s._hash(lease.session.token,'session'),lease.worker,lease.fence)),
            ("INSERT INTO synthetic_state.facts(operation,kind) SELECT id,'SUCCEEDED' FROM synthetic_state.operations",()),
            ("UPDATE synthetic_state.operations SET charge=0",()),
            ("UPDATE synthetic_state.policy SET limits='{}'",()),
        ]
        for sql,args in attempts:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with psycopg.connect(**s._connection) as c:c.execute(sql,args)
        self.assertEqual(s.snapshot()['gross'],30)
        with admin() as c:
            rows=c.execute("SELECT rolname,rolsuper,rolcreaterole,rolcreatedb,rolreplication,rolbypassrls,rolcanlogin FROM pg_roles WHERE rolname IN ('whereto_synthetic_worker','whereto_synthetic_owner') ORDER BY rolname").fetchall()
            self.assertEqual(rows,[('whereto_synthetic_owner',False,False,False,False,False,False),
                                   ('whereto_synthetic_worker',False,False,False,False,False,True)])
            self.assertFalse(c.execute("SELECT pg_has_role('whereto_synthetic_worker','whereto_synthetic_owner','MEMBER')").fetchone()[0])
            functions=c.execute("SELECT p.proname,p.prosecdef,r.rolname,p.proconfig,has_function_privilege('whereto_synthetic_worker',p.oid,'EXECUTE') FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace JOIN pg_roles r ON r.oid=p.proowner WHERE n.nspname='synthetic_state'").fetchall()
            for name,definer,owner,config,executable in functions:
                self.assertEqual(owner,'whereto_synthetic_owner')
                self.assertEqual(executable,name=='protocol')
                if name=='protocol':
                    self.assertTrue(definer);self.assertEqual(config,['search_path=pg_catalog, pg_temp'])

    def test_direct_routine_cannot_forge_or_replay_operation_or_fence(self):
        s=store();h,lease,cap=ready(s);args=self.raw_reservation(s,lease,cap)
        for changes in [dict(capability='f'*64),dict(fence=lease.fence+1),dict(worker=str(uuid4())),
                        dict(revision=2),dict(session='f'*64),dict(provider='google'),
                        dict(charge=-1),dict(charge=True),dict(charge=None),dict(charge='0')]:
            with self.subTest(changes=changes),self.assertRaises(psycopg.Error):
                self.raw(s,'reserve',dict(args,**changes))
        transition={k:v for k,v in args.items() if k not in ('provider','charge')}
        with self.assertRaises(psycopg.Error):self.raw(s,'transition',dict(transition,state='SUCCEEDED'))
        self.raw(s,'reserve',args)
        with self.assertRaises(psycopg.Error):self.raw(s,'transition',dict(transition,state='SUCCEEDED'))
        self.raw(s,'transition',dict(transition,state='INTENT'))
        self.raw(s,'transition',dict(transition,state='SUCCEEDED'))
        with self.assertRaises(psycopg.Error):self.raw(s,'reserve',dict(args,operation=str(uuid4())))
        other=s.issue(lease,'ordinary_plan',str(uuid4()))
        with self.assertRaises(psycopg.Error):self.raw(s,'reserve',dict(args,capability=s._hash(other.token,'cap')))
        newer=s.claim(h,1)
        with self.assertRaises(psycopg.Error):self.raw(s,'transition',dict(transition,state='FAILED'))
        with self.assertRaises(psycopg.Error):self.raw(s,'reserve',dict(args,operation=str(uuid4())))
        self.assertEqual(s.snapshot()['gross'],30);self.assertEqual(newer.fence,lease.fence+1)

    def test_direct_routine_enforces_finances_uncertainty_and_policy(self):
        limits=Limits(30,30,1,1);fixture(limits);s=store(limits);_,lease,cap=ready(s)
        args=self.raw_reservation(s,lease,cap)
        self.raw(s,'reserve',args)
        transition={k:v for k,v in args.items() if k not in ('provider','charge')}
        self.raw(s,'transition',dict(transition,state='UNCERTAIN'))
        _,other,cap2=ready(s)
        for changes in [dict(charge=1),dict(charge=0),dict(charge=0,provider='synthetic_ai')]:
            with self.assertRaises(psycopg.Error):self.raw(s,'reserve',self.raw_reservation(s,other,cap2,**changes))
        with self.assertRaises(psycopg.Error):self.raw(s,'transition',dict(transition,state='INTENT'))
        with self.assertRaises(psycopg.Error):self.raw(s,'check',dict(version=VERSION,fingerprint='x',limits=asdict(limits)))
        self.assertEqual(s.snapshot(),dict(attempts=1,gross=30,states={'UNCERTAIN':1},planning_authorized=False))

    def test_direct_routine_rejects_missing_evidence_expiry_wrong_kind_and_unknown_api(self):
        s=store();_,lease,cap=ready(s);args=self.raw_reservation(s,lease,cap)
        for action,payload in [('refund',{}),('reserve',dict(args,ignore=True)),('snapshot',{'force':True}),('snapshot',None)]:
            with self.assertRaises(psycopg.Error):self.raw(s,action,payload)
        with admin() as c:c.execute("UPDATE synthetic_state.evidence SET payload='{}'")
        with self.assertRaises(psycopg.Error):self.raw(s,'reserve',args)
        with self.assertRaises(psycopg.Error):self.raw(s,'read',s._lease(lease))
        with admin() as c:c.execute('DELETE FROM synthetic_state.evidence')
        with self.assertRaises(psycopg.Error):self.raw(s,'reserve',args)
        fixture();s=store();_,lease,cap=ready(s)
        with admin() as c:c.execute("UPDATE synthetic_state.sessions SET expires=clock_timestamp()-interval '1 second'")
        with self.assertRaises(psycopg.Error):self.raw(s,'reserve',self.raw_reservation(s,lease,cap))
        self.assertEqual(s.snapshot()['attempts'],0)

    def test_direct_routine_caps_apply_after_success_without_active_lockout(self):
        limits=Limits(80,60,2,1,2);fixture(limits);s=store(limits);_,lease,cap=ready(s)
        args=self.raw_reservation(s,lease,cap);self.raw(s,'reserve',args)
        transition={k:v for k,v in args.items() if k not in ('provider','charge')}
        self.raw(s,'transition',dict(transition,state='INTENT'));self.raw(s,'transition',dict(transition,state='SUCCEEDED'))
        _,other,cap2=ready(s)
        with self.assertRaises(psycopg.Error):self.raw(s,'reserve',self.raw_reservation(s,other,cap2,charge=0))
        with self.assertRaises(psycopg.Error):self.raw(s,'reserve',self.raw_reservation(s,other,cap2,charge=51,provider='synthetic_ai'))
        self.raw(s,'reserve',self.raw_reservation(s,other,cap2,charge=50,provider='synthetic_ai'))
        _,last,cap3=ready(s)
        with self.assertRaises(psycopg.Error):self.raw(s,'reserve',self.raw_reservation(s,last,cap3,charge=0,provider='synthetic_ai'))
        self.assertEqual(s.snapshot()['gross'],80);self.assertEqual(s.snapshot()['attempts'],2)

    def test_corrupt_bootstrap_policy_cannot_be_used_through_direct_routine(self):
        s=store();_,lease,cap=ready(s)
        # Simulates a privileged configuration fault; runtime cannot disable triggers.
        with admin() as c:
            c.execute('ALTER TABLE synthetic_state.policy DISABLE TRIGGER USER')
            c.execute("UPDATE synthetic_state.policy SET limits='{}'")
            c.execute('ALTER TABLE synthetic_state.policy ENABLE TRIGGER USER')
        with self.assertRaises(psycopg.Error):self.raw(s,'reserve',self.raw_reservation(s,lease,cap))
        with self.assertRaises(Denied):s.snapshot()

    def test_caller_isolation_search_path_and_rollback_cannot_bypass(self):
        s=store();_,lease,cap=ready(s)
        with psycopg.connect(**s._connection) as c:
            c.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
            with self.assertRaises(psycopg.errors.RaiseException):s._invoke(c,'snapshot',{})
        with psycopg.connect(**s._connection) as c:
            c.execute('SET LOCAL search_path=public,pg_temp')
            self.assertEqual(s._invoke(c,'snapshot',{})['attempts'],0)
            s._invoke(c,'reserve',self.raw_reservation(s,lease,cap));c.rollback()
        # No committed reservation or send authority returned by LocalPostgres;
        # rollback permits the same capability only because no operation committed.
        self.assertEqual(s.snapshot()['attempts'],0)
        s.reserve(lease,cap,str(uuid4()),'synthetic_maps',30)
        self.assertEqual(s.snapshot()['gross'],30)

    def test_actual_ordinary_pending_options_and_selection_contracts(self):
        from backend.ai.ollama import Interpretation
        from backend.interpretation import InterpretationInput, ClarificationAnswers, interpret_request
        from backend.real_planning import PlannerInput
        from backend.saved_plans import Receipts,SaveRequest,SavedDocument
        from backend.ranking import recommend_plans
        from backend.testing_clock import calendar_clock
        from backend.models import PlanningRequest
        calls=[]
        class Fake:
            def interpret(self,text):
                calls.append(1)
                return Interpretation.model_validate({'activities':['coffee','museum'],'location':'Baltimore','budget_per_person':None,'date':None,'preferences':[]})
        # Actual interpreter pending answers are deterministic and do not repeat inference.
        with calendar_clock():
            result=interpret_request(InterpretationInput(text='Coffee and museum in Baltimore',calendarTimezone='America/New_York'),Fake(),now=datetime(2026,11,2,15,tzinfo=timezone.utc))
            self.assertIsNotNone(result.pending)
            s=store();h=s.create(Kind.PENDING,result.pending);l=s.claim(h,1)
            pending=s.read(l)
            answer=interpret_request(InterpretationInput(text=pending.text,pending=pending,answers=ClarificationAnswers(date='2026-11-07'),calendarTimezone='America/New_York'),Fake(),now=datetime(2026,11,2,15,tzinfo=timezone.utc))
            self.assertEqual(len(calls),1);self.assertIsNotNone(answer.request)
            p=PlannerInput.model_validate(answer.request.model_dump());s.revise(h,1,Kind.ORDINARY,p)
            with self.assertRaises(Denied):s.read(l)
            ranked=recommend_plans(PlanningRequest.model_validate(p.model_dump(exclude={'locationFirst','searchRadius'})))
            view=s.create(Kind.OPTIONS,ranked);lease=s.claim(view,1)
            # RankingResult declares OutingRequest; JSON restores that declared type,
            # not the original in-memory PlanningRequest subclass. Compare every
            # canonical field (including excluded/private fields), not class identity.
            self.assertEqual(encode(Kind.OPTIONS,s.read(lease)),encode(Kind.OPTIONS,ranked))
            registry=Receipts();issued=registry.issue(ranked);options=issued.plans+issued.provisionalPlans
            selected=registry.select(SaveRequest(receipt=issued.saveReceipt,accessToken=issued.saveAccessToken,candidateIds=[x.candidate.id for x in options],selectedId=options[0].candidate.id))
            doc=s.create(Kind.SELECTED,selected);doclease=s.claim(doc,1)
            self.assertEqual(SavedDocument.model_validate_json(s.read(doclease).model_dump_json()),selected)
            self.assertEqual(s.snapshot()['attempts'],0)

    def test_actual_advanced_planner_dtos_and_handoff_are_not_provider_authority(self):
        from backend.test_advanced_planning import IntegrationTests
        from backend.journey import Journey
        from backend.interpretation import InterpretationResult,InterpretationContext
        from backend.ai.ollama import Interpretation
        fixture_test=IntegrationTests('test_named_roundtrip_dto_and_receipt');fixture_test.setUp()
        try:
            session=fixture_test.session(endpoint={'kind':'origin','source':'return to start'})
            from backend.test_advanced_routing import start
            result=fixture_test.run_session(session,startingLocation=start())
            self.assertEqual(result.status,'results')
            s=store();h=s.create(Kind.ADVANCED_RESULTS,result);l=s.claim(h,1)
            self.assertEqual(s.read(l),result)
            cap=s.issue(l,'browse_only',str(uuid4()))
            with self.assertRaises(Denied):s.reserve(l,cap,str(uuid4()),'synthetic_maps',1)
            interpretation=Interpretation(activities=['coffee'],budget_per_person=None,date=None,location=None,preferences=[],journey=Journey(stops=[{'source':'coffee'}]))
            handoff=InterpretationResult(interpretation=interpretation,request=None,notes=[],issues=[],executionStatus='advanced_unavailable',context=InterpretationContext())
            h=s.create(Kind.HANDOFF,handoff);l=s.claim(h,1);cap=s.issue(l,'handoff_only',str(uuid4()))
            with self.assertRaises(Denied):s.reserve(l,cap,str(uuid4()),'synthetic_maps',1)
            self.assertEqual(s.snapshot()['attempts'],0)
        finally:fixture_test.doCleanups()

    def test_graph_optionality_identity_date_and_destination_tampering(self):
        from copy import deepcopy
        from backend.ai import Interpretation
        from backend.journey_fixtures import reply
        from backend.interpretation import InterpretationResult,InterpretationContext
        result=InterpretationResult(interpretation=Interpretation.model_validate(reply(
            ['coffee','museum'],order=[(0,1,'coffee then museum')],optional={1:'maybe museum'})),
            request=None,notes=[],issues=[],executionStatus='advanced_unavailable',
            context=InterpretationContext(destination='New York',date='2026-11-07'))
        s=store();h=s.create(Kind.HANDOFF,result);lease=s.claim(h,1)
        original=json.loads(encode(Kind.HANDOFF,result))
        changes=[
            lambda d:d['interpretation']['journey']['order'][0].update(before=1,after=0),
            lambda d:d['interpretation']['journey']['stops'][1].update(requirement='required'),
            lambda d:d['interpretation']['journey']['stops'][0].update(source='other venue'),
            lambda d:d['context'].update(date='2026-11-08'),
            lambda d:d['context'].update(destination='Other city')]
        for change in changes:
            modified=deepcopy(original);change(modified)
            with admin() as c:c.execute('UPDATE synthetic_state.evidence SET payload=%s',(Jsonb(modified),))
            with self.assertRaises(Denied):s.read(lease)
        with admin() as c:c.execute("UPDATE synthetic_state.evidence SET payload=%s,integrity=sha256(convert_to((%s::jsonb)::text,'UTF8'))",(Jsonb(original),Jsonb(original)))
        self.assertEqual(encode(Kind.HANDOFF,s.read(lease)),encode(Kind.HANDOFF,result))

    def test_default_production_guards_and_real_provider_names_still_refuse(self):
        from backend.admission import validate_environment
        for env in [{'WHERETO_ENV':'production'},{'WHERETO_ENV':'test','K_SERVICE':'synthetic'}]:
            with patch.dict(os.environ,env,clear=True):
                with self.assertRaises(RuntimeError):validate_environment()
        s=store();_,lease,cap=ready(s)
        with self.assertRaises(Denied):s.reserve(lease,cap,str(uuid4()),'google',1)
        self.assertEqual(s.snapshot()['attempts'],0)

    def test_no_existing_admission_receipt_can_be_forged_by_the_store(self):
        from backend.planning_admission import AdmissionRegistry,AdmissionError
        s=store();_,l,cap=ready(s);r=s.reserve(l,cap,str(uuid4()),'synthetic_maps',0)
        registry=AdmissionRegistry();scope=registry.new_scope()
        with self.assertRaises(AdmissionError):registry.run(r,scope,1,ordinary(),lambda _:self.fail('work admitted'))
        with self.assertRaises(Denied):s.create('raw_model',ordinary())


def seed_crash():
    fixture();s=store();h,l,cap=ready(s);r=s.reserve(l,cap,str(uuid4()),'synthetic_maps',30);s.transition(r,'INTENT')
    Path('/tmp/synthetic-crash-case.json').write_text(json.dumps({'token':h.token,'worker':l.worker,'fence':l.fence}))


def after_database_crash():
    s=store();snap=s.snapshot();assert snap['gross']==30 and snap['states']=={'INTENT':1}
    with admin() as c:assert c.execute('SELECT count(*) FROM synthetic_state.evidence').fetchone()[0]==0
    case=json.loads(Path('/tmp/synthetic-crash-case.json').read_text())
    lease=WorkerLease(SessionHandle(case['token']),1,case['worker'],case['fence'])
    try:s.read(lease)
    except Denied:pass
    else:raise AssertionError('Unlogged synthetic evidence unexpectedly survived unclean restart')
    try:s.claim(lease.session,1)
    except Denied:pass
    else:raise AssertionError('Missing evidence was reauthorized')
    _,fresh,newcap=ready(s)
    try:s.reserve(fresh,newcap,str(uuid4()),'synthetic_maps',1)
    except Denied:pass
    else:raise AssertionError('Uncertain exposure admitted new work')
    assert s.snapshot()['attempts']==1
    print('PostgreSQL crash recovery retained INTENT/charge; volatile evidence loss refused; no resend.')


if __name__=='__main__':
    import sys
    if len(sys.argv)>1 and sys.argv[1]=='seed':seed_crash()
    elif len(sys.argv)>1 and sys.argv[1]=='after_crash':after_database_crash()
    elif len(sys.argv)>1 and sys.argv[1]=='unavailable':
        try:store()
        except Unavailable:print('Actual PostgreSQL outage refused without fallback.')
        else:raise AssertionError('Expected database outage')
    else:unittest.main()
