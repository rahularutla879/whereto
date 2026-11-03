"""Consolidated 50E acceptance: fictional Google evidence, actual sends forbidden."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from backend.ai import Interpretation
from backend.interpretation import InterpretationInput, interpret_request
from backend.journey import validate_journey
from backend.routes import matrix_body, parse_matrix, current_evidence
from backend.routes_transport import _validate_basic_body
from backend.test_routes import point, element
from backend.test_advanced_planning import IntegrationTests
from backend.test_advanced_routing import start
from backend.test_advanced_timing import AdvancedTimingTests, activity, context, duration, NOW
from backend.advanced_timing import _bounds, _limit
from backend.development_cost import DevelopmentCost, dispatch

A='go to suny college of optometry first and then head out for coffee and be back within 3 hours'
B='go to suny college of optometry first and then head out for coffee now'

def extracted(text=A):
    journey={'stops':[{'source':'suny college of optometry','kind':'named_place'},{'source':'coffee'}],
        'ordering':'constrained','order':[{'before':0,'after':1,'source':'suny college of optometry first and then head out for coffee'}]}
    if text==A:journey.update(endpoint={'kind':'origin','source':'be back'},total_duration={'minutes':180,'relation':'maximum','source':'within 3 hours'})
    return Interpretation(activities=['suny college of optometry','coffee'],budget_per_person=None,date=None,location=None,preferences=[],journey=journey)

class ConsolidatedTests(unittest.TestCase):
    def setUp(self):
        self.h=IntegrationTests('test_named_roundtrip_dto_and_receipt');self.h.setUp();self.addCleanup(self.h.doCleanups)
    def test_model_invented_date_phrase_cannot_supply_missing_calendar(self):
        from backend.date_resolution import resolve_datetime
        calendar=resolve_datetime(A,['now'],[],None,now=NOW)
        self.assertIsNone(calendar.date);self.assertNotIn('now',calendar.date_expressions)
    def test_actual_baseline_failure_shape_retains_source_omission_guard(self):
        raw=extracted();raw.journey.endpoint=None;raw.journey.total_duration=None
        issue,ambiguous=validate_journey(A,raw)
        self.assertTrue(ambiguous);self.assertTrue(issue)
    def test_exact_three_hour_wording_asks_endpoint_then_keeps_every_constraint_without_model(self):
        provider=Mock();provider.interpret.return_value=extracted()
        r=interpret_request(InterpretationInput(text=A),provider,now=NOW)
        self.assertEqual(r.executionStatus,'clarification_required');self.assertTrue(any(q.field=='endpoint' for q in r.questions));self.assertEqual(provider.interpret.call_count,1)
        with patch('backend.interpretation.create_provider',side_effect=AssertionError('No model on answer')):
            r=interpret_request(InterpretationInput(text=A,pending=r.pending,answers={'endpoint':'return to my starting point'}),provider,now=NOW)
        self.assertEqual(provider.interpret.call_count,1);self.assertEqual(r.executionStatus,'advanced_unavailable')
        self.assertEqual(r.context.endpointStatus,'origin_confirmed');self.assertEqual(r.interpretation.journey.total_duration.minutes,180)
        self.assertEqual([s.source for s in r.interpretation.journey.stops],['suny college of optometry','coffee'])
    def test_missing_model_endpoint_prompts_without_inventing_a_return(self):
        raw=extracted();raw.journey.endpoint=None;raw.journey.total_duration=None
        provider=Mock();provider.interpret.return_value=raw
        r=interpret_request(InterpretationInput(text=A),provider,now=NOW)
        self.assertEqual([q.field for q in r.questions],['endpoint'])
        self.assertIsNone(r.interpretation.journey.endpoint);self.assertEqual(r.interpretation.journey.total_duration.minutes,180)
        r=interpret_request(InterpretationInput(text=A,pending=r.pending,answers={'endpoint':'return to my starting point'}),provider,now=NOW)
        self.assertEqual(provider.interpret.call_count,1);self.assertEqual(r.context.endpointStatus,'origin_confirmed')
        self.assertEqual(r.interpretation.journey.endpoint.kind,'origin')
    def test_now_retained_then_anchor_uses_verified_destination_and_refreshes(self):
        provider=Mock();provider.interpret.return_value=extracted(B)
        r=interpret_request(InterpretationInput(text=B),provider,now=NOW)
        self.assertTrue(r.context.departureNow)
        s=self.h.session();s.text=B;s.context.departureNow=True;s.context.date=None
        result=self.h.run_session(s,startingLocation=start())
        self.assertEqual(result.status,'results');self.assertEqual(result.date,'2026-11-02');self.assertTrue(result.preferences['departureNow'])
        self.assertEqual(s.context.departureInstant,NOW)
        snapshot=s.router.timing_snapshot();self.assertTrue(all(l.evidence.estimate_type=='traffic_aware' for c in snapshot.candidates for l in c.legs))
        searches,calls=len(self.h.searches),len(self.h.calls)
        with patch('backend.advanced_planning.datetime',wraps=datetime) as clock:
            clock.now.side_effect=lambda tz=None:(NOW+timedelta(seconds=10)).astimezone(tz or timezone.utc)
            fresh=self.h.run_session(s,startingLocation=start(),edits={'dwell':[dict(occurrence=0,minutes=10,relation='exact')]})
        self.assertEqual(s.context.departureInstant,NOW+timedelta(seconds=10))
        self.assertEqual(s.router.timing_snapshot().context.departureInstant,NOW+timedelta(seconds=10))
        self.assertEqual((len(self.h.searches),len(self.h.calls)),(searches,calls))
        result=self.h.run_session(s,startingLocation=start(),edits={'departure':'10:00'})
        self.assertFalse(result.preferences['departureNow']);self.assertEqual(result.preferences['departure'],'10:00')
    def test_policy_freshness_walk_and_provider_fallback(self):
        origins,dests=[point('a')],[point('b')]
        self.assertEqual(matrix_body(origins,dests,'drive')['routingPreference'],'TRAFFIC_AWARE')
        self.assertNotIn('routingPreference',matrix_body(origins,dests,'walk'))
        bad=matrix_body(origins,dests,'drive')|{'routingPreference':'TRAFFIC_AWARE_OPTIMAL'}
        with self.assertRaises(Exception):_validate_basic_body(bad)
        leg=parse_matrix([element(duration='1799.999999999s')],origins,dests,'drive')[0]
        self.assertEqual(leg.duration_nanoseconds,1799999999999);self.assertTrue(current_evidence(leg,'drive'))
        self.assertFalse(current_evidence(leg,'walk'));self.assertFalse(current_evidence(leg,'drive',now=leg.observed_at+timedelta(seconds=300)))
        self.assertFalse(current_evidence(leg.model_copy(update={'estimate_type':'traffic_unaware'}),'drive'))
        failed=parse_matrix([element(fallbackInfo={'routingMode':'FALLBACK_TRAFFIC_UNAWARE'})],origins,dests,'drive')[0]
        self.assertIsNone(failed.duration_seconds);self.assertEqual(failed.error_code,'traffic_policy_unavailable')
    def test_pro_ledger_keeps_legacy_essentials_and_shared_element_capacity(self):
        with TemporaryDirectory() as folder,patch.dict(os.environ,WHERETO_DEV_COST_LEDGER=folder+'/ledger.json'):
            cost=DevelopmentCost()
            for sku in ['matrix_element','matrix_pro_element']:
                with cost.reserve({sku:6}):dispatch('matrix',6)
            data=json.loads(Path(folder+'/ledger.json').read_text());row=data['days'][cost.day()]
            self.assertEqual(row['grossMicrousd'],90000);self.assertEqual(row['dispatched'],{'matrix_element':6,'matrix_pro_element':6})
            self.assertEqual(cost.minute_capacity(),138)
            from backend.provider_budget import ProviderLimitError
            with cost.reserve({'matrix_element':1}):
                with self.assertRaises(ProviderLimitError):dispatch('matrix',1,sku='matrix_pro_element')
    def test_shortest_first_then_unseen_alternatives_without_places_or_model(self):
        from backend.test_advanced_routing import COFFEE
        self.h.records=[v for v in self.h.records if v['id']!='Synthetic_coffee']
        for n in range(1,7):
            key=f'Synthetic_coffee{n}'
            self.h.records.append({**COFFEE,'id':key,'rating':4+n/10})
            self.h.values['DRIVE','Synthetic_college',key]=n*60
            self.h.values['DRIVE',key,'origin']=n*60
        s=self.h.session(endpoint={'kind':'origin','source':'return'},total_duration=duration(180,'maximum'))
        r=self.h.run_session(s,startingLocation=start(),edits={'dwell':[dict(occurrence=0,minutes=60,relation='exact'),dict(occurrence=1,minutes=30,relation='exact')]})
        first=[p.knownTravelSeconds for p in r.options]
        self.assertEqual(first,sorted(first));self.assertEqual(first[0],240)
        self.assertTrue(all(p.durationState=='feasible' for p in r.options));shown={p.id for p in r.options}
        searches=len(self.h.searches)
        with patch('backend.places_transport.text_search',side_effect=AssertionError('No Places for different')),patch('backend.interpretation.create_provider',side_effect=AssertionError('No model')):
            next_page=self.h.run_session(s,startingLocation=start(),action='different')
        self.assertFalse(shown & {p.id for p in next_page.options});self.assertTrue(all(p.knownTravelSeconds>=first[-1] for p in next_page.options));self.assertEqual(len(self.h.searches),searches)
        self.assertTrue(all([v.placeId for v in p.stops][0]=='Synthetic_college' and p.ending=='origin' for p in next_page.options))
    def test_three_hour_return_limit_exact_boundary_and_flexible_do_not_waive_it(self):
        for policy,value in [('strict',30),('flexible',20)]:
            for extra,expected in [('0','results'),('0.000000001','no_results')]:
                with self.subTest(policy=policy,extra=extra):
                    self.h.values.update({('DRIVE','origin','Synthetic_college'):1800,('DRIVE','Synthetic_college','Synthetic_coffee'):1800,('DRIVE','Synthetic_coffee','origin'):Decimal(1800)+Decimal(extra)})
                    s=self.h.session([{'source':'SUNY College of Optometry','kind':'named_place','duration':duration(60)},{'source':'coffee','duration':duration(30)}],endpoint={'kind':'origin','source':'return'},total_duration=duration(180,'maximum'))
                    r=self.h.run_session(s,startingLocation=start(),firstTravel={'value':value,'unit':'minutes','mode':policy})
                    self.assertEqual(r.status,expected)
                    if r.options:self.assertEqual(r.options[0].elapsedUpperSeconds,10800)

    def test_relation_bounds_survive_exploration_and_flexible_never_waives_whole_cap(self):
        for relation in ['exact','maximum','minimum','under','approximate']:
            for policy in ['strict','flexible']:
                with self.subTest(relation=relation,policy=policy):
                    s=self.h.session([{'source':'grocery shopping'},{'source':'ATM','duration':duration(5)}],endpoint={'kind':'origin','source':'return'},total_duration=duration(45,'maximum'))
                    args={'startingLocation':start(),'firstTravel':{'value':10,'unit':'minutes','mode':policy}}
                    r=self.h.run_session(s,**args,edits={'dwell':[dict(occurrence=0,minutes=34,relation=relation)]})
                    self.assertEqual(r.options[0].durationState,'unverified' if relation in ('minimum','approximate') else 'feasible')
                    for action in ['different','discover']:
                        r=self.h.run_session(s,**args,action=action)
                        self.assertTrue(all(p.durationState!='infeasible' and p.totalConstraint.minutes==45 for p in r.options))
                    r=self.h.run_session(s,**args,edits={'dwell':[dict(occurrence=0,minutes=60,relation='exact')]})
                    self.assertEqual(r.options,[])
    def test_expired_routes_require_explicit_regeneration_and_reuse_places(self):
        s=self.h.session(endpoint={'kind':'origin','source':'return'})
        self.h.run_session(s,startingLocation=start());searches=len(self.h.searches);calls=len(self.h.calls)
        for c in s.candidates.values():
            for l in c.legs:
                object.__setattr__(l.evidence,'observed_at',datetime.now(timezone.utc)-timedelta(seconds=301))
        r=self.h.run_session(s,startingLocation=start(),action='different')
        self.assertEqual(r.options,[]);self.assertEqual(len(self.h.calls),calls)
        # A deliberate edit refreshes current routing using the retained venue pool.
        from time import time
        with patch('backend.routes.time',return_value=time()+301):
            r=self.h.run_session(s,startingLocation=start(),edits={'dwell':[dict(occurrence=0,minutes=10,relation='exact')]})
        self.assertEqual(len(self.h.searches),searches);self.assertTrue(r.options)
    def test_duration_ranges_and_nanosecond_boundary(self):
        for relation,lo,hi,exclusive in [('exact',1800,1800,False),('maximum',0,1800,False),('minimum',1800,None,False),('under',0,1800,True),('approximate',0,None,False)]:
            with self.subTest(relation=relation):
                from backend.journey import Duration
                bound=_bounds(Duration.model_validate(duration(30,relation)))
                self.assertEqual((bound.lower,bound.upper,bound.upper_exclusive),(lo,hi,exclusive))
        from backend.advanced_timing import DurationRange
        from backend.journey import Duration
        strict=Duration.model_validate(duration(30,'under'))
        self.assertEqual(_limit(DurationRange(lower=Decimal('1799.999999999'),upper=Decimal('1799.999999999')),strict)[0],'feasible')
        self.assertEqual(_limit(DurationRange(lower=1800,upper=1800),strict)[0],'infeasible')

class NowHoursTests(unittest.TestCase):
    setUp=AdvancedTimingTests.setUp
    matrix=AdvancedTimingTests.matrix
    resolve=AdvancedTimingTests.resolve
    timed=AdvancedTimingTests.timed
    candidate=AdvancedTimingTests.candidate
    hours_record=AdvancedTimingTests.hours_record
    def test_closed_at_exact_arrival_unknown_dwell_is_excluded(self):
        c=self.candidate([activity('coffee')],records=[self.hours_record(opened=15)])
        self.assertEqual(c.hours_state,'infeasible')
    def test_opens_before_arrival_unknown_dwell_remains_qualified(self):
        c=self.candidate([activity('coffee')],records=[self.hours_record(opened=14)])
        self.assertNotEqual(c.hours_state,'infeasible');self.assertEqual(c.hours_state,'unverified')


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(loader.loadTestsFromTestCase(c) for c in (ConsolidatedTests,NowHoursTests))
