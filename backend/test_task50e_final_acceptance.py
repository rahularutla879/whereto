"""Task 50E acceptance: invented Google evidence; all real HTTP blocked."""
from copy import deepcopy
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
import os,unittest
from backend import test_advanced_planning as integration
from backend.test_advanced_timing import duration
from backend.test_advanced_routing import start
from backend.hours_fixtures49 import fixture_hours
from backend.saved_plans import receipts,SaveRequest,SavedDocument

class AcceptanceRepairTests(unittest.TestCase):
    setUp=integration.IntegrationTests.setUp
    matrix=integration.IntegrationTests.matrix
    search=integration.IntegrationTests.search
    session=integration.IntegrationTests.session
    run_session=integration.IntegrationTests.run_session
    def closed_session(self,*,coffee_closed=False,total=180):
        now=datetime.now(timezone.utc)-timedelta(seconds=2)
        clock=patch('backend.advanced_planning.datetime',wraps=datetime).start();self.addCleanup(patch.stopall)
        clock.now.side_effect=lambda tz=None:datetime.now(timezone.utc).astimezone(tz or timezone.utc)
        self.records=deepcopy(self.records)
        for p in self.records:
            closed=p['id']=='Synthetic_college' or coffee_closed and p['id']=='Synthetic_coffee'
            p.update(fixture_hours(closed=closed,now=now))
            # Explicit invented 24-hour evidence keeps open-café cases independent
            # of the wall-clock time at which this test suite is run.
            if not closed:p['currentOpeningHours']['periods']=[{'open':{'day':0,'hour':0,'minute':0}}]
        s=self.session([{'source':'SUNY College of Optometry','kind':'named_place','duration':duration(10)},{'source':'coffee','duration':duration(10)}],total_duration=duration(total,'maximum'),endpoint={'kind':'origin','source':'return'})
        s.context.date=now.astimezone(__import__('zoneinfo').ZoneInfo('America/New_York')).date()
        s.context.departureNow=True;s.context.departureSource='now'
        return s

    def test_closed_named_offer_explicit_exact_identity_and_save(self):
        s=self.closed_session();r=self.run_session(s,startingLocation=start())
        self.assertEqual(r.status,'no_results');self.assertIn('SUNY College of Optometry is expected to be closed',r.message)
        self.assertEqual(len(r.closureOffers),1)
        counts=len(self.searches),len(self.calls)
        r=self.run_session(s,startingLocation=start(),proceedClosed=r.closureOffers[0]['token'])
        self.assertEqual(r.status,'results');self.assertTrue(r.options[0].stops[0].closedVisitException)
        self.assertEqual(r.options[0].stops[0].placeId,'Synthetic_college')
        self.assertEqual(r.options[0].stops[0].hoursState,'infeasible');self.assertEqual(r.options[0].state,'unverified')
        self.assertEqual(r.options[0].ending,'origin');self.assertEqual(counts,(len(self.searches),len(self.calls)))
        r=self.run_session(s,startingLocation=start(),edits={'dwell':[{'occurrence':1,'minutes':20,'relation':'exact'}]})
        self.assertTrue(r.options[0].stops[0].closedVisitException)  # A later café visit does not change the college visit.
        self.assertEqual(counts,(len(self.searches),len(self.calls)))
        d=receipts.select(SaveRequest(receipt=r.saveReceipt,accessToken=r.saveAccessToken,candidateIds=[r.options[0].id],selectedId=r.options[0].id))
        self.assertEqual(d.itineraries[0].advanced.closedVisitOccurrences,[0])
        for forbidden in ('currentOpeningHours','periods','duration_seconds','observedAt','latitude'):self.assertNotIn(forbidden,d.model_dump_json())
        self.assertEqual(SavedDocument.model_validate_json(d.model_dump_json()),d)
        malformed=d.model_dump();malformed['itineraries'][0]['advanced'].update(closedVisitOccurrences=[3],occurrenceOrder=[3])
        with self.assertRaises(ValueError):SavedDocument.model_validate(malformed)
        print('Acceptance closed fixture:',s.selection_counts,'provider calls before/after',counts,(len(self.searches),len(self.calls)))

    def test_forged_or_stale_closure_cannot_authorize(self):
        import secrets
        s=self.closed_session();r=self.run_session(s,startingLocation=start())
        with self.assertRaises(ValueError):self.run_session(s,startingLocation=start(),proceedClosed=secrets.token_urlsafe(32))
        with self.assertRaises(ValueError):self.run_session(s,startingLocation=start(),proceedClosed=r.closureOffers[0]['token'],edits={'dwell':[{'occurrence':0,'minutes':11,'relation':'exact'}]})

    def test_closure_does_not_waive_cafe_hours_or_deadline(self):
        for coffee_closed,total in [(True,180),(False,1)]:
            s=self.closed_session(coffee_closed=coffee_closed,total=total);r=self.run_session(s,startingLocation=start())
            if r.closureOffers:
                r=self.run_session(s,startingLocation=start(),proceedClosed=r.closureOffers[0]['token'])
            self.assertEqual(r.options,[])

    def test_removal_and_duration_change_reconfirm(self):
        for edits in ({'removeClosure':[0]},{'dwell':[{'occurrence':0,'minutes':12,'relation':'exact'}]}):
            s=self.closed_session();r=self.run_session(s,startingLocation=start());r=self.run_session(s,startingLocation=start(),proceedClosed=r.closureOffers[0]['token'])
            self.assertTrue(r.preferences['closedVisits'])
            r=self.run_session(s,startingLocation=start(),edits=edits)
            self.assertFalse(r.options);self.assertTrue(r.closureOffers);self.assertEqual(r.preferences['closedVisits'],[])

    def test_manual_future_date_survives_model_free_session_renewal(self):
        from backend.interpretation import InterpretationContext
        from backend.advanced_planning import Session
        s=self.closed_session()
        future=s.context.date+timedelta(days=1)
        context=s.context.model_copy(update={'date':future,'dateOverride':True})
        renewed=Session(s.text,s.journey,context,integration.ProviderBudget(integration.ProviderSettings()))
        r=self.run_session(renewed,startingLocation=start())
        self.assertEqual(r.date,future.isoformat());self.assertEqual(r.status,'clarification')
        self.assertEqual(r.questions[0]['field'],'departure')

    def test_dense_optional_inventory_and_edit_benchmark(self):
        from backend.test_stop_resolution import place
        from time import perf_counter
        from statistics import median
        self.records=[place(f'Synthetic_{kind}_{i}',f'Invented {kind} {i}',types=[kind],lat=40.75+i*.0001) for kind in ('supermarket','pharmacy','cafe') for i in range(10)]
        s=self.optional();r=self.run_session(s,startingLocation=start())
        self.assertGreater(s.selection_counts['optionalInclusive'],0)
        self.assertTrue(any(q.get('occurrence')==2 for q in r.questions))
        count=len(self.searches),len(self.calls)
        times=[]
        with patch('backend.interpretation.create_provider',side_effect=AssertionError('No model for structured edits')):
            for n in range(10):
                started=perf_counter()
                r=self.run_session(s,startingLocation=start(),edits={'dwell':[{'occurrence':2,'minutes':10 if n%2 else 20,'relation':'exact'}]})
                times.append((perf_counter()-started)*1000)
                self.assertTrue(any(len(o.stops)==3 for o in r.options))
        self.assertEqual(count,(len(self.searches),len(self.calls)))
        self.assertEqual(len({o.id for o in r.options}),len(r.options))
        print('Acceptance dense optional:',s.selection_counts,'coverage',s.resolver.coverage(s.router,s.seen), 'edit median ms',round(median(times),3),'max ms',round(max(times),3),'incremental Qwen/Google=0/0')

    def test_recorded_actual_qwen_preserves_both_exact_owner_requests(self):
        import json
        from pathlib import Path
        from unittest.mock import Mock
        from backend.ai import Interpretation
        from backend.interpretation import InterpretationInput,interpret_request
        rows=json.loads(Path('backend/repair_extractions.json').read_text())[-2:]
        for row in rows:
            provider=Mock();provider.interpret.return_value=Interpretation.model_validate(row['raw'])
            result=interpret_request(InterpretationInput(text=row['text']),provider)
            self.assertEqual(provider.interpret.call_count,1)
            if 'SUNY' in row['text']:
                self.assertTrue(result.context.departureNow)
                self.assertEqual(result.interpretation.journey.stops[0].kind,'named_place')
                self.assertEqual((result.interpretation.journey.order[0].before,result.interpretation.journey.order[0].after),(0,1))
            else:
                journey=result.interpretation.journey
                self.assertEqual([v.requirement for v in journey.stops],['required','required','optional'])
                self.assertEqual(journey.endpoint.kind,'origin');self.assertEqual(journey.total_duration.minutes,90)
                self.assertIsNone(journey.stops[2].duration)

    def optional(self):
        return self.session([{'source':'grocery shopping','duration':duration(20)},{'source':'pharmacy','duration':duration(20)},{'source':'coffee','requirement':'optional'}],endpoint={'kind':'origin','source':'return'},total_duration=duration(90,'maximum'))

    def test_optional_unknown_asks_even_when_no_coffee_is_selected(self):
        s=self.optional();r=self.run_session(s,startingLocation=start())
        self.assertTrue(any(q['field']=='dwell' and q.get('occurrence')==2 for q in r.questions))
        c=next(c for c in s.router.all_candidates if len(c.visits)==3)
        self.assertIsNone(c.visits[2].requested.duration)
        counts=len(self.searches),len(self.calls)
        r=self.run_session(s,startingLocation=start(),edits={'dwell':[{'occurrence':2,'minutes':10,'relation':'exact'}]})
        self.assertTrue(any(len(o.stops)==3 for o in r.options));self.assertTrue(any(len(o.stops)==2 for o in r.options))
        for o in r.options:self.assertEqual([v.occurrence for v in o.stops[:2]],[0,1]);self.assertEqual(o.ending,'origin')
        self.assertEqual(counts,(len(self.searches),len(self.calls)))
        print('Acceptance optional fixture:',s.selection_counts,'provider calls before/after',counts,(len(self.searches),len(self.calls)))
        r=self.run_session(s,startingLocation=start(),edits={'dwell':[{'occurrence':2,'minutes':80,'relation':'exact'}]})
        self.assertTrue(r.options);self.assertTrue(all(len(o.stops)==2 for o in r.options))
        self.assertTrue(all('original time budget' in o.omitted[0]['explanation'] for o in r.options))
        self.assertGreater(s.selection_counts['exclusions'].get('duration_lower_bound_exceeds_limit',0)+sum(s.selection_counts['exclusions'].values()),0)

    def test_optional_closed_cafes_are_not_overridden(self):
        from zoneinfo import ZoneInfo
        now=datetime.now(timezone.utc)-timedelta(seconds=2)
        clock=patch('backend.advanced_planning.datetime',wraps=datetime).start();self.addCleanup(patch.stopall)
        clock.now.side_effect=lambda tz=None:datetime.now(timezone.utc).astimezone(tz or timezone.utc)
        self.records=deepcopy(self.records)
        for p in self.records:p.update(fixture_hours(closed=p['id']=='Synthetic_coffee',now=now))
        s=self.optional();s.context.date=now.astimezone(ZoneInfo('America/New_York')).date()+timedelta(days=1)
        r=self.run_session(s,startingLocation=start())
        self.assertTrue(r.options);self.assertTrue(all(len(o.stops)==2 for o in r.options));self.assertFalse(r.closureOffers)
        self.assertTrue(all(o.omitted[0]['reason']=='known_closed' for o in r.options))

    def test_date_change_keeps_named_identity_and_reuses_routes(self):
        s=self.closed_session();r=self.run_session(s,startingLocation=start());r=self.run_session(s,startingLocation=start(),proceedClosed=r.closureOffers[0]['token'])
        counts=len(self.searches),len(self.calls)
        future=(s.context.date+timedelta(days=1)).isoformat()
        r=self.run_session(s,startingLocation=start(),date=future,edits={'departure':'14:00'})
        self.assertEqual(r.preferences['closedVisits'],[]);self.assertEqual(r.date,future)
        self.assertEqual(counts,(len(self.searches),len(self.calls)))
        self.assertTrue(r.closureOffers)

