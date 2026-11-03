"""Task50E full pipeline with invented Google-shaped fixtures; network blocked."""
from datetime import date, datetime, timezone
import os
import secrets
import unittest
from unittest.mock import patch
from backend.advanced_planning import Session, Sessions, AdvancedInput
from backend.interpretation import InterpretationContext
from backend.journey import Journey
from backend.provider_budget import ProviderBudget,ProviderSettings
from backend.saved_plans import receipts,SaveRequest,SavedDocument,PersistenceError
from backend import test_advanced_routing as routing_fixtures
from backend.test_advanced_routing import start, COLLEGE, COFFEE, GROCERY, BANK, STATION, PHARMACY
from backend.test_stop_resolution import place
from backend.test_advanced_timing import duration


class IntegrationTests(unittest.TestCase):
    matrix=routing_fixtures.AdvancedRoutingTests.matrix
    def setUp(self):
        routing_fixtures.AdvancedRoutingTests.setUp(self)
        p=patch.dict(os.environ,VENUE_DATA_MODE='real',WHERETO_REAL_DEV='1',WHERETO_ENV='development',WHERETO_ADVANCED_DEV='1')
        p.start();self.addCleanup(p.stop)
        clock=patch('backend.advanced_planning.datetime',wraps=datetime)
        fake_clock=clock.start();self.addCleanup(clock.stop)
        fake_clock.now.side_effect=lambda tz=None:datetime(2026,11,2,13,tzinfo=timezone.utc).astimezone(tz or timezone.utc)
        self.searches=[]
        self.records=[COLLEGE,COFFEE,GROCERY,BANK,PHARMACY,STATION]
        p=patch('backend.places_transport.text_search',side_effect=self.search)
        p.start();self.addCleanup(p.stop)
    def search(self,body,**kwargs):
        self.searches.append(body)
        q=body['textQuery'].lower()
        t=next((t for word,t in [('cafe','cafe'),('coffee','cafe'),('grocer','supermarket'),('atm','atm'),('bank','bank'),('pharmac','pharmacy')] if word in q),None)
        return {'places':[p for p in self.records if t is None or t in p['types']]}
    def session(self,stops=None,**kwargs):
        return Session('Synthetic public test request',Journey(stops=stops or [{'source':'SUNY College of Optometry','kind':'named_place'},{'source':'coffee'}],**kwargs),
            InterpretationContext(destination='New York',date='2026-11-07',timezone='America/New_York',timezoneBasis='destination_calendar'),ProviderBudget(ProviderSettings()))
    def run_session(self,s,**kwargs):return s.run(AdvancedInput(token=s.token,**kwargs))
    def test_named_roundtrip_dto_and_receipt(self):
        s=self.session(endpoint={'kind':'origin','source':'return to start'})
        r=self.run_session(s,startingLocation=start())
        self.assertEqual(r.status,'results');self.assertEqual(len(r.options),1)
        self.assertEqual([v.placeId for v in r.options[0].stops],['Synthetic_college','Synthetic_coffee'])
        self.assertEqual(r.options[0].ending,'origin');self.assertEqual(len(r.options[0].legs),3)
        self.assertNotIn('latitude',r.model_dump_json());self.assertNotIn('private_start',r.model_dump_json())
        document=receipts.select(SaveRequest(receipt=r.saveReceipt,accessToken=r.saveAccessToken,candidateIds=[r.options[0].id],selectedId=r.options[0].id))
        self.assertEqual(document.version,2);self.assertEqual(document.itineraries[0].advanced.occurrenceOrder,[0,1])
        self.assertEqual(document.itineraries[0].advanced.ending,'origin')
        self.assertNotIn('Synthetic coffee cafe',document.model_dump_json());self.assertNotIn('latitude',document.model_dump_json())
        count=(len(self.searches),len(self.calls))
        again=self.run_session(s,startingLocation=start())
        self.assertEqual(again,r);self.assertEqual(count,(len(self.searches),len(self.calls)))
    def test_ambiguity_choice_reuses_resolution(self):
        self.records += [place('Synthetic_other','Penn Station','2 Fixture Road, New York',['train_station'])]
        s=self.session([{'source':'Penn Station','kind':'named_place'},{'source':'coffee'}])
        r=self.run_session(s);self.assertEqual(r.status,'clarification');self.assertEqual(len(r.questions[0]['choices']),2)
        counts=len(self.searches)
        with self.assertRaises(ValueError):self.run_session(s,choice={'occurrence':0,'placeId':'fabricated'})
        r=self.run_session(s,choice={'occurrence':0,'placeId':'Synthetic_station'})
        self.assertEqual(r.status,'results');self.assertEqual(len(self.searches),counts)
        self.assertEqual(r.options[0].stops[0].placeId,'Synthetic_station')
    def test_duration_and_departure_reuse_routes(self):
        s=self.session([{'source':'grocery shopping'},{'source':'ATM','duration':duration(5)}],endpoint={'kind':'origin','source':'return'},total_duration=duration(45,'maximum'),deadline={'source':'by 6 PM','minute':1080})
        r=self.run_session(s,startingLocation=start());self.assertEqual(r.options[0].durationState,'unverified')
        self.assertEqual({q['field'] for q in r.questions},{'dwell','departure'})
        counts=(len(self.searches),len(self.calls))
        r=self.run_session(s,startingLocation=start(),dwell={'occurrence':0,'minutes':20,'relation':'exact'},departure='17:00')
        self.assertEqual(r.options[0].durationState,'feasible');self.assertEqual(r.options[0].deadlineState,'feasible')
        self.assertEqual(r.options[0].stops[0].duration.minutes,20)
        self.assertEqual(counts,(len(self.searches),len(self.calls)))
        r=self.run_session(s,startingLocation=start(),dwell={'occurrence':0,'minutes':80,'relation':'exact'})
        self.assertEqual(r.status,'no_results');self.assertEqual(r.options,[])
    def test_approximate_answer_stays_unknown(self):
        s=self.session([{'source':'coffee'}],total_duration=duration(45,'maximum'))
        self.run_session(s)
        r=self.run_session(s,dwell={'occurrence':0,'minutes':10})
        self.assertEqual(r.options[0].durationState,'unverified');self.assertIsNone(r.options[0].elapsedUpperSeconds)
    def test_home_and_missing_origin_do_not_discover(self):
        for endpoint in [{'kind':'home','source':'return home'},{'kind':'origin','source':'return to start'}]:
            s=self.session(endpoint=endpoint);r=self.run_session(s)
            self.assertIn(r.status,('unsupported','clarification'));self.assertFalse(self.searches);self.assertFalse(self.calls)
    def test_final_endpoint_and_walking(self):
        s=self.session([{'source':'coffee'}],endpoint={'kind':'named_place','source':'finish at Penn Station'})
        from backend.models import TransportationMode
        s.context.transport=TransportationMode.walking
        # Assignment follows the enum boundary used by InterpretationContext.
        s.context=InterpretationContext.model_validate(s.context.model_dump())
        r=self.run_session(s)
        self.assertEqual(r.options[0].ending,'named_destination')
        self.assertEqual(r.options[0].legs[-1].mode,'walk');self.assertEqual(r.options[0].legs[-1].role,'final_destination')
    def test_partial_order_optional_and_saved_selection(self):
        s=self.session([{'source':'pharmacy'},{'source':'bank'},{'source':'grocery shopping','requirement':'optional'}],ordering='constrained',order=[{'before':0,'after':1,'source':'pharmacy before bank'}])
        r=self.run_session(s)
        for option in r.options:
            order=[v.occurrence for v in option.stops];self.assertLess(order.index(0),order.index(1))
        selected=r.options[-1]
        d=receipts.select(SaveRequest(receipt=r.saveReceipt,accessToken=r.saveAccessToken,candidateIds=[p.id for p in r.options],selectedId=selected.id))
        self.assertEqual(len(d.itineraries),1);self.assertEqual(d.selectedId,selected.id)
        corrupt=d.model_dump();corrupt['itineraries'][0]['advanced']['occurrenceOrder']=[1,0]
        with self.assertRaises(ValueError):SavedDocument.model_validate(corrupt)
    def test_expiry_gates_and_config_changes(self):
        registry=Sessions();s=self.session();registry.items[s.token]=s
        self.assertEqual(registry.run(AdvancedInput(token=s.token)).status,'results')
        with self.assertRaises(ValueError):self.run_session(s,startingLocation=start())
        s.expires=0
        with self.assertRaises(ValueError):registry.run(AdvancedInput(token=s.token))
        with patch.dict(os.environ,WHERETO_ADVANCED_DEV='0'):
            with self.assertRaises(Exception):registry.run(AdvancedInput(token=s.token))
    def test_arbitrary_route_input_rejected(self):
        for key in ('route','options','feasible','placeId','context'):
            with self.assertRaises(ValueError):AdvancedInput.model_validate({'token':secrets.token_urlsafe(32),key:{}})
    def test_strict_limits_and_unresolved_required(self):
        s=self.session();r=self.run_session(s,firstTravel={'value':0,'unit':'minutes','mode':'strict'},startingLocation=start())
        self.assertEqual(r.status,'no_results')
        s=self.session([{'source':'Unknown College','kind':'named_place'},{'source':'coffee'}]);r=self.run_session(s)
        self.assertEqual(r.status,'no_results');self.assertEqual(r.options,[])
    def test_relative_date_without_destination_timezone_needs_explicit_date(self):
        session=Session('Go to Penn Station today.',Journey(stops=[{'source':'Penn Station','kind':'named_place'}]),
            InterpretationContext(date='2026-11-07',timezone='UTC',timezoneBasis='unknown'),ProviderBudget(ProviderSettings()))
        result=self.run_session(session)
        self.assertEqual(result.status,'clarification');self.assertEqual(result.questions[0]['field'],'date')
        self.assertFalse(self.searches)
        result=self.run_session(session,date='2026-11-07')
        self.assertEqual(result.status,'results')
        # At 02:00 UTC on Nov3 it is still Nov2 in New York. Do not declare
        # the user's confirmed Nov2 date expired using an unknown UTC basis.
        session=Session('Go to Penn Station today.',Journey(stops=[{'source':'Penn Station','kind':'named_place'}]),
            InterpretationContext(date='2026-11-02',timezone='UTC',timezoneBasis='unknown'),ProviderBudget(ProviderSettings()))
        with patch('backend.advanced_planning.datetime',wraps=datetime) as clock:
            clock.now.side_effect=lambda tz=None:datetime(2026,11,3,2,tzinfo=timezone.utc).astimezone(tz or timezone.utc)
            answer=self.run_session(session,date='2026-11-02')
            self.assertEqual(answer.status,'clarification');self.assertEqual(answer.questions[0]['field'],'destination')
            answer=self.run_session(session,destination='New York')
            self.assertEqual(answer.status,'results');self.assertEqual(answer.date,'2026-11-02')
            counts=(len(self.searches),len(self.calls))
            answer=self.run_session(session,departure='14:00')
            self.assertEqual(answer.status,'clarification');self.assertEqual(answer.questions[0]['field'],'departure')
            answer=self.run_session(session,departure='22:00')
            self.assertEqual(answer.status,'results')
            self.assertEqual(counts,(len(self.searches),len(self.calls)))

    def test_provider_error_categories_survive_the_complete_route_pipeline(self):
        from backend.routes import RouteError
        for code,expected in [('quota','provider_quota_rejected'),('application_limit','provider_local_admission'),('provider','provider_service_error')]:
            with self.subTest(code=code):
                self.route_error=RouteError(code,'Invented transport failure')
                result=self.run_session(self.session())
                self.assertEqual(result.code,expected)
                self.assertTrue(result.message)
                self.assertTrue(all(p.state=='unverified' for p in result.options))

    def test_private_decimal_origin_clause_never_enters_saved_source(self):
        session=self.session([{'source':'coffee','duration':{'minutes':15,'relation':'exact','source':'Start from 40.75,-73.98; coffee for 15 minutes'}}])
        session.text='Start from 40.75,-73.98, then get coffee.'
        session.context.originText='40'  # Conservative parser stopped at a decimal.
        result=self.run_session(session,startingLocation=start())
        self.assertNotIn('40.75',result.model_dump_json());self.assertNotIn('73.98',result.model_dump_json())
        document=receipts.select(SaveRequest(receipt=result.saveReceipt,accessToken=result.saveAccessToken,candidateIds=[p.id for p in result.options],selectedId=result.options[0].id))
        text=document.model_dump_json()
        self.assertNotIn('73.98',text);self.assertNotIn('40.75',text)
        self.assertIn('private location omitted',text)

    def test_token_substitution(self):
        r=self.run_session(self.session())
        with self.assertRaises(PersistenceError):receipts.select(SaveRequest(receipt=r.saveReceipt,accessToken=secrets.token_urlsafe(32),candidateIds=[r.options[0].id],selectedId=r.options[0].id))

