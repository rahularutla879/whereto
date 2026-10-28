"""100/activity, classified browsing and cancellation, entirely invented evidence."""
import os
import unittest
from tempfile import TemporaryDirectory
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch
from backend.test_discovery_acceptance import Discovery
from backend.real_planning import real_plans, more_real_plans
from backend.provider_budget import ProviderBudget, ProviderSettings, ProviderLimitError
from backend.sequential_discovery import initialize, expand, can_expand
from backend.option_sessions import option_sessions
from backend.travel_classification import classify
from backend.provider_work import cancelled, wait_for_capacity, check_cancelled
from backend.test_real_planning import outing
from backend.routes import RouteLeg
from backend.models import Venue
from backend.planner import _walk

class Pools(Discovery):
    # Inherit the fixture transport and its tripwire, not its test cases.
    def test_100_independent_activity_pools_staged_and_bounded(self):
        from backend.places import QUERIES
        from backend.location_fixtures import place
        from backend.development_cost import dispatch
        for activities in (['movie','food'],['bowling','food'],['food','drinks'],['bowling','food','drinks']):
            with self.subTest(activities=activities):
                self.clock+=61
                counters={a:0 for a in activities};calls=[]
                def supplied(body,**_):
                    dispatch('search');calls.append(body)
                    activity=next((a for a in activities if body['textQuery'].startswith(QUERIES[a]) or a=='food' and 'restaurant' in body['textQuery']),activities[0])
                    offset=counters[activity];counters[activity]+=10
                    box=body.get('locationRestriction',{}).get('rectangle')
                    lat=(box['low']['latitude']+box['high']['latitude'])/2 if box else 40.75
                    lon=(box['low']['longitude']+box['high']['longitude'])/2 if box else -73.98
                    types={'movie':'movie_theater','food':'restaurant','bowling':'bowling_alley','drinks':'bar'}
                    records=[place(f'Synthetic_{activity}_{n}',f'Synthetic {activity} {n}',lat,lon,types=[types[activity]]) for n in range(offset,offset+10)]
                    for p in records:
                        p['formattedAddress']='Synthetic Manhattan, New York'
                        p['addressComponents']=[{'longText':'Manhattan','types':['sublocality_level_1']},{'longText':'New York','types':['locality']}]
                    return {'places':records,'nextPageToken':f'synthetic-page-{activity}-{offset+10}'} if offset%30<20 else {'places':records}
                with patch('backend.places_transport.text_search',side_effect=supplied):
                    r=self.request().model_copy(update={'activities':activities,'dinnerStops':None})
                    context=initialize(r,ProviderBudget().outing())
                    initial=[sum(a in v.activities for v in context['discovery'].venues) for a in activities]
                    self.assertTrue(all(n<100 for n in initial))
                    for action in range(60):
                        if not can_expand(context):break
                        self.clock+=61
                        before=len(calls);expand(context)
                        self.assertLessEqual(len(calls)-before,2)
                    counts={a:sum(a in v.activities for v in context['discovery'].venues) for a in activities}
                    self.assertEqual(counts,dict.fromkeys(activities,100))
                    self.assertFalse(can_expand(context))
                    print('PER_ACTIVITY_100',{'activities':activities,'retained':counts,'searches':len(calls),'initial':initial})
    def test_manhattan_no_limit_all_stop_diversity_and_fifteen_actions(self):
        r=real_plans(self.request(),ProviderBudget())
        seen=set();by_activity=[set(),set()];searches=len(self.calls)
        for action in range(16):
            self.clock+=61
            self.assertTrue(r.provisionalPlans or r.explorationPlans)
            plans=r.provisionalPlans+r.explorationPlans
            for p in plans:
                signature=tuple(v.id for v in p.candidate.venues)
                self.assertNotIn(signature,seen);seen.add(signature)
                for i,v in enumerate(p.candidate.venues):by_activity[i].add(v.id)
            if action<15:r=more_real_plans(r.optionsToken)
        self.assertEqual(len(self.calls),searches)
        self.assertEqual(len(seen),48)
        self.assertEqual(len(by_activity[0]),10)
        self.assertGreaterEqual(len(by_activity[1]),15)
        print('BROWSE_15',{'full':len(seen),'first':len(by_activity[0]),'later':len(by_activity[1]),'searches':searches,'elements':r.diagnostics['matrixElements']})

# Do not execute inherited historical cases twice.
for name in Discovery.__dict__:
    if name.startswith('test_') and name not in Pools.__dict__:
        setattr(Pools,name,None)

