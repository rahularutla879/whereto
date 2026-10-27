"""Location-first acceptance, invented provider data and a fail-on-network guard."""
import os
import unittest
from datetime import datetime,timezone
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from backend.provider_budget import ProviderBudget,ProviderSettings,ProviderLimitError
from backend.real_planning import real_plans,more_real_plans
from backend.test_real_planning import ENV,outing
from backend.location_fixtures import spatial_search_fixture,place,matrix_fixture
from backend.location_policy import FirstTravel,first_intent,effective_max
from backend.starting_areas import StartingAreaQuery,suggest_starting_areas,references
from backend.routes import AuthorizedStart,RoutePoint,parse_matrix
from backend.feasibility import FeasibilityInput,EvidenceStop,evaluate_feasibility
from backend.venue_normalization import normalize_google_place
from backend.places import DiscoveryRequest,SearchArea,PlacesDiscovery,DiscoveryError
from backend.option_sessions import option_sessions

START={'point':{'id':'authorized-start','coordinates':{'latitude':38.9,'longitude':-77.02}},'explicitly_authorized':True,'source':'manual','label':'Synthetic hotel','precision':'address_or_place'}


class LocationFirst(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.env={**ENV,'WHERETO_START_LOOKUP_DEV':'1','WHERETO_EXPLORATION_DEV':'1','WHERETO_DEV_COST_LEDGER':self.temp.name+'/cost.json'}
        for p in (patch.dict(os.environ,self.env,clear=True),patch('requests.sessions.Session.send',side_effect=AssertionError('Google forbidden'))):
            p.start();self.addCleanup(p.stop)
        self.search=patch('backend.places_transport.text_search',side_effect=spatial_search_fixture).start()
        self.matrix=patch('backend.routes_transport.compute_matrix',side_effect=matrix_fixture).start()
        self.addCleanup(patch.stopall);self.addCleanup(references.entries.clear);self.addCleanup(option_sessions.entries.clear)

    def request(self,**kwargs):
        return outing(locationFirst=True,**kwargs).model_copy(update={'location':'Washington, DC'})

    def test_first_intent_grammar_scope_units_and_hardness(self):
        examples=[('Within 20 minutes of my hotel.',20,'minutes','strict',False),('Within 8 miles of Union Station.',8,'miles','strict',False),
            ('Keep the first stop under 15 minutes away.',15,'minutes','strict',True),('Prefer somewhere around 20 minutes away.',20,'minutes','flexible',False),
            ('First stop at most 20 minutes away.',20,'minutes','strict',False)]
        for text,n,unit,mode,exclusive in examples:
            p,_,error=first_intent(text);self.assertIsNone(error)
            self.assertEqual((p.value,p.unit,p.mode,p.exclusive),(n,unit,mode,exclusive))
        self.assertIsNotNone(first_intent('Within 20 minutes of my hotel. Within 8 miles of Union Station.')[2])
        self.assertEqual(effective_max(FirstTravel(value=20,mode='flexible')),40)
        self.assertEqual(effective_max(FirstTravel(value=20,mode='strict')),20)

    def test_actual_interpretation_pipeline_miles_strict_flexible_and_geo(self):
        from backend.interpretation import InterpretationInput,interpret_request
        from backend.ai import Interpretation
        provider=SimpleNamespace(interpret=lambda text:Interpretation(activities=['bowling','dinner'],people=3,location='Washington, DC',preferences=[],budget_per_person=None,date=None))
        base='Plan bowling and dinner in Washington, DC on Saturday, November 14, 2026 for 3 people. '
        for phrase in ('Within 8 miles of Union Station.','Keep the first stop under 15 minutes away.','Prefer somewhere around 20 minutes away.'):
            r=interpret_request(InterpretationInput(text=base+phrase),provider)
            self.assertIsNotNone(r.request,r.issues)
            self.assertIsNotNone(r.request.firstTravel)
            self.assertIsNone(r.request.maxLegTravel);self.assertIsNone(r.request.travel)
        blocked=interpret_request(InterpretationInput(text=base+'Within 8 miles of my hotel and keep driving between stops under 5 minutes.'),provider)
        self.assertIsNone(blocked.request,'Omitted between-stop cap must not be masked by a first-origin phrase.')
        r=interpret_request(InterpretationInput(text=base+'Only within Washington, DC. No Virginia.'),provider)
        self.assertIsNotNone(r.request,r.issues);self.assertTrue(r.request.geography.strictDestination);self.assertEqual(r.request.geography.excludedRegions,['VA'])

    def test_minutes_and_miles_exact_route_boundaries(self):
        origin=AuthorizedStart(**START)
        venue=normalize_google_place(place('a','Synthetic bowling'),'bowling')
        for unit,amount,seconds,meters in [('minutes',20,1200,1000),('miles',125,10,201168)]:
            for exclusive,state in [(True,'infeasible'),(False,'feasible')]:
                routes=parse_matrix([{'originIndex':0,'destinationIndex':0,'status':{},'condition':'ROUTE_EXISTS','duration':f'{seconds}s','distanceMeters':meters}],[origin.point],[RoutePoint(id='a',place_id='a')],'drive')
                r=evaluate_feasibility(FeasibilityInput(candidate_id='a',stops=[EvidenceStop(venue=venue)],mode='drive',routes=routes,starting_location=origin,first_preference=FirstTravel(value=amount,unit=unit,exclusive=exclusive),evaluated_at=datetime.now(timezone.utc)))
                self.assertEqual(r.travel_state,state)

    def test_sequential_multiple_anchors_and_actual_origin(self):
        r=real_plans(self.request(startingLocation=START,firstTravel={'value':8,'unit':'miles'}),ProviderBudget())
        self.assertEqual(len(r.provisionalPlans),3,r.message)
        bowling=[c.args[0] for c in self.search.call_args_list if 'bowling' in c.args[0]['textQuery']]
        dinners=[c.args[0] for c in self.search.call_args_list if 'restaurant' in c.args[0]['textQuery']]
        self.assertNotIn('locationBias',bowling[0])
        self.assertIn('locationRestriction',bowling[0])
        self.assertIn('Washington, DC',bowling[0]['textQuery'])
        self.assertGreaterEqual(len(dinners),2)
        self.assertGreater(len({str(q['locationRestriction']) for q in dinners}),1)
        self.assertTrue(all(p.firstLeg['miles'] is not None for p in r.provisionalPlans))
        self.assertGreaterEqual(len({p.candidate.venues[0].id for p in r.provisionalPlans}),2)
        self.assertNotIn('38.9',r.model_dump_json())

    def test_preferred_city_allows_neighbors_hard_city_and_exclusion_do_not(self):
        session=ProviderBudget();adapter=PlacesDiscovery(session.outing())
        base=SearchArea(name='Washington, DC',coordinates=START['point']['coordinates'],radius_m=30000,enforce_name=False)
        allowed=adapter.discover(DiscoveryRequest(activity='bowling',destination=base))
        self.assertTrue(any('MD' in (v.facts.address or '') for v in allowed.venues))
        self.assertTrue(any('VA' in (v.facts.address or '') for v in allowed.venues))
        strict=PlacesDiscovery(session.outing()).discover(DiscoveryRequest(activity='bowling',destination=base.model_copy(update={'enforce_name':True})))
        self.assertTrue(all('DC' in v.facts.address for v in strict.venues))
        excluded=PlacesDiscovery(session.outing()).discover(DiscoveryRequest(activity='bowling',destination=base.model_copy(update={'excluded_regions':['VA']})))
        self.assertFalse(any('VA' in v.facts.address for v in excluded.venues))
        self.assertFalse(any(v.facts.id=='Synthetic_unsupported_arcade' for v in allowed.venues))

    def test_suggestions_verified_scored_confirmed_and_reused(self):
        session=ProviderBudget();query=StartingAreaQuery(destination='Washington, DC',activities=['bowling','food'])
        response=suggest_starting_areas(query,session)
        self.assertGreaterEqual(len(response['matches']),1)
        scores=[p['score'] for p in response['matches']];self.assertEqual(scores,sorted(scores,reverse=True))
        match=response['matches'][0]
        request=self.request(referenceToken=response['referenceToken'],startingLocation={**START,'point':{'id':'reference_'+match['placeId'],'coordinates':match['coordinates']},'source':'suggested'})
        r=real_plans(request,session)
        self.assertTrue(r.provisionalPlans,r.message)
        self.assertTrue(all(p.firstLeg['source']=='suggested' and p.firstLeg['originLabel']==match['name'] for p in r.provisionalPlans))
        self.assertEqual(sum(c.args[0]['textQuery'].startswith('public transit') for c in self.search.call_args_list),3)
        self.assertEqual(r.request.location,'Washington, DC')

    def test_suggestion_no_trustworthy_reference_and_gate_disabled(self):
        self.search.side_effect=lambda body,**kw:{'places':[place('private','Synthetic private house',types=['private_residence'])]}
        self.assertEqual(suggest_starting_areas(StartingAreaQuery(destination='Washington, DC',activities=['bowling']),ProviderBudget())['matches'],[])
        with patch.dict(os.environ,{'WHERETO_START_LOOKUP_DEV':'0'}):
            with self.assertRaises(DiscoveryError):suggest_starting_areas(StartingAreaQuery(destination='Washington, DC',activities=['bowling']),ProviderBudget())

    def test_flexible_entire_double_range_initially_eligible_strict_does_not_expand(self):
        def slow_first(body):
            result=matrix_fixture(body)
            for element in result:
                if 'location' in body['origins'][element['originIndex']]['waypoint']:element['duration']='1320s'
            return result
        self.matrix.side_effect=slow_first
        r=real_plans(self.request(startingLocation=START,firstTravel={'value':20,'mode':'flexible'}),ProviderBudget())
        self.assertTrue(r.provisionalPlans,r.message)
        context,_=option_sessions.get(r.optionsToken);self.assertNotIn('band',context)
        self.assertTrue(all(p.firstLeg['exceedsPreference'] for p in r.provisionalPlans))
        self.search.reset_mock();self.matrix.reset_mock()
        r=real_plans(self.request(startingLocation=START,firstTravel={'value':20,'mode':'strict'}),ProviderBudget())
        self.assertFalse(r.provisionalPlans)
        context,_=option_sessions.get(r.optionsToken);self.assertNotIn('band',context)
        self.assertLessEqual(len([c for c in self.search.call_args_list if 'bowling' in c.args[0]['textQuery']]),1)

    def test_three_four_and_repeated_activities(self):
        for iteration,activities in enumerate((['coffee','bowling','food'],['coffee','museum','bowling','food'],['bowling','food','bowling'])):
            with self.subTest(activities=activities):
                # Separate synthetic minute windows for finite action tests.
                with patch('backend.development_cost.time',return_value=10000+iteration*100),patch('backend.provider_budget.monotonic',return_value=10000):
                    r=real_plans(self.request(activities=activities,startingLocation=START),ProviderBudget())
                self.assertTrue(r.provisionalPlans,r.message)
                self.assertTrue(all([v.activity for v in p.candidate.venues]==activities for p in r.provisionalPlans))
                self.assertLessEqual(r.diagnostics['candidateCombinations'],96)

    def test_fifteen_alternative_actions_share_inventory_and_budgets(self):
        session=ProviderBudget();seen=set();primaries=set();requests=[]
        for action in range(16):
            with patch('backend.development_cost.time',return_value=20000+action*100),patch('backend.provider_budget.monotonic',return_value=20000+action*100):
                result=real_plans(self.request(startingLocation=START),session) if action==0 else more_real_plans(token)
            token=result.optionsToken
            plans=result.provisionalPlans+[p for batch in result.alternativeBatches for p in batch]
            self.assertTrue(plans,(action,result.message))
            for plan in plans:
                self.assertNotIn(plan.candidate.id,seen);seen.add(plan.candidate.id);primaries.add(plan.candidate.venues[0].id)
            context,_=option_sessions.get(token)
            requests.append(context['outing'].usage()['providerAttempts'])
            self.assertLessEqual(context.get('actionDiscoveryCalls',0),7 if action==0 else 2)
            self.assertLessEqual(context.get('actionRouteStages',0),2)
        self.assertGreaterEqual(len(seen),48)
        self.assertGreaterEqual(len(primaries),10)
        self.assertEqual(requests,sorted(requests))
        self.assertIs(context['outing']._session,session)
        print('LOCATION_FIRST_FIXTURE_SUMMARY',{'actions':16,'uniqueOffered':len(seen),'primaryVenues':len(primaries),'searches':context['outing'].usage()['placesSearchRequests'],'routeElements':context['outing'].usage()['reservedMatrixElements']})

    def test_unavailable_routes_and_quota_do_not_create_fake_plans_or_retry(self):
        self.matrix.return_value=[];self.matrix.side_effect=None
        result=real_plans(self.request(startingLocation=START),ProviderBudget())
        self.assertFalse(result.provisionalPlans)
        calls=self.search.call_count
        self.search.side_effect=DiscoveryError('quota','Provider quota reached.')
        with self.assertRaises(DiscoveryError):real_plans(self.request(),ProviderBudget())
        self.assertEqual(self.search.call_count,calls+1)

    def test_identical_anchor_query_reuses_results_for_repeated_positions(self):
        def colocated(body,**kwargs):
            found=spatial_search_fixture(body,**kwargs)
            for p in found['places']:p['location']=START['point']['coordinates']
            return found
        self.search.side_effect=colocated
        result=real_plans(self.request(activities=['bowling','food','bowling'],startingLocation=START,firstTravel={'value':10},geography={'strictDestination':True}),ProviderBudget())
        self.assertTrue(result.provisionalPlans,result.message)
        context,_=option_sessions.get(result.optionsToken)
        self.assertTrue(context['positionIds'][2])
        self.assertEqual(self.search.call_count,2,'Repeated identical spatial query reuses the first observation.')
        self.assertTrue(all(len({v.id for v in p.candidate.venues})==3 for p in result.provisionalPlans))

    def test_normal_mode_location_first_preserves_ceiling_and_origin_source(self):
        with patch.dict(os.environ,{'WHERETO_EXPLORATION_DEV':'0'}):
            request=self.request(activities=['coffee','museum','bowling','food'],startingLocation={**START,'source':'device','precision':'device','accuracy_m':125})
            result=real_plans(request,ProviderBudget())
        self.assertTrue(result.provisionalPlans,result.message)
        self.assertLessEqual(result.diagnostics['placesSearchRequests'],10)
        self.assertLessEqual(result.diagnostics['matrixElements'],300)
        self.assertTrue(all(p.firstLeg['source']=='device' and p.firstLeg['approximate'] for p in result.provisionalPlans))

    def test_near_me_fixed_radius_remains_global_across_anchor_searches(self):
        request=self.request(startingLocation=START,currentArea={'coordinates':START['point']['coordinates']},searchRadius=500.0).model_copy(update={'location':'near me'})
        result=real_plans(request,ProviderBudget())
        self.assertTrue(result.provisionalPlans,result.message)
        context,_=option_sessions.get(result.optionsToken)
        from backend.venue_geography import distance_m
        from backend.venue_models import Coordinates
        self.assertTrue(all(distance_m(Coordinates(**START['point']['coordinates']),v.facts.coordinates)<=500 for v in context['discovery'].venues))

    def test_region_exclusion_requires_evidence_and_reference_tokens_expire(self):
        from backend.venue_geography import geographic_reason
        from backend.venue_models import Coordinates
        self.assertEqual(geographic_reason(SearchArea(name='Washington, DC',enforce_name=False,coordinates=START['point']['coordinates'],excluded_regions=['VA']),Coordinates(**START['point']['coordinates']),[]),'excluded_region_unverified')
        session=ProviderBudget()
        with patch('backend.starting_areas.monotonic',return_value=100):
            result=suggest_starting_areas(StartingAreaQuery(destination='Washington, DC',activities=['bowling']),session)
        with patch('backend.starting_areas.monotonic',return_value=701):
            with self.assertRaises(DiscoveryError):references.confirm(result['referenceToken'],result['matches'][0]['placeId'],session)

    def test_provider_rectangle_is_finite_and_does_not_mix_bias_with_restriction(self):
        from backend.places import search_body
        for latitude,longitude in [(38.9,-77.02),(89.99,0),(0,179.99)]:
            body=search_body(DiscoveryRequest(activity='bowling',destination=SearchArea(name='Washington, DC',coordinates={'latitude':latitude,'longitude':longitude},radius_m=50000,restrict_to_area=True)),10)
            self.assertNotIn('locationBias',body)
            box=body['locationRestriction']['rectangle']
            self.assertLessEqual(box['low']['latitude'],box['high']['latitude'])
            self.assertTrue(all(-180<=box[k]['longitude']<=180 for k in ('low','high')))
        # A remote authorized point cannot silently turn explicit DC into New York.
        self.search.side_effect=lambda body,**kw:{'places':[{**place('remote','Synthetic remote bowling',40.7,-74.0),'addressComponents':[{'longText':'New York','types':['locality']},{'shortText':'NY','types':['administrative_area_level_1']}]}]}
        result=real_plans(self.request(startingLocation={**START,'point':{'id':'authorized-start','coordinates':{'latitude':40.7,'longitude':-74.0}}}),ProviderBudget())
        self.assertFalse(result.provisionalPlans)
        self.search.side_effect=lambda body,**kwargs:{'places':[None]}
        with self.assertRaises(DiscoveryError):real_plans(self.request(),ProviderBudget())

    def test_mock_mode_does_not_ignore_new_hard_geography(self):
        from backend import main as api
        with patch.dict(os.environ,{'WHERETO_EXPLORATION_DEV':'0'}),patch.object(api,'provider_budget',ProviderBudget(ProviderSettings(mode='mock'))):
            response=api.generate_plan(self.request(geography={'excludedRegions':['MD']}).model_copy(update={'location':'Baltimore'}))
        self.assertEqual(response.status_code,422)
        self.assertIn('ignored constraint',response.body.decode())

    def test_missing_origin_requires_confirmation_without_provider_calls(self):
        r=real_plans(self.request(startingLocation=None),ProviderBudget())
        self.assertFalse(r.provisionalPlans);self.assertIn('confirm',r.message)
        self.assertEqual(self.search.call_count,0);self.assertEqual(self.matrix.call_count,0)

if __name__=='__main__':unittest.main()
