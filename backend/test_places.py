"""Task 40 offline tests. Never require credentials or contact Google."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from google.auth.exceptions import RefreshError, TransportError
from pydantic import ValidationError
import requests

from backend.models import ActivityType, OutingRequest
from backend.places import (Coordinates, DiscoveryError, DiscoveryRequest, FIELD_MASK, PROJECT,
                            PlacesDiscovery, QUERIES, SearchArea, StartingLocation,
                            TravelConstraints, parse_response, search_body)
from backend.places_transport import _AuthRequest, access_token, text_search
from backend.provider_budget import ProviderBudget, ProviderLimitError, ProviderSettings
from backend.ranking import recommend_plans


def place(city="Baltimore", state="MD", lat=39.28, lng=-76.60):
    return {"id": "original-google-id", "displayName": {"text": "Example test venue"},
            "formattedAddress": f"123 Example St, {city}, {state}",
            "location": {"latitude": lat, "longitude": lng},
            "addressComponents": [{"longText": city, "shortText": city, "types": ["locality"]},
                                  {"longText": "Maryland" if state == "MD" else "District of Columbia",
                                   "shortText": state, "types": ["administrative_area_level_1"]}]}


def request(**kwargs):
    return DiscoveryRequest(activity="bowling", destination=SearchArea(name="Baltimore, MD"), **kwargs)


class DiscoveryTests(unittest.TestCase):
    def test_bowling_uses_strict_type_without_changing_other_searches(self):
        body = search_body(request(), 10)
        self.assertEqual(body['includedType'], 'bowling_alley')
        self.assertIs(body['strictTypeFiltering'], True)
        self.assertEqual(body['pageSize'], 10)
        for activity in ActivityType:
            if activity != ActivityType.bowling:
                other = search_body(DiscoveryRequest(activity=activity, destination={'name': 'Washington, DC'}), 10)
                self.assertNotIn('includedType', other)
                self.assertNotIn('strictTypeFiltering', other)

    def test_activity_queries_cover_all_existing_categories(self):
        self.assertEqual(set(QUERIES), {a.value for a in ActivityType})
        for activity, query in {"food": "restaurants", "movie": "movie theaters", "drinks": "bars",
                                "arcade": "video arcades", "museum": "museums", "coffee": "cafes"}.items():
            body = search_body(DiscoveryRequest(activity=activity, destination={"name": "Washington, DC"}), 3)
            self.assertEqual(body["textQuery"], query + " in Washington, DC")
            self.assertNotIn("Baltimore", json.dumps(body))
        with self.assertRaises(ValidationError):
            DiscoveryRequest(activity="invented", destination={"name": "Baltimore"})

    def test_city_and_neighborhood_queries_no_ip_or_starting_position(self):
        for name in ("Baltimore", "Fells Point, Baltimore, MD"):
            body = search_body(DiscoveryRequest(activity="coffee", destination={"name": name}), 3)
            self.assertIn(name, body["textQuery"])
            self.assertIn("rectangle", body["locationBias"])
            self.assertNotIn("circle", body["locationBias"])
            box = body["locationBias"]["rectangle"]
            self.assertLessEqual(box["high"]["longitude"] - box["low"]["longitude"], 180)

    def test_coordinates_radius_and_point_bias(self):
        for radius in (None, 2500.0, 50000.0):
            req = DiscoveryRequest(activity="museum", current_location={
                "coordinates": {"latitude": 38.9, "longitude": -77.03}, "radius_m": radius})
            body = search_body(req, 3)
            self.assertEqual(body["textQuery"], "museums")
            self.assertEqual(body["locationBias"]["circle"]["radius"], radius or 0)
            self.assertNotIn("locationRestriction", body)

    def test_explicit_destination_precedes_current_location(self):
        req = request(current_location=SearchArea(coordinates=Coordinates(latitude=0, longitude=0), radius_m=10))
        self.assertEqual(search_body(req, 3), search_body(request(), 3))
        self.assertEqual(len(parse_response({"places": [place()]}, req.area, 3).candidates), 1)

    def test_named_destination_coordinates_and_explicit_radius(self):
        req = DiscoveryRequest(activity="bowling", destination={"name": "Baltimore, MD",
            "coordinates": {"latitude": 39.28, "longitude": -76.6}, "radius_m": 1000})
        self.assertIn("Baltimore, MD", search_body(req, 3)["textQuery"])
        result = parse_response({"places": [place(), place(lat=40)]}, req.area, 3)
        self.assertEqual((len(result.candidates), result.excluded_count), (1, 1))

    def test_start_and_travel_are_separate_and_not_sent(self):
        req = request(starting_location=StartingLocation(address="Private starting address"),
                      travel_constraints=TravelConstraints(max_first_leg_minutes=0,
                                                          max_between_activities_minutes=15))
        self.assertEqual(search_body(req, 3), search_body(request(), 3))
        with self.assertRaises(ValidationError):
            DiscoveryRequest(activity="coffee", starting_location={"address": "Baltimore"})

    def test_missing_location_and_invalid_coordinates_radius(self):
        for payload in ({"activity": "coffee"}, {"activity": "coffee", "destination": {}},
                        {"activity": "coffee", "current_location": {"name": "Baltimore"}},
                        {"activity": "coffee", "destination": {"name": "Baltimore", "radius_m": 5}}):
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                DiscoveryRequest.model_validate(payload)
        for lat, lng in ((91, 0), (-91, 0), (0, 181), (0, -181), (float("nan"), 0),
                         (True, 0), ("39", 0), (0, float("inf"))):
            with self.assertRaises(ValidationError):
                Coordinates(latitude=lat, longitude=lng)
        for radius in (-1, 0, 50001, float("nan"), True, "500"):
            with self.assertRaises(ValidationError):
                SearchArea(coordinates=Coordinates(latitude=0, longitude=0), radius_m=radius)

    def test_parses_original_id_and_no_invented_details(self):
        data = place()
        data["rating"] = 5  # Unexpected expensive fields cannot enter result contract.
        result = parse_response({"places": [data]}, request().area, 3)
        candidate = result.candidates[0]
        self.assertEqual(candidate.provider_id, "original-google-id")
        self.assertEqual(candidate.provider, "google_places")
        self.assertEqual(set(candidate.model_dump()), {"provider", "provider_id", "display_name", "address", "coordinates", "attributions", "types", "primaryType", "rating", "userRatingCount"})

    def test_name_matches_do_not_override_geographic_evidence(self):
        wrong = place("Washington", "DC")
        wrong["displayName"]["text"] = "Baltimore Maryland Museum"
        wrong["formattedAddress"] = "Baltimore, MD"  # Must use structured geographic components.
        result = parse_response({"places": [wrong, place()]}, request().area, 3)
        self.assertEqual((len(result.candidates), result.excluded_count), (1, 1))
        self.assertEqual(len(parse_response({"places": [place()]}, SearchArea(name="Baltimore, Maryland"), 3).candidates), 1)

    def test_neighborhood_component_required(self):
        area = SearchArea(name="Fells Point, Baltimore, MD")
        data = place()
        self.assertFalse(parse_response({"places": [data]}, area, 3).candidates)
        data["addressComponents"].append({"longText": "Fells Point", "types": ["neighborhood"]})
        self.assertEqual(len(parse_response({"places": [data]}, area, 3).candidates), 1)
        data["addressComponents"][-1]["types"] = ["sublocality_level_1"]
        self.assertEqual(len(parse_response({"places": [data]}, area, 3).candidates), 1)

    def test_coordinate_radius_geographic_check_antimeridian(self):
        area = SearchArea(coordinates=Coordinates(latitude=0, longitude=179.999), radius_m=1000)
        result = parse_response({"places": [place(lat=0, lng=-179.999), place()]}, area, 3)
        self.assertEqual((len(result.candidates), result.excluded_count), (1, 1))

    def test_empty_and_invalid_responses(self):
        for data in ({}, {"places": []}):
            self.assertEqual(parse_response(data, request().area, 3).candidates, [])
        for data in ([], {"places": None}, {"places": [{}]}, {"places": [place()] * 4}):
            with self.assertRaises(DiscoveryError):
                parse_response(data, request().area, 3)
        for key in ("id", "location", "displayName", "formattedAddress"):
            data = place()
            del data[key]
            with self.assertRaises(DiscoveryError):
                parse_response({"places": [data]}, request().area, 3)

    def test_disabled_before_any_auth_or_transport(self):
        with patch.dict(os.environ, {}, clear=True), patch("backend.places_transport.text_search") as transport:
            with self.assertRaisesRegex(DiscoveryError, "disabled"):
                PlacesDiscovery(ProviderBudget().outing()).discover(request())
            transport.assert_not_called()

    @patch.dict(os.environ, {"WHERETO_PLACES_DEV": "1"})
    def test_budget_duplicates_and_failed_attempts(self):
        adapter = PlacesDiscovery(ProviderBudget(ProviderSettings(requests_per_session=1)).outing())
        with patch("backend.places_transport.text_search", side_effect=DiscoveryError("quota", "quota")) as transport:
            with self.assertRaises(DiscoveryError):
                adapter.discover(request())
            with self.assertRaisesRegex(ProviderLimitError, "already attempted"):
                adapter.discover(request())
            with self.assertRaisesRegex(ProviderLimitError, "session request limit"):
                adapter.discover(DiscoveryRequest(activity="coffee", destination={"name": "Baltimore"}))
            self.assertEqual(transport.call_count, 1)

    @patch.dict(os.environ, {"WHERETO_PLACES_DEV": "1"})
    def test_ten_search_limit_and_shared_session(self):
        session = ProviderBudget()
        adapter = PlacesDiscovery(session.outing())
        with patch("backend.places_transport.text_search", return_value={}) as transport:
            for activity in ("food", "movie", "museum", "coffee", "drinks", "karaoke", "concert", "art", "outdoors", "baseball"):
                adapter.discover(DiscoveryRequest(activity=activity, destination={"name": "Baltimore"}))
            with self.assertRaisesRegex(ProviderLimitError, "search limit"):
                adapter.discover(request())
            self.assertEqual(transport.call_count, 10)

    @patch.dict(os.environ, {"WHERETO_PLACES_DEV": "1"})
    def test_lower_candidate_limit_is_sent(self):
        adapter = PlacesDiscovery(ProviderBudget(ProviderSettings(candidates_per_activity=1)).outing())
        with patch("backend.places_transport.text_search", return_value={"places": [place()], "nextPageToken": "never-follow"}) as transport:
            self.assertEqual(len(adapter.discover(request()).candidates), 1)
            self.assertEqual(transport.call_args.args[0]["pageSize"], 1)
            transport.assert_called_once()

    def test_mock_isolation_even_with_dev_switch(self):
        req = OutingRequest(activities=["bowling", "drinks", "food"], date="2026-11-07")
        baseline = recommend_plans(req).model_dump()
        with patch.dict(os.environ, {"WHERETO_PLACES_DEV": "1"}), \
             patch("backend.places_transport.text_search", side_effect=AssertionError("real provider")), \
             patch("backend.provider_budget.OutingBudget.reserve", side_effect=AssertionError("budget")):
            self.assertEqual(recommend_plans(req).model_dump(), baseline)
            self.assertEqual(ProviderSettings.from_env().mode, "mock")


class TransportTests(unittest.TestCase):
    def setUp(self):
        environment = patch.dict(os.environ, {"WHERETO_PLACES_DEV": "1"})
        environment.start()
        self.addCleanup(environment.stop)
        self.session = MagicMock()
        self.response = self.session.post.return_value
        self.response.status_code = 200
        self.response.json.return_value = {"places": [place()]}

    def test_transport_also_checks_disabled_gate(self):
        with patch.dict(os.environ, {}, clear=True), patch("backend.places_transport.requests.Session") as session:
            with self.assertRaisesRegex(DiscoveryError, "disabled"):
                text_search({})
            session.assert_not_called()

    def run_search(self):
        with patch("backend.places_transport.requests.Session") as factory, \
             patch("backend.places_transport.access_token", return_value="test-token"):
            factory.return_value.__enter__.return_value = self.session
            return text_search({"textQuery": "bowling alleys in Baltimore", "pageSize": 3})

    def test_single_post_project_fields_timeout_no_redirect_retry(self):
        self.run_search()
        self.session.post.assert_called_once()
        args, kwargs = self.session.post.call_args
        self.assertEqual(args[0], "https://places.googleapis.com/v1/places:searchText")
        self.assertEqual(kwargs["headers"]["X-Goog-User-Project"], PROJECT)
        self.assertEqual(kwargs["headers"]["X-Goog-FieldMask"], FIELD_MASK)
        self.assertNotIn("*", FIELD_MASK)
        self.assertEqual(set(FIELD_MASK.split(",")), {"places.id", "places.displayName", "places.formattedAddress",
                         "places.location", "places.addressComponents", "places.attributions", "places.types", "places.primaryType", "nextPageToken"})
        self.assertFalse(kwargs["allow_redirects"])
        self.assertEqual(kwargs["timeout"], (5, 15))
        self.assertEqual(self.session.mount.call_args.args[1].max_retries.total, 0)

    def test_provider_errors_do_not_expose_bodies_or_retry(self):
        for status, code in ((400, "invalid_request"), (401, "authentication"), (403, "permission"),
                             (429, "quota"), (500, "provider"), (302, "provider")):
            self.session.reset_mock()
            self.response.status_code = status
            self.response.text = "secret provider internals"
            with self.assertRaises(DiscoveryError) as caught:
                self.run_search()
            self.assertEqual(caught.exception.code, code)
            self.assertNotIn("secret", str(caught.exception))
            self.session.post.assert_called_once()

    def test_timeout_connection_and_invalid_json(self):
        for error in (requests.Timeout("sensitive"), requests.ConnectionError("sensitive")):
            self.session.post.side_effect = error
            with self.assertRaises(DiscoveryError) as caught:
                self.run_search()
            self.assertNotIn("sensitive", str(caught.exception))
        self.session.post.side_effect = None
        self.response.json.side_effect = ValueError("sensitive")
        with self.assertRaises(DiscoveryError):
            self.run_search()

    def test_missing_adc_no_metadata_discovery_or_places(self):
        with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": "/nonexistent/adc.json"}), \
             patch("backend.places_transport.google.auth.load_credentials_from_file") as load:
            with self.assertRaisesRegex(DiscoveryError, "authentication"):
                access_token(self.session)
            load.assert_not_called()
        self.session.post.assert_not_called()

    def test_adc_identity_permissions_and_expired_refresh(self):
        from backend.places import SERVICE_ACCOUNT
        from google.auth.impersonated_credentials import Credentials
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "adc.json"
            config = {"type": "impersonated_service_account", "service_account_impersonation_url":
                      f"https://iamcredentials.googleapis.com/v1/projects/-/serviceAccounts/{SERVICE_ACCOUNT}:generateAccessToken"}
            path.write_text(json.dumps(config))
            path.chmod(0o600)
            credentials = MagicMock(spec=Credentials)
            credentials.service_account_email = SERVICE_ACCOUNT
            credentials.valid = True
            credentials.token = "test-token"
            with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": str(path)}), \
                 patch("backend.places_transport.google.auth.load_credentials_from_file", return_value=(credentials, None)):
                self.assertEqual(access_token(self.session), "test-token")
                credentials.refresh.side_effect = RefreshError("sensitive refresh credential")
                with self.assertRaises(DiscoveryError) as caught:
                    access_token(self.session)
                self.assertNotIn("sensitive", str(caught.exception))
                credentials.refresh.side_effect = None
                credentials.service_account_email = "wrong-account"
                with self.assertRaises(DiscoveryError):
                    access_token(self.session)
                path.chmod(0o644)
                with self.assertRaises(DiscoveryError):
                    access_token(self.session)
            config["type"] = "service_account"
            path.write_text(json.dumps(config))
            path.chmod(0o600)
            with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": str(path)}):
                with self.assertRaises(DiscoveryError):
                    access_token(self.session)
            path.write_text("[]")
            with patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": str(path)}):
                with self.assertRaises(DiscoveryError):
                    access_token(self.session)

    def test_auth_retries_and_unknown_hosts_refused(self):
        auth = _AuthRequest(self.session)
        with patch("google.auth.transport.requests.Request.__call__", return_value=object()) as send:
            auth("https://oauth2.googleapis.com/token", method="POST")
            with self.assertRaises(TransportError):
                auth("https://oauth2.googleapis.com/token", method="POST")
            with self.assertRaises(TransportError):
                auth("https://untrusted.example/token", method="POST")
            self.assertEqual(send.call_count, 1)


if __name__ == "__main__":
    unittest.main()
