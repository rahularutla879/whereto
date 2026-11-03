"""Invented Google-shaped responses only; block network in every routing test."""
import os
import unittest
from unittest.mock import patch

from pydantic import ValidationError
import requests

from backend.models import OutingRequest
from backend.ranking import recommend_plans
from backend.places import DiscoveryError
from backend.provider_budget import ProviderBudget, ProviderSettings
from backend.routes import (AuthorizedStart, FIELD_MASK, GoogleRouteCalculator, RouteError,
                            RoutePoint, RouteRequest, matrix_body, parse_matrix, plan_matrices)
from backend.routes_transport import compute_matrix


def point(name):
    return RoutePoint(id=name, place_id="Place_" + name)


def element(i=0, j=0, **changes):
    return dict(originIndex=i, destinationIndex=j, status={}, condition="ROUTE_EXISTS",
                duration="160.5s", distanceMeters=822) | changes


def response(body):
    return [element(i, j, duration=f"{100 + i * 20 + j}s")
            for i in range(len(body['origins'])) for j in range(len(body['destinations']))][::-1]


def route_request(groups=None, **kwargs):
    return RouteRequest(activity_groups=groups or [[point("a")], [point("b")]], mode=kwargs.pop("mode", "drive"), **kwargs)


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.network = patch("socket.socket", side_effect=AssertionError("Unintended network"))
        self.network.start()
        self.addCleanup(self.network.stop)
        self.env = patch.dict(os.environ, {"WHERETO_ROUTES_DEV": "1"})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.transport = patch("backend.routes_transport.compute_matrix", side_effect=response)
        self.post = self.transport.start()
        self.addCleanup(self.transport.stop)
        self.outing = ProviderBudget().outing()
        self.calculator = GoogleRouteCalculator(self.outing)

    def test_element_quota_failure_stops_later_unsent_batches(self):
        self.post.side_effect=lambda body:[element(status={'code':8,'message':'RESTRICTED_PROVIDER_TEXT'})]
        result=self.calculator.calculate(route_request([[point('a')],[point('b')],[point('c')]]))
        self.assertEqual(self.post.call_count,1)
        self.assertEqual([l.error_code for l in result.legs],['quota','not_requested'])
        self.assertTrue(all(l.error_context['quotaBoundary']=='unknown' for l in result.legs))
        self.assertNotIn('RESTRICTED_PROVIDER_TEXT',result.model_dump_json())

    def test_drive_and_walk_metrics_and_minimal_features(self):
        for mode in ("drive", "walk"):
            with self.subTest(mode=mode):
                calculator = GoogleRouteCalculator(ProviderBudget().outing())
                result = calculator.calculate(route_request(mode=mode))
                leg = result.legs[0]
                self.assertEqual((leg.origin_id, leg.destination_id), ("a", "b"))
                self.assertEqual((leg.status, leg.mode, leg.duration_seconds, leg.distance_meters), ("ok", mode, 100, 822))
                self.assertEqual(leg.duration_minutes, 100 / 60)
                self.assertEqual(leg.provider, "google_routes")
                body = self.post.call_args.args[0]
                self.assertEqual(set(body), {"origins", "destinations", "travelMode"} | ({"routingPreference"} if mode == "drive" else set()))
                self.assertEqual(body.get("routingPreference"), "TRAFFIC_AWARE" if mode == "drive" else None)
        self.assertEqual(FIELD_MASK, "originIndex,destinationIndex,status,condition,distanceMeters,duration,fallbackInfo")

    def test_multi_origin_destination_out_of_order_and_asymmetry(self):
        req = route_request([[point("a"), point("b")], [point("c"), point("d")], [point("a")]])
        result = self.calculator.calculate(req)
        self.assertEqual(result.matrix_elements, 6)
        self.assertEqual(result.matrix_requests, 2)
        legs = {(l.origin_id, l.destination_id): l for l in result.legs}
        self.assertEqual(legs['b', 'd'].duration_seconds, 121)
        self.assertEqual(legs['a', 'c'].duration_seconds, 100)
        self.assertEqual(legs['c', 'a'].duration_seconds, 100)
        # Distinct provider values in reversed directions must survive unchanged.
        self.post.side_effect = [[element(duration="101s")], [element(duration="207s")]]
        result = GoogleRouteCalculator(ProviderBudget().outing()).calculate(route_request([[point("a")], [point("b")], [point("a")]]))
        self.assertEqual([l.duration_seconds for l in result.legs], [101, 207])

    def test_only_adjacent_required_pairs_and_duplicate_reuse(self):
        req = route_request([[point("a")], [point("b"), point("b")], [point("a")], [point("b")]])
        result = self.calculator.calculate(req)
        self.assertEqual([(l.origin_id, l.destination_id) for l in result.legs], [('a', 'b'), ('b', 'a')])
        self.assertEqual(result.matrix_elements, 2)
        self.assertEqual(self.post.call_count, 2)
        pairs, matrices = plan_matrices(route_request([[point("a"), point("b")], [point("c"), point("d")], [point("e")]]))
        sent = {(a.id, b.id) for origins, destinations in matrices for a in origins for b in destinations}
        self.assertEqual(sent, set(pairs))
        self.assertNotIn(('a', 'e'), sent)

    def test_same_venue_needs_no_google_and_equal_coordinates_do_not_prove_identity(self):
        result = self.calculator.calculate(route_request([[point("a")], [point("a")]]))
        self.assertEqual((result.matrix_elements, result.legs[0].status, result.legs[0].duration_seconds), (0, 'same_location', 0))
        self.assertEqual(result.legs[0].provider, 'local_identity')
        self.post.assert_not_called()
        loc = dict(latitude=39.0, longitude=-76.0)
        a, b = RoutePoint(id='x', coordinates=loc), RoutePoint(id='y', coordinates=loc)
        self.assertEqual(self.calculator.calculate(route_request([[a], [b]])).matrix_elements, 1)
        alias = RoutePoint(id='alias', place_id=point('a').place_id)
        result = self.calculator.calculate(route_request([[point('a')], [alias]]))
        self.assertEqual(result.legs[0].status, 'same_location')

    def test_identical_provider_pairs_reuse_metrics_without_losing_caller_ids(self):
        a, b = point('a'), point('b')
        alias_a = RoutePoint(id='alias_a', place_id=a.place_id)
        alias_b = RoutePoint(id='alias_b', place_id=b.place_id)
        result = self.calculator.calculate(route_request([[a, alias_a], [b, alias_b]]))
        self.assertEqual(result.matrix_elements, 1)
        self.post.assert_called_once()
        self.assertEqual({(l.origin_id, l.destination_id) for l in result.legs},
                         {('a', 'b'), ('a', 'alias_b'), ('alias_a', 'b'), ('alias_a', 'alias_b')})
        self.assertTrue(all(l.duration_seconds == 100 for l in result.legs))

    def test_explicit_start_is_optional_separate_and_requires_authorization(self):
        self.assertEqual(self.calculator.calculate(route_request([[point('a')]])).legs, [])
        start = AuthorizedStart(point=RoutePoint(id='user_start', coordinates=dict(latitude=39.0, longitude=-76.0)), explicitly_authorized=True)
        result = self.calculator.calculate(route_request(starting_location=start))
        self.assertEqual([(l.origin_id, l.destination_id) for l in result.legs], [('user_start', 'a'), ('a', 'b')])
        self.assertEqual(result.matrix_elements, 2)
        self.assertNotIn('39.0', repr(start))
        for value in ({'point': start.point}, {'point': start.point, 'explicitly_authorized': False}, {'point': start.point, 'explicitly_authorized': 1}):
            with self.assertRaises(ValidationError):
                AuthorizedStart(**value)
        with self.assertRaises(ValidationError):
            RouteRequest(activity_groups=[[point('a')]], mode='walk', destination='Baltimore')

    def test_validation_of_inputs_and_identity(self):
        for data in ({'id': 'a'}, {'id': 'a', 'place_id': ''}, {'id': 'a', 'place_id': 'places/id'},
                     {'id': 'a', 'place_id': 'bad id'}, {'id': 'a', 'coordinates': {'latitude': 91, 'longitude': 0}},
                     {'id': 'a', 'coordinates': {'latitude': float('nan'), 'longitude': 0}},
                     {'id': 'a', 'coordinates': {'latitude': True, 'longitude': 0}},
                     {'id': 'a', 'place_id': 'id', 'coordinates': {'latitude': 0, 'longitude': 0}}):
            with self.subTest(data=data), self.assertRaises(ValidationError):
                RoutePoint(**data)
        for groups in ([], [[]], [[point('a')]*21], [[point('a')]]*5, [[point('a')], [RoutePoint(id='a', place_id='other')]]):
            with self.assertRaises(ValidationError):
                RouteRequest(activity_groups=groups, mode='drive')
        with self.assertRaises(ValidationError):
            route_request(mode='transit')
        for origins, destinations, mode in (([], [point('a')], 'drive'), ([point('a')], [], 'walk'), ([point('a')], [point('b')], 'bike')):
            with self.assertRaises(RouteError):
                matrix_body(origins, destinations, mode)

    def test_existing_venue_bridge_preserves_id_and_rejects_fictional_facts(self):
        from backend.venue_normalization import normalize_google_place
        venue = normalize_google_place({'id': 'Stable_Google-ID', 'displayName': {'text': 'Invented test venue'}}, 'coffee')
        routed = RoutePoint.from_venue(venue)
        self.assertEqual((routed.id, routed.place_id), (venue.id, venue.id))
        self.assertIsNone(routed.coordinates)
        with self.assertRaises(RouteError):
            RoutePoint.from_venue(venue.model_copy(update={'evidence': 'fictional'}))
        self.post.assert_not_called()

    def test_rejected_batch_leaves_budget_available_and_respects_lower_candidate_limit(self):
        calculator = GoogleRouteCalculator(ProviderBudget(ProviderSettings(requests_per_outing=1)).outing())
        with self.assertRaises(RouteError):
            calculator.calculate(route_request([[point('a')], [point('b')], [point('c')]]))
        self.post.assert_not_called()
        self.assertEqual(calculator.calculate(route_request()).matrix_elements, 1)
        self.post.reset_mock()
        calculator = GoogleRouteCalculator(ProviderBudget(ProviderSettings(candidates_per_activity=1)).outing())
        with self.assertRaises(RouteError) as caught:
            calculator.calculate(route_request([[point('a'), point('b')], [point('c')]]))
        self.assertEqual(caught.exception.code, 'application_limit')
        self.post.assert_not_called()

    def test_unreachable_errors_missing_metrics_and_partial_matrix(self):
        variants = [element(condition='ROUTE_NOT_FOUND'), element(status={'code': 7, 'message': 'sensitive ignored'}),
                    element(duration=None), element(duration='NaNs'), element(duration='-1s'), element(duration=True),
                    element(distanceMeters=None), element(distanceMeters=True), element(status=None), element(condition=None)]
        for item in variants:
            with self.subTest(item=item):
                legs = parse_matrix([item], [point('a')], [point('b')], 'drive')
                self.assertIsNone(legs[0].duration_seconds)
                self.assertIsNone(legs[0].distance_meters)
                self.assertNotEqual(legs[0].status, 'ok')
                self.assertNotIn('sensitive', legs[0].model_dump_json())
        legs = parse_matrix([element(), element(0, 1, status={'code': 8})], [point('a')], [point('b'), point('c'), point('d')], 'walk')
        self.assertEqual([l.status for l in legs], ['ok', 'error', 'unknown'])
        self.assertEqual(legs[-1].error_code, 'missing_element')
        self.assertEqual(legs[1].provider_status_code, 8)

    def test_malformed_indices_and_duplicate_elements(self):
        for data in ({}, [None], [element(originIndex=None)], [element(originIndex=True)], [element(destinationIndex=99)]):
            with self.assertRaises(RouteError):
                parse_matrix(data, [point('a')], [point('b')], 'drive')
        legs = parse_matrix([element(), element()], [point('a')], [point('b'), point('c')], 'drive')
        self.assertEqual([l.error_code for l in legs], ['duplicate_element', 'missing_element'])
        self.assertTrue(all(l.duration_seconds is None for l in legs))

    def test_fractional_zero_and_missing_fields_remain_precise(self):
        self.assertEqual(parse_matrix([element()], [point('a')], [point('b')], 'drive')[0].duration_seconds, 160.5)
        self.assertEqual(parse_matrix([element(duration='0s', distanceMeters=0)], [point('a')], [point('b')], 'walk')[0].duration_seconds, 0)
        for field in ('originIndex', 'destinationIndex', 'status', 'condition', 'duration', 'distanceMeters'):
            item = element()
            del item[field]
            if field in ('originIndex', 'destinationIndex', 'distanceMeters'):
                leg = parse_matrix([item], [point('a')], [point('b')], 'drive')[0]
                self.assertEqual(leg.status, 'ok')
                if field == 'distanceMeters':
                    self.assertEqual(leg.distance_meters, 0)
            else:
                self.assertIsNone(parse_matrix([item], [point('a')], [point('b')], 'drive')[0].duration_seconds)

    def test_27_elements_and_whole_plan_exhaustion_before_any_io(self):
        self.calculator = GoogleRouteCalculator(ProviderBudget(ProviderSettings(matrix_elements_per_outing=27)).outing())
        groups = [[point(f'{i}_{j}') for j in range(3)] for i in range(4)]
        result = self.calculator.calculate(route_request(groups))
        self.assertEqual((result.matrix_elements, result.matrix_requests), (27, 3))
        start = AuthorizedStart(point=point('start'), explicitly_authorized=True)
        self.post.reset_mock()
        with self.assertRaises(RouteError) as caught:
            GoogleRouteCalculator(ProviderBudget(ProviderSettings(matrix_elements_per_outing=27)).outing()).calculate(route_request(groups, starting_location=start))
        self.assertEqual(caught.exception.code, 'application_limit')
        self.post.assert_not_called()
        with self.assertRaises(RouteError):
            self.calculator.calculate(route_request([[point('x')], [point('y')]]))

    def test_session_request_and_minute_limits_no_partial_sending(self):
        for settings in (ProviderSettings(matrix_elements_per_session=0), ProviderSettings(requests_per_outing=1), ProviderSettings(requests_per_session=1)):
            with self.subTest(settings=settings):
                with self.assertRaises(RouteError):
                    GoogleRouteCalculator(ProviderBudget(settings).outing()).calculate(route_request([[point('a')], [point('b')], [point('c')]]))
        self.post.assert_not_called()
        session = ProviderBudget(ProviderSettings(matrix_elements_per_minute=60))
        for n in range(2):
            with session.outing().reserve('matrix', str(n), origins=3, destinations=9):
                pass
        with self.assertRaisesRegex(RouteError, 'minute quota'):
            GoogleRouteCalculator(session.outing()).calculate(route_request([[point('a')]*1, [point(str(n)) for n in range(3)], [point(str(n+3)) for n in range(3)]]))
        self.post.assert_not_called()

    def test_minute_admission_expires_without_sleep_or_automatic_retry(self):
        session = ProviderBudget(ProviderSettings(matrix_elements_per_minute=60))
        with patch('backend.provider_budget.monotonic', return_value=100):
            for n in range(2):
                with session.outing().reserve('matrix', str(n), origins=3, destinations=9):
                    pass
        request = route_request([[point('a'), point('b'), point('c')], [point('d'), point('e'), point('f')]])
        calculator = GoogleRouteCalculator(session.outing())
        with patch('backend.provider_budget.monotonic', return_value=159):
            with self.assertRaises(RouteError):
                calculator.calculate(request)
        self.post.assert_not_called()
        with patch('backend.provider_budget.monotonic', return_value=160):
            self.assertEqual(calculator.calculate(request).matrix_elements, 9)
        self.post.assert_called_once()

    def test_failed_transport_stops_remaining_matrices_and_never_retries(self):
        self.post.side_effect = RouteError('timeout', 'Safe timeout')
        req = route_request([[point('a')], [point('b')], [point('c')]])
        result = self.calculator.calculate(req)
        self.assertEqual([l.error_code for l in result.legs], ['timeout', 'not_requested'])
        self.assertEqual(result.matrix_elements, 2)
        self.post.assert_called_once()
        with self.assertRaises(RouteError):
            self.calculator.calculate(req)
        self.post.assert_called_once()

    def test_disabled_before_transport_or_auth_including_direct_transport(self):
        with patch.dict(os.environ, {'WHERETO_ROUTES_DEV': '0'}), patch('backend.routes_transport.access_token') as auth:
            for action in (lambda: self.calculator.calculate(route_request()), lambda: compute_matrix(matrix_body([point('a')], [point('b')], 'drive'))):
                with self.assertRaises(RouteError) as caught:
                    action()
                self.assertEqual(caught.exception.code, 'disabled')
            auth.assert_not_called()
        self.post.assert_not_called()

    def test_mock_planner_isolation(self):
        with patch('backend.routes.GoogleRouteCalculator.calculate', side_effect=AssertionError('real routing')), patch('backend.provider_budget.OutingBudget.reserve_matrices', side_effect=AssertionError('budget')):
            result = recommend_plans(OutingRequest(activities=['bowling', 'drinks', 'food'], date='2026-11-07'))
        self.assertTrue(result.plans or result.provisionalPlans)
        self.post.assert_not_called()


