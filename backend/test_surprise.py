"""Invented provider fixtures only, with the inherited fail-on-network guard."""
import os
import random
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from backend import test_location_first as fixture
from backend.real_planning import real_plans,more_real_plans
from backend.provider_budget import ProviderBudget
from backend.option_sessions import option_sessions
from backend.surprise import weighted,venue_order,select
from backend.location_policy import FirstTravel
from backend.between_policy import between_intent
from backend.interpretation import InterpretationInput,interpret_request
from backend.ai import Interpretation

class Selection(unittest.TestCase):
    def test_seeded_sampling_without_replacement_and_real_source_is_not_constant(self):
        values=list(range(20))
        a=weighted(values,lambda _:1,random.Random(7));b=weighted(values,lambda _:1,random.Random(7))
        self.assertEqual(a,b);self.assertEqual(len(set(a)),20)
        self.assertNotEqual(a,weighted(values,lambda _:1,random.Random(8)))
        with patch('backend.surprise.SystemRandom') as secure:
            secure.return_value.random.return_value=.5
            weighted(values,lambda _:1)
            secure.assert_called_once_with()

    def test_novel_ids_quality_weights_and_spatial_diversity(self):
        venues=[SimpleNamespace(id=str(i),activity='bowling',rating=4.5,ratingCount=100,relevanceStrength='strong',coordinates=SimpleNamespace(latitude=38.9+i*.01,longitude=-77.02)) for i in range(6)]
        order=venue_order(venues,{'0','1','2'},rng=random.Random(4))
        self.assertEqual({v.id for v in order[:3]},{'3','4','5'})
        self.assertEqual(len({v.id for v in order}),6)
        low=SimpleNamespace(id='low',score=.1,candidate=SimpleNamespace(id='low',venues=[venues[0]]))
        high=SimpleNamespace(id='high',score=.9,candidate=SimpleNamespace(id='high',venues=[venues[1]]),surpriseRepeated=False)
        self.assertEqual(select([low,high],1,{},rng=random.Random(1)),[high])

    def test_scoped_natural_preferences_do_not_swallow_total_or_first_limits(self):
        for phrase,value,unit,mode,exclusive in [
            ('under 10 minutes between activities',10,'minutes','strict',True),
            ('at most 10 minutes between stops',10,'minutes','strict',False),
            ("I'd prefer within 5 miles between venues",5,'miles','flexible',False),
            ('Prefer 10 minutes between activities',10,'minutes','flexible',False),
            ('between places around 10 minutes',10,'minutes','flexible',False),
        ]:
            p,spans,error=between_intent(phrase)
            self.assertIsNone(error);self.assertEqual((p.value,p.unit,p.mode,p.exclusive),(value,unit,mode,exclusive))
            self.assertTrue(spans)
        self.assertIsNone(between_intent('20 minutes total driving')[0])
        self.assertIsNone(between_intent('within 10 minutes of my hotel')[0])
        self.assertTrue(between_intent('under 5 miles between stops and under 10 minutes between venues')[2])

    def test_unseen_primary_priority_and_small_pool_repetition_are_explicit(self):
        venues=[SimpleNamespace(id=str(i),activity='bowling',rating=None,ratingCount=None,relevanceStrength='strong') for i in range(4)]
        plans=[SimpleNamespace(score=.8,candidate=SimpleNamespace(id=str(i),venues=[v]),surpriseRepeated=False) for i,v in enumerate(venues)]
        chosen=select(plans,3,{'usedPrimary':{'0'}},rng=random.Random(2))
        self.assertEqual({p.candidate.venues[0].id for p in chosen},{'1','2','3'})
        varied=select(plans,3,{'usedPrimary':{'0','1','2','3'}},rng=random.Random(2))
        self.assertEqual(len({p.candidate.venues[0].id for p in varied}),3)
        reused=select(plans[:1],3,{'usedPrimary':{'0'}},rng=random.Random(2))
        self.assertEqual(len(reused),1);self.assertTrue(reused[0].surpriseRepeated)

    def test_supported_low_rating_threshold_never_invents_missing_quality(self):
        def plan(identity,rating,count):
            venue=SimpleNamespace(id=identity,activity='bowling',rating=rating,ratingCount=count,relevanceStrength='strong')
            return SimpleNamespace(score=.8,candidate=SimpleNamespace(id=identity,venues=[venue]),surpriseRepeated=False)
        plans=[plan('low',2.9,10),plan('unknown',None,None),plan('small_sample',2.0,2),plan('supported',4.3,100)]
        chosen=select(plans,3,{},rng=random.Random(3))
        self.assertEqual({p.candidate.id for p in chosen},{'unknown','small_sample','supported'})

    def test_interpretation_pipeline_flexible_miles_and_strict_minutes(self):
        base='Plan bowling and dinner in Washington, DC on November 14, 2026 for 3 people. '
        for phrase,minutes,unit,mode in [('At most 10 minutes between stops.',10,'minutes','strict'),("I'd prefer within 5 miles between activities.",None,'miles','flexible')]:
            model=SimpleNamespace(interpret=lambda _:Interpretation(activities=['bowling','dinner'],location='Washington, DC',people=3,budget_per_person=None,date=None,preferences=[],travel_leg_minutes=minutes))
            result=interpret_request(InterpretationInput(text=base+phrase),model)
            self.assertIsNotNone(result.request,result.issues)
            self.assertEqual(result.request.betweenTravel.unit,unit)
            self.assertEqual(result.request.betweenTravel.mode,mode)
            self.assertIsNone(result.request.firstTravel)

