"""Consolidated improvements: invented Google fixtures, network forbidden."""
import os
import unittest
from unittest.mock import patch
from pydantic import ValidationError
from backend.real_planning import real_plans, more_real_plans
from backend.test_real_planning import outing, ENV
from backend.real_fixtures import search_fixture, matrix_fixture
from backend.provider_budget import ProviderBudget, ProviderSettings, ProviderLimitError
from backend.starting_places import StartingPlaceQuery, lookup_starting_places
from backend.places import DiscoveryError, SearchArea, parse_response
from backend.option_sessions import option_sessions
from backend.places_transport import text_search as transport_search


class ImprovementTests(unittest.TestCase):
    def setUp(self):
        self.stack = []
        for p in (patch.dict(os.environ, {**ENV, 'WHERETO_START_LOOKUP_DEV': '1', 'WHERETO_RATINGS_DEV': '1'}, clear=True),
                  patch('requests.sessions.Session.send', side_effect=AssertionError('No live requests'))):
            p.start(); self.addCleanup(p.stop)
        self.search = patch('backend.places_transport.text_search', side_effect=search_fixture).start()
        self.matrix = patch('backend.routes_transport.compute_matrix', side_effect=matrix_fixture).start()
        self.addCleanup(patch.stopall)
        self.addCleanup(option_sessions.entries.clear)
        self.session = ProviderBudget()

    def test_approved_defaults_and_validated_configuration(self):
        s = self.session.settings
        self.assertEqual((s.candidates_per_activity, s.matrix_elements_per_outing, s.matrix_elements_per_session, s.matrix_elements_per_minute), (100, 300, 1500, 150))
        self.assertEqual((s.requests_per_session, s.requests_per_outing, s.details_per_outing, s.retries), (50, 30, 6, 0))
        with patch.dict(os.environ, {'WHERETO_CANDIDATES': '7', 'WHERETO_MATRIX_OUTING': '80'}):
            settings = ProviderSettings.from_env()
            self.assertEqual((settings.candidates_per_activity, settings.matrix_elements_per_outing), (7,80))
        for field, value in [('candidates_per_activity',101), ('matrix_elements_per_outing',301), ('matrix_elements_per_session',1501), ('matrix_elements_per_minute',151)]:
            with self.assertRaises(ValidationError): ProviderSettings(**{field:value})

    def test_ten_discovered_but_initial_routing_not_all_to_all(self):
        result = real_plans(outing(), self.session)
        self.assertEqual(result.diagnostics['discoveredCounts'], [10,10])
        self.assertEqual(result.diagnostics['shortlistedCounts'], [6,6])
        self.assertEqual(result.diagnostics['matrixElements'],42)
        self.assertTrue(all(c.args[0]['pageSize']==10 for c in self.search.call_args_list))
        self.assertEqual(len({p.candidate.venues[0].id for p in result.provisionalPlans}),3)
        self.assertTrue(all(p.stops[0].venue.ratingCount is not None for p in result.provisionalPlans))
        self.assertNotIn('"latitude":', result.model_dump_json())

    def test_arcade_false_positive_never_reaches_bowling_itineraries(self):
        def response(body):
            data = search_fixture(body)
            if body['textQuery'].startswith('bowling'):
                candidate = data['places'][0]
                candidate.update(displayName={'text': 'Example Racing Arcade'},
                                 types=['video_arcade', 'bar'], primaryType='video_arcade')
            return data
        self.search.side_effect = response
        result = real_plans(outing(), self.session)
        self.assertEqual(result.diagnostics['discoveredCounts'], [9, 10])
        self.assertEqual(result.diagnostics['matrixElements'], 42)
        self.assertEqual(self.search.call_count, 2)
        for plan in result.provisionalPlans:
            self.assertNotEqual(plan.stops[0].venue.name, 'Example Racing Arcade')
        self.assertTrue(self.search.call_args_list[0].args[0]['strictTypeFiltering'])

    def test_alternatives_do_not_repeat_and_expansion_reuses_routes_and_budget(self):
        result=real_plans(outing(maxLegTravel=10,budget=0),self.session)
        token=result.optionsToken
        seen=set(); widths=[]; counts=[]
        for _ in range(40):
            for p in result.provisionalPlans + [p for batch in result.alternativeBatches for p in batch]:
                identity=tuple(v.id for v in p.candidate.venues)
                self.assertNotIn(identity,seen);seen.add(identity)
                self.assertLessEqual(p.totalTravel,10)
                self.assertTrue(any(i.code=='unverified_budget' for i in p.issues))
            widths.append(result.diagnostics.get('shortlistedCounts'))
            counts.append(result.diagnostics.get('matrixElements'))
            if not result.canExpand:break
            result=more_real_plans(token)
        self.assertGreater(len(seen),9)
        self.assertIn([10,10],widths)
        self.assertIn(106,counts)
        self.assertEqual(self.search.call_count,2)
        self.assertEqual(self.session._elements,110)
        self.assertLessEqual(self.session._requests,20)

    def test_three_four_stop_and_separate_start_under_150(self):
        for activities, expected in [(['bowling','food','museum'],36),(['bowling','food','museum','coffee'],52)]:
            with self.subTest(activities=activities):
                session=ProviderBudget()
                result=real_plans(outing(activities=activities,startingLocation={'point':{'id':'origin','place_id':'Fixture_start'},'explicitly_authorized':True,'precision':'postal_area'},maxFirstLegTravel=10),session)
                self.assertEqual(result.diagnostics['matrixElements'],expected)
                self.assertTrue(all(p.firstLeg['approximate'] for p in result.provisionalPlans))
                self.assertTrue(all([v.activity.value for v in p.candidate.venues]==activities for p in result.provisionalPlans))

    def test_repeated_activities_ids_and_direction_are_preserved(self):
        result=real_plans(outing(activities=['bowling','food','bowling']),self.session)
        self.assertEqual(self.search.call_count,2)
        for p in result.provisionalPlans:
            self.assertEqual(len({v.id for v in p.candidate.venues}),3)
            self.assertEqual([(e['route']['origin_id'],e['route']['destination_id']) for e in p.routeEvidence],[(p.stops[0].venue.id,p.stops[1].venue.id),(p.stops[1].venue.id,p.stops[2].venue.id)])
        self.assertFalse(real_plans(outing(maxLegTravel=0),ProviderBudget()).provisionalPlans)

    def test_failed_expansion_cannot_reset_or_retry_budget(self):
        result=real_plans(outing(),self.session)
        for _ in range(40):
            if result.diagnostics.get('shortlistedCounts')==[10,10]: break
            # Eventually require new route evidence; fail that attempt.
            self.matrix.side_effect=__import__('backend.routes',fromlist=['RouteError']).RouteError('quota','Quota unavailable')
            result=more_real_plans(result.optionsToken)
        self.assertFalse(result.canExpand)
        self.assertTrue(any(i.code == "route_provider_quota" for p in result.provisionalPlans for i in p.issues))
        count=self.matrix.call_count
        with self.assertRaisesRegex(DiscoveryError,'stopped'):more_real_plans(result.optionsToken)
        self.assertEqual(self.matrix.call_count,count)

    def test_starting_search_exact_and_approximate_confirmation_candidates(self):
        def response(body, **kwargs):
            self.assertEqual(body['pageSize'],3)
            self.assertNotIn('rating',kwargs['field_mask'])
            result=search_fixture({'textQuery':'cafes in Baltimore','pageSize':3})
            for p,t in zip(result['places'],['street_address','postal_code','neighborhood']):p['types']=[t]
            return result
        self.search.side_effect=response
        result=lookup_starting_places(StartingPlaceQuery(query='A synthetic address'),self.session)
        self.assertEqual([m['precision'] for m in result['matches']],['address_or_place','postal_area','neighborhood'])
        self.assertEqual(self.session._requests,1)
        self.assertTrue(all(m['attributions'] for m in result['matches']))
        self.assertEqual(self.session._lookups,1)
        self.matrix.assert_not_called()

    def test_lookup_gates_invalid_data_and_session_limits(self):
        for query in ['', 'ab', 'a\nb', 'x'*201]:
            with self.assertRaises(ValidationError):StartingPlaceQuery(query=query)
        with patch.dict(os.environ,{'WHERETO_START_LOOKUP_DEV':'0'}):
            with self.assertRaisesRegex(DiscoveryError,'disabled'):lookup_starting_places(StartingPlaceQuery(query='Baltimore'),self.session)
        self.search.assert_not_called()
        self.search.return_value={'places':[{}]};self.search.side_effect=None
        with self.assertRaises(DiscoveryError):lookup_starting_places(StartingPlaceQuery(query='Baltimore'),self.session)
        self.assertEqual(self.session._requests,1)
        with self.assertRaises(ProviderLimitError):lookup_starting_places(StartingPlaceQuery(query='Baltimore'),ProviderBudget(ProviderSettings(mode='real',requests_per_session=0)))

    def test_confidence_aware_rating_ranking_missing_ratings_and_relevance(self):
        def supplied(body):
            result=search_fixture(body)
            for i,p in enumerate(result['places']):
                p['rating'],p['userRatingCount']=(5.0,1) if i==0 else (4.5,1000)
            return result
        self.search.side_effect=supplied
        result=real_plans(outing(activities=['bowling'],cost='experience'),self.session)
        self.assertNotEqual(result.provisionalPlans[0].stops[0].venue.id,'Fixture_bowling_0')
        self.search.side_effect=lambda body: {'places':[dict(p,rating=None,userRatingCount=None) for p in search_fixture(body)['places']]}
        result=real_plans(outing(),ProviderBudget())
        self.assertTrue(result.provisionalPlans)
        self.assertTrue(all(p.stops[0].venue.rating is None for p in result.provisionalPlans))

    def test_missing_and_invalid_ratings_not_zero(self):
        place=search_fixture({'textQuery':'bowling alleys in Baltimore','pageSize':1})['places'][0]
        place['rating']=0
        with self.assertRaises(DiscoveryError):parse_response({'places':[place]},SearchArea(name='Baltimore'),10)

    def test_bounded_expansion_finds_routes_outside_initial_shortlist(self):
        def routed(body):
            values=matrix_fixture(body)
            for e in values:
                a=body['origins'][e['originIndex']]['waypoint']['placeId']
                b=body['destinations'][e['destinationIndex']]['waypoint']['placeId']
                e['duration']='120s' if a.endswith('_9') or b.endswith('_9') else '600s'
            return values
        self.matrix.side_effect=routed
        result=real_plans(outing(maxLegTravel=3),self.session)
        self.assertEqual(len(result.provisionalPlans),3)
        self.assertEqual(result.diagnostics['shortlistedCounts'],[10,10])
        self.assertEqual(result.diagnostics['matrixElements'],106)
        self.assertTrue(all(p.totalTravel<=3 for p in result.provisionalPlans))
        self.assertEqual(self.search.call_count,2)

    def test_ratings_mask_requires_explicit_local_gate_and_lookup_stays_pro(self):
        from unittest.mock import Mock
        from backend.places import FIELD_MASK
        response=Mock(status_code=200);response.json.return_value={'places':[]}
        with patch('backend.places_transport.access_token',return_value='synthetic'), patch('requests.Session.post',return_value=response) as post:
            transport_search({'textQuery':'synthetic'})
            mask=post.call_args.kwargs['headers']['X-Goog-FieldMask']
            self.assertEqual(mask,FIELD_MASK+',places.rating,places.userRatingCount,places.containingPlaces')
            self.assertNotIn('review',mask.lower())
            transport_search({'textQuery':'synthetic'},field_mask=FIELD_MASK)
            self.assertEqual(post.call_args.kwargs['headers']['X-Goog-FieldMask'],FIELD_MASK)
            with patch.dict(os.environ,{'WHERETO_RATINGS_DEV':'0'}):
                transport_search({'textQuery':'synthetic'})
                self.assertEqual(post.call_args.kwargs['headers']['X-Goog-FieldMask'],FIELD_MASK+',places.containingPlaces')
                with self.assertRaises(DiscoveryError): transport_search({},field_mask=FIELD_MASK+',places.rating,places.userRatingCount')
        with self.assertRaises(DiscoveryError):transport_search({},field_mask='*')

    def test_continuation_expiry_and_overlap_refuse_without_provider_calls(self):
        result=real_plans(outing(),self.session)
        context,lock=option_sessions.get(result.optionsToken)
        searches,routes=self.search.call_count,self.matrix.call_count
        lock.acquire()
        try:
            with self.assertRaisesRegex(DiscoveryError,'running'):more_real_plans(result.optionsToken)
        finally:lock.release()
        option_sessions.expire(result.optionsToken)
        with self.assertRaisesRegex(DiscoveryError,'expired'):more_real_plans(result.optionsToken)
        self.assertEqual((self.search.call_count,self.matrix.call_count),(searches,routes))

    def test_shortlisting_considers_the_rest_of_the_sequence(self):
        from types import SimpleNamespace
        from backend.venue_models import Coordinates
        from backend.routing_shortlist import shortlist
        def point(identity, latitude, longitude):
            return SimpleNamespace(id=identity,relevanceStrength='strong'), SimpleNamespace(coordinates=Coordinates(latitude=latitude,longitude=longitude))
        a,af=point('A',0.0,0.0)
        b,bf=point('Near_first',0.001,0.0)
        c,cf=point('Along_full_path',0.0,0.010)
        d,df=point('Final',0.0,0.011)
        selected=shortlist([[a],[b,c],[d]],{'A':af,b.id:bf,c.id:cf,d.id:df},1)
        self.assertEqual(selected[1][0].id,'Along_full_path')

    def test_expanded_discovery_still_excludes_geography_duplicates_and_mismatches(self):
        from copy import deepcopy
        def supplied(body):
            result=search_fixture(body)
            result['places'][1]=deepcopy(result['places'][0])
            result['places'][2]['displayName']['text']='Synthetic Dental Clinic'
            result['places'][2]['types']=['dentist']
            result['places'][3]['addressComponents'][0]['longText']='Unrelated City'
            result['places'][3]['addressComponents'][0]['shortText']='Unrelated City'
            return result
        self.search.side_effect=supplied
        result=real_plans(outing(),self.session)
        self.assertEqual(result.diagnostics['discoveredCounts'],[7,7])
        self.assertGreater(result.diagnostics['excludedCandidates'],0)
        self.assertTrue(all('Dental' not in stop.venue.name for p in result.provisionalPlans for stop in p.stops))
        self.assertEqual(self.search.call_count,2)

    def test_options_revalidate_calendar_before_any_new_routing(self):
        result=real_plans(outing(),self.session)
        calls=self.matrix.call_count
        with patch('backend.location_context.outing_problem',return_value=('outing_date_expired','The outing date or time has passed.')):
            with self.assertRaisesRegex(DiscoveryError,'date or time'):more_real_plans(result.optionsToken)
        self.assertEqual(self.matrix.call_count,calls)

    def test_legacy_total_stop_diversity_can_repeat_primary_despite_competitive_alternatives(self):
        from backend.ranking import _select
        def supplied(body):
            result=search_fixture({**body,'pageSize':3})
            for place in result['places']:
                place.pop('rating',None);place.pop('userRatingCount',None)
            return result
        def routed(body):
            values=matrix_fixture(body)
            for e in values:
                a=body['origins'][e['originIndex']]['waypoint']['placeId']
                b=body['destinations'][e['destinationIndex']]['waypoint']['placeId']
                e['duration']='120s'
                if not (a.endswith('_0') or b.endswith('_0')):e['condition']='ROUTE_NOT_FOUND'
            return values
        self.search.side_effect=supplied;self.matrix.side_effect=routed
        from backend.ranking import score_candidates
        captured=[]
        def capture(request,plans):
            ranked=score_candidates(request,plans);captured.extend(ranked)
            return ranked
        with patch('backend.real_planning.score_candidates',side_effect=capture):
            result=real_plans(outing(),self.session)
        ranked=sorted(captured,key=lambda p:tuple(v.id for v in p.candidate.venues))
        previous=_select(ranked,3)
        improved=_select(ranked,3,prefer_primary=True)
        self.assertEqual(len({p.candidate.venues[0].id for p in previous}),1)
        self.assertEqual(len({p.candidate.venues[0].id for p in improved}),3)

    def test_dinner_excludes_cafe_only_evidence_but_keeps_mixed_restaurants_provisional(self):
        def supplied(body):
            result=search_fixture(body)
            if body['textQuery'].startswith('dinner '):
                result['places'][0]['types']=['cafe','coffee_shop']
                result['places'][1]['types']=['cafe','restaurant']
            return result
        self.search.side_effect=supplied
        result=real_plans(outing(dinner=True),self.session)
        self.assertEqual(result.diagnostics['discoveredCounts'],[10,9])
        for p in result.provisionalPlans+[p for batch in result.alternativeBatches for p in batch]:
            self.assertNotEqual(p.stops[1].venue.id,'Fixture_food_0')
            self.assertTrue(any(i.code=='unverified_dinner' for i in p.issues))
        self.assertEqual(self.search.call_count,2)