class RouteTransportTests(unittest.TestCase):
    def setUp(self):
        self.patches = [patch.dict(os.environ, {'WHERETO_ROUTES_DEV': '1'}),
                        patch('socket.socket', side_effect=AssertionError('Unintended network')),
                        patch('backend.routes_transport.access_token', return_value='synthetic-token'),
                        patch('backend.routes_transport.requests.Session')]
        values = [p.start() for p in self.patches]
        self.auth, self.session = values[2], values[3].return_value.__enter__.return_value
        for p in self.patches:
            self.addCleanup(p.stop)
        self.body = matrix_body([point('a')], [point('b')], 'drive')
        self.session.post.return_value.status_code = 200
        self.session.post.return_value.json.return_value = [element()]

    def test_fixed_endpoint_headers_zero_retries_redirects_and_timeout(self):
        self.assertEqual(compute_matrix(self.body), [element()])
        args, kwargs = self.session.post.call_args
        self.assertEqual(args[0], 'https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix')
        self.assertEqual(kwargs['headers']['X-Goog-FieldMask'], FIELD_MASK)
        self.assertEqual(kwargs['headers']['X-Goog-User-Project'], 'where-to-512422')
        self.assertEqual(kwargs['timeout'], (5, 15))
        self.assertFalse(kwargs['allow_redirects'])
        self.assertEqual(self.session.mount.call_args.args[1].max_retries.total, 0)
        self.session.post.assert_called_once()

    def test_http_failures_are_safe_and_not_retried(self):
        for status, code in ((400, 'invalid_request'), (401, 'authentication'), (403, 'permission'), (429, 'quota'), (500, 'provider'), (302, 'provider')):
            self.session.post.reset_mock()
            self.session.post.return_value.status_code = status
            with self.assertRaises(RouteError) as caught:
                compute_matrix(self.body)
            self.assertEqual(caught.exception.code, code)
            self.session.post.assert_called_once()
            self.assertNotIn('synthetic-token', str(caught.exception))

    def test_timeout_network_invalid_json_and_auth_failures(self):
        for error, code in ((requests.Timeout('private payload'), 'timeout'), (requests.ConnectionError('secret'), 'provider')):
            self.session.post.side_effect = error
            with self.assertRaises(RouteError) as caught:
                compute_matrix(self.body)
            self.assertEqual(caught.exception.code, code)
            self.assertNotIn('private', str(caught.exception))
        self.session.post.side_effect = None
        self.session.post.return_value.json.return_value = {'error': 'secret'}
        with self.assertRaises(RouteError):
            compute_matrix(self.body)
        self.session.post.reset_mock()
        self.auth.side_effect = DiscoveryError('authentication', 'private details')
        with self.assertRaises(RouteError) as caught:
            compute_matrix(self.body)
        self.assertEqual(caught.exception.code, 'authentication')
        self.session.post.assert_not_called()

    def test_expensive_options_rejected_before_auth(self):
        for body in (self.body | {'routingPreference': 'TRAFFIC_AWARE_OPTIMAL'}, self.body | {'extraComputations': ['TOLLS']}, self.body | {'departureTime': 'now'}):
            with self.assertRaises(RouteError):
                compute_matrix(body)
        self.auth.assert_not_called()

    def test_invalid_and_nested_inputs_refused_before_auth(self):
        for body in (None, {}, self.body | {'origins': []}, self.body | {'origins': [None]},
                     self.body | {'origins': [{'waypoint': {'placeId': 'bad/id'}}]},
                     self.body | {'origins': [{'waypoint': {'placeId': 'id', 'via': True}}]},
                     self.body | {'origins': [{'waypoint': {'placeId': 'id'}, 'routeModifiers': {'avoidTolls': True}}]},
                     self.body | {'origins': [{'waypoint': {'location': {'latLng': {'latitude': 99, 'longitude': 0}}}}]}):
            with self.subTest(body=body), self.assertRaises(RouteError):
                compute_matrix(body)
        self.auth.assert_not_called()
