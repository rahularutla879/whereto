"""Task 50C invented Places/Matrix fixtures; all actual network sends forbidden."""
import os
import unittest
from statistics import median
from time import perf_counter
from unittest.mock import patch

from pydantic import ValidationError

from backend.advanced_routing import AdvancedRouter, AdvancedRouteCandidate
from backend.interpretation import InterpretationContext
from backend.journey import Journey, RequestedStop
from backend.places import SearchArea
from backend.provider_budget import ProviderBudget, ProviderSettings
from backend.routes import AuthorizedStart, RouteError, RoutePoint
from backend.stop_resolution import StopResolver
from backend.test_stop_resolution import place


def start():
    return AuthorizedStart(point=RoutePoint(id='private_start', coordinates={'latitude':40.75,'longitude':-73.98}),
                           explicitly_authorized=True)


def activity(source, optional=False, **kwargs):
    return RequestedStop(source=source, requirement='optional' if optional else 'required', **kwargs)


def named(source):
    return RequestedStop(source=source, kind='named_place')


def record(identity, name, types, lat=40.75):
    return place(identity, name, types=types, lat=lat)


COLLEGE = record('Synthetic_college', 'SUNY College of Optometry', ['university'])
COFFEE = record('Synthetic_coffee', 'Synthetic coffee cafe', ['cafe'])
GROCERY = record('Synthetic_grocery', 'Synthetic grocery supermarket', ['supermarket'])
BANK = record('Synthetic_bank', 'Synthetic bank ATM', ['bank','atm'])
PHARMACY = record('Synthetic_pharmacy', 'Synthetic pharmacy', ['pharmacy'])
STATION = record('Synthetic_station', 'Penn Station', ['train_station'])