class Classification(unittest.TestCase):
    def plan(self,seconds='600s',meters=1609,**kwargs):
        r=outing(**kwargs)
        vertices=[Venue(id='Synthetic_a',name='Synthetic A',activity='bowling'),Venue(id='Synthetic_b',name='Synthetic B',activity='food')]
        candidate=next(_walk(r,[[v] for v in vertices]))
        plan=SimpleNamespace(candidate=candidate)
        def leg(a,b):
            # Exact nanoseconds are preserved independently from display.
            n=int(float(seconds.removesuffix('s'))*10**9)
            return RouteLeg(origin_id=a,destination_id=b,mode='drive',status='ok',estimate_type='traffic_unaware',duration_seconds=n/10**9,duration_nanoseconds=n,duration_minutes=(n/10**9)/60,distance_meters=meters)
        routes={(vertices[0].id,vertices[1].id):leg(vertices[0].id,vertices[1].id),(r.startingLocation.point.id,vertices[0].id):leg(r.startingLocation.point.id,vertices[0].id)}
        return r,plan,routes
    def test_strict_and_flexible_exact_boundaries_and_unknown(self):
        for preference,seconds,expected in [
            ({'value':10.,'mode':'strict','exclusive':True},'600s','beyond_limit'),
            ({'value':10.,'mode':'strict'},'600s','matching'),
            ({'value':5.,'mode':'flexible'},'599s','outside_preference'),
            ({'value':5.,'mode':'flexible'},'600s','outside_preference'),
            ({'value':5.,'mode':'flexible'},'600.001s','beyond_limit')]:
            r,p,routes=self.plan(seconds,firstTravel=preference)
            category,messages=classify(r,p,routes,r.startingLocation)
            self.assertEqual(category,expected)
            if expected!='matching':self.assertTrue(messages)
        r,p,routes=self.plan()
        routes.clear()
        self.assertEqual(classify(r,p,routes,r.startingLocation)[0],'unverified')
    def test_miles_scope_total_and_accessibility_tristate(self):
        r,p,routes=self.plan('60s',32187,betweenTravel={'value':10.001,'unit':'miles','mode':'flexible'})
        self.assertEqual(classify(r,p,routes,r.startingLocation)[0],'outside_preference')
        r=r.model_copy(update={'travel':0})
        self.assertEqual(classify(r,p,routes,r.startingLocation)[0],'beyond_limit')
        r=r.model_copy(update={'travel':None,'betweenTravel':None,'requireWheelchairAccess':True})
        self.assertEqual(classify(r,p,routes,r.startingLocation)[0],'unverified')
        for v in p.candidate.venues:v.wheelchairAccessible=True
        self.assertEqual(classify(r,p,routes,r.startingLocation)[0],'matching')
        p.candidate.venues[0].wheelchairAccessible=False
        with self.assertRaisesRegex(ValueError,'inaccessible'):classify(r,p,routes,r.startingLocation)
    def test_retention_and_route_frontier_are_independent_in_normal_mode(self):
        from backend.routing_shortlist import expansion_width
        self.assertEqual(ProviderSettings().candidates_per_activity,100)
        self.assertEqual(expansion_width(ProviderSettings(),2),20)
        self.assertEqual(expansion_width(ProviderSettings(),4),10)

    def test_bounded_admission_and_cancellation_make_zero_provider_calls(self):
        event=Event();token=cancelled.set(event)
        try:
            event.set()
            with self.assertRaisesRegex(ProviderLimitError,'cancelled'):wait_for_capacity(lambda:0,.01)
            event.clear()
            self.assertEqual(wait_for_capacity(lambda:0,.01),0)
            self.assertEqual(wait_for_capacity(lambda:12,.01),12)
        finally:cancelled.reset(token)

# Imported fixture class is not a second test suite in this module.
del Discovery

