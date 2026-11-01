"""Full provider-shaped offline orchestration; any actual send fails the test."""
import os
import unittest
from unittest.mock import patch

from backend.models import ActivityType, PlanningRequest
from backend.places import DiscoveryError
from backend.provider_budget import ProviderBudget, ProviderSettings, ProviderLimitError
from backend.real_planning import PlannerInput, real_plans, more_real_plans
from backend.real_fixtures import search_fixture, matrix_fixture
from backend.venue_details import DetailsSessions, contact_links

ENV = {'VENUE_DATA_MODE': 'real', 'WHERETO_REAL_DEV': '1', 'WHERETO_ENV': 'development', 'NODE_ENV': 'development'}


def outing(**kwargs):
    kwargs.setdefault('startingLocation',{'point':{'id':'authorized-start','place_id':'Fixture_origin_0'},'explicitly_authorized':True,'source':'manual','precision':'address_or_place'})
    return PlannerInput(activities=kwargs.pop('activities', ['bowling', 'food']), location='Baltimore', people=2,
                        date='2026-11-07', **kwargs)


class RealPlanningTests(unittest.TestCase):
    def setUp(self):
        for p in [patch.dict(os.environ, ENV, clear=True),
                  patch('requests.sessions.Session.send', side_effect=AssertionError('Unintended network'))]:
            p.start(); self.addCleanup(p.stop)
        self.search = patch('backend.places_transport.text_search', side_effect=search_fixture).start()
        self.matrix = patch('backend.routes_transport.compute_matrix', side_effect=matrix_fixture).start()
        self.addCleanup(patch.stopall)
        self.session = ProviderBudget(ProviderSettings(mode="real", candidates_per_activity=3, matrix_elements_per_outing=27, matrix_elements_per_session=300))

    def run_plan(self, **kwargs):
        return real_plans(outing(**kwargs), self.session)

    def test_complete_pipeline_three_real_provisional_options_and_source_labels(self):
        result = self.run_plan(budget=10, dinner=True)
        self.assertEqual(len(result.provisionalPlans), 3)
        self.assertFalse(result.plans)
        self.assertEqual(result.dataMode, 'real')
        self.assertEqual(result.diagnostics['matrixElements'], 12)
        self.assertEqual(self.search.call_count, 2)
        self.assertEqual(self.search.call_args_list[1].args[0]["textQuery"], "dinner restaurants in Baltimore")
        self.assertEqual(self.matrix.call_count, 2)
        for p in result.provisionalPlans:
            self.assertIsNone(p.costPerPerson)
            self.assertIsNone(p.stops[0].end)
            self.assertTrue(any(i.code == 'unverified_budget' for i in p.issues))
            self.assertEqual([v.activity for v in p.candidate.venues], ['bowling', 'food'])
            self.assertTrue(all(v.id == v.providerPlaceId for v in p.candidate.venues))
            self.assertEqual(p.routeEvidence[0]['route']['mode'], 'drive')
            self.assertEqual(p.stops[0].venue.evidenceLabels['claims']['name']['certainty'], 'reported')
        # Full contract revalidation, including no coordinates in public response.
        self.assertNotIn('"latitude":', result.model_dump_json())
        type(result).model_validate_json(result.model_dump_json())

    def test_bounded_additional_options_reuse_all_evidence_and_preserve_limits(self):
        result = self.run_plan(budget=0, maxLegTravel=10, travel=10)
        all_plans = result.provisionalPlans + [p for batch in result.alternativeBatches for p in batch]
        self.assertEqual(len(result.alternativeBatches), 0)
        from backend.real_planning import more_real_plans
        for _ in range(2):
            more=more_real_plans(result.optionsToken)
            all_plans+=more.provisionalPlans
        self.assertEqual(len(all_plans),9)
        self.assertEqual(len({tuple(v.id for v in p.candidate.venues) for p in all_plans}),9)
        self.assertEqual(self.search.call_count, 2)
        self.assertEqual(self.matrix.call_count, 2)
        self.assertEqual(result.diagnostics['matrixElements'], 12)
        self.assertTrue(all(p.totalTravel <= 10 and any(i.code == 'unverified_budget' for i in p.issues) for p in all_plans))
        serialized = result.model_dump(mode='json')
        serialized['alternativeBatches'] = [[serialized['provisionalPlans'][0]]]
        with self.assertRaises(ValueError):
            type(result).model_validate(serialized)
        # Same constraints reject alternatives as well as initial options.
        rejected = self.run_plan(maxLegTravel=0)
        self.assertFalse(rejected.provisionalPlans)
        self.assertFalse(rejected.alternativeBatches)

    def test_shared_venues_preserved_when_only_one_activity_has_choices(self):
        def limited(body):
            result = search_fixture(body)
            if 'bowling' in body['textQuery'] or 'museum' in body['textQuery']:
                result['places'] = result['places'][:1]
            return result
        self.search.side_effect = limited
        result = self.run_plan(activities=['bowling', 'food', 'museum'])
        self.assertEqual(len(result.provisionalPlans), 3)
        self.assertEqual(len({p.candidate.venues[0].id for p in result.provisionalPlans}), 1)
        self.assertEqual(len({p.candidate.venues[1].id for p in result.provisionalPlans}), 3)
        self.assertFalse(result.alternativeBatches)

    def test_manual_starting_place_is_not_silently_ignored_or_geocoded(self):
        for text in ('Inner Harbor, Baltimore', '21201', '1 Synthetic Street, Baltimore'):
            result = self.run_plan(manualStartingPlace=text, maxFirstLegTravel=10)
            self.assertFalse(result.provisionalPlans)
            self.assertIn('Find and confirm', result.message)
            self.assertEqual(result.request.location, 'Baltimore')
            self.assertNotIn(text, result.model_dump_json())
        self.assertEqual(self.search.call_count, 0)
        self.assertEqual(self.matrix.call_count, 0)

    def test_all_29_categories_no_fabricated_events(self):
        for activity in ActivityType:
            self.session = ProviderBudget(ProviderSettings(mode="real", candidates_per_activity=3, matrix_elements_per_outing=27, matrix_elements_per_session=300))
            result = self.run_plan(activities=[activity])
            self.assertTrue(result.provisionalPlans, activity)
            self.assertTrue(all(p.candidate.venues[0].kind == 'venue' for p in result.provisionalPlans))
            if activity in ('movie', 'concert'):
                self.assertTrue(any(i.code == 'session_not_verified' for i in result.provisionalPlans[0].issues))

    def test_repeated_order_and_deduplicated_searches(self):
        result = self.run_plan(activities=['coffee', 'museum', 'coffee'])
        self.assertEqual(self.search.call_count, 2)
        self.assertEqual(result.diagnostics['matrixElements'], 21)
        for p in result.provisionalPlans:
            self.assertEqual([v.activity for v in p.candidate.venues], ['coffee', 'museum', 'coffee'])
            self.assertEqual(len(set(v.id for v in p.candidate.venues)), 3)
        self.assertEqual(len(result.provisionalPlans), 3)

    def test_multi_activity_place_not_two_visits(self):
        def shared(body):
            data = search_fixture(body)
            for i, place in enumerate(data['places']):
                place['id'] = f'Shared_{i}'; place['displayName']['text'] = f'Shared venue {i}'
            return data
        self.search.side_effect = shared
        result = self.run_plan()
        for p in result.provisionalPlans:
            self.assertNotEqual(p.candidate.venues[0].id, p.candidate.venues[1].id)
        self.assertEqual(result.diagnostics['matrixElements'], 9)

    def test_travel_limits_exact_seconds_no_rounding_rejection(self):
        self.matrix.side_effect = lambda body: [dict(e, duration='120s') for e in matrix_fixture(body)]
        self.assertTrue(self.run_plan(maxLegTravel=2, travel=2).provisionalPlans)
        self.session = ProviderBudget(ProviderSettings(mode="real", candidates_per_activity=3, matrix_elements_per_outing=27, matrix_elements_per_session=300))
        self.matrix.side_effect = lambda body: [dict(e, duration='120.000000001s') for e in matrix_fixture(body)]
        result = self.run_plan(maxLegTravel=2)
        self.assertFalse(result.provisionalPlans)
        self.assertFalse(result.explorationPlans)
        self.assertTrue(result.canShowBeyond)
        result=more_real_plans(result.optionsToken,show_beyond=True)
        self.assertTrue(result.explorationPlans)
        self.assertTrue(all(p.travelDeviations for p in result.explorationPlans))
        self.session = ProviderBudget(ProviderSettings(mode="real", candidates_per_activity=3, matrix_elements_per_outing=27, matrix_elements_per_session=300))
        self.assertFalse(self.run_plan(travel=0).provisionalPlans)

    def test_missing_route_never_invents_travel(self):
        self.matrix.return_value = []; self.matrix.side_effect = None
        p = self.run_plan().provisionalPlans[0]
        self.assertIsNone(p.totalTravel)
        self.assertIsNone(p.legs[0].minutes)
        self.assertTrue(any(i.code == 'route_unknown' for i in p.issues))

    def test_start_is_separate_enforced_and_not_echoed(self):
        start = {'point': {'id': 'authorized-start', 'coordinates': {'latitude': 39.28, 'longitude': -76.60}}, 'explicitly_authorized': True}
        result = self.run_plan(startingLocation=start, maxFirstLegTravel=0)
        self.assertFalse(result.provisionalPlans)
        self.assertFalse(result.explorationPlans)
        self.assertTrue(result.canShowBeyond)
        result=more_real_plans(result.optionsToken,show_beyond=True)
        self.assertTrue(result.explorationPlans)
        self.assertTrue(all(p.travelClassification=='beyond_limit' for p in result.explorationPlans))
        self.assertNotIn('"latitude":', result.model_dump_json())
        self.session = ProviderBudget(ProviderSettings(mode="real", candidates_per_activity=3, matrix_elements_per_outing=27, matrix_elements_per_session=300))
        result = self.run_plan(startingLocation=start, maxFirstLegTravel=10)
        self.assertTrue(result.provisionalPlans[0].firstLeg)
        self.assertEqual(result.request.maxFirstLegTravel, 10)
        self.assertEqual(result.diagnostics['matrixElements'], 12)
        self.session = ProviderBudget(ProviderSettings(mode="real", candidates_per_activity=3, matrix_elements_per_outing=27, matrix_elements_per_session=300))
        self.search.reset_mock()
        self.assertFalse(self.run_plan(startingLocation=None,maxFirstLegTravel=5).provisionalPlans)
        self.search.assert_not_called()

    def test_explicit_destination_ignores_current_search_point(self):
        request = outing(currentArea={'coordinates': {'latitude': 0, 'longitude': 0}})
        request.location = 'Washington, DC'
        result = real_plans(request, self.session)
        self.assertTrue(result.provisionalPlans)
        for call in self.search.call_args_list:
            self.assertIn('Washington, DC', call.args[0]['textQuery'])
            self.assertNotIn('circle', call.args[0]['locationBias'])

    def test_near_me_requires_permission_or_manual_city(self):
        request = outing(); request.location = 'near me'
        self.assertFalse(real_plans(request, self.session).provisionalPlans)
        self.search.assert_not_called()
        request.currentArea = __import__('backend.places', fromlist=['SearchArea']).SearchArea(coordinates={'latitude': 39.28, 'longitude': -76.60})
        result = real_plans(request, self.session)
        self.assertTrue(result.provisionalPlans)
        self.assertIn('circle', self.search.call_args.args[0]['locationBias'])

    def test_empty_partial_invalid_discovery_never_mock_fallback(self):
        for response in ({'places': []}, {'places': [{'id': 'bad'}]}):
            self.session = ProviderBudget(ProviderSettings(mode="real", candidates_per_activity=3, matrix_elements_per_outing=27, matrix_elements_per_session=300))
            self.search.return_value = response; self.search.side_effect = None
            if response['places']:
                with self.assertRaises(DiscoveryError): self.run_plan()
            else:
                self.assertFalse(self.run_plan().provisionalPlans)
        self.matrix.assert_not_called()

    def test_provider_failures_and_application_budget(self):
        for code in ('quota', 'authentication', 'permission', 'timeout'):
            self.search.side_effect = DiscoveryError(code, 'Safe failure')
            with self.assertRaises(DiscoveryError): self.run_plan()
        self.search.side_effect = search_fixture
        self.session = ProviderBudget(ProviderSettings(mode='real', matrix_elements_per_outing=8))
        result = self.run_plan()
        self.assertLessEqual(result.diagnostics['matrixElements'], 8)
        self.assertTrue(all(p.routeEvidence for p in result.provisionalPlans))

    def test_four_activity_start_is_staged_within_lower_27_cap(self):
        start = {'point': {'id': 'start', 'place_id': 'Explicit_Start'}, 'explicitly_authorized': True}
        result = self.run_plan(activities=['coffee', 'museum', 'bowling', 'food'], startingLocation=start)
        self.assertLessEqual(result.diagnostics['matrixElements'], 27)
        self.assertTrue(all(p.firstLeg and len(p.routeEvidence) == 3 for p in result.provisionalPlans))

    def test_modes_and_production_guard_before_network(self):
        for changes in ({'WHERETO_REAL_DEV': ''}, {'WHERETO_ENV': 'production'}, {'NODE_ENV': 'production'}, {'VERCEL': '1'}):
            with patch.dict(os.environ, changes), self.assertRaises(ProviderLimitError): self.run_plan()
        self.search.assert_not_called()
        from backend.ranking import recommend_plans
        self.assertTrue(recommend_plans(PlanningRequest(activities=['coffee'], date='2026-11-07')).provisionalPlans)
        self.search.assert_not_called()

    def test_contact_links_validation_missing_and_minimal_mask(self):
        from backend.venue_details import DETAILS_MASK
        self.assertNotIn('rating', DETAILS_MASK)
        result = contact_links({'id': 'A', 'nationalPhoneNumber': '(202) 555-0100', 'websiteUri': 'https://example.com'}, 'A')
        self.assertEqual(result['telephoneUrl'], 'tel:2025550100')
        for website in ('javascript:alert(1)', 'https://user:pass@example.com', 'https://example.com/\nsecret'):
            self.assertIsNone(contact_links({'id': 'A', 'websiteUri': website, 'nationalPhoneNumber': 'bad'}, 'A')['website'])
        self.assertIsNone(contact_links({'id': 'A'}, 'A')['phone'])
        with self.assertRaises(DiscoveryError): contact_links({'id': 'B'}, 'A')

    def test_details_on_demand_original_id_budget_gate_no_repeat(self):
        sessions = DetailsSessions()
        token = sessions.create(['A', 'B'], self.session.outing())
        with patch('backend.venue_details.fetch_details', return_value={'placeId': 'A'}) as send:
            send.assert_not_called()
            with self.assertRaises(DiscoveryError): sessions.get(token, 'A')
            with patch.dict(os.environ, {'WHERETO_CONTACT_DETAILS_DEV': '1'}):
                with self.assertRaises(DiscoveryError): sessions.get(token, 'wrong')
                self.assertEqual(sessions.get(token, 'A')['placeId'], 'A')
                with self.assertRaises(DiscoveryError): sessions.get(token, 'A')
            self.assertEqual(send.call_count, 1)
        zero = ProviderBudget(ProviderSettings(mode='real', details_per_outing=0))
        token = sessions.create(['A'], zero.outing())
        with patch.dict(os.environ, {'WHERETO_CONTACT_DETAILS_DEV': '1'}), self.assertRaises(ProviderLimitError): sessions.get(token, 'A')


    def test_interpretation_near_me_and_first_leg_grounding(self):
        from types import SimpleNamespace
        from backend.ai import Interpretation
        from backend.interpretation import InterpretationInput, interpret_request
        def provider(location=None):
            return SimpleNamespace(interpret=lambda text: Interpretation(activities=['Coffee'], people=2,
                budget_per_person=None, date=None, location=location, preferences=[]))
        text = 'Coffee near me for 2 people on 2026-11-07 within 10 minutes of me'
        result = interpret_request(InterpretationInput(text=text, hasCurrentLocation=True), provider())
        self.assertIsNotNone(result.request, result.issues)
        self.assertEqual(result.request.location, 'near me')
        self.assertEqual(result.request.maxFirstLegTravel, 10)
        missing = interpret_request(InterpretationInput(text=text), provider())
        self.assertEqual(missing.request.location,"near me")
        self.assertNotIn('location', [q.field for q in missing.questions])
        explicit = interpret_request(InterpretationInput(text='Coffee in Washington, DC near me for 2 people on 2026-11-07', hasCurrentLocation=True), provider('Washington, DC'))
        self.assertEqual(explicit.request.location, 'Washington, DC')
        unsupported = interpret_request(InterpretationInput(text='Coffee near me for 2 people on 2026-11-07 within 2 miles', hasCurrentLocation=True), provider())
        self.assertIsNone(unsupported.request)
        self.assertIn('radius', ' '.join(unsupported.issues))

    def test_contact_transport_minimal_fields_and_safe_failures(self):
        from unittest.mock import Mock
        from backend.venue_details import fetch_details, DETAILS_MASK
        with patch.dict(os.environ, {'WHERETO_CONTACT_DETAILS_DEV': '1'}), \
             patch('backend.places_transport.access_token', return_value='synthetic-test-token'), \
             patch('requests.Session.get') as get:
            response = Mock(status_code=200)
            response.json.return_value = {'id': 'A', 'internationalPhoneNumber': '+1 202 555 0100', 'websiteUri': 'https://example.com'}
            get.return_value = response
            self.assertEqual(fetch_details('A')['telephoneUrl'], 'tel:+12025550100')
            self.assertEqual(get.call_args.args[0], 'https://places.googleapis.com/v1/places/A')
            self.assertEqual(get.call_args.kwargs['headers']['X-Goog-FieldMask'], DETAILS_MASK)
            self.assertFalse(get.call_args.kwargs['allow_redirects'])
            for status in (401, 403, 429, 500):
                response.status_code = status
                with self.assertRaises(DiscoveryError): fetch_details('A')
            self.assertEqual(get.call_count, 5)

    def test_mock_api_refuses_new_location_limits_and_real_revisit_is_explicit(self):
        from backend.main import generate_plan
        import backend.main as api
        with patch.object(api, 'provider_budget', ProviderBudget(ProviderSettings())):
            self.assertEqual(generate_plan(outing(maxFirstLegTravel=5)).status_code, 422)
        self.assertFalse(self.run_plan(allowRevisits=True).provisionalPlans)
        self.search.assert_not_called()


    def test_radius_is_strict_finite_and_bounded(self):
        from pydantic import ValidationError
        for radius in ('1000', True, float('nan'), float('inf'), 0, -1, 50001):
            with self.assertRaises(ValidationError): outing(searchRadius=radius)
        self.assertEqual(outing(searchRadius=1000).searchRadius, 1000)