if __name__=='__main__':unittest.main()

@unittest.skipUnless(os.environ.get('WHERETO_DB_SCHEMA_TESTS')=='1','Opt-in committed advanced PostgreSQL checks')
class HostedAdvancedTests(unittest.TestCase):
    def test_committed_restricted_write_fresh_process_reopen_and_cleanup(self):
        import json
        import subprocess
        import psycopg
        from backend.database_check import connection_settings
        from backend.saved_plans import save,reopen,OpenRequest,digest
        harness=IntegrationTests('test_named_roundtrip_dto_and_receipt');harness.setUp()
        try:
            session=harness.session([{'source':'pharmacy'},{'source':'bank'},{'source':'grocery shopping','requirement':'optional'}],ordering='constrained',order=[{'before':0,'after':1,'source':'pharmacy before bank'}],endpoint={'kind':'origin','source':'return'})
            result=harness.run_session(session,startingLocation=start())
            request=SaveRequest(receipt=result.saveReceipt,accessToken=result.saveAccessToken,candidateIds=[p.id for p in result.options],selectedId=result.options[0].id)
            with psycopg.connect(**connection_settings(os.environ),autocommit=True) as admin:
                key=digest(request.accessToken)
                try:
                    self.assertEqual(save(request),{'saved':True})
                    first=reopen(OpenRequest(accessToken=request.accessToken))
                    self.assertEqual(first['version'],2);self.assertEqual(len(first['itineraries']),1)
                    # Separate interpreter proves no process-local receipt/session dependency.
                    script="import json,sys;from backend.saved_plans import reopen,OpenRequest;v=reopen(OpenRequest(accessToken=sys.stdin.read()));print(json.dumps(v))"
                    process=subprocess.run(['backend/.venv/bin/python','-c',script],input=request.accessToken,text=True,capture_output=True,check=True)
                    reopened=json.loads(process.stdout)
                    self.assertEqual(reopened,first)
                    self.assertEqual(reopened['itineraries'][0]['advanced']['ending'],'origin')
                    with self.assertRaises(PersistenceError):reopen(OpenRequest(accessToken=secrets.token_urlsafe(32)))
                    print('50E hosted committed write/restart-read/token isolation: passed; schema migrations unchanged')
                finally:
                    admin.execute('DELETE FROM whereto.plans WHERE access_hash=%s',(key,))
                    self.assertEqual(admin.execute('SELECT count(*) FROM whereto.plans WHERE access_hash=%s',(key,)).fetchone()[0],0)
        finally:harness.doCleanups()