class AdvancedRoutingTests(unittest.TestCase):
    def setUp(self):
        for patcher in (patch.dict(os.environ, {'WHERETO_STOP_RESOLUTION_DEV':'1', 'WHERETO_PLACES_DEV':'1', 'WHERETO_ROUTES_DEV':'1'}),
                        patch('requests.sessions.Session.send', side_effect=AssertionError('No actual provider requests'))):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.calls = []
        self.values = {}
        self.route_error = None
        self.partial = False
        self.matrix_patch = patch('backend.routes_transport.compute_matrix', side_effect=self.matrix)
        self.matrix_patch.start()
        self.addCleanup(self.matrix_patch.stop)

    def matrix(self, body):
        self.calls.append(body)
        if self.route_error:
            raise self.route_error
        result = []
        for i, a in enumerate(body['origins']):
            for j, b in enumerate(body['destinations']):
                aid = a['waypoint'].get('placeId', 'origin')
                bid = b['waypoint'].get('placeId', 'origin')
                value = self.values.get((body['travelMode'],aid,bid), 120 if body['travelMode']=='DRIVE' else 600)
                if value is None:
                    continue
                if value == 'unreachable':
                    result.append({'originIndex':i,'destinationIndex':j,'status':{},'condition':'ROUTE_NOT_FOUND'})
                else:
                    result.append({'originIndex':i,'destinationIndex':j,'status':{},'condition':'ROUTE_EXISTS',
                                   'duration':str(value)+'s','distanceMeters':int(value)*5})
        return result[:1] if self.partial else result

    def resolve(self, stops, *, records=None, context=None, settings=None, **kwargs):
        resolver = StopResolver(ProviderBudget(settings or ProviderSettings()).outing())
        data = records if records is not None else [COLLEGE,COFFEE,GROCERY,BANK,PHARMACY,STATION]
        def search(body, **unused):
            query = body['textQuery'].casefold()
            types = ('cafe' if 'cafe' in query or 'coffee' in query else
                     'supermarket' if 'supermarket' in query or 'grocer' in query else
                     'pharmacy' if 'pharmac' in query else
                     'bank' if 'bank' in query else 'atm' if 'atm' in query else None)
            return {'places': [p for p in data if types is None or types in p['types']]}
        with patch('backend.places_transport.text_search', side_effect=search):
            resolver.resolve(Journey(stops=stops, **kwargs), SearchArea(name='New York'), context=context)
        return resolver

    def plan(self, stops, *, origin=None, beyond=False, **kwargs):
        resolver = self.resolve(stops, **kwargs)
        return AdvancedRouter(resolver).plan(origin=origin, allow_beyond_limit=beyond)

    def test_mandatory_college_then_coffee(self):
        r = self.plan([named('SUNY College of Optometry'), activity('coffee')],
                      order=[{'before':0,'after':1,'source':'college then coffee'}])
        self.assertEqual(r.status,'constructed')
        c=r.candidates[0]
        self.assertEqual([v.occurrence for v in c.visits],[0,1])
        self.assertEqual([v.selected.place_id for v in c.visits],['Synthetic_college','Synthetic_coffee'])
        self.assertEqual(c.route_status,'verified')
        self.assertEqual((r.matrix_elements,r.matrix_requests),(1,1))
        self.assertEqual(c.execution,'unavailable')

    def test_college_coffee_round_trip_directional(self):
        self.values['DRIVE','origin','Synthetic_college']=60
        self.values['DRIVE','Synthetic_coffee','origin']=420
        r=self.plan([named('SUNY College of Optometry'),activity('coffee')],origin=start(),endpoint={'kind':'origin','source':'return to where I started'})
        c=r.candidates[0]
        self.assertEqual([l.role for l in c.legs],['origin_to_first','inter_activity','return_to_origin'])
        self.assertEqual(c.travel_total_seconds,600)
        self.assertEqual(r.matrix_elements,3)
        self.assertNotIn('private_start',r.model_dump_json())
        self.assertNotIn('latitude',r.model_dump_json(exclude={'candidates':{'__all__':{'visits':{'__all__':{'selected':{'facts'}}}}}}))

    def test_grocery_atm_round_trip(self):
        r=self.plan([activity('grocery shopping'),activity('ATM')],origin=start(),endpoint={'kind':'origin','source':'return'})
        self.assertEqual(r.status,'constructed')
        self.assertEqual(r.candidates[0].travel_total_seconds,360)
        self.assertEqual(r.matrix_elements,3)

    def test_single_store_round_trip_and_no_invented_reverse(self):
        self.values['DRIVE','Synthetic_grocery','origin']=None
        r=self.plan([activity('grocery shopping')],origin=start(),endpoint={'kind':'origin','source':'return'})
        c=r.candidates[0]
        self.assertEqual(len(c.legs),2)
        self.assertEqual(c.known_travel_seconds,120)
        self.assertIsNone(c.travel_total_seconds)
        self.assertEqual(c.route_status,'unverified')
        self.assertEqual(c.missing_leg_indexes,[1])
        self.assertIsNone(c.legs[-1].evidence.duration_seconds)

    def test_partial_order_allows_grocery_anywhere(self):
        r=self.plan([activity('pharmacy'),activity('bank'),activity('grocery shopping')],
                    order=[{'before':0,'after':1,'source':'pharmacy before bank'}])
        orders={tuple(v.occurrence for v in c.visits) for c in r.candidates}
        self.assertEqual(orders,{(0,1,2),(0,2,1),(2,0,1)})
        self.assertEqual((r.matrix_elements,r.matrix_requests),(5,3))

    def test_flexible_order_uses_verified_travel(self):
        self.values['DRIVE','Synthetic_bank','Synthetic_grocery']=600
        self.values['DRIVE','Synthetic_grocery','Synthetic_bank']=60
        r=self.plan([activity('bank'),activity('grocery shopping')],ordering='flexible')
        self.assertEqual([v.occurrence for v in r.candidates[0].visits],[1,0])
        self.assertEqual(r.candidates[0].travel_total_seconds,60)
        self.assertEqual(r.matrix_elements,2)

    def test_unspecified_keeps_source_order(self):
        r=self.plan([activity('bank'),activity('grocery shopping')])
        self.assertTrue(all([v.occurrence for v in c.visits]==[0,1] for c in r.candidates))
        self.assertEqual(r.matrix_elements,1)

    def test_cyclic_and_conflicting_order_does_not_route(self):
        for kwargs in ({'order':[{'before':0,'after':1,'source':'before'},{'before':1,'after':0,'source':'before'}]},
                       {'ordering':'constrained'}):
            r=self.plan([activity('bank'),activity('coffee')],**kwargs)
            self.assertEqual(r.status,'unresolved')
        self.assertFalse(self.calls)

    def test_exact_final_station_identity_and_final_leg(self):
        r=self.plan([activity('bank')],origin=start(),endpoint={'kind':'named_place','source':'finish at Penn Station'})
        c=r.candidates[0]
        self.assertEqual(c.endpoint.place_id,'Synthetic_station')
        self.assertEqual([l.role for l in c.legs],['origin_to_first','final_destination'])
        self.assertEqual(c.legs[-1].evidence.destination_id,'Synthetic_station')
        self.assertEqual(r.matrix_elements,2)

    def test_ambiguous_final_station_not_routed(self):
        r=self.plan([activity('bank')],records=[BANK,STATION,record('Synthetic_other_station','Penn Station',['train_station'])],
                    endpoint={'kind':'named_place','source':'finish at Penn Station'})
        self.assertEqual(r.status,'unresolved')
        self.assertFalse(self.calls)

    def test_home_confirmed_origin(self):
        r=self.plan([activity('coffee')],origin=start(),context=InterpretationContext(endpointStatus='origin_confirmed'),
                    endpoint={'kind':'home','source':'return home'})
        self.assertEqual(r.candidates[0].legs[-1].role,'return_to_origin')

    def test_home_needs_verification_or_missing_origin(self):
        for context in (None,InterpretationContext(endpointStatus='location_needs_verification',endpointAnswer='123 Fictional Street'),
                        InterpretationContext(endpointStatus='origin_confirmed')):
            r=self.plan([activity('coffee')],context=context,endpoint={'kind':'home','source':'return home'})
            self.assertEqual(r.status,'unresolved')
        r=self.plan([activity('coffee')],endpoint={'kind':'origin','source':'return'})
        self.assertEqual(r.status,'unresolved')
        self.assertFalse(self.calls)

    def test_verified_separate_home_destination_uses_final_leg(self):
        # An independently verified named destination uses the existing named endpoint
        # resolver. A syntactic home-answer alone above cannot gain that authority.
        r=self.plan([activity('coffee')],origin=start(),endpoint={'kind':'named_place','source':'finish at Penn Station'})
        self.assertEqual(r.candidates[0].legs[-1].role,'final_destination')

    def test_origin_and_endpoint_same_place(self):
        origin=AuthorizedStart(point=RoutePoint(id='private_start',place_id='Synthetic_station'),explicitly_authorized=True)
        r=self.plan([activity('coffee')],origin=origin,endpoint={'kind':'named_place','source':'finish at Penn Station'})
        self.assertEqual(len(r.candidates[0].legs),2)
        self.assertEqual(r.matrix_elements,2)

    def test_optional_coffee_explicit_omission_no_time_claim(self):
        r=self.plan([activity('grocery shopping'),activity('coffee',True)])
        self.assertTrue(r.candidates)
        self.assertTrue(any(c.omitted for c in r.candidates))
        for c in r.candidates:
            self.assertEqual(c.temporal_status,'not_evaluated')
            self.assertIn(0,[v.occurrence for v in c.visits])
            if c.omitted:
                self.assertEqual(c.omitted[0].reason,'routing_cost_or_applicability')
            else:
                self.assertTrue(c.visits[1].optional_included)

    def test_optional_unresolved_omitted_required_not(self):
        r=self.plan([activity('grocery shopping'),named('Missing College').model_copy(update={'requirement':'optional'})])
        self.assertEqual(r.candidates[0].omitted[0].reason,'identity_unavailable')
        r=self.plan([activity('grocery shopping'),named('Missing College')])
        self.assertEqual(r.status,'unresolved')

    def test_repeated_activity_occurrences_distinct_venues(self):
        r=self.plan([activity('coffee'),activity('coffee')],records=[COFFEE,record('Synthetic_cafe2','Synthetic second coffee cafe',['cafe'])])
        self.assertEqual(r.status,'constructed')
        self.assertTrue(all([v.occurrence for v in c.visits]==[0,1] for c in r.candidates))
        self.assertTrue(all(len({v.selected.place_id for v in c.visits})==2 for c in r.candidates))
        self.assertEqual(r.matrix_elements,2)

    def test_duplicate_physical_venue_prohibited(self):
        r=self.plan([activity('coffee'),activity('coffee')],records=[COFFEE])
        self.assertEqual(r.status,'no_candidates')
        self.assertFalse(self.calls)

    def test_missing_and_multiple_mandatory_named_place(self):
        for records in ([],[COLLEGE,record('Synthetic_other','SUNY College of Optometry',['university'])]):
            r=self.plan([named('SUNY College of Optometry')],records=records)
            self.assertEqual(r.status,'unresolved')
        self.assertFalse(self.calls)

    def test_reverse_unavailable_not_inferred(self):
        self.values['DRIVE','Synthetic_coffee','Synthetic_bank']='unreachable'
        r=self.plan([activity('bank'),activity('coffee')],ordering='flexible')
        self.assertEqual(r.candidates[0].route_status,'verified')
        other=next(c for c in r.candidates if c.visits[0].occurrence==1)
        self.assertIsNone(other.travel_total_seconds)
        self.assertEqual(other.legs[0].evidence.status,'unreachable')

    def test_failures_each_leg_preserve_other_metrics(self):
        pairs=[('origin','Synthetic_college'),('Synthetic_college','Synthetic_coffee'),('Synthetic_coffee','origin')]
        for pair in pairs:
            with self.subTest(pair=pair):
                self.values={('DRIVE',*pair):None}
                r=self.plan([named('SUNY College of Optometry'),activity('coffee')],origin=start(),endpoint={'kind':'origin','source':'return'})
                c=r.candidates[0]
                self.assertEqual(c.route_status,'unverified')
                self.assertEqual(c.known_travel_seconds,240)
                self.assertIsNone(c.travel_total_seconds)
                self.assertEqual(len(c.missing_leg_indexes),1)

    def test_driving_walking_separate_policy_and_duration(self):
        for mode,seconds in [('driving',120),('walking',600)]:
            r=self.plan([activity('bank'),activity('coffee')],context=InterpretationContext(transport=mode))
            c=r.candidates[0]
            self.assertEqual(c.travel_total_seconds,seconds)
            self.assertEqual(c.mode,'drive' if mode=='driving' else 'walk')
            self.assertEqual('routingPreference' in self.calls[-1],mode=='driving')
        self.assertEqual(len(self.calls),2)

    def test_walking_only_unavailable(self):
        self.values['WALK','Synthetic_bank','Synthetic_coffee']=None
        r=self.plan([activity('bank'),activity('coffee')],context=InterpretationContext(transport='walking'))
        self.assertEqual(r.candidates[0].route_status,'unverified')
        self.assertIsNone(r.candidates[0].travel_total_seconds)
        self.assertTrue(all(b['travelMode']=='WALK' for b in self.calls))

    def test_strict_first_stop_limit_and_explicit_exception(self):
        self.values['DRIVE','origin','Synthetic_coffee']=601
        context=InterpretationContext(firstTravel={'value':10.,'unit':'minutes','mode':'strict'})
        r=self.plan([activity('coffee')],origin=start(),context=context)
        self.assertEqual(r.status,'no_candidates')
        r=self.plan([activity('coffee')],origin=start(),context=context,beyond=True)
        self.assertEqual(r.candidates[0].route_status,'beyond_limit')
        self.assertAlmostEqual(r.candidates[0].checks[0].excess_over_maximum,1/60)
        self.assertEqual(context.firstTravel.value,10)

    def test_flexible_preference_maximum_and_exact_exclusion(self):
        context=InterpretationContext(firstTravel={'value':10.,'mode':'flexible'})
        for seconds,state in [(600,'matching'),(900,'outside_preference'),(1200,'outside_preference'),(1201,None)]:
            self.values['DRIVE','origin','Synthetic_coffee']=seconds
            r=self.plan([activity('coffee')],origin=start(),context=context)
            if state:
                self.assertEqual(r.candidates[0].checks[0].state,state)
            else:
                self.assertEqual(r.status,'no_candidates')
        context.firstTravel.mode='strict';context.firstTravel.exclusive=True
        self.values['DRIVE','origin','Synthetic_coffee']=600
        self.assertEqual(self.plan([activity('coffee')],origin=start(),context=context).status,'no_candidates')

    def test_first_stop_distance_limit(self):
        context=InterpretationContext(firstTravel={'value':0.1,'unit':'miles'})
        self.assertEqual(self.plan([activity('coffee')],origin=start(),context=context).status,'no_candidates')
        context.firstTravel.value=1.
        self.assertEqual(self.plan([activity('coffee')],origin=start(),context=context).candidates[0].checks[0].state,'matching')

    def test_between_cap_does_not_apply_to_return_or_first(self):
        self.values['DRIVE','origin','Synthetic_bank']=1800
        self.values['DRIVE','Synthetic_coffee','origin']=2400
        context=InterpretationContext(betweenTravel={'value':3.,'mode':'strict'})
        r=self.plan([activity('bank'),activity('coffee')],origin=start(),context=context,endpoint={'kind':'origin','source':'return'})
        self.assertEqual(r.candidates[0].route_status,'verified')
        self.assertEqual([c.leg_index for c in r.candidates[0].checks],[1])
        context.betweenTravel.value=1.
        self.assertEqual(self.plan([activity('bank'),activity('coffee')],origin=start(),context=context).status,'no_candidates')

    def test_legacy_per_leg_cap_is_enforced(self):
        r=self.plan([activity('bank'),activity('coffee')],context=InterpretationContext(maxLegTravel=1))
        self.assertEqual(r.status,'no_candidates')
        r=self.plan([activity('bank'),activity('coffee')],context=InterpretationContext(maxLegTravel=2))
        self.assertEqual(r.candidates[0].checks[0].state,'matching')

    def test_total_between_cap_excludes_first_return_and_whole_trip(self):
        self.values['DRIVE','origin','Synthetic_bank']=1800
        self.values['DRIVE','Synthetic_coffee','origin']=2400
        args=dict(origin=start(),endpoint={'kind':'origin','source':'return'})
        stops=[activity('bank'),activity('grocery shopping'),activity('coffee')]
        r=self.plan(stops,context=InterpretationContext(travel=4),**args)
        self.assertEqual(r.candidates[0].between_total_check.total_seconds,240)
        self.assertEqual(r.candidates[0].travel_total_seconds,4440)
        self.assertEqual(self.plan(stops,context=InterpretationContext(travel=3),**args).status,'no_candidates')
        self.assertEqual(self.plan(stops,context=InterpretationContext(travel=4,travelExclusive=True),**args).status,'no_candidates')

    def test_partial_total_cannot_pass_and_known_lower_bound_can_fail(self):
        self.values['DRIVE','Synthetic_bank','Synthetic_grocery']=None
        stops=[activity('bank'),activity('grocery shopping'),activity('coffee')]
        r=self.plan(stops,context=InterpretationContext(travel=4))
        self.assertEqual(r.candidates[0].between_total_check.state,'unknown')
        self.assertIsNone(r.candidates[0].between_total_check.total_seconds)
        self.values['DRIVE','Synthetic_grocery','Synthetic_coffee']=301
        self.assertEqual(self.plan(stops,context=InterpretationContext(travel=4)).status,'no_candidates')

    def test_interpretation_handoff_retains_travel_only_scopes_and_manual_precedence(self):
        from backend.ai import Interpretation
        from backend.interpretation import InterpretationInput, interpret_request, advanced_travel_fields, ManualPreferences
        from backend.journey_fixtures import reply
        from backend.test_journey import NOW
        from unittest.mock import Mock
        raw='Go to SUNY College of Optometry then get coffee, under 5 minutes total travel.'
        provider=Mock()
        provider.interpret.return_value=Interpretation.model_validate(reply(['SUNY College of Optometry','coffee'],
            kinds={0:'named_place'},order=[(0,1,'SUNY College of Optometry then get coffee')]))
        r=interpret_request(InterpretationInput(text=raw),provider,now=NOW)
        self.assertEqual((r.context.travel,r.context.travelExclusive),(5,True))
        self.assertIsNone(r.interpretation.journey.total_duration)
        r=interpret_request(InterpretationInput(text=raw,preferences={'travel':'10'}),provider,now=NOW)
        self.assertEqual((r.context.travel,r.context.travelExclusive),(10,False))
        fields,issues=advanced_travel_fields('under 8 minutes each leg',ManualPreferences())
        self.assertEqual(fields['maxLegTravel'],8)
        self.assertTrue(fields['maxLegTravelExclusive'])
        self.assertFalse(issues)
        _,issues=advanced_travel_fields('under 5 miles total travel',ManualPreferences())
        self.assertTrue(issues)
        _,issues=advanced_travel_fields('under 5 miles each leg',ManualPreferences())
        self.assertTrue(issues)
        _,issues=advanced_travel_fields('',ManualPreferences(travel='invalid'))
        self.assertTrue(issues)

    def test_missing_route_never_passes_hard_limit(self):
        self.values['DRIVE','origin','Synthetic_coffee']=None
        r=self.plan([activity('coffee')],origin=start(),context=InterpretationContext(firstTravel={'value':10.}))
        self.assertEqual(r.candidates[0].checks[0].state,'unknown')
        self.assertEqual(r.candidates[0].route_status,'unverified')

    def test_duration_deadline_dwell_hours_preserved_without_arrivals(self):
        coffee={**COFFEE,'regularOpeningHours':{'periods':[],'weekdayDescriptions':['Explicitly closed']},'timeZone':{'id':'America/New_York'}}
        dwell={'minutes':15,'relation':'exact','source':'coffee for 15 minutes'}
        total={'minutes':30,'relation':'maximum','source':'within 30 minutes'}
        deadline={'source':'by 5 PM','minute':1020}
        r=self.plan([activity('coffee',duration=dwell)],records=[coffee],context=InterpretationContext(date='2026-11-07',timezone='America/New_York'),
                    total_duration=total,deadline=deadline)
        c=r.candidates[0]
        self.assertEqual(c.journey.total_duration.minutes,30)
        self.assertEqual(c.journey.deadline.minute,1020)
        self.assertEqual(c.visits[0].requested.duration.minutes,15)
        self.assertEqual(c.visits[0].selected.facts.regularOpeningHours.periods,[])
        self.assertEqual(c.visits[0].selected.facts.timeZone.id,'America/New_York')
        self.assertTrue(c.visits[0].selected.facts.observedAt)
        self.assertEqual((r.date,r.timezone),('2026-11-07','America/New_York'))
        self.assertEqual(c.temporal_status,'not_evaluated')
        self.assertNotIn('arrival',c.model_dump_json())

    def test_verified_current_closed_date_excluded_without_visit_times(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        day=datetime.now(ZoneInfo('America/New_York')).date()
        closed={**COFFEE, 'currentOpeningHours':{'periods':[]}, 'timeZone':{'id':'America/New_York'}}
        r=self.plan([activity('coffee')], records=[closed],
                    context=InterpretationContext(date=day,timezone='America/New_York'))
        self.assertEqual(r.status,'no_candidates')
        self.assertEqual(r.hours_exclusions[0].candidate.place_id,'Synthetic_coffee')
        self.assertEqual(r.hours_exclusions[0].status,'closed')
        self.assertFalse(self.calls)
        r=self.plan([activity('grocery shopping'),activity('coffee',True)], records=[GROCERY,closed],
                    context=InterpretationContext(date=day,timezone='America/New_York'))
        self.assertEqual(r.candidates[0].omitted[0].reason,'known_closed')
        self.assertEqual(len(r.hours_exclusions),1)

    def test_required_return_cannot_be_removed_from_contract(self):
        c=self.plan([activity('coffee')], origin=start(), endpoint={'kind':'origin','source':'return'}).candidates[0]
        data=c.model_dump();data['legs'].pop()
        data.update(known_travel_seconds=120.,known_distance_meters=600,travel_total_seconds=120.)
        with self.assertRaises(ValidationError):AdvancedRouteCandidate.model_validate(data)

    def test_local_application_limit_distinct_from_cloud(self):
        r=self.plan([activity('bank'),activity('coffee')],settings=ProviderSettings(matrix_elements_per_outing=0))
        self.assertEqual(r.candidates[0].legs[0].evidence.error_code,'application_limit')
        self.assertEqual(r.matrix_elements,0)
        self.assertFalse(self.calls)
        self.route_error=RouteError('quota','Google Cloud quota rejection')
        r=self.plan([activity('bank'),activity('coffee')])
        self.assertEqual(r.candidates[0].legs[0].evidence.error_code,'quota')
        self.assertEqual(r.matrix_elements,1)
        self.assertEqual(len(self.calls),1)

    def test_partial_matrix_retains_good_evidence_no_retries(self):
        self.partial=True
        r=self.plan([activity('bank'),activity('coffee')],records=[BANK,COFFEE,record('Synthetic_cafe2','Synthetic second coffee',['cafe'])])
        self.assertEqual({c.route_status for c in r.candidates},{'verified','unverified'})
        self.assertEqual(r.matrix_elements,2)
        self.assertEqual(len(self.calls),1)

    def test_transport_failure_stops_remaining_batches(self):
        self.route_error=RouteError('timeout','safe timeout')
        r=self.plan([activity('bank'),activity('coffee')],origin=start(),endpoint={'kind':'origin','source':'return'})
        self.assertEqual(len(self.calls),1)
        self.assertEqual(r.matrix_elements,3)
        self.assertEqual(r.candidates[0].known_travel_seconds,0)
        self.assertIsNone(r.candidates[0].travel_total_seconds)
        self.assertTrue(any(l.evidence.error_code=='not_requested' for l in r.candidates[0].legs))

    def test_no_duplicate_directed_requests_and_reuse_active_result(self):
        resolver=self.resolve([activity('bank'),activity('coffee')])
        router=AdvancedRouter(resolver)
        first=router.plan(origin=start())
        calls=len(self.calls)
        second=router.plan(origin=start())
        self.assertEqual(first,second)
        first.candidates.clear()
        self.assertTrue(router.plan(origin=start()).candidates)
        self.assertEqual(calls,len(self.calls))
        with self.assertRaises(RouteError):router.plan()
        pairs=[]
        for body in self.calls:
            pairs += [(str(a),str(b),body['travelMode']) for a in body['origins'] for b in body['destinations']]
        self.assertEqual(len(pairs),len(set(pairs)))

    def test_many_combinations_bounded_and_deterministic(self):
        records=[record(f'Synthetic_{kind}{i}',f'Synthetic {kind} {i}', [kind],40.75+i*.001)
                 for kind in ('cafe','bank','supermarket','pharmacy') for i in range(10)]
        kwargs=dict(records=records,ordering='flexible',origin=start(),endpoint={'kind':'origin','source':'return'})
        r=self.plan([activity('coffee'),activity('bank'),activity('grocery shopping'),activity('pharmacy')],**kwargs)
        self.assertTrue(r.candidates)
        self.assertLessEqual(r.considered_paths,24)
        self.assertLessEqual(r.matrix_elements,27)
        self.assertLessEqual(sum(len(b['origins'])*len(b['destinations']) for b in self.calls),27)
        self.assertTrue(all(len(c.visits)==4 for c in r.candidates))
        print(f'50C dense fixture: {r.considered_paths} considered, {r.admitted_paths} admitted; {r.matrix_elements} elements, {r.matrix_requests} requests; existing gross estimate ${r.matrix_elements*.005:.3f}')
        again=self.plan([activity('coffee'),activity('bank'),activity('grocery shopping'),activity('pharmacy')],**kwargs)
        self.assertEqual([[(v.occurrence,v.selected.place_id) for v in c.visits] for c in r.candidates],
                         [[(v.occurrence,v.selected.place_id) for v in c.visits] for c in again.candidates])
        self.assertEqual((r.matrix_elements,r.matrix_requests),(again.matrix_elements,again.matrix_requests))

    def test_identical_physical_orders_deduplicated_across_occurrence_assignments(self):
        records=[record(f'Synthetic_multi{i}',f'Synthetic coffee bank grocery pharmacy {i}',
                        ['cafe','bank','supermarket','pharmacy'],40.75+i*.001) for i in range(10)]
        r=self.plan([activity('coffee'),activity('bank'),activity('grocery shopping'),activity('pharmacy')],
                    records=records,ordering='flexible')
        orders=[tuple(v.selected.place_id for v in c.visits) for c in r.candidates]
        self.assertEqual(len(orders),len(set(orders)))

    def test_unsupported_stop_count_and_mode_no_io(self):
        for kwargs in ({'stops':[activity('coffee')]*5},{'stops':[activity('coffee')],'context':InterpretationContext(transport='cycling')}):
            r=self.plan(**kwargs)
            self.assertEqual(r.status,'unsupported')
        self.assertFalse(self.calls)

    def test_optional_dependency_preserves_transitive_precedence(self):
        r=self.plan([activity('bank'),activity('coffee',True),activity('grocery shopping')],
                    order=[{'before':0,'after':1,'source':'bank before coffee'}, {'before':1,'after':2,'source':'coffee before groceries'}])
        self.assertTrue(r.candidates)
        for c in r.candidates:
            order=[v.occurrence for v in c.visits]
            self.assertLess(order.index(0),order.index(2))

    def test_gate_trusted_resolution_and_expiry(self):
        resolver=self.resolve([activity('coffee')])
        with self.assertRaises(TypeError):AdvancedRouter(resolver.routing_snapshot())
        with patch.dict(os.environ,{'WHERETO_STOP_RESOLUTION_DEV':'0'}):
            with self.assertRaises(Exception):AdvancedRouter(resolver).plan()
        resolver._expires=0
        with self.assertRaises(ValueError):AdvancedRouter(resolver).plan()
        self.assertFalse(self.calls)

    def test_contract_rejects_false_totals_unknown_zero_mode_and_omission(self):
        c=self.plan([activity('bank'),activity('coffee')]).candidates[0]
        for mutate in (lambda d:d.update(travel_total_seconds=0),lambda d:d.update(route_status='unverified'),
                       lambda d:d['visits'].pop(),lambda d:d['legs'][0]['evidence'].update(mode='walk'),
                       lambda d:d['legs'][0].update(from_occurrence=1)):
            data=c.model_dump();mutate(data)
            with self.assertRaises(ValidationError):AdvancedRouteCandidate.model_validate(data)

    def test_no_new_public_endpoint_or_advanced_save_shape(self):
        from backend.main import app
        paths=[r.path for r in app.routes]
        self.assertFalse(any('advanced' in p or 'resolve' in p for p in paths))
        from backend.models import OutingRequest
        with self.assertRaises(ValidationError):OutingRequest(activities=['coffee'],journey={'stops':[]})

    def test_offline_overhead_benchmark(self):
        resolver=self.resolve([named('SUNY College of Optometry'),activity('coffee')],endpoint={'kind':'origin','source':'return'})
        samples=[]
        # Fresh outing per iteration; no resetting actual provider counters.
        for _ in range(20):
            resolver=self.resolve([named('SUNY College of Optometry'),activity('coffee')],endpoint={'kind':'origin','source':'return'})
            begin=perf_counter();r=AdvancedRouter(resolver).plan(origin=start());samples.append((perf_counter()-begin)*1000)
            self.assertEqual(r.matrix_elements,3)
        print(f'50C offline routing only: median={median(samples):.3f}ms max={max(samples):.3f}ms; 3 elements, 3 requests, $0.015 existing gross estimate; live=$0')


if __name__ == '__main__':
    unittest.main()
