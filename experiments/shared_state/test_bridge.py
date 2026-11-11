"""Actual application paths, isolated SQL and invented provider evidence only."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime,timezone
import json
import multiprocessing as mp
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4

import psycopg
from backend import action_dispatch as io
from backend.ai import Interpretation
from backend.interpretation import InterpretationInput,ClarificationAnswers
from backend.provider_budget import ProviderBudget,ProviderSettings
from backend.saved_refresh import RefreshRequest
from backend.test_real_planning import ENV,outing
from backend.real_fixtures import search_fixture,matrix_fixture
from backend.testing_clock import calendar_clock
from experiments.shared_state import test_financial as f
from experiments.shared_state import test_store as core
from experiments.shared_state.action_bridge import Broker,BridgeStore,LocalIssuer
from experiments.shared_state.contracts import Denied

NOW=datetime(2026,11,2,13,tzinfo=timezone.utc)


def fixture():
    f.fixture(extension=lambda c:c.execute(Path(__file__).with_name('bridge.sql').read_text(),prepare=False))


def store():return BridgeStore(key=core.KEY,password=os.environ['SYNTHETIC_WORKER_PASSWORD'],limits=f.LIMITS)


@contextmanager
def issuer_connection():
    with core.admin() as c:
        c.execute('SET LOCAL ROLE whereto_synthetic_issuer')
        yield c


class Model:
    def __init__(self,data=None):self.calls=0;self.data=data or dict(activities=['coffee','museum'],location='Baltimore',date='2026-11-07',budget_per_person=None,preferences=[])
    def interpret(self,text):self.calls+=1;return Interpretation.model_validate(deepcopy(self.data))


def crash_worker(pipe):
    s=store()
    broker=Broker(s,LocalIssuer(issuer_connection,f.ROOT),Model(),ProviderBudget(ProviderSettings(mode='real',candidates_per_activity=3)),None,now=NOW)
    def crash(value):
        pipe.send(broker._Broker__batch['reservation'])
        os._exit(42)  # Actual process death after SQL INTENT and dispatch commit.
    broker._Broker__fake=crash
    token,_=broker.interpret(InterpretationInput(text='Coffee and museum in Baltimore on November 7, 2026',calendarTimezone='America/New_York'),execution={'startingLocation':outing().startingLocation})
    broker.plan(token)


class BridgeTests(unittest.TestCase):
    def setUp(self):
        fixture();self.enterContext(calendar_clock(NOW))
        self.enterContext(patch.dict(os.environ,ENV|{'WHERETO_START_LOOKUP_DEV':'1','WHERETO_CONTACT_DETAILS_DEV':'1','WHERETO_ADVANCED_DEV':'1','WHERETO_STOP_RESOLUTION_DEV':'1','WHERETO_ROUTES_DEV':'1'},clear=False))
        self.enterContext(patch('requests.sessions.Session.send',side_effect=AssertionError('Live transport forbidden')))
        self.enterContext(patch('backend.advanced_planning.datetime',wraps=datetime))
        from backend import advanced_planning
        advanced_planning.datetime.now.side_effect=lambda tz=None:NOW.astimezone(tz or timezone.utc)
        self.model=Model();self.calls=[];self.s=store()
        self.broker=self.make(self.model)
    def make(self,model):return Broker(self.s,LocalIssuer(issuer_connection,f.ROOT),model,ProviderBudget(ProviderSettings(mode='real',candidates_per_activity=3)),self.fake,now=NOW)
    def fake(self,v):
        self.calls.append(deepcopy(v))
        if v['operation']=='matrix':return matrix_fixture(v['body'])
        if v['operation']=='details':return {'id':v['url'].rsplit('/',1)[-1],'name':'Synthetic venue'}
        return search_fixture(v['body'])
    def initial(self,data=None,text='Coffee and museum in Baltimore on November 7, 2026',preferences=None):
        if data:self.broker=self.make(Model(data))
        token,result=self.broker.interpret(InterpretationInput(text=text,calendarTimezone='America/New_York',preferences=preferences or {}),execution={'startingLocation':outing().startingLocation})
        return token,result

    def test_actual_ordinary_pipeline_financial_dispatch_and_options(self):
        token,result=self.initial();self.assertIsNotNone(result.request)
        planned=self.broker.plan(token)
        self.assertTrue(planned.provisionalPlans);self.assertGreater(len(self.calls),2)
        self.assertEqual(self.model.calls,1)
        self.assertGreater(self.s.snapshot()['gross'],0)
        if planned.optionsToken:self.broker.more(token)
        from backend.saved_plans import receipts,SaveRequest
        candidates=planned.provisionalPlans+planned.plans
        planned=receipts.issue(planned)
        selected=receipts.select(SaveRequest(receipt=planned.saveReceipt,accessToken=planned.saveAccessToken,candidateIds=[p.candidate.id for p in candidates],selectedId=candidates[0].candidate.id))
        self.assertEqual(selected.selectedId,candidates[0].candidate.id)

    def test_pending_date_answer_no_new_model_and_no_browser_snapshot_authority(self):
        self.model.data['date']=None
        token,result=self.initial(text='Coffee and museum in Baltimore',preferences={'transport':'walking'})
        self.assertIsNotNone(result.pending);self.assertEqual(self.calls,[])
        resolved=self.broker.answer(token,ClarificationAnswers(date='2026-11-07'))
        self.assertIsNotNone(resolved.request);self.assertEqual(resolved.request.transport.value,'walking')
        # Pending completion preserves current source evidence without another inference.
        planned=self.broker.plan(token);self.assertTrue(planned.provisionalPlans);self.assertTrue(self.calls);self.assertEqual(self.model.calls,1)
        self.assertTrue(all(v['body']['travelMode']=='WALK' for v in self.calls if v['operation']=='matrix'))
        with self.assertRaises(Denied):self.broker.plan(token)
        with self.assertRaises(Denied):self.broker.interpret(InterpretationInput(text=result.pending.text,pending=result.pending))

    def test_invalid_source_revocation_and_direct_transport_are_blocked(self):
        with self.assertRaises(Denied):self.broker.dispatch(io.Request.make('search','POST','invalid','',{}))
        token,_=self.initial();self.broker.revoke(token)
        with self.assertRaises(Denied):self.broker.plan(token)
        self.assertEqual(self.calls,[]);self.assertEqual(self.s.snapshot()['attempts'],0)

    def test_changed_payload_after_reservation_retains_uncertainty(self):
        token,_=self.initial();original=self.broker.dispatch
        def mutate(request):
            v=request.value();v['body']['textQuery']='Unrelated destination'
            return original(io.Request.make(v['operation'],v['method'],v['url'],v['mask'],v['body']))
        with patch.object(self.broker,'dispatch',side_effect=mutate):
            with self.assertRaises(Denied):self.broker.plan(token)
        self.assertEqual(self.calls,[]);self.assertEqual(self.s.snapshot()['attempts'],1)
        self.assertEqual(self.s.snapshot()['states'],{'UNCERTAIN':1})

    def test_wrong_method_mask_and_dimensions_canonical_mismatch(self):
        for field,value in [('method','GET'),('mask','places.id'),('url','https://example.invalid')]:
            fixture();self.s=store();self.broker=self.make(self.model);token,_=self.initial()
            original=self.broker.dispatch
            def mutate(request):
                v=request.value();v[field]=value
                return original(io.Request.make(v['operation'],v['method'],v['url'],v['mask'],v['body']))
            with patch.object(self.broker,'dispatch',side_effect=mutate),self.assertRaises(Denied):self.broker.plan(token)
        self.assertEqual(self.calls,[])

    def test_runtime_cannot_register_action_or_call_old_financial_reserve(self):
        for sql,args in [('SELECT synthetic_state.register_action(%s,%s,%s,%s)',('f'*64,'e'*64,None,None)),
                         ('SELECT synthetic_state.financial_protocol(%s,%s)',('usage',psycopg.types.json.Jsonb({})))]:
            with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                with psycopg.connect(**self.s._connection) as c:c.execute(sql,args)

    def test_refresh_specific_owner_decision_and_replay(self):
        doc={'dataMode':'real','selectedId':'chosen','itineraries':[{'candidateId':'chosen','stops':[{'reference':'Synthetic_one'},{'reference':'Synthetic_two'}]}]}
        request=RefreshRequest(accessToken='A'*43,candidateId='chosen',refreshId=uuid4())
        with patch('backend.saved_plans.reopen',return_value=doc),patch('backend.saved_refresh.reopen',return_value=doc):
            result=self.broker.refresh(request);self.assertTrue(all(v['status']=='refreshed' for v in result['venues'].values()))
            count=len(self.calls);self.broker.refresh(request);self.assertEqual(len(self.calls),count)
            # Lost native memory must not reset durable refresh consumption.
            restarted=self.make(self.model)
            with self.assertRaises(Denied):restarted.refresh(request)
        self.assertEqual(self.model.calls,0)

    def test_refresh_changed_document_or_unselected_itinerary_refuses(self):
        request=RefreshRequest(accessToken='A'*43,candidateId='other',refreshId=uuid4())
        doc={'dataMode':'real','selectedId':'chosen','itineraries':[{'candidateId':'other','stops':[{'reference':'Synthetic_one'}]}]}
        with patch('backend.saved_plans.reopen',return_value=doc),self.assertRaises(Denied):self.broker.refresh(request)
        self.assertEqual(self.calls,[])

    def advanced_fixture(self,index=3):
        from backend.journey_fixtures import CASES
        from backend.test_advanced_planning import IntegrationTests
        from backend.test_advanced_routing import AdvancedRoutingTests,COLLEGE,COFFEE,GROCERY,BANK,PHARMACY,STATION
        from types import SimpleNamespace
        text,data,_=CASES[index];self.broker=self.make(Model(data))
        search=IntegrationTests('test_named_roundtrip_dto_and_receipt');search.searches=[];search.records=[COLLEGE,COFFEE,GROCERY,BANK,PHARMACY,STATION]
        route=SimpleNamespace(calls=[],values={},route_error=None,partial=False)
        def fake(v):
            self.calls.append(deepcopy(v))
            if v['operation']=='matrix':return AdvancedRoutingTests.matrix(route,v['body'])
            if v['operation']=='details':return {'id':v['url'].rsplit('/',1)[-1]}
            return search.search(v['body'])
        self.broker._Broker__fake=fake  # Trusted synthetic response provider, not an approval.
        source,result=self.broker.interpret(InterpretationInput(text=text,calendarTimezone='America/New_York'))
        token=self.broker.plan(source)
        return source,result,token

    def test_actual_advanced_date_area_origin_and_named_order(self):
        from backend.advanced_planning import AdvancedInput
        from backend.test_advanced_routing import start
        source,_,token=self.advanced_fixture()
        self.assertTrue(token);self.assertEqual(self.calls,[])
        r=self.broker.advance(source,AdvancedInput(token=token,date='2026-11-07',destination='New York',startingLocation=start()))
        self.assertEqual(r.status,'results');self.assertTrue(r.options)
        self.assertEqual([s.placeId for s in r.options[0].stops],['Synthetic_college','Synthetic_coffee'])
        self.assertTrue(any(v['operation']=='matrix' for v in self.calls))
        with self.assertRaises(Denied):self.broker.advance(source,AdvancedInput(token='A'*43))

    def test_contradictory_source_never_creates_advanced_session_or_search(self):
        from backend.journey_fixtures import CASES
        text,data,_=CASES[20];self.broker=self.make(Model(data))
        source,result=self.broker.interpret(InterpretationInput(text=text,calendarTimezone='America/New_York'))
        self.broker.plan(source)
        self.assertEqual(self.calls,[]);self.assertEqual(self.s.snapshot()['attempts'],0)

    def test_lookup_and_starting_area_use_actual_typed_controls(self):
        from backend.starting_places import StartingPlaceQuery
        # Search response ownership/membership and coordinates are checked by the
        # existing lookup implementation, not by a synthetic interpretation.
        result=self.broker.lookup(StartingPlaceQuery(query='Coffee shop Baltimore'))
        self.assertTrue(self.calls);self.assertTrue(result)
        self.assertEqual(self.calls[0]['body']['textQuery'],'Coffee shop Baltimore')
        self.assertEqual(self.s.snapshot()['gross'],32000)

    def test_lost_admission_or_evidence_refuses_dispatch_retains_charge(self):
        for fault in ['admission','evidence']:
            fixture();self.s=store();self.broker=self.make(self.model);token,_=self.initial()
            original=self.broker.dispatch
            def interrupt(request):
                if fault=='evidence':
                    with core.admin() as c:c.execute('DELETE FROM synthetic_state.evidence')
                else:
                    http=self.broker._Broker__current['http']
                    self.s._call('admission_release',id=http,worker=self.s._worker)
                return original(request)
            with patch.object(self.broker,'dispatch',side_effect=interrupt),self.assertRaises(Denied):self.broker.plan(token)
            self.assertEqual(self.calls,[]);self.assertGreater(self.s.snapshot()['gross'],0)

    def test_interrupted_fake_transport_no_retry(self):
        token,_=self.initial()
        def uncertain(v):self.calls.append(v);raise TimeoutError('Synthetic uncertain response')
        self.broker._Broker__fake=uncertain
        with self.assertRaises(TimeoutError):self.broker.plan(token)
        self.assertEqual(len(self.calls),1);self.assertEqual(self.s.snapshot()['states'],{'UNCERTAIN':1})
        with self.assertRaises(ValueError):self.broker.plan(token)

    def test_source_edit_invalidation_and_tampered_internal_snapshot(self):
        token,_=self.initial()
        source=self.broker._Broker__sources[token]
        source.payload.location='Other destination'
        with self.assertRaises(Denied):self.broker.plan(token)
        self.assertEqual(self.calls,[])
        source.payload.location='Baltimore'
        new,_=self.broker.replace(token,InterpretationInput(text='Coffee and museum in Baltimore on November 7, 2026',calendarTimezone='America/New_York'),execution={'startingLocation':outing().startingLocation})
        with self.assertRaises(Denied):self.broker.plan(token)
        self.assertNotEqual(new,token)

    def test_refresh_revoked_access_and_changed_document_before_next_send(self):
        from backend.saved_plans import PersistenceError
        request=RefreshRequest(accessToken='A'*43,candidateId='chosen',refreshId=uuid4())
        with patch('backend.saved_plans.reopen',side_effect=PersistenceError(404)),self.assertRaises(PersistenceError):self.broker.refresh(request)
        self.assertEqual(self.calls,[])
        doc={'dataMode':'real','selectedId':'chosen','itineraries':[{'candidateId':'chosen','stops':[{'reference':'Synthetic_one'},{'reference':'Synthetic_two'}]}]}
        original=self.broker._Broker__fake
        def change(v):
            response=original(v);doc['selectedId']='changed';return response
        self.broker._Broker__fake=change
        with patch('backend.saved_plans.reopen',side_effect=lambda _:deepcopy(doc)),patch('backend.saved_refresh.reopen',side_effect=lambda _:deepcopy(doc)):
            with self.assertRaises(Denied):self.broker.refresh(request)
        self.assertEqual(len(self.calls),1)

    def test_optional_flexible_and_origin_advanced_workflows(self):
        from backend.advanced_planning import AdvancedInput
        from backend.test_advanced_routing import start
        for index in (5,7,9):
            with self.subTest(index=index):
                fixture();self.s=store();self.calls=[]
                source,raw,token=self.advanced_fixture(index)
                self.assertTrue(token)
                result=self.broker.advance(source,AdvancedInput(token=token,date='2026-11-07',destination='New York',startingLocation=start()))
                self.assertEqual(result.status,'results');self.assertTrue(result.options)
                for option in result.options:
                    included={s.occurrence for s in option.stops}
                    self.assertIn(0,included)
                    if index==7:self.assertIn(1,included)
                    if index==9:self.assertEqual(option.ending,'origin')
                if index==5:
                    # Existing legacy optional-coffee order loss is preserved.
                    self.assertEqual(raw.interpretation.journey.order,[])
                    self.assertTrue(any(len(o.stops)==1 for o in result.options))

    def test_contact_membership_and_single_use(self):
        token,_=self.initial();result=self.broker.plan(token)
        from backend.venue_details import details_sessions
        identity=next(iter(details_sessions.entries[result.detailsToken][1]))
        self.broker.contact(token,identity)
        count=len(self.calls)
        from backend.places import DiscoveryError
        with self.assertRaises(DiscoveryError):self.broker.contact(token,identity)
        with self.assertRaises(DiscoveryError):self.broker.contact(token,'Synthetic_unauthorized')
        self.assertEqual(len(self.calls),count)

    def test_expired_source_and_contextvar_default_refuse(self):
        token,_=self.initial()
        with patch('experiments.shared_state.action_bridge.monotonic',return_value=10**15),self.assertRaises(Denied):self.broker.plan(token)
        self.assertEqual(self.calls,[])
        self.assertIsNone(io.search({'invalid':object()}))
        self.assertEqual(io.send(None),(False,None))

    def test_real_worker_crash_retains_exposure_and_fences_old_dispatch(self):
        ctx=mp.get_context('fork');parent,child=ctx.Pipe(duplex=False)
        process=ctx.Process(target=crash_worker,args=(child,));process.start()
        self.assertTrue(parent.poll(20));reservation=parent.recv();process.join(10)
        self.assertEqual(process.exitcode,42)
        restarted=store();before=restarted.snapshot()['gross'];self.assertGreater(before,0)
        restarted.claim(reservation.lease.session,1)
        self.assertEqual(restarted.snapshot()['states'],{'UNCERTAIN':1})
        with self.assertRaises(Denied):restarted.transition(reservation,'SUCCEEDED')
        self.assertEqual(restarted.snapshot()['gross'],before)
        parent.close();child.close()

    def test_actual_starting_area_resolution(self):
        from backend.starting_areas import StartingAreaQuery
        self.broker.lookup(StartingAreaQuery(destination='Baltimore',activities=['coffee']))
        self.assertTrue(self.calls)
        self.assertTrue(all('Baltimore' in v['body'].get('textQuery','') for v in self.calls if v['operation']=='search'))

    def test_sql_dispatch_digest_and_context_ownership(self):
        token,_=self.initial();original=self.s._call
        def alter(command,**args):
            if command=='dispatch':args['payload_digest']='0'*64
            return original(command,**args)
        with patch.object(self.s,'_call',side_effect=alter),self.assertRaises(Denied):self.broker.plan(token)
        self.assertEqual(self.calls,[]);self.assertGreater(self.s.snapshot()['gross'],0)
        with self.assertRaises(Denied):self.broker.dispatch(io.Request.make('search','POST','https://invalid','x',{}))

    def test_cancel_after_reservation_does_not_send_or_refund(self):
        from backend.provider_work import cancelled
        from backend.provider_budget import ProviderLimitError
        from threading import Event
        token,_=self.initial();event=Event();context=cancelled.set(event);original=self.broker.dispatch
        def cancel(request):event.set();return original(request)
        try:
            with patch.object(self.broker,'dispatch',side_effect=cancel):
                try:self.broker.plan(token)
                except ProviderLimitError:pass
        finally:cancelled.reset(context)
        self.assertEqual(self.calls,[]);self.assertGreater(self.s.snapshot()['gross'],0)
        self.assertEqual(self.s.snapshot()['states'],{'UNCERTAIN':1})

    def test_pending_location_and_unsafe_execution_override(self):
        self.model.data['location']=None
        token,result=self.initial(text='Coffee and museum on November 7, 2026')
        self.assertIsNotNone(result.pending)
        self.broker.answer(token,ClarificationAnswers(location='Baltimore'))
        planned=self.broker.plan(token)
        self.assertTrue(planned.provisionalPlans);self.assertEqual(self.model.calls,1)
        with self.assertRaises(Denied):self.broker.interpret(InterpretationInput(text='Coffee'),execution={'activities':['museum']})

    def test_altered_matrix_dimensions_mode_and_geography_never_send(self):
        for field in ('dimensions','mode','geography'):
            with self.subTest(field=field):
                fixture();self.s=store();self.calls=[];self.broker=self.make(self.model);token,_=self.initial()
                original=self.broker.dispatch
                def mutate(request):
                    v=request.value()
                    if v['operation']=='matrix':
                        if field=='dimensions':v['body']['origins']=v['body']['origins']*2
                        elif field=='mode':v['body']['travelMode']='WALK'
                        else:v['body']['origins'][0]['waypoint']={'location':{'latLng':{'latitude':0,'longitude':0}}}
                        request=io.Request.make(v['operation'],v['method'],v['url'],v['mask'],v['body'])
                    return original(request)
                with patch.object(self.broker,'dispatch',side_effect=mutate),self.assertRaises(Denied):self.broker.plan(token)
                self.assertFalse(any(v['operation']=='matrix' for v in self.calls))
                self.assertEqual(self.s.snapshot()['states'].get('UNCERTAIN'),1)

    def test_new_source_revision_invalidates_already_reserved_action(self):
        token,_=self.initial();original=self.broker.dispatch
        def advance_revision(request):
            s=self.broker._Broker__sources[token]
            s.revision+=1;s.digest=self.broker._seal(s)  # Synthetic server-owned edit during work.
            return original(request)
        with patch.object(self.broker,'dispatch',side_effect=advance_revision),self.assertRaises(Denied):self.broker.plan(token)
        self.assertEqual(self.calls,[]);self.assertEqual(self.s.snapshot()['states'],{'UNCERTAIN':1})

if __name__=='__main__':unittest.main()