@unittest.skipUnless(os.environ.get('WHERETO_DB_SCHEMA_TESTS')=='1','Opt-in committed closure-intent PostgreSQL check')
class HostedClosedVisitTests(unittest.TestCase):
    def test_selected_override_committed_fresh_process_and_exact_cleanup(self):
        import json,subprocess,psycopg
        from backend.saved_plans import save,reopen,OpenRequest,digest
        from backend.database_check import connection_settings
        h=AcceptanceRepairTests('test_closed_named_offer_explicit_exact_identity_and_save');h.setUp()
        try:
            s=h.closed_session();r=h.run_session(s,startingLocation=start())
            r=h.run_session(s,startingLocation=start(),proceedClosed=r.closureOffers[0]['token'])
            req=SaveRequest(receipt=r.saveReceipt,accessToken=r.saveAccessToken,candidateIds=[p.id for p in r.options],selectedId=r.options[0].id)
            key=digest(req.accessToken)
            with psycopg.connect(**connection_settings(os.environ),autocommit=True) as admin:
                try:
                    self.assertEqual(save(req),{'saved':True})
                    script='import json,sys;from backend.saved_plans import reopen,OpenRequest;print(json.dumps(reopen(OpenRequest(accessToken=sys.stdin.read()))))'
                    out=subprocess.run(['backend/.venv/bin/python','-c',script],input=req.accessToken,text=True,capture_output=True,check=True)
                    value=json.loads(out.stdout);self.assertEqual(value,reopen(OpenRequest(accessToken=req.accessToken)))
                    self.assertEqual(value['version'],2);self.assertEqual(len(value['itineraries']),1);self.assertEqual(value['selectedId'],r.options[0].id)
                    self.assertEqual(value['itineraries'][0]['advanced']['closedVisitOccurrences'],[0])
                    for key_name in ('currentOpeningHours','observedAt','duration_seconds','latitude'):self.assertNotIn(key_name,out.stdout)
                finally:
                    admin.execute('DELETE FROM whereto.plans WHERE access_hash=%s',(key,))
            with psycopg.connect(**connection_settings(os.environ),autocommit=True) as verify:self.assertEqual(verify.execute('SELECT count(*) FROM whereto.plans WHERE access_hash=%s',(key,)).fetchone()[0],0)
        finally:h.doCleanups()
