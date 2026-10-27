"""Latest Task 46 acceptance: invented providers, no billable requests."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from backend import test_location_first as fixture
from backend.location_policy import FirstTravel,effective_max,exceeds,first_intent
from backend.provider_errors import classify
from backend.routes import RouteLeg
from backend.places import DiscoveryCandidate
from backend.starting_scoring import compare
from backend.interpretation import InterpretationInput,interpret_request
from backend.ai import Interpretation

PROMPT="Plan bowling followed by dinner in Washington, DC, on Saturday, November 14, 2026, for 3 people. I'd prefer the first stop to be within 20 minutes of my starting point."

def leg(a='origin',b='venue',seconds=2400,meters=1000):
    return RouteLeg(origin_id=a,destination_id=b,mode='drive',duration_seconds=float(seconds),duration_minutes=seconds/60,duration_nanoseconds=int(seconds*10**9),distance_meters=meters,status='ok',estimate_type='traffic_unaware')

class Acceptance(unittest.TestCase):
    def test_unsupported_radius_never_points_to_the_removed_control(self):
        model=SimpleNamespace(interpret=lambda _:Interpretation(activities=['bowling','dinner'],people=3,location='Washington, DC',budget_per_person=None,date=None,preferences=[]))
        result=interpret_request(InterpretationInput(text='Plan bowling and dinner near me within a radius of 5 miles on November 14, 2026 for 3 people.'),model)
        self.assertIsNone(result.request)
        self.assertTrue(any('Geographic radius' in issue for issue in result.issues))
        self.assertNotIn('Optional starting location',' '.join(result.issues))

    def test_exact_prompt_through_interpretation_and_source_grounding(self):
        model=SimpleNamespace(interpret=lambda _:Interpretation(activities=['bowling','dinner'],people=3,location='Washington, DC',budget_per_person=None,date=None,preferences=[]))
        for phrase,n,unit,mode,exclusive in [(PROMPT,20,'minutes','flexible',False),
             (PROMPT.replace('20 minutes','5 miles'),5,'miles','flexible',False),
             (PROMPT.replace("I'd prefer the first stop to be within 20 minutes of my starting point",'Keep the first stop under 20 minutes away'),20,'minutes','strict',True),
             (PROMPT.replace("I'd prefer the first stop to be within 20 minutes of my starting point",'Keep the first stop at most 20 minutes away'),20,'minutes','strict',False)]:
            result=interpret_request(InterpretationInput(text=phrase),model)
            self.assertIsNotNone(result.request,result.issues)
            p=result.request.firstTravel
            self.assertEqual((p.value,p.unit,p.mode,p.exclusive),(n,unit,mode,exclusive))
            self.assertEqual(str(result.request.date),'2026-11-14');self.assertEqual(result.request.people,3)
            self.assertEqual(result.request.activities,['bowling','food'])
            self.assertIsNone(result.request.maxLegTravel)
            if mode=='flexible':self.assertIsNone(result.request.maxFirstLegTravel)

    def test_precise_double_boundaries_and_strict_comparisons(self):
        preference=FirstTravel(value=20,mode='flexible')
        for seconds,rejected in [(2399,False),(2400,False),(2401,True)]:self.assertEqual(exceeds(leg(seconds=seconds),preference),rejected)
        self.assertEqual(effective_max(preference),40)
        self.assertTrue(exceeds(leg(seconds=1200),FirstTravel(value=20,exclusive=True)))
        self.assertFalse(exceeds(leg(seconds=1200),FirstTravel(value=20)))
        for meters,rejected in [(32186,False),(32187,True)]:self.assertEqual(exceeds(leg(meters=meters),FirstTravel(value=10,unit='miles',mode='flexible')),rejected)
        self.assertFalse(exceeds(leg(meters=201168),FirstTravel(value=62.5,unit='miles',mode='flexible')))
        self.assertTrue(exceeds(leg(meters=201169),FirstTravel(value=62.5,unit='miles',mode='flexible')))

    def test_region_diversity_uses_coverage_and_unsupported_labels_are_withheld(self):
        candidates=[DiscoveryCandidate(provider_id=f'Public_{i}',display_name=f'Invented public reference {i}',address='Synthetic DC',coordinates={'latitude':38.8+i*.05,'longitude':-77.0},types=['transit_station']) for i in range(3)]
        first=[SimpleNamespace(id=f'First_{i}') for i in range(6)];second=[SimpleNamespace(id='Dinner')]
        routes={}
        for i,p in enumerate(candidates):
            for j,v in enumerate(first):routes['reference_'+p.provider_id,v.id]=leg('reference_'+p.provider_id,v.id,600 if j//2==i else 2100 if j//2==(i+1)%3 else 2700)
        for v in first:routes[v.id,'Dinner']=leg(v.id,'Dinner',300)
        selected,diagnostics=compare(candidates,first,second,routes,FirstTravel(value=20,mode='flexible'))
        self.assertEqual(len(selected),3)
        self.assertTrue(all(len(r['valid'])==4 and len(r['preferred'])==2 for r in selected))
        self.assertEqual([p['place'].provider_id for p in selected],[p['place'].provider_id for p in compare(candidates,first,second,routes,FirstTravel(value=20,mode='flexible'))[0]])
        self.assertTrue(all(p['maximumCoverageOverlap']<.8 for p in diagnostics['selection']))
        for p in candidates:
            for v in first:routes['reference_'+p.provider_id,v.id]=leg('reference_'+p.provider_id,v.id,600)
        same,_=compare(candidates,first,second,routes,FirstTravel(value=20,mode='flexible'))
        self.assertEqual(len(same),1,'Identical venue coverage and travel does not manufacture three areas.')
        self.assertNotIn('Shorter',same[0]['label'])
        strict,_=compare(candidates,first,second,{},FirstTravel(value=1))
        self.assertEqual(strict,[])

    def test_provider_classification_requires_actual_evidence_and_never_echoes_payload(self):
        for operation,limit,boundary in [('search','SearchTextRequestPerDayPerProject','daily'),('search','SearchTextRequestPerMinutePerProject','minute'),('matrix','ComputeRouteMatrixElementsPerDayPerProject','daily'),('matrix','ComputeRouteMatrixElementsPerMinutePerProject','minute'),('details','GetPlaceRequestPerDayPerProject','daily')]:
            response=SimpleNamespace(status_code=429,json=lambda:{'error':{'message':'PRIVATE_RAW_RESPONSE','details':[{'reason':'RATE_LIMIT_EXCEEDED','metadata':{'quota_limit':limit,'private':'SECRET'}}]}})
            code,message,diagnostics=classify(response,operation)
            self.assertEqual(code,'quota');self.assertEqual(diagnostics['quotaBoundary'],boundary)
            self.assertNotIn('PRIVATE',message+json.dumps(diagnostics));self.assertNotIn('SECRET',message+json.dumps(diagnostics))
        code,message,info=classify(SimpleNamespace(status_code=429,json=lambda:{}),'matrix')
        self.assertEqual(info['quotaBoundary'],'unknown');self.assertNotIn('daily',message)
        self.assertIn('Routes',message)
        _,message,_=classify(SimpleNamespace(status_code=403,json=lambda:{'error':{'details':[{'reason':'BILLING_DISABLED'}]}}),'details')
        self.assertIn('billing disabled',message)

class Pipeline(unittest.TestCase):
    def setUp(self):fixture.LocationFirst.setUp(self)
    request=fixture.LocationFirst.request
    def test_complete_initial_double_range_and_continuation_keep_origin(self):
        def routes(body):
            result=fixture.matrix_fixture(body)
            for e in result:
                point=body['origins'][e['originIndex']]['waypoint']
                if 'location' in point:
                    j=e['destinationIndex'];e['duration']=f'{900 if j==0 else 2400 if j==1 else 2401}s'
            return result
        self.matrix.side_effect=routes
        from backend.real_planning import real_plans,more_real_plans
        from backend.provider_budget import ProviderBudget
        from backend.option_sessions import option_sessions
        result=real_plans(self.request(startingLocation=fixture.START,firstTravel={'value':20,'mode':'flexible'}),ProviderBudget())
        self.assertTrue(result.provisionalPlans,result.message)
        self.assertTrue(all(p.firstLeg['minutes']<=40 for p in result.provisionalPlans))
        self.assertTrue(any(p.firstLeg['exceedsPreference'] for p in result.provisionalPlans))
        context,_=option_sessions.get(result.optionsToken);origin=context['request'].startingLocation
        with patch('backend.development_cost.time',return_value=20000),patch('backend.provider_budget.monotonic',return_value=20000):
            more_real_plans(result.optionsToken)
        self.assertEqual(context['request'].startingLocation,origin)
        self.assertEqual(effective_max(context['request'].firstTravel),40)

    def test_manual_origin_anchors_include_the_preferred_activity_region(self):
        from backend.location_fixtures import acceptance_search_fixture,acceptance_matrix_fixture
        from backend.real_planning import real_plans
        from backend.provider_budget import ProviderBudget
        self.search.side_effect=acceptance_search_fixture;self.matrix.side_effect=acceptance_matrix_fixture
        start={**fixture.START,'point':{'id':'authorized-start','coordinates':{'latitude':38.91,'longitude':-77.02}}}
        result=real_plans(self.request(startingLocation=start,firstTravel={'value':25,'mode':'flexible'}),ProviderBudget())
        self.assertTrue(result.provisionalPlans,result.message)
        self.assertTrue(any(not p.firstLeg['exceedsPreference'] for p in result.provisionalPlans))
