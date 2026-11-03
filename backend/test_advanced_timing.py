"""Invented provider-shaped evidence; no real HTTP, model or database access."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import os
from statistics import median
from time import perf_counter
import unittest
from unittest.mock import patch, Mock

from pydantic import ValidationError

from backend.advanced_routing import AdvancedRouter, AdvancedRouteCandidate
from backend.advanced_timing import (evaluate_advanced_timing, explicit_departure,
    DurationRange, TimedCandidate, _limit)
from backend.interpretation import InterpretationContext, InterpretationInput, interpret_request
from backend import test_advanced_routing as routing_fixtures
from backend.test_advanced_routing import activity, start, COFFEE, BANK, GROCERY, STATION, PHARMACY
from backend.hours_fixtures49 import fixture_hours

NOW = datetime(2026, 11, 2, 13, tzinfo=timezone.utc)


def duration(minutes, relation='exact'):
    return {'minutes':minutes, 'relation':relation, 'source':f'{relation} {minutes} minutes'}


def context(minute=14*60, day='2026-11-02', zone='America/New_York'):
    hour, m = divmod(minute, 60)
    source = f'Start at {hour%12 or 12}:{m:02d} '+('PM' if hour >= 12 else 'AM')
    return InterpretationContext(date=day, timezone=zone, timezoneBasis='destination_calendar', departureMinute=minute, departureSource=source)


class AdvancedTimingTests(unittest.TestCase):
    setUp = routing_fixtures.AdvancedRoutingTests.setUp
    matrix = routing_fixtures.AdvancedRoutingTests.matrix
    resolve = routing_fixtures.AdvancedRoutingTests.resolve

    def timed(self, stops=None, *, ctx=None, records=None, origin=True, now=NOW, **kwargs):
        stops = stops if stops is not None else [activity('coffee', duration=duration(15))]
        records = records if records is not None else [COFFEE, BANK, GROCERY, STATION]
        resolver = self.resolve(stops, context=ctx if ctx is not None else context(), records=records, **kwargs)
        for group in resolver._result.stops + ([resolver._result.endpoint] if resolver._result.endpoint else []):
            for candidate in group.candidates:
                candidate.facts.observedAt = {k:now for k in candidate.facts.observedAt}
        router = AdvancedRouter(resolver)
        with patch('backend.planning_hours.datetime') as clock:
            clock.now.return_value = now
            router.plan(origin=start() if origin else None)
        count = len(self.calls)
        with patch('backend.places_transport.text_search', side_effect=AssertionError('No resolution')),\
             patch('backend.routes_transport.compute_matrix', side_effect=AssertionError('No routing')):
            result = evaluate_advanced_timing(router, evaluated_at=now)
        self.assertEqual(len(self.calls), count)
        self.assertEqual(result.incremental_provider_requests, 0)
        return router, result

    def candidate(self, *args, **kwargs):
        return self.timed(*args, **kwargs)[1].candidates[0]

    def test_total_45_minute_numeric_boundaries(self):
        # Two-minute first leg plus dwell, exactly 2700 seconds at 43 minutes.
        for dwell, relation, state in [(42,'maximum','feasible'), (44,'maximum','infeasible'),
                                       (43,'maximum','feasible'), (43,'under','infeasible')]:
            with self.subTest(dwell=dwell, relation=relation):
                c = self.candidate([activity('coffee', duration=duration(dwell))],total_duration=duration(45,relation))
                self.assertEqual(c.elapsed.lower, Decimal(120+dwell*60))
                self.assertEqual(c.duration_state,state)

    def test_travel_only_lower_bound_can_fail_with_unknown_dwell(self):
        self.values['DRIVE','origin','Synthetic_coffee'] = 2701
        c=self.candidate([activity('coffee')],total_duration=duration(45,'maximum'))
        self.assertEqual(c.duration_state,'infeasible')
        self.assertEqual(c.state,'infeasible')
        self.assertIsNone(c.elapsed.upper)

    def test_unknown_grocery_and_exact_atm(self):
        c=self.candidate([activity('grocery shopping'),activity('ATM',duration=duration(5))],
            endpoint={'kind':'origin','source':'return'},total_duration=duration(45,'maximum'))
        self.assertEqual(c.known_travel_seconds,360)
        self.assertEqual(c.elapsed.lower,660)
        self.assertIsNone(c.elapsed.upper)
        self.assertEqual(c.duration_state,'unverified')
        self.assertIsNone(c.visits[1].arrival.latest)
        self.assertIsNone(c.finish.latest)
        self.assertEqual(c.visits[0].dwell.lower,0)  # lower bound, never an exact dwell
        self.assertIsNone(c.visits[0].dwell.upper)

    def test_32_travel_five_atm_unknown_grocery_leaves_eight_not_feasible(self):
        self.values = {('DRIVE','origin','Synthetic_grocery'):600,
                       ('DRIVE','Synthetic_grocery','Synthetic_bank'):600,
                       ('DRIVE','Synthetic_bank','origin'):720}
        c=self.candidate([activity('grocery shopping'),activity('ATM',duration=duration(5))],
            endpoint={'kind':'origin','source':'return'},total_duration=duration(45,'maximum'))
        self.assertEqual(c.travel.upper,1920)
        self.assertEqual(c.elapsed.lower,2220)
        self.assertEqual(2700-c.elapsed.lower,480)
        self.assertEqual(c.duration_state,'unverified')

    def test_dwell_relations_and_no_invented_defaults(self):
        for relation,lo,hi,exclusive,state in [('exact',900,900,False,'feasible'),
            ('minimum',900,None,False,'unverified'),('maximum',0,900,False,'feasible'),
            ('under',0,900,True,'feasible'),('approximate',0,None,False,'unverified')]:
            with self.subTest(relation=relation):
                c=self.candidate([activity('coffee',duration=duration(15,relation))],total_duration=duration(45,'maximum'))
                self.assertEqual((c.dwell.lower,c.dwell.upper,c.dwell.upper_exclusive),(lo,hi,exclusive))
                self.assertEqual(c.duration_state,state)
        c=self.candidate([activity('coffee',evidence='quick coffee')],records=[COFFEE])
        self.assertIsNone(c.visits[0].dwell_constraint)
        self.assertIsNone(c.dwell.upper)

    def test_minimum_dwell_proves_failure(self):
        c=self.candidate([activity('coffee',duration=duration(45,'minimum'))],total_duration=duration(45,'maximum'))
        self.assertEqual(c.elapsed.lower,2820)
        self.assertEqual(c.duration_state,'infeasible')

    def test_exclusive_upper_dwell_can_fit_exclusive_budget(self):
        c=self.candidate([activity('coffee',duration=duration(43,'under'))],total_duration=duration(45,'under'))
        self.assertEqual(c.elapsed.upper,2700)
        self.assertTrue(c.elapsed.upper_exclusive)
        self.assertEqual(c.duration_state,'feasible')

    def test_upper_bound_exceeding_budget_is_unknown_not_failure(self):
        c=self.candidate([activity('coffee',duration=duration(50,'maximum'))],total_duration=duration(45,'maximum'))
        self.assertEqual(c.duration_state,'unverified')

    def test_soft_total_preference_is_not_hard_violation(self):
        c=self.candidate([activity('coffee',duration=duration(50))],total_duration=duration(1,'approximate'))
        self.assertEqual(c.duration_state,'feasible')
        self.assertIn('soft_duration_preference',[r.code for r in c.reasons])

    def test_exact_minimum_and_maximum_whole_trip_relations(self):
        from backend.journey import Duration
        bounds=DurationRange(lower=120,upper=120)
        for relation,minutes,state in [('exact',2,'feasible'),('exact',1,'infeasible'),
            ('exact',3,'infeasible'),('minimum',1,'feasible'),('minimum',3,'infeasible')]:
            self.assertEqual(_limit(bounds,Duration(**duration(minutes,relation)))[0],state)
        self.assertEqual(_limit(DurationRange(lower=0,upper=180),Duration(**duration(2)))[0],'unverified')

    def test_single_round_trip_asymmetric_return(self):
        self.values['DRIVE','Synthetic_coffee','origin']=333
        c=self.candidate(endpoint={'kind':'origin','source':'return'})
        self.assertEqual(c.travel.upper,453)
        self.assertEqual(c.elapsed.upper,1353)
        self.assertEqual(c.finish.latest.minute,22)
        self.assertEqual([l.role for l in c.route.legs],['origin_to_first','return_to_origin'])

    def test_multi_round_trip_includes_all_legs_once(self):
        c=self.candidate([activity('bank',duration=duration(5)),activity('coffee',duration=duration(15))],
            endpoint={'kind':'origin','source':'return'})
        self.assertEqual(c.travel.upper,360)
        self.assertEqual(c.elapsed.upper,1560)
        self.assertEqual(c.visits[1].arrival.earliest.minute,9)
        self.assertEqual(c.finish.latest.minute,26)

    def test_separate_endpoint_arrival(self):
        c=self.candidate(endpoint={'kind':'named_place','source':'Penn Station'})
        self.assertEqual(c.route.endpoint.place_id,'Synthetic_station')
        self.assertEqual(c.travel.upper,240)
        self.assertEqual(c.finish.latest.minute,19)
        self.assertEqual(c.route.ending,'named_destination')

    def test_missing_required_route_evidence_per_role(self):
        for a,b,index in [('origin','Synthetic_bank',0),('Synthetic_bank','Synthetic_coffee',1),('Synthetic_coffee','origin',2)]:
            with self.subTest(role=index):
                self.values={('DRIVE',a,b):None}
                c=self.candidate([activity('bank',duration=duration(5)),activity('coffee',duration=duration(15))],
                    endpoint={'kind':'origin','source':'return'},total_duration=duration(45,'maximum'))
                self.assertEqual(c.route.missing_leg_indexes,[index])
                self.assertEqual(c.travel.lower,240)
                self.assertIsNone(c.travel.upper)
                self.assertEqual(c.duration_state,'unverified')
                self.assertEqual(c.state,'unverified')

    def test_missing_topology_rejected_including_first_return_interstop(self):
        c=self.candidate([activity('bank'),activity('coffee')],endpoint={'kind':'origin','source':'return'})
        for i in range(3):
            data=c.route.model_dump();data['legs'].pop(i)
            with self.assertRaises(ValidationError):AdvancedRouteCandidate.model_validate(data)

    def test_mode_specific_seconds(self):
        for mode,seconds in [('driving',120),('walking',600)]:
            ctx=InterpretationContext(**{**context().model_dump(),'transport':mode})
            c=self.candidate(ctx=ctx)
            self.assertEqual(c.travel.upper,seconds)
            self.assertEqual(c.elapsed.upper,seconds+900)

    def test_order_is_preserved_fixed_partial_flexible(self):
        stops=[activity('bank',duration=duration(3)),activity('grocery shopping',duration=duration(6)),activity('coffee',duration=duration(9))]
        for kwargs in ({},{'order':[{'before':0,'after':1,'source':'bank before grocery'}]}, {'ordering':'flexible'}):
            router,result=self.timed(stops,**kwargs)
            before=router.timing_snapshot()
            self.assertEqual([c.route for c in result.candidates],before.candidates)
            for c in result.candidates:
                self.assertEqual(c.dwell.upper,1080)
                self.assertEqual([v.occurrence for v in c.visits],[v.occurrence for v in c.route.visits])
                self.assertEqual(c.elapsed.upper,1440)

    def test_optional_included_omitted_and_time_failure(self):
        _,result=self.timed([activity('grocery shopping',duration=duration(10)),activity('coffee',True,duration=duration(60))],
            total_duration=duration(45,'maximum'))
        self.assertEqual({len(c.visits) for c in result.candidates},{1,2})
        for c in result.candidates:
            self.assertIn(0,[v.occurrence for v in c.visits])
            self.assertEqual(c.duration_state,'infeasible' if len(c.visits)==2 else 'feasible')
            if c.route.omitted:self.assertEqual(c.route.omitted[0].reason,'routing_cost_or_applicability')

    def test_optional_unknown_never_claimed_to_fit(self):
        _,result=self.timed([activity('grocery shopping',duration=duration(10)),activity('coffee',True)],total_duration=duration(45,'maximum'))
        included=next(c for c in result.candidates if len(c.visits)==2)
        self.assertEqual(included.duration_state,'unverified')

    def test_deadline_exact_departure_and_equality(self):
        for relation,minute,state in [('by',14*60+17,'feasible'),('before',14*60+17,'infeasible'),
                                      ('by',14*60+16,'infeasible'),('by',14*60+18,'feasible')]:
            c=self.candidate(deadline={'minute':minute,'relation':relation,'source':'by clock'})
            self.assertEqual(c.deadline_state,state)
            self.assertEqual(c.start.hour,14)
            self.assertEqual(c.finish.latest.minute,17)

    def test_deadline_no_explicit_departure_does_not_use_default_10am(self):
        ctx=InterpretationContext(date='2026-11-02',timezone='America/New_York')
        c=self.candidate(ctx=ctx,deadline={'minute':1080,'source':'by 6 PM'})
        self.assertIsNone(c.start)
        self.assertIsNone(c.visits[0].arrival.earliest)
        self.assertIsNone(c.finish.latest)
        self.assertEqual(c.deadline_state,'unverified')

    def test_earlier_deadline_clarifies_overnight(self):
        c=self.candidate(deadline={'minute':13*60,'source':'by 1 PM'})
        self.assertEqual(c.deadline_state,'unverified')
        self.assertIn('clarify_overnight_deadline',[r.code for r in c.reasons])

    def test_explicit_earlier_deadline_date_is_impossible(self):
        c=self.candidate(deadline={'minute':13*60,'source':'by 1 PM on 2026-11-02'})
        self.assertEqual(c.deadline_state,'infeasible')

    def test_overnight_projection_and_explicit_next_day_deadline(self):
        c=self.candidate(ctx=context(23*60+50),deadline={'minute':10,'source':'by 12:10 AM the following day'})
        self.assertEqual(c.finish.latest.isoformat(),'2026-11-03T00:07:00-05:00')
        self.assertEqual(c.deadline_state,'feasible')

    def test_unknown_dwell_deadline_and_projection_ranges(self):
        c=self.candidate([activity('coffee',duration=duration(15,'minimum'))],deadline={'minute':1080,'source':'by 6 PM'})
        self.assertEqual(c.deadline_state,'unverified')
        self.assertIsNone(c.finish.latest)
        self.assertEqual(c.finish.earliest.minute,17)
        c=self.candidate([activity('coffee',duration=duration(15,'maximum'))])
        self.assertEqual(c.visits[0].departure.earliest.minute,2)
        self.assertEqual(c.visits[0].departure.latest.minute,17)

    def test_destination_timezone_independent_of_host_browser(self):
        c=self.candidate(ctx=context(zone='Asia/Kolkata'))
        self.assertEqual(c.start.utcoffset(),timedelta(hours=5,minutes=30))
        self.assertEqual(c.finish.latest.hour,14)

    def test_browser_or_fallback_timezone_does_not_anchor_destination_clocks(self):
        for basis in ('browser_reported','unknown'):
            ctx=context();ctx.timezoneBasis=basis
            c=self.candidate(ctx=ctx,deadline={'minute':1080,'source':'by 6 PM'})
            self.assertIsNone(c.start)
            self.assertEqual(c.deadline_state,'unverified')

    def test_dst_elapsed_arithmetic_crosses_fold_and_gap(self):
        for day,minute,now,expected in [('2026-11-01',30,datetime(2026,11,1,tzinfo=timezone.utc),'2026-11-01T01:32:00-05:00'),
            ('2026-03-08',90,datetime(2026,3,8,tzinfo=timezone.utc),'2026-03-08T04:32:00-04:00')]:
            c=self.candidate([activity('coffee',duration=duration(120))],ctx=context(minute,day),now=now)
            self.assertEqual(c.finish.latest.isoformat(),expected)
            self.assertEqual(c.elapsed.upper,7320)

    def test_dst_ambiguous_nonexistent_anchors_unverified(self):
        for day,minute in [('2026-11-01',90),('2026-03-08',150)]:
            c=self.candidate(ctx=context(minute,day))
            self.assertIsNone(c.start)
            self.assertIsNone(c.finish.latest)

    def hours_record(self, *, opened=9, closed=22, zone='America/New_York', **kwargs):
        record={**COFFEE,**fixture_hours(now=NOW,zone=zone,closed=closed is True,**kwargs)}
        for p in record['currentOpeningHours']['periods']:
            p['open']['hour']=opened;p['close']['hour']=closed
        return record

    def test_date_specific_hours_full_visit(self):
        c=self.candidate(records=[self.hours_record()])
        self.assertEqual(c.hours_state,'feasible')
        self.assertEqual(c.state,'feasible')
        self.assertTrue(c.visits[0].special_day)
        self.assertIsNotNone(c.visits[0].hours_observed_at)

    def test_closing_before_visit_completes(self):
        c=self.candidate(records=[self.hours_record(closed=14)])
        self.assertEqual(c.hours_state,'infeasible')
        self.assertEqual(c.state,'infeasible')

    def test_opens_after_arrival(self):
        c=self.candidate(records=[self.hours_record(opened=15)])
        self.assertEqual(c.hours_state,'infeasible')

    def test_date_closed_and_holiday_current_overrides_regular(self):
        router,result=self.timed(records=[self.hours_record(closed=True)])
        self.assertEqual(result.routing_status,'no_candidates')
        self.assertEqual(result.candidates,[])
        self.assertEqual(router.timing_snapshot().hours_exclusions[0].status,'closed')
        record=self.hours_record(opened=15)
        c=self.candidate(records=[record])
        self.assertEqual(c.hours_state,'infeasible')
        self.assertTrue(c.visits[0].special_day)

    def test_24_hour_and_overnight_hours(self):
        record=self.hours_record()
        record['currentOpeningHours']['periods']=[{'open':{'day':0,'hour':0,'minute':0}}]
        c=self.candidate(records=[record])
        self.assertEqual(c.hours_state,'feasible')
        record=self.hours_record()
        p=record['currentOpeningHours']['periods'][0]
        p['open']['hour']=22
        p['close']={**p['close'],'hour':2,'day':2,'date':{'year':2026,'month':11,'day':3}}
        record['currentOpeningHours']['periods']=[p]
        c=self.candidate(records=[record],ctx=context(23*60+50))
        self.assertEqual(c.hours_state,'feasible')

    def test_missing_regular_truncated_stale_outside_coverage(self):
        c=self.candidate()
        self.assertEqual(c.hours_state,'unverified')
        record=self.hours_record();record.pop('currentOpeningHours')
        self.assertEqual(self.candidate(records=[record]).hours_state,'unverified')
        record=self.hours_record();record['currentOpeningHours']['periods'][0]['open']['truncated']=True
        self.assertEqual(self.candidate(records=[record]).hours_state,'unverified')
        router,_=self.timed(records=[self.hours_record()])
        self.assertEqual(evaluate_advanced_timing(router,evaluated_at=NOW+timedelta(days=1)).candidates[0].hours_state,'unverified')
        self.assertEqual(self.candidate(records=[self.hours_record()],ctx=context(day='2026-11-09')).hours_state,'unverified')

    def test_hours_use_venue_timezone_when_different(self):
        # 14:02 New York = 19:02 London, closed there at 18:00.
        c=self.candidate(records=[self.hours_record(zone='Europe/London',closed=18)])
        self.assertEqual(c.hours_state,'infeasible')
        self.assertEqual(c.visits[0].hours_timezone,'Europe/London')

    def test_bounded_hours_envelope_success_failure_is_conservative(self):
        c=self.candidate([activity('coffee',duration=duration(15,'maximum'))],records=[self.hours_record()])
        self.assertEqual(c.hours_state,'feasible')
        c=self.candidate([activity('coffee',duration=duration(15,'maximum'))],records=[self.hours_record(closed=14)])
        self.assertEqual(c.hours_state,'unverified')
        c=self.candidate([activity('coffee',duration=duration(15,'minimum'))],records=[self.hours_record(closed=14)])
        self.assertIsNone(c.elapsed.upper)
        self.assertEqual(c.hours_state,'infeasible')
        self.assertEqual(c.visits[0].hours_code,'closed_during_mandatory_visit_core')
        bank={**BANK,**fixture_hours(now=NOW)}
        for p in bank['currentOpeningHours']['periods']:
            p['close']['hour']=14
        c=self.candidate([activity('coffee',duration=duration(5,'maximum')),activity('bank',duration=duration(30))],
            records=[self.hours_record(),bank])
        self.assertEqual(c.visits[1].hours_code,'closed_during_mandatory_visit_core')
        self.assertEqual(c.hours_state,'infeasible')

    def test_unknown_dwell_missing_hours_and_hard_violation_precedence(self):
        c=self.candidate([activity('coffee')],total_duration=duration(1,'maximum'))
        self.assertEqual(c.duration_state,'infeasible')
        self.assertEqual(c.hours_state,'unverified')
        self.assertEqual(c.state,'infeasible')

    def test_deadline_includes_return_and_named_destination(self):
        for endpoint in ({'kind':'origin','source':'return'}, {'kind':'named_place','source':'Penn Station'}):
            c=self.candidate(endpoint=endpoint,deadline={'minute':14*60+18,'source':'by 2:18 PM'})
            self.assertEqual(c.deadline_state,'infeasible')
            self.assertEqual(c.elapsed.upper,1140)

    def test_no_origin_first_activity_anchor_and_no_invented_leg(self):
        c=self.candidate(origin=False)
        self.assertEqual(c.travel.upper,0)
        self.assertEqual(c.visits[0].arrival.earliest.hour,14)
        self.assertEqual(c.elapsed.upper,900)

    def test_nanosecond_strict_comparison_and_outward_clock_rounding(self):
        self.values['DRIVE','origin','Synthetic_coffee']=Decimal('120.000000001')
        c=self.candidate([activity('coffee',duration=duration(43))],total_duration=duration(45,'maximum'),
            deadline={'minute':14*60+45,'source':'by 2:45 PM'})
        self.assertEqual(c.elapsed.upper,Decimal('2700.000000001'))
        self.assertEqual(c.duration_state,'infeasible')
        self.assertEqual(c.deadline_state,'infeasible')
        self.assertEqual(c.finish.latest.microsecond,1)
        self.assertEqual(c.finish.earliest.microsecond,0)

    def test_no_model_network_or_storage_during_evaluation_and_no_mutation(self):
        router,result=self.timed()
        before=router.timing_snapshot().model_dump_json()
        with patch('requests.sessions.Session.send',side_effect=AssertionError('No HTTP')),\
             patch('backend.advanced_routing.GoogleRouteCalculator',side_effect=AssertionError('No routes')),\
             patch('builtins.open',side_effect=AssertionError('No storage')):
            again=evaluate_advanced_timing(router,evaluated_at=NOW)
        self.assertEqual(result,again)
        self.assertEqual(before,router.timing_snapshot().model_dump_json())
        output=result.model_dump_json()
        self.assertNotIn('coordinates',str(result.candidates[0].route.origin.model_dump()))
        self.assertNotIn('private_start',output)
        result.candidates.clear()
        self.assertTrue(evaluate_advanced_timing(router,evaluated_at=NOW).candidates)

    def test_source_constraints_preferences_and_omissions_unchanged(self):
        ctx=InterpretationContext(**{**context().model_dump(),'firstTravel':{'value':1.0,'mode':'flexible'}})
        # Validate manually assigned fields before resolution, matching backend boundary.
        ctx=InterpretationContext.model_validate(ctx.model_dump())
        router,result=self.timed([activity('coffee',duration=duration(5))],ctx=ctx,
            total_duration=duration(45,'under'),deadline={'minute':1080,'relation':'before','source':'before 6 PM'})
        c=result.candidates[0]
        self.assertEqual(c.route,router.timing_snapshot().candidates[0])
        self.assertEqual(c.route.checks[0].preference.mode,'flexible')
        self.assertEqual(c.travel_preference_state,'feasible')
        self.assertEqual(c.route.journey.deadline.relation,'before')

    def test_gate_expiry_wrong_input_and_unplanned(self):
        router,result=self.timed()
        with self.assertRaises(TypeError):evaluate_advanced_timing(result,evaluated_at=NOW)
        with self.assertRaises(ValueError):evaluate_advanced_timing(router,evaluated_at=NOW.replace(tzinfo=None))
        with patch.dict(os.environ,{'WHERETO_STOP_RESOLUTION_DEV':'0'}):
            with self.assertRaises(Exception):evaluate_advanced_timing(router,evaluated_at=NOW)
        router.resolver._expires=0
        with self.assertRaises(ValueError):evaluate_advanced_timing(router,evaluated_at=NOW)
        new=AdvancedRouter(self.resolve([activity('coffee')]))
        with self.assertRaises(ValueError):evaluate_advanced_timing(new,evaluated_at=NOW)

    def test_unreachable_route_is_proven_failure_and_preferences_stay_separate(self):
        self.values['DRIVE','origin','Synthetic_coffee']='unreachable'
        c=self.candidate()
        self.assertEqual(c.routing_state,'infeasible')
        self.assertEqual(c.state,'infeasible')
        resolver=self.resolve([activity('coffee',duration=duration(5))],
            context=InterpretationContext(firstTravel={'value':1.0,'mode':'strict'}))
        self.values.clear()
        router=AdvancedRouter(resolver);router.plan(origin=start(),allow_beyond_limit=True)
        c=evaluate_advanced_timing(router,evaluated_at=NOW).candidates[0]
        self.assertEqual(c.routing_state,'feasible')
        self.assertEqual(c.travel_preference_state,'infeasible')
        self.assertEqual(c.state,'infeasible')

    def test_changed_resolution_invalidates_timing(self):
        router,_=self.timed()
        router.resolver._result.context.departureMinute=100
        with self.assertRaises(ValueError):evaluate_advanced_timing(router,evaluated_at=NOW)

    def test_malformed_bounds_and_contradictory_output(self):
        for fields in ({'lower':5,'upper':4},{'lower':0,'upper':0,'upper_exclusive':True},
                       {'lower':0,'upper_exclusive':True},{'lower':'NaN'}):
            with self.assertRaises(ValidationError):DurationRange(**fields)
        c=self.candidate()
        for mutate in (lambda d:d.update(state='feasible'),lambda d:d['elapsed'].update(lower=0),
                       lambda d:d['visits'][0].update(occurrence=1),
                       lambda d:d['visits'][0]['dwell'].update(upper=1000),
                       lambda d:d['visits'][0]['arrival'].update(latest='2026-11-02T18:00:00Z')):
            data=c.model_dump();mutate(data)
            with self.assertRaises(ValidationError):TimedCandidate.model_validate(data)
        with self.assertRaises(ValidationError):self.candidate([activity('coffee',duration=duration(0,'under'))])

    def test_explicit_departure_parser_rejects_defaults_after_and_conflicts(self):
        for raw in ('after 2 PM','from 2 PM to 4 PM','10 AM default','visit museum at 2 PM','start at 2 PM and depart at 3 PM'):
            self.assertEqual(explicit_departure(raw),(None,None))
        self.assertEqual(explicit_departure('start at 2 PM')[0],840)
        self.assertEqual(explicit_departure('Leave at 11:50 PM')[0],1430)

    def test_actual_interpretation_handoff_anchor_source_and_masked_deadline(self):
        from backend.journey_fixtures import reply
        from backend.ai import Interpretation
        provider=Mock()
        provider.interpret.return_value=Interpretation.model_validate(reply(['coffee'],location='New York',
            dates=['2026-11-07'],durations={0:{'minutes':15,'source':'coffee for 15 minutes'}},
            deadline={'source':'by 3 PM'}))
        result=interpret_request(InterpretationInput(text='Start at 2 PM, coffee for 15 minutes in New York on 2026-11-07, finish by 3 PM.'),provider,now=NOW)
        self.assertEqual(result.context.departureMinute,840)
        self.assertEqual(result.context.departureSource,'Start at 2 PM')
        self.assertEqual(result.interpretation.journey.deadline.minute,900)
        self.assertIsNone(result.request)
        self.assertEqual(provider.interpret.call_count,1)

    def test_timing_has_no_standalone_public_evidence_endpoint(self):
        from backend.main import app
        self.assertFalse(any('timing' in r.path for r in app.routes))
        from backend.models import OutingRequest
        with self.assertRaises(ValidationError):OutingRequest(activities=['coffee'],journey={'stops':[]})

    def test_pure_evaluation_benchmark(self):
        router,_=self.timed([activity('bank',duration=duration(5)),activity('coffee',duration=duration(15))],
            endpoint={'kind':'origin','source':'return'},total_duration=duration(45,'maximum'))
        samples=[]
        for _ in range(100):
            begin=perf_counter();evaluate_advanced_timing(router,evaluated_at=NOW);samples.append((perf_counter()-begin)*1000)
        print(f'50D local evaluation incl. trusted snapshot: median={median(samples):.3f}ms max={max(samples):.3f}ms; incremental Google=0 requests/$0')
        router,result=self.timed([activity('bank',duration=duration(5)),activity('coffee',duration=duration(10)),
            activity('grocery shopping',duration=duration(15)),activity('pharmacy',duration=duration(5))],
            records=[BANK,COFFEE,GROCERY,PHARMACY],ordering='flexible',endpoint={'kind':'origin','source':'return'})
        self.assertEqual(len(result.candidates),3)
        for c in result.candidates:
            self.assertEqual(c.elapsed.upper,2700)
        samples=[]
        for _ in range(100):
            begin=perf_counter();evaluate_advanced_timing(router,evaluated_at=NOW);samples.append((perf_counter()-begin)*1000)
        print(f'50D four-stop/three-candidate evaluation: median={median(samples):.3f}ms max={max(samples):.3f}ms; incremental Google=0 requests/$0')


if __name__ == '__main__': unittest.main()
