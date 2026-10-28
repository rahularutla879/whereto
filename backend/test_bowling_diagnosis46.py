"""Reproduce missing bowling variety with invented providers. No live access."""
import json
import os
import unittest
from unittest.mock import patch
from backend.places import DiscoveryRequest, SearchArea, search_body
from backend.provider_budget import ProviderBudget
from backend.real_planning import PlannerInput, real_plans, more_real_plans
from backend.real_fixtures import bowling_diagnostic_fixture, search_fixture, matrix_fixture, paginated_search_fixture
from backend.test_real_planning import ENV
from backend.option_sessions import option_sessions
from backend.venue_quality import assess_candidates
from backend.test_venue_quality import venue


class BowlingDiagnosis(unittest.TestCase):
    def setUp(self):
        for p in (patch.dict(os.environ,{**ENV,'WHERETO_RATINGS_DEV':'1'},clear=True),
                  patch('requests.sessions.Session.send',side_effect=AssertionError('No provider sends'))):
            p.start();self.addCleanup(p.stop)
        self.search = patch('backend.places_transport.text_search',side_effect=bowling_diagnostic_fixture).start()
        self.matrix = patch('backend.routes_transport.compute_matrix',side_effect=matrix_fixture).start()
        self.clock = patch('backend.provider_budget.monotonic',return_value=1000).start()
        self.addCleanup(patch.stopall);self.addCleanup(option_sessions.entries.clear)

    def request(self, **extra):
        extra.setdefault("startingLocation",{"point":{"id":"authorized-start","place_id":"Fixture_origin_0"},"explicitly_authorized":True,"source":"manual"})
        return PlannerInput(activities=['bowling','food'],location='Washington, DC',date='2026-11-14',people=3,dinner=True,transport='driving',**extra)

    def test_same_area_refinement_escapes_type_filter_not_geography_or_relevance(self):
        area=SearchArea(name='Washington, DC')
        strict=search_body(DiscoveryRequest(activity='bowling',destination=area),10)
        expanded=search_body(DiscoveryRequest(activity='bowling',destination=area,search_variant='alternative'),10)
        self.assertEqual((strict['textQuery'],expanded['textQuery']),('bowling alleys in Washington, DC','bowling centers in Washington, DC'))
        self.assertEqual(strict['includedType'],'bowling_alley');self.assertTrue(strict['strictTypeFiltering'])
        self.assertNotIn('includedType',expanded);self.assertNotIn('strictTypeFiltering',expanded)
        self.assertEqual(strict['locationBias'],expanded['locationBias'])
        self.assertEqual(strict['pageSize'],10);self.assertEqual(expanded['pageSize'],10)

    def test_complete_funnel_supported_multi_activity_and_one_known_travel_failure(self):
        def routes(body):
            data=matrix_fixture(body)
            for e in data:
                if body['origins'][e['originIndex']]['waypoint']['placeId']=='Fixture_bowling_5':e['duration']='900s'
            return data
        self.matrix.side_effect=routes
        session=ProviderBudget();r=real_plans(self.request(maxLegTravel=5),session)
        initial=r.diagnostics['venuePipeline']['bowling']
        self.assertEqual((initial['googleResultsReceived'],initial['eligibleRetained'],initial['rankedVenues']),(2,2,2))
        context,_=option_sessions.get(r.optionsToken);budget=context['outing']
        r=more_real_plans(r.optionsToken,expand_discovery=True)
        row=r.diagnostics['venuePipeline']['bowling']
        self.assertEqual((row['googleResultsReceived'],row['geographyRejected'],row['duplicatesRemoved'],row['relevanceRejected'],row['eligibleRetained']),(11,1,3,1,6))
        self.assertEqual(row['geographyReasons'],{'different_named_area_or_region':1})
        self.assertEqual(row['relevanceRejectedByReason'],{'arcade_without_bowling_evidence':1})
        self.assertEqual(row['latestSearch'],{'newEligibleMatches':4,'previouslyKnownMatches':2,'newlyRetained':4})
        self.assertEqual((row['shortlistedForRouting'],row['selectedForRouting'],row['excludedByCheckedRouteFeasibility'],row['routeCompatibleVenues'],row['rankedVenues']),(6,6,1,5,5))
        self.assertEqual(row['unusedRankedVenues'],5)
        self.assertTrue(any('5 represented in ranking; 5 in unused ranked options' in n for n in r.notes))
        self.assertTrue(any('arcades without bowling evidence' in n for n in r.notes))
        self.assertEqual(row['searchStrategies'],{'bowling_strict_type':1,'bowling_text_evidence':1})
        self.assertEqual(row['requestedPageSize'],10);self.assertEqual(row['geographyPolicy'],'verified_named_area')
        self.assertEqual(r.diagnostics['configuredLimits'],{'candidatesPerActivity':100,'searchesPerOuting':10,'matrixElementsPerOuting':300})
        self.assertTrue(any('Latest backend coverage — bowling: 11 Google results' in n for n in r.notes))
        ids={v.facts.id for v in context['discovery'].venues if 'bowling' in v.activities}
        self.assertTrue({'Fixture_bowling_2','Fixture_bowling_3'}<=ids)
        self.assertFalse({'Fixture_bowling_6','Fixture_bowling_7'} & ids)
        self.assertIs(context['outing'],budget)
        self.assertEqual(budget.usage()['placesSearchRequests'],4)
        self.assertLessEqual(budget.usage()['reservedMatrixElements'],150)
        self.assertTrue(all(p.totalTravel<=5 and p.candidate.venues[0].id!='Fixture_bowling_5' for p in r.provisionalPlans))
        for private in ('Fixture_','Synthetic','Washington','Arlington','latitude','longitude','pageToken','textQuery'):
            self.assertNotIn(private,json.dumps(r.diagnostics))

    def test_primary_shortage_expands_even_when_two_venues_make_three_plans(self):
        def searches(body):
            data=search_fixture(body)
            for p in data['places']:p.update(rating=4.5,userRatingCount=200)
            return data
        def routes(body):
            data=matrix_fixture(body)
            for e in data:
                a=body['origins'][e['originIndex']]['waypoint']['placeId']
                e['duration']='600s' if a in {f'Fixture_bowling_{n}' for n in (2,3,4,5)} else '120s'
            return data
        self.search.side_effect=searches;self.matrix.side_effect=routes
        r=real_plans(self.request(maxLegTravel=5),ProviderBudget())
        self.assertTrue(r.diagnostics['primaryCoverageExpansion'])
        self.assertEqual(r.diagnostics['shortlistedCounts'],[10,10])
        self.assertEqual(r.diagnostics['venuePipeline']['bowling']['routeCompatibleVenues'],6)
        self.assertEqual(r.diagnostics['venuePipeline']['bowling']['excludedByCheckedRouteFeasibility'],4)
        self.assertEqual(len({p.candidate.venues[0].id for p in r.provisionalPlans}),3)
        self.assertTrue(any(p.candidate.venues[0].id not in {'Fixture_bowling_0','Fixture_bowling_1'} for p in r.provisionalPlans))
        self.assertEqual(self.search.call_count,2)
        self.assertLessEqual(r.diagnostics['matrixElements'],150)

    def test_unfiltered_refinement_does_not_admit_a_generic_entertainment_center(self):
        def search(body):
            if body.get('strictTypeFiltering'):return bowling_diagnostic_fixture(body)
            data=bowling_diagnostic_fixture(body)
            if body['textQuery'].startswith('bowling'):
                p=data['places'][2]
                p.update(displayName={'text':'Synthetic Family Fun Center'},types=['amusement_center'],primaryType='amusement_center')
                data['places']=[p]
            return data
        self.search.side_effect=search
        r=real_plans(self.request(),ProviderBudget())
        r=more_real_plans(r.optionsToken,expand_discovery=True)
        row=r.diagnostics['venuePipeline']['bowling']
        self.assertEqual(row['eligibleRetained'],2)
        self.assertEqual(row['relevanceRejectedByReason'],{'activity_evidence_required':1})
        self.assertEqual(row['latestSearch']['newEligibleMatches'],0)

    def test_absolute_rating_scale_preserves_other_eligible_primary_venues(self):
        def searches(body):
            data=search_fixture(body)
            for i,p in enumerate(data['places']):
                p.update(rating=5.0 if 'bowling' in body['textQuery'] and i<2 else 4.0,userRatingCount=1000)
            return data
        def routes(body):
            data=matrix_fixture(body)
            for e in data:e['duration']='120s'
            return data
        self.search.side_effect=searches;self.matrix.side_effect=routes
        r=real_plans(self.request(),ProviderBudget())
        row=r.diagnostics['venuePipeline']['bowling']
        self.assertEqual((row['eligibleRetained'],row['routeCompatibleVenues'],row['rankedVenues']),(10,6,6))
        self.assertEqual(row['withinBestScoreWindow'],6)
        self.assertEqual(row['selectedVenues'],3)
        self.assertEqual(row['excludedByCheckedRouteFeasibility'],0)

    def test_duplicate_rejected_arcades_are_in_dedup_counts(self):
        wrong=venue(name='Synthetic Arcade',types=['video_arcade'])
        result=assess_candidates([wrong,wrong])
        self.assertFalse(result.venues)
        self.assertEqual(result.diagnostics['duplicate_place_id'],1)
        self.assertEqual(result.stages['bowling']['duplicatesRemoved'],1)
        self.assertEqual(result.stages['bowling']['relevanceRejectedByReason'],{'arcade_without_bowling_evidence':1})

    def test_one_multi_activity_venue_is_not_two_visits_or_a_routing_attempt(self):
        def search(body):
            p=bowling_diagnostic_fixture(body)['places'][0]
            p.update(id='Only_Synthetic_Venue',displayName={'text':'Synthetic Bowling Restaurant'},types=['bowling_alley','restaurant'])
            return {'places':[p]}
        self.search.side_effect=search
        r=real_plans(self.request(),ProviderBudget())
        self.assertFalse(r.provisionalPlans)
        self.assertIn('distinct real venues',r.message)
        for row in r.diagnostics['venuePipeline'].values():
            self.assertEqual((row['eligibleRetained'],row['shortlistedForRouting'],row['selectedForRouting']),(1,1,0))
        self.matrix.assert_not_called()

    def test_checked_unknown_routes_are_not_counted_as_excluded_or_compatible(self):
        self.matrix.side_effect=lambda body:[]
        r=real_plans(self.request(maxLegTravel=5),ProviderBudget())
        row=r.diagnostics['venuePipeline']['bowling']
        self.assertEqual(row['routeCompatibleVenues'],0)
        self.assertEqual(row['excludedByCheckedRouteFeasibility'],0)
        self.assertEqual(row['routeUnverifiedVenues'],2)

    def test_repeated_actions_have_no_repeated_outings_or_fresh_budgets(self):
        r=real_plans(self.request(),ProviderBudget());context,_=option_sessions.get(r.optionsToken)
        budget=context['outing'];seen=set();primaries=set()
        def collect(response):
            for batch in [response.provisionalPlans,*response.alternativeBatches]:
                for p in batch:
                    self.assertNotIn(p.candidate.id,seen);seen.add(p.candidate.id);primaries.add(p.candidate.venues[0].id)
        collect(r)
        while r.canDiscover:
            r=more_real_plans(r.optionsToken,expand_discovery=True);collect(r)
        for _ in range(20):
            if not r.canExpand:break
            r=more_real_plans(r.optionsToken);collect(r)
        self.assertGreaterEqual(len(primaries),5)
        self.assertEqual(context['outing'],budget)
        self.assertEqual(self.search.call_count,4)
        self.assertLessEqual(budget.usage()['reservedMatrixElements'],300)
        self.assertLessEqual(budget.usage()['providerAttempts'],30)
        for call in self.search.call_args_list:self.assertIn('Washington, DC',call.args[0]['textQuery'])

    def test_twenty_relevant_candidates_retained_and_provider_pages_not_repeated(self):
        self.search.side_effect=paginated_search_fixture
        r=real_plans(self.request(),ProviderBudget())
        r=more_real_plans(r.optionsToken,expand_discovery=True)
        self.assertEqual(r.diagnostics['venuePipeline']['bowling']['eligibleRetained'],20)
        self.assertEqual(r.diagnostics['venuePipeline']['bowling']['latestSearch']['newEligibleMatches'],10)
        requests=[json.dumps(c.args[0],sort_keys=True) for c in self.search.call_args_list]
        self.assertEqual(len(requests),len(set(requests)))