class PipelineAlternatives(unittest.TestCase):
    def test_travel_only_violations_are_explicit_and_constraints_unchanged(self):
        from backend.real_fixtures import search_fixture,matrix_fixture
        from backend.test_real_planning import ENV
        with patch.dict(os.environ,ENV,clear=True),patch('requests.sessions.Session.send',side_effect=AssertionError('No Google')),patch('backend.places_transport.text_search',side_effect=search_fixture),patch('backend.routes_transport.compute_matrix',side_effect=matrix_fixture):
            request=outing(maxFirstLegTravel=1)
            r=real_plans(request,ProviderBudget(ProviderSettings(mode='real',candidates_per_activity=3)))
            self.assertFalse(r.provisionalPlans)
            self.assertEqual(len(r.explorationPlans),3)
            self.assertTrue(all(p.feasibility=='violated' and p.travelClassification=='beyond_limit' and p.travelDeviations for p in r.explorationPlans))
            self.assertEqual(r.request.maxFirstLegTravel,1)
            type(r).model_validate_json(r.model_dump_json())
    def test_unknown_access_is_separated_and_known_incompatible_not_usable(self):
        from backend.real_fixtures import search_fixture,matrix_fixture
        from backend.test_real_planning import ENV
        with patch.dict(os.environ,ENV,clear=True),patch('requests.sessions.Session.send',side_effect=AssertionError('No Google')),patch('backend.places_transport.text_search',side_effect=search_fixture),patch('backend.routes_transport.compute_matrix',side_effect=matrix_fixture):
            r=real_plans(outing(requireWheelchairAccess=True),ProviderBudget(ProviderSettings(mode='real',candidates_per_activity=3)))
            self.assertTrue(all(p.travelClassification=='unverified' for p in r.provisionalPlans))
            self.assertTrue(all(any('wheelchair' in m for m in p.travelDeviations) for p in r.provisionalPlans))
    def test_matching_page_then_separate_strict_alternative_pages(self):
        from backend.real_fixtures import search_fixture,matrix_fixture
        from backend.test_real_planning import ENV
        def routed(body):
            result=matrix_fixture(body)
            for element in result:
                source=body['origins'][element['originIndex']]['waypoint'].get('placeId')
                target=body['destinations'][element['destinationIndex']]['waypoint'].get('placeId')
                if source=='Fixture_origin_0':
                    element['duration']='30s' if target.endswith('_0') else '600s'
            return result
        with patch.dict(os.environ,ENV,clear=True),patch('requests.sessions.Session.send',side_effect=AssertionError('No Google')),patch('backend.places_transport.text_search',side_effect=search_fixture) as searches,patch('backend.routes_transport.compute_matrix',side_effect=routed):
            r=real_plans(outing(maxFirstLegTravel=1),ProviderBudget(ProviderSettings(mode='real',candidates_per_activity=3)))
            self.assertEqual(len(r.provisionalPlans),3)
            self.assertFalse(r.explorationPlans)
            self.assertTrue(all(p.travelClassification=='matching' for p in r.provisionalPlans))
            signatures={tuple(v.id for v in p.candidate.venues) for p in r.provisionalPlans}
            for _ in range(2):
                r=more_real_plans(r.optionsToken)
                self.assertFalse(r.provisionalPlans)
                self.assertEqual(len(r.explorationPlans),3)
                for p in r.explorationPlans:
                    identity=tuple(v.id for v in p.candidate.venues)
                    self.assertNotIn(identity,signatures);signatures.add(identity)
                    self.assertEqual(p.travelClassification,'beyond_limit')
                    self.assertTrue(any('9 min over' in d for d in p.travelDeviations))
            self.assertEqual(searches.call_count,2)
            self.assertEqual(len(signatures),9)

    def test_verified_access_precedes_unknown_and_incompatible_is_excluded(self):
        from backend.real_fixtures import search_fixture,matrix_fixture
        from backend.test_real_planning import ENV
        from backend.places import PlacesDiscovery
        original=PlacesDiscovery.discover_many
        def evidence(discovery,queries):
            result=original(discovery,queries)
            for venue in result.venues:
                venue.facts.wheelchairAccessible=not venue.facts.id.endswith('_0')
            return result
        with patch.dict(os.environ,ENV,clear=True),patch('requests.sessions.Session.send',side_effect=AssertionError('No Google')),patch('backend.places_transport.text_search',side_effect=search_fixture),patch('backend.routes_transport.compute_matrix',side_effect=matrix_fixture),patch('backend.places.PlacesDiscovery.discover_many',evidence):
            r=real_plans(outing(requireWheelchairAccess=True),ProviderBudget(ProviderSettings(mode='real',candidates_per_activity=3)))
            self.assertEqual(len(r.provisionalPlans),3)
            self.assertTrue(all(p.travelClassification=='matching' and all(v.wheelchairAccessible is True for v in p.candidate.venues) for p in r.provisionalPlans))

    def test_persistent_minute_capacity_includes_other_outings(self):
        from backend.development_cost import DevelopmentCost,dispatch
        with TemporaryDirectory() as directory,patch.dict(os.environ,{'WHERETO_DEV_COST_LEDGER':directory+'/usage.json'},clear=True):
            c=DevelopmentCost()
            with c.reserve({'matrix_element':106}):dispatch('matrix',106)
            self.assertEqual(DevelopmentCost().minute_capacity(),44)
            with self.assertRaisesRegex(Exception,'minute'):
                with DevelopmentCost().reserve({'matrix_element':45}):self.fail('Must not admit')
            self.assertEqual(DevelopmentCost().minute_capacity(),44)

class Disconnect(unittest.IsolatedAsyncioTestCase):
    async def test_disconnect_stops_further_dispatches_without_a_provider_retry(self):
        from backend.provider_work import run_work
        steps=[]
        class Request:
            async def is_disconnected(self):return True
        def work():
            from time import sleep
            steps.append('started')
            sleep(.15)
            check_cancelled()
            steps.append('must not dispatch')
        with self.assertRaisesRegex(ProviderLimitError,'cancelled'):
            await run_work(Request(),work)
        self.assertEqual(steps,['started'])
