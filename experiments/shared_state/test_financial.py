"""Synthetic financial authority tests; admin is fixture-only, never a client issuer."""
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import multiprocessing as mp
import os
from pathlib import Path
import unittest
from uuid import uuid4

import psycopg
from psycopg.types.json import Jsonb
from backend.development_cost import RATES
from backend.provider_budget import ProviderSettings
from experiments.shared_state import test_store as core
from experiments.shared_state.contracts import Kind, Limits, Denied, Unavailable
from experiments.shared_state.financial import FinancialPostgres, VERSION, RATE_VERSION

LIMITS=Limits(10**12,10**12,10**12,10**12,16)  # Core numeric envelope, NOT an application spending grant.
ROOT='00000000-0000-4000-8000-000000000001'
START=datetime(2026,11,1,5,30,tzinfo=timezone.utc)


def fixture(profile='bounded',daily=None,settings=None,extension=None):
    settings=(settings or ProviderSettings()).model_dump(exclude={'mode','exploration'})
    def install(c):
        c.execute(Path(__file__).with_name('financial_schema.sql').read_text(),prepare=False)
        c.execute('INSERT INTO synthetic_state.finance_policy VALUES(1,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                  (VERSION,RATE_VERSION,Jsonb(RATES),Jsonb(settings),'America/New_York',daily,10000000,profile!='bounded','synthetic-local-project-v1',profile))
        c.execute("UPDATE synthetic_state.test_clock SET value=%s",(START,))
        c.execute(Path(__file__).with_name('financial_routines.sql').read_text(),prepare=False)
        if extension:extension(c)
    core.fixture(LIMITS,extension=install)


def store():
    return FinancialPostgres(key=core.KEY,password=os.environ['SYNTHETIC_WORKER_PASSWORD'],limits=LIMITS)


def clock(value):
    with core.admin() as c:c.execute('UPDATE synthetic_state.test_clock SET value=%s',(value,))


def item(operation='details',variant='essentials',rows=0,cols=0,key=None):
    return dict(operation=operation,variant=variant,rows=rows,cols=cols,
                request_digest=sha256((key or str(uuid4())).encode()).hexdigest())


def enroll(s,h,root=ROOT,outing=None):
    outing=outing or str(uuid4())
    with core.admin() as c:
        c.execute('SET LOCAL ROLE whereto_synthetic_issuer')
        c.execute('SELECT synthetic_state.enroll_budget(%s,%s,%s)',(s._hash(h.token,'session'),root,outing))
    return outing


def approve(s,cap,items):
    with core.admin() as c:
        c.execute('SET LOCAL ROLE whereto_synthetic_issuer')
        c.execute('SELECT synthetic_state.approve_requests(%s,%s)',(s._hash(cap.token,'cap'),Jsonb(items)))


def ready(s,items=None,root=ROOT,outing=None):
    h=s.create(Kind.ORDINARY,core.ordinary());outing=enroll(s,h,root,outing)
    lease=s.claim(h,1);cap=s.issue(lease,'ordinary_plan',str(uuid4()))
    if items is not None:approve(s,cap,items)
    return h,lease,cap,outing


def reserve(s,items=None,root=ROOT,outing=None,finish=True):
    _,lease,cap,outing=ready(s,items or [item()],root,outing)
    r=s.reserve(lease,cap,str(uuid4()))
    if finish:complete(s,r,len(items or [None]))
    return r,outing


def dispatch(s,r,n):
    for ordinal in range(1,n+1):
        s._call('dispatch',**s._lease(r.lease),capability=s._hash(r.capability.token,'cap'),
                operation=r.operation,ordinal=ordinal)


def complete(s,r,n=1):
    s.transition(r,'INTENT');dispatch(s,r,n);s.transition(r,'SUCCEEDED')


def child(lease,cap,barrier,q,crash=None):
    s=store();l=s.claim(lease.session,lease.revision)
    if barrier:barrier.wait(timeout=15)
    try:
        if crash=='before_commit':
            with s._tx() as c:
                s._invoke(c,'reserve',dict(**s._lease(l),capability=s._hash(cap.token,'cap'),operation=str(uuid4())))
                os._exit(41)
        r=s.reserve(l,cap,str(uuid4()))
        if crash=='reserved':os._exit(42)
        s.transition(r,'INTENT')
        if crash=='intent':os._exit(42)
        dispatch(s,r,1)
        if crash=='sent':os._exit(42)
        s.transition(r,'SUCCEEDED')
        if crash=='outcome':os._exit(42)
        q.put('reserved')
    except Denied:
        if q:q.put('denied')
        else:raise


def admission_child(barrier,q):
    s=store();ident=sha256(str(uuid4()).encode()).hexdigest();barrier.wait(timeout=15)
    try:
        s._call('admit',id=ident,worker=s._worker,domain='http',fingerprint=ident)
        q.put('reserved')
    except Denied:q.put('denied')


class FinancialTests(unittest.TestCase):
    def setUp(self):fixture()

    def raw(self,s,verb,args):
        with psycopg.connect(**s._connection) as c:
            return c.execute('SELECT synthetic_state.financial_protocol(%s,%s)',(verb,Jsonb(args))).fetchone()['financial_protocol']

    def args(self,s,l,cap):
        return dict(**s._lease(l),capability=s._hash(cap.token,'cap'),operation=str(uuid4()))

    def test_exact_source_rates_and_all_operation_types(self):
        s=store()
        specs=[item('search','pro'),item('search','enterprise'),item('lookup','pro'),
               item('details','essentials'),item('details','pro'),item('matrix','walk',2,3),item('matrix','drive',1,2),item('route','none')]
        r,_=reserve(s,specs)
        self.assertFalse(r.planning_authorized)
        self.assertEqual(s.snapshot()['gross'],32000+35000+32000+20000+17000+6*5000+2*10000)
        with core.admin() as c:
            rows=c.execute('SELECT sku,units,rate,charge,rate_version FROM synthetic_state.financial_lines ORDER BY ordinal').fetchall()
        self.assertEqual(rows[-1],('none',0,0,0,RATE_VERSION))
        self.assertTrue(all(charge==units*rate for _,units,rate,charge,_ in rows))

    def test_arbitrary_prices_providers_units_and_scopes_refuse(self):
        s=store();_,l,cap,_=ready(s,[item()]);args=self.args(s,l,cap)
        for action,payload in [(None,args),('usage',None),('reserve',None),('reserve',[])]:
            with self.assertRaises(psycopg.Error):self.raw(s,action,payload)
        for field,value in [('charge',0),('rate',1),('units',0),('provider','google'),('root',str(uuid4())),('outing',str(uuid4())),('day','2020-01-01'),('rate_version','other')]:
            with self.subTest(field=field),self.assertRaises(psycopg.Error):self.raw(s,'reserve',dict(args,**{field:value}))
        self.assertEqual(s.snapshot()['attempts'],0)
        self.raw(s,'reserve',args)
        self.assertEqual(s.snapshot()['gross'],20000)

    def test_worker_cannot_issue_policy_or_bypass_private_core(self):
        s=store();_,l,cap,_=ready(s,[item()])
        attacks=[('SELECT synthetic_state.protocol(%s,%s)',('reserve',Jsonb(dict(self.args(s,l,cap),provider='synthetic_maps',charge=0)))),
          ('SELECT synthetic_state.approve_requests(%s,%s)',(s._hash(cap.token,'cap'),Jsonb([item('route','none')]))),
          ('SELECT synthetic_state.enroll_budget(%s,%s,%s)',(s._hash(l.session.token,'session'),ROOT,str(uuid4()))),
          ('SET ROLE whereto_synthetic_issuer',()),('SELECT synthetic_state.protocol_now()',()),
          ("UPDATE synthetic_state.test_clock SET value='2099-01-01'",()),
          ("UPDATE synthetic_state.finance_policy SET daily_limit=1000000000",()),
          ("UPDATE synthetic_state.finance_policy SET rates='{}'",())]
        with core.admin() as c:
            names=c.execute("SELECT tablename FROM pg_tables WHERE schemaname='synthetic_state'").fetchall()
        for (name,) in names:
            attacks += [(f'INSERT INTO synthetic_state.{name} DEFAULT VALUES',()),(f'DELETE FROM synthetic_state.{name}',()),(f'TRUNCATE synthetic_state.{name}',())]
        for sql,params in attacks:
            with self.subTest(sql=sql),self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with psycopg.connect(**s._connection) as c:c.execute(sql,params)
        self.assertEqual(s.snapshot()['attempts'],0)

    def test_unapproved_new_sessions_cannot_reset_or_move_outing(self):
        s=store();h,l,cap,outing=ready(s,[item()]);r=s.reserve(l,cap,str(uuid4()));complete(s,r)
        unbound=s.create(Kind.ORDINARY,core.ordinary());new=s.claim(unbound,1);cap2=s.issue(new,'ordinary_plan',str(uuid4()))
        with self.assertRaises(Denied):s.reserve(new,cap2,str(uuid4()))
        with self.assertRaises(psycopg.Error):enroll(s,h,str(uuid4()),str(uuid4()))
        # A valid revision keeps its original outing. Reusing old authority fails.
        s.revise(h,1,Kind.ORDINARY,core.ordinary());current=s.claim(h,2)
        with self.assertRaises(Denied):s.reserve(l,cap,str(uuid4()))
        with core.admin() as c:self.assertEqual(c.execute('SELECT outing FROM synthetic_state.budget_bindings WHERE session=%s',(s._hash(h.token,'session'),)).fetchone()[0],__import__('uuid').UUID(outing))
        self.assertEqual(store().snapshot()['gross'],20000)

    def test_invalid_dimensions_overflow_variant_and_duplicate_plans(self):
        s=store()
        for bad in [item('matrix','drive',-1,1),item('matrix','walk',True,1),item('matrix','walk',10**12,10**12),
                    item('matrix','optimal',1,1),item('lookup','enterprise'),item('details','unknown'),item('search','pro',1,1)]:
            _,_,cap,_=ready(s)
            with self.subTest(bad=bad),self.assertRaises(psycopg.Error):approve(s,cap,[bad])
        _,l,cap,_=ready(s);same=item()
        with self.assertRaises(psycopg.Error):approve(s,cap,[same,same])
        with self.assertRaises(Denied):s.reserve(l,cap,str(uuid4()))
        self.assertEqual(s.snapshot()['attempts'],0)

    def test_per_outing_and_session_scopes_preserve_consumption(self):
        settings=ProviderSettings(details_per_outing=1,requests_per_session=2)
        fixture(settings=settings);s=store();_,l,c,o=ready(s,[item()]);r=s.reserve(l,c,str(uuid4()));complete(s,r)
        with self.assertRaises(Denied):reserve(s,[item()],outing=o)
        reserve(s,[item()])
        with self.assertRaises(Denied):reserve(store(),[item('route','none')])
        self.assertEqual(s.snapshot()['attempts'],2)

    def test_requests_searches_lookup_and_matrix_scope_boundaries(self):
        for settings,first,second in [
          (ProviderSettings(requests_per_outing=1),item('route','none'),item('route','none')),
          (ProviderSettings(searches_per_outing=1),item('search','pro'),item('search','pro')),
          (ProviderSettings(lookups_per_session=1),item('lookup','pro'),item('lookup','pro')),
          (ProviderSettings(matrix_elements_per_outing=2),item('matrix','walk',1,2),item('matrix','walk',1,1)),
          (ProviderSettings(matrix_elements_per_session=2),item('matrix','drive',1,2),item('matrix','drive',1,1))]:
            with self.subTest(settings=settings):
                fixture(settings=settings);s=store();_,o=reserve(s,[first])
                with self.assertRaises(Denied):reserve(s,[second],outing=o)
                self.assertEqual(s.snapshot()['attempts'],1)

    def test_minute_exact_boundary_and_no_worker_time_override(self):
        s=store();reserve(s,[item('matrix','walk',1,150)])
        _,l,c,_=ready(s,[item('matrix','walk',1,1)])
        with self.assertRaises(Denied):s.reserve(l,c,str(uuid4()))
        clock(START+timedelta(seconds=59,microseconds=999999))
        with self.assertRaises(Denied):s.reserve(l,c,str(uuid4()))
        clock(START+timedelta(seconds=60));r=s.reserve(l,c,str(uuid4()));complete(s,r)
        with psycopg.connect(**s._connection) as conn:
            conn.execute("SET timezone='Pacific/Auckland'")
            self.assertEqual(s._invoke(conn,'usage',{})['timezone'],'America/New_York')
        clock(START)
        with self.assertRaises(Denied):s.usage()

    def test_shared_search_and_details_minute_across_approved_roots(self):
        for op,variant in [('search','pro'),('details','essentials')]:
            fixture('exploration');s=store()
            for _ in range(10):reserve(s,[item(op,variant)],root=str(uuid4()))
            with self.assertRaises(Denied):reserve(s,[item(op,variant)],root=str(uuid4()))
            clock(START+timedelta(seconds=60));reserve(s,[item(op,variant)],root=str(uuid4()))
            self.assertEqual(s.snapshot()['attempts'],11)

    def test_day_rollover_dst_timezone_and_original_day_binding(self):
        fixture('ledger_enforced',daily=20000);s=store();r,_=reserve(s,[item()])
        with self.assertRaises(Denied):reserve(s,[item()],root=str(uuid4()))
        # DST repeats 01:30 local; it does not create a new financial day.
        clock(START+timedelta(hours=1))
        with self.assertRaises(Denied):reserve(s,[item()],root=str(uuid4()))
        clock(datetime(2026,11,2,5,tzinfo=timezone.utc));reserve(s,[item()])
        self.assertEqual(s.usage()['dayMicrousd'],20000);self.assertEqual(s.snapshot()['gross'],40000)
        with core.admin() as c:self.assertEqual([str(x[0]) for x in c.execute('SELECT DISTINCT calendar_day FROM synthetic_state.financial_lines ORDER BY calendar_day').fetchall()],['2026-11-01','2026-11-02'])

    def test_profiles_do_not_invent_daily_cap_and_exploration_exception(self):
        for profile in ['bounded','exploration']:
            fixture(profile);s=store();self.assertIsNone(s.usage()['dailyLimitMicrousd'])
        # Exploration retains six Details and minute limits despite uncapped search/session totals.
        s=store();_,o=reserve(s,[item() for _ in range(6)])
        with self.assertRaises(Denied):reserve(s,[item()],outing=o)

    def test_zero_charge_consumes_attempts_and_replay_and_batch_atomicity(self):
        fixture(settings=ProviderSettings(requests_per_outing=1));s=store();r,o=reserve(s,[item('route','none')])
        self.assertEqual(s.snapshot()['gross'],0)
        with self.assertRaises(Denied):reserve(s,[item('route','none')],outing=o)
        with self.assertRaises(Denied):s.reserve(r.lease,r.capability,str(uuid4()))
        fixture();s=store();_,l,c,_=ready(s,[item('matrix','drive',1,151),item()])
        with self.assertRaises(Denied):s.reserve(l,c,str(uuid4()))
        self.assertEqual(s.snapshot()['attempts'],0);self.assertEqual(s.snapshot()['gross'],0)

    def test_dispatch_no_retry_sku_or_partial_batch_success(self):
        s=store();_,l,c,_=ready(s,[item(),item()]);r=s.reserve(l,c,str(uuid4()));s.transition(r,'INTENT')
        dispatch(s,r,1)
        with self.assertRaises(Denied):dispatch(s,r,1)
        with self.assertRaises(Denied):s.transition(r,'SUCCEEDED')
        s.transition(r,'FAILED')
        self.assertEqual(s.snapshot()['gross'],40000)
        with self.assertRaises(Denied):s.reserve(l,c,str(uuid4()))

    def test_missing_corrupt_evidence_and_uncertainty_keep_exposure(self):
        s=store();h,l,c,_=ready(s,[item()]);r=s.reserve(l,c,str(uuid4()));s.transition(r,'INTENT')
        with core.admin() as conn:conn.execute("UPDATE synthetic_state.evidence SET payload='{}'")
        with self.assertRaises(Denied):s.transition(r,'SUCCEEDED')
        with self.assertRaises(Denied):store().claim(h,1)
        with self.assertRaises(Denied):reserve(store(),[item('route','none')])
        self.assertEqual(s.snapshot()['gross'],20000)

    def test_process_exit_and_restart_never_resend_reserved_units(self):
        for phase in ['before_commit','reserved','intent','sent','outcome']:
            fixture();s=store();h,l,c,_=ready(s,[item()]);ctx=mp.get_context('spawn')
            p=ctx.Process(target=child,args=(l,c,None,None,phase));p.start();p.join(20);self.assertEqual(p.exitcode,41 if phase=='before_commit' else 42)
            self.assertEqual(store().snapshot()['gross'],0 if phase=='before_commit' else 20000)
            if phase=='before_commit':continue
            fresh=store();current=fresh.claim(h,1)
            with self.assertRaises(Denied):fresh.reserve(current,c,str(uuid4()))

    def test_two_processes_cannot_exceed_daily_or_outing_boundary(self):
        for shared_outing in [False,True]:
            fixture('ledger_enforced',daily=20000,settings=ProviderSettings(details_per_outing=1));s=store();o=str(uuid4())
            sets=[ready(s,[item()],ROOT if shared_outing else str(uuid4()),o if shared_outing else None) for _ in range(2)]
            ctx=mp.get_context('spawn');barrier=ctx.Barrier(2);q=ctx.Queue()
            ps=[ctx.Process(target=child,args=(l,c,barrier,q)) for _,l,c,_ in sets]
            for p in ps:p.start()
            for p in ps:p.join(20);self.assertEqual(p.exitcode,0)
            self.assertEqual(sorted([q.get(timeout=2),q.get(timeout=2)]),['denied','reserved'])
            self.assertEqual(s.snapshot()['gross'],20000)

    def test_competing_workers_at_each_unit_and_session_boundary(self):
        cases=[
            (ProviderSettings(requests_per_outing=1),item('route','none'),True),
            (ProviderSettings(searches_per_outing=1),item('search','pro'),True),
            (ProviderSettings(details_per_outing=1),item(),True),
            (ProviderSettings(matrix_elements_per_outing=1),item('matrix','walk',1,1),True),
            (ProviderSettings(requests_per_session=1),item('route','none'),False),
            (ProviderSettings(lookups_per_session=1),item('lookup','pro'),False),
            (ProviderSettings(matrix_elements_per_session=1),item('matrix','drive',1,1),False)]
        for settings,spec,same_outing in cases:
            with self.subTest(settings=settings):
                fixture(settings=settings);s=store();o=str(uuid4())
                sets=[ready(s,[spec|{'request_digest':sha256(str(uuid4()).encode()).hexdigest()}],outing=o if same_outing else None) for _ in range(2)]
                self.race(sets)
                self.assertEqual(s.snapshot()['attempts'],1)

    def race(self,sets):
        ctx=mp.get_context('spawn');barrier=ctx.Barrier(2);q=ctx.Queue()
        ps=[ctx.Process(target=child,args=(l,c,barrier,q)) for _,l,c,_ in sets]
        for p in ps:p.start()
        for p in ps:p.join(20);self.assertEqual(p.exitcode,0)
        self.assertEqual(sorted([q.get(timeout=2),q.get(timeout=2)]),['denied','reserved'])

    def test_competing_workers_at_root_and_shared_minute_boundaries(self):
        for shared,kind,variant in [(False,'search','pro'),(False,'details','essentials'),(False,'matrix','walk'),
                                    (True,'search','pro'),(True,'details','essentials'),(True,'matrix','drive')]:
            with self.subTest(shared=shared,kind=kind):
                fixture('exploration' if shared else 'bounded');s=store()
                if kind=='matrix':reserve(s,[item(kind,variant,1,149)],root=str(uuid4()) if shared else ROOT)
                else:
                    for _ in range(9):reserve(s,[item(kind,variant)],root=str(uuid4()) if shared else ROOT)
                sets=[ready(s,[item(kind,variant,1,1) if kind=='matrix' else item(kind,variant)],root=str(uuid4()) if shared else ROOT) for _ in range(2)]
                before=s.snapshot()['attempts'];self.race(sets)
                self.assertEqual(s.snapshot()['attempts'],before+1)

    def test_admission_competing_workers_capacity_and_burst(self):
        for count,release in [(15,False),(239,True)]:
            fixture();s=store()
            for _ in range(count):
                ident=sha256(str(uuid4()).encode()).hexdigest()
                s._call('admit',id=ident,worker=s._worker,domain='http',fingerprint=ident)
                if release:s._call('admission_release',id=ident,worker=s._worker)
            ctx=mp.get_context('spawn');barrier=ctx.Barrier(2);q=ctx.Queue()
            ps=[ctx.Process(target=admission_child,args=(barrier,q)) for _ in range(2)]
            for p in ps:p.start()
            for p in ps:p.join(20);self.assertEqual(p.exitcode,0)
            self.assertEqual(sorted([q.get(timeout=2),q.get(timeout=2)]),['denied','reserved'])

    def test_cross_day_dispatch_stays_charged_to_reservation_day(self):
        fixture('ledger_enforced',daily=20000);clock(datetime(2026,11,2,4,59,50,tzinfo=timezone.utc));s=store()
        _,l,c,_=ready(s,[item()]);r=s.reserve(l,c,str(uuid4()));s.transition(r,'INTENT')
        clock(datetime(2026,11,2,5,0,10,tzinfo=timezone.utc));dispatch(s,r,1);s.transition(r,'SUCCEEDED')
        self.assertEqual(s.usage()['dayMicrousd'],0);self.assertEqual(s.snapshot()['gross'],20000)
        with core.admin() as conn:self.assertEqual(str(conn.execute('SELECT calendar_day FROM synthetic_state.financial_lines').fetchone()[0]),'2026-11-01')

    def test_corrupt_history_or_unknown_policy_fails_closed(self):
        s=store();r,_=reserve(s,[item()],finish=False)
        with core.admin() as conn:conn.execute('TRUNCATE synthetic_state.financial_lines CASCADE')
        with self.assertRaises(Denied):s.snapshot()
        with core.admin() as conn:self.assertEqual(conn.execute('SELECT sum(charge) FROM synthetic_state.operations').fetchone()[0],20000)
        fixture();s=store()
        with core.admin() as conn:
            conn.execute('ALTER TABLE synthetic_state.finance_policy DISABLE TRIGGER USER')
            conn.execute("UPDATE synthetic_state.finance_policy SET rate_version='unknown'")
        with self.assertRaises(Denied):store()

    def test_duplicate_request_identity_cannot_move_to_new_capability(self):
        s=store();spec=item();_,o=reserve(s,[spec])
        with self.assertRaises(Denied):reserve(s,[spec],outing=o)
        self.assertEqual(s.snapshot()['attempts'],1)

    def test_default_fifty_request_and_ten_lookup_session_ceiling(self):
        s=store()
        for _ in range(2):
            _,l,_,_=ready(s)
            for _ in range(25):
                cap=s.issue(l,'ordinary_plan',str(uuid4()));approve(s,cap,[item('route','none')])
                r=s.reserve(l,cap,str(uuid4()));complete(s,r)
        with self.assertRaises(Denied):reserve(store(),[item('route','none')])
        self.assertEqual(s.snapshot()['attempts'],50)
        fixture();s=store()
        for _ in range(10):reserve(s,[item('lookup','pro')])
        clock(START+timedelta(seconds=60))
        with self.assertRaises(Denied):reserve(store(),[item('lookup','pro')])
        self.assertEqual(s.snapshot()['attempts'],10)

    def test_default_daily_ten_dollars_derived_from_matrix_units(self):
        fixture('ledger_enforced',daily=10000000);s=store()
        for index,units in enumerate([150]*6+[100]):
            clock(START+timedelta(seconds=60*index));reserve(s,[item('matrix','drive',1,units)])
        self.assertEqual(s.usage()['dayMicrousd'],10000000)
        with self.assertRaises(Denied):reserve(s,[item('matrix','drive',1,1)])
        self.assertEqual(s.snapshot()['gross'],10000000)

    def test_default_matrix_session_survives_old_evidence_expiry(self):
        s=store()
        for i in range(10):
            clock(START+timedelta(seconds=60*i));reserve(s,[item('matrix','walk',1,150)])
        clock(START+timedelta(seconds=600))
        with self.assertRaises(Denied):reserve(store(),[item('matrix','walk',1,1)])
        self.assertEqual(s.snapshot()['attempts'],10)

    def test_actual_ordinary_pending_options_selected_dtos_with_financial_role(self):
        from unittest.mock import patch
        # Reuse existing real interpreter/planner/selection contract test verbatim;
        # only substitute the restricted V3 client. No new planning implementation.
        case=core.SharedPostgresTests('test_actual_ordinary_pending_options_and_selection_contracts')
        with patch.object(core,'store',store):case.test_actual_ordinary_pending_options_and_selection_contracts()
        self.assertEqual(store().snapshot()['attempts'],0)

    def test_actual_advanced_handoff_and_result_dtos_with_financial_role(self):
        from backend.test_advanced_planning import IntegrationTests
        from backend.test_advanced_routing import start
        from backend.ai.ollama import Interpretation
        from backend.journey import Journey
        from backend.interpretation import InterpretationResult,InterpretationContext
        case=IntegrationTests('test_named_roundtrip_dto_and_receipt');case.setUp()
        try:
            result=case.run_session(case.session(endpoint={'kind':'origin','source':'return to start'}),startingLocation=start())
            self.assertEqual(result.status,'results');s=store()
            handoff=InterpretationResult(interpretation=Interpretation(activities=['coffee'],budget_per_person=None,date=None,location=None,preferences=[],journey=Journey(stops=[{'source':'coffee'}])),request=None,notes=[],issues=[],executionStatus='advanced_unavailable',context=InterpretationContext())
            for kind,payload,purpose in [(Kind.ADVANCED_RESULTS,result,'browse_only'),(Kind.HANDOFF,handoff,'handoff_only')]:
                h=s.create(kind,payload);l=s.claim(h,1);self.assertEqual(s.read(l),payload)
                c=s.issue(l,purpose,str(uuid4()))
                with self.assertRaises(Denied):s.reserve(l,c,str(uuid4()))
            self.assertEqual(s.snapshot()['attempts'],0)
        finally:case.doCleanups()

    def test_existing_provider_budget_usage_matches_sql_units(self):
        from backend.provider_budget import ProviderBudget
        budget=ProviderBudget();outing=budget.outing();s=store();_,l,_,o=ready(s)
        specs=[item('lookup','pro'),item('details','pro'),item('matrix','drive',1,2)]
        for spec in specs:
            op=spec['operation'];key=spec['request_digest']
            context=outing.reserve_matrices([(key,1,2)],traffic_aware=True) if op=='matrix' else outing.reserve(op,key,details_pro=op=='details')
            with context:
                c=s.issue(l,'ordinary_plan',str(uuid4()));approve(s,c,[spec]);r=s.reserve(l,c,str(uuid4()));complete(s,r)
        usage=outing.usage()
        with core.admin() as conn:
            row=conn.execute("SELECT count(*),count(*) FILTER(WHERE kind IN ('search','lookup')),count(*) FILTER(WHERE kind='details'),sum(units) FILTER(WHERE kind='matrix') FROM synthetic_state.financial_lines").fetchone()
        self.assertEqual(row,(usage['providerAttempts'],usage['placesSearchRequests'],usage['placesDetailsRequests'],usage['reservedMatrixElements']))
        self.assertEqual(s.snapshot()['gross'],32000+17000+20000)

    def test_existing_standalone_daily_guard_matches_sql_enforced_profile(self):
        from tempfile import TemporaryDirectory
        from unittest.mock import patch
        from backend.development_cost import DevelopmentCost,AccountingError,dispatch as record_dispatch
        with TemporaryDirectory(prefix='whereto-synthetic-usage-') as tmp:
            with patch.dict(os.environ,{'WHERETO_DEV_COST_LEDGER':str(Path(tmp)/'fictional-usage.json'),'WHERETO_DEV_DAILY_USD':'0.02'}):
                ledger=DevelopmentCost()
                self.assertEqual(ledger.limit,20000)
                with ledger.reserve({'details':1}) as charge:record_dispatch('details',1,sku='details')
                with self.assertRaises(AccountingError):
                    with ledger.reserve({'details':1}):self.fail('Over-limit admitted')
            fixture('ledger_enforced',daily=ledger.limit);s=store();reserve(s,[item()])
            with self.assertRaises(Denied):reserve(s,[item()])
            self.assertEqual(s.snapshot()['gross'],charge)

    def test_inference_burst_is_separate_from_http_and_has_same_window(self):
        s=store()
        for _ in range(240):
            ident=sha256(str(uuid4()).encode()).hexdigest()
            s._call('admit',id=ident,worker=s._worker,domain='inference',fingerprint=ident)
            s._call('admission_release',id=ident,worker=s._worker)
        with self.assertRaises(Denied):s._call('admit',id='a'*64,worker=s._worker,domain='inference',fingerprint='a'*64)
        s._call('admit',id='b'*64,worker=s._worker,domain='http',fingerprint='b'*64)
        clock(START+timedelta(seconds=10))
        s._call('admit',id='a'*64,worker=s._worker,domain='inference',fingerprint='a'*64)

    def test_request_admission_capacity_references_burst_and_restart(self):
        s=store();leases=[]
        for _ in range(16):
            args=dict(id=sha256(str(uuid4()).encode()).hexdigest(),worker=s._worker,
                      domain='http',fingerprint=sha256(str(uuid4()).encode()).hexdigest())
            s._call('admit',**args);leases.append(args)
        with self.assertRaises(Denied):s._call('admit',**dict(leases[0],id='a'*64,fingerprint='b'*64))
        # Fresh process/store cannot release another worker's lease or reset counters.
        with self.assertRaises(Denied):store()._call('admission_release',id=leases[0]['id'],worker=str(uuid4()))
        for args in leases:s._call('admission_release',id=args['id'],worker=s._worker)
        a=leases[0]
        for _ in range(224):
            ident=sha256(str(uuid4()).encode()).hexdigest()
            s._call('admit',id=ident,worker=s._worker,domain='http',fingerprint=ident)
            s._call('admission_release',id=ident,worker=s._worker)
        with self.assertRaises(Denied):s._call('admit',**dict(a,id='c'*64,fingerprint='d'*64))
        clock(START+timedelta(seconds=10));s._call('admit',**dict(a,id='c'*64,fingerprint='d'*64))
        s._call('admission_retain',id='c'*64,worker=s._worker);s._call('admission_release',id='c'*64,worker=s._worker)
        with self.assertRaises(Denied):s._call('admit',**dict(a,id='e'*64,fingerprint='d'*64))
        s._call('admission_release',id='c'*64,worker=s._worker)
        s._call('admit',id='f'*64,worker=s._worker,domain='inference',fingerprint='a'*64)
        with self.assertRaises(Denied):s._call('admit',id='b'*64,worker=s._worker,domain='inference',fingerprint='b'*64)


def seed():
    fixture();s=store();h,l,c,_=ready(s,[item()]);r=s.reserve(l,c,str(uuid4()));s.transition(r,'INTENT')
    Path('/tmp/synthetic-finance-crash.json').write_text(json.dumps({'token':h.token}))


def after_crash():
    s=store();assert s.snapshot()['gross']==20000 and s.snapshot()['states']=={'INTENT':1}
    from experiments.shared_state.contracts import SessionHandle
    h=SessionHandle(json.loads(Path('/tmp/synthetic-finance-crash.json').read_text())['token'])
    try:s.claim(h,1)
    except Denied:pass
    else:raise AssertionError('Missing volatile evidence reauthorized')
    try:reserve(s,[item()])
    except Denied:pass
    else:raise AssertionError('Uncertain exposure permitted more root work')
    print('Financial SIGKILL recovery retained computed charge/units/INTENT; no resend or reset.')


if __name__=='__main__':
    import sys
    mode=sys.argv[1] if len(sys.argv)>1 else None
    if mode=='seed':seed()
    elif mode=='after_crash':after_crash()
    elif mode=='unavailable':
        try:store()
        except Unavailable:print('Financial database outage refused without fallback.')
        else:raise AssertionError('Database outage admitted')
    else:unittest.main()