class Pipeline(unittest.TestCase):
    def setUp(self):
        fixture.LocationFirst.setUp(self)
        self.random=random.Random(121)
        self.rng=patch('backend.surprise.SystemRandom',side_effect=lambda:self.random)
        self.rng.start();self.addCleanup(self.rng.stop)
    def request(self,**extra):
        return fixture.LocationFirst.request(self,startingLocation=None,planningMode='surprise',**extra)
    def test_surprise_sequential_no_landmarks_or_first_legs(self):
        result=real_plans(self.request(),ProviderBudget())
        self.assertEqual(len(result.provisionalPlans),3,result.message)
        self.assertTrue(all(p.firstLeg is None for p in result.provisionalPlans))
        self.assertTrue(all(not c.args[0]['textQuery'].startswith('public transit') for c in self.search.call_args_list))
        dinners=[c.args[0] for c in self.search.call_args_list if 'restaurant' in c.args[0]['textQuery']]
        self.assertGreaterEqual(len(dinners),2);self.assertLessEqual(len(dinners),3)
        self.assertNotEqual(dinners[0]['locationRestriction'],dinners[1]['locationRestriction'])
        for call in self.matrix.call_args_list:
            self.assertTrue(all('placeId' in row['waypoint'] for row in call.args[0]['origins']))
            self.assertTrue(all('reference_' not in row['waypoint']['placeId'] for row in call.args[0]['origins']))
        self.assertEqual(result.request.location,'Washington, DC')
        self.assertEqual(result.request.planningMode,'surprise')

    def test_multiple_activity_regions_survive_initial_downstream_shortlist(self):
        from backend.location_fixtures import acceptance_search_fixture,acceptance_matrix_fixture
        self.search.side_effect=acceptance_search_fixture;self.matrix.side_effect=acceptance_matrix_fixture
        result=real_plans(self.request(betweenTravel={'value':10,'mode':'strict'}),ProviderBudget())
        self.assertEqual(len(result.provisionalPlans),3,result.message)
        primaries=[p.candidate.venues[0].id for p in result.provisionalPlans]
        self.assertEqual(len(set(primaries)),3)
        self.assertGreaterEqual(len({int(identity.rsplit('_',1)[1])%3 for identity in primaries}),2)
        self.assertTrue(all(p.totalTravel==4 for p in result.provisionalPlans))

    def test_first_constraint_origin_and_near_me_conflicts_fail_before_requests(self):
        for extra in [{'firstTravel':{'value':20}}, {'maxFirstLegTravel':20}, {'currentArea':{'coordinates':{'latitude':0,'longitude':0}}}]:
            with self.assertRaisesRegex(Exception,'first activity'):real_plans(self.request(**extra),ProviderBudget())
        with self.assertRaisesRegex(Exception,'destination city'):
            real_plans(self.request().model_copy(update={'location':'near me'}),ProviderBudget())
        self.assertEqual(self.search.call_count,0)

    def test_precise_between_minutes_miles_and_total_remain_separate(self):
        def response(seconds,meters):
            def run(body):
                return [dict(row,duration=seconds,distanceMeters=meters) for row in fixture.matrix_fixture(body)]
            return run
        for preference,seconds,meters,accepted in [
            ({'value':10,'mode':'flexible'},'1200s',1000,True),
            ({'value':10,'mode':'flexible'},'1200.000000001s',1000,False),
            ({'value':10,'mode':'strict','exclusive':True},'600s',1000,False),
            ({'value':10,'mode':'strict'},'600s',1000,True),
            ({'value':5,'unit':'miles','mode':'flexible'},'30s',16093,True),
            ({'value':5,'unit':'miles','mode':'flexible'},'30s',16094,False),
            ({'value':62.5,'unit':'miles','mode':'flexible'},'30s',201168,True),
            ({'value':62.5,'unit':'miles','mode':'flexible'},'30s',201169,False),
        ]:
            with self.subTest(preference=preference,seconds=seconds):
                self.matrix.side_effect=response(seconds,meters)
                with patch('backend.development_cost.time',return_value=20000+self.matrix.call_count*100):
                    result=real_plans(self.request(betweenTravel=preference),ProviderBudget())
                self.assertEqual(bool(result.provisionalPlans),accepted,result.message)
                if accepted and preference['mode']=='flexible':
                    self.assertTrue(any(i.code=='extra_between_travel' for i in result.provisionalPlans[0].issues))
        self.matrix.side_effect=response('601s',100)
        with patch('backend.development_cost.time',return_value=30000):
            result=real_plans(self.request(betweenTravel={'value':10,'mode':'flexible'},travel=10),ProviderBudget())
        self.assertFalse(result.provisionalPlans)

    def test_three_four_repeated_activities_and_normal_budget(self):
        for activities in [['bowling','food','coffee'],['bowling','food','coffee','museum'],['bowling','food','bowling']]:
            with patch.dict(os.environ,{'WHERETO_EXPLORATION_DEV':'0'}):
                result=real_plans(self.request(activities=activities),ProviderBudget())
            self.assertTrue(result.provisionalPlans,result.message)
            self.assertTrue(all([v.activity for v in p.candidate.venues]==activities for p in result.provisionalPlans))
            self.assertLessEqual(result.diagnostics['placesSearchRequests'],10)
            self.assertLessEqual(result.diagnostics['matrixElements'],300)

    def test_fifteen_continuations_report_actual_primary_and_full_uniqueness(self):
        session=ProviderBudget();seen=set();first=set();usage=[]
        for action in range(16):
            with patch('backend.development_cost.time',return_value=20000+action*100),patch('backend.provider_budget.monotonic',return_value=20000+action*100):
                result=real_plans(self.request(),session) if not action else more_real_plans(token,expand_discovery=action==1)
            token=result.optionsToken
            self.assertEqual(len(result.provisionalPlans),3,(action,result.message))
            for plan in result.provisionalPlans:
                signature=tuple(v.id for v in plan.candidate.venues)
                self.assertNotIn(signature,seen);seen.add(signature);first.add(signature[0])
            context,_=option_sessions.get(token)
            usage.append(context['outing'].usage()['providerAttempts'])
            self.assertLessEqual(context.get('actionDiscoveryCalls',0),8 if not action else 2)
            self.assertLessEqual(context.get('actionRouteStages',0),2)
        eligible=len(context['positionIds'][0])
        self.assertEqual(len(seen),48)
        self.assertGreaterEqual(len(first),10)
        self.assertLessEqual(len(first),eligible)
        self.assertEqual(usage,sorted(usage))
        print('SURPRISE_FIXTURE_SUMMARY',{'actions':16,'eligibleFirstPool':eligible,'firstVenueUniqueness':len(first),'completeItineraryUniqueness':len(seen),'searches':context['outing'].usage()['placesSearchRequests'],'routeElements':context['outing'].usage()['reservedMatrixElements']})

    def test_exhausted_expired_and_quota_sessions_no_retry(self):
        result=real_plans(self.request(),ProviderBudget());token=result.optionsToken
        context,_=option_sessions.get(token)
        self.search.side_effect=fixture.DiscoveryError('quota','Places daily quota fixture')
        before=self.search.call_count
        with self.assertRaisesRegex(Exception,'daily quota'):more_real_plans(token,expand_discovery=True)
        self.assertEqual(self.search.call_count,before+1)
        self.assertEqual(len(result.provisionalPlans),3)
        self.assertTrue(context['stopped'])
        with self.assertRaisesRegex(Exception,'earlier provider'):more_real_plans(token)
        option_sessions.entries.clear()
        with self.assertRaisesRegex(Exception,'expired'):more_real_plans(token)

    def test_hard_geography_and_known_limits_precede_random_output(self):
        result=real_plans(self.request(geography={'strictDestination':True,'excludedRegions':['VA']}),ProviderBudget())
        self.assertTrue(result.provisionalPlans,result.message)
        self.assertTrue(all(', Washington, DC' in v.address for p in result.provisionalPlans for v in p.candidate.venues))
        self.assertTrue(all('Synthetic_unsupported_arcade'!=v.id for p in result.provisionalPlans for v in p.candidate.venues))

    def test_local_cost_guard_fails_closed_during_surprise_discovery(self):
        with patch.dict(os.environ,{'WHERETO_DEV_DAILY_USD':'0.04','WHERETO_DEV_WARN_USD':'0.04'}):
            result=real_plans(self.request(),ProviderBudget())
        self.assertTrue(result.provisionalPlans)
        self.assertGreater(result.diagnostics['estimatedDayGrossUsd'],.04)
        self.assertTrue(result.diagnostics['estimatedUsageWarning'])
        self.assertGreater(self.search.call_count,1)

    def test_missing_route_evidence_and_tiny_pool_never_add_filler(self):
        self.matrix.side_effect=lambda body:[]
        result=real_plans(self.request(),ProviderBudget())
        self.assertTrue(result.provisionalPlans)
        self.assertTrue(all(p.travelClassification=="unverified" and p.totalTravel is None for p in result.provisionalPlans))
        self.matrix.side_effect=fixture.matrix_fixture
        from backend.location_fixtures import spatial_search_fixture
        def tiny(body,**kwargs):
            found=spatial_search_fixture(body,**kwargs);found['places']=found['places'][:1];found.pop('nextPageToken',None);return found
        self.search.side_effect=tiny
        with patch('backend.development_cost.time',return_value=20000):
            result=real_plans(self.request(),ProviderBudget())
        self.assertEqual(len(result.provisionalPlans),1,result.message)

if __name__=='__main__':unittest.main()
