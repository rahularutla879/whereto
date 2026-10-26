"""Task 41 fixtures are invented provider-shaped data; never saved live content."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import os
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from backend.mock_data import load_mock_venues
from backend.models import ActivityType, OutingRequest, ScheduledEvent
from backend.places import DiscoveryError, PlacesDiscovery, parse_response, SearchArea, FIELD_MASK
from backend.provider_budget import ProviderBudget, ProviderSettings
from backend.ranking import recommend_plans
from backend.test_places import place, request
from backend.venue_models import VenueFacts
from backend.venue_normalization import (NormalizationError, normalize_google_place,
                                        normalize_google_places, normalize_discovery_candidates)

NOW = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)


def enriched():
    return {**place(), "name": "places/original-google-id", "types": ["bowling_alley", "point_of_interest"],
            "rating": 4.3, "userRatingCount": 123, "websiteUri": "https://example.org/venue",
            "googleMapsUri": "https://maps.google.com/?cid=123", "priceLevel": "PRICE_LEVEL_MODERATE",
            "priceRange": {"startPrice": {"currencyCode": "USD", "units": "12", "nanos": 500000000},
                           "endPrice": {"currencyCode": "USD", "units": "25"}},
            "regularOpeningHours": {"periods": [{"open": {"day": 6, "hour": 22, "minute": 0},
                                                  "close": {"day": 0, "hour": 2, "minute": 0}}],
                                    "weekdayDescriptions": ["Saturday: 10 PM–2 AM"]},
            "currentOpeningHours": {"openNow": False, "periods": [],
                                    "specialDays": [{"date": {"year": 2026, "month": 10, "day": 24}}],
                                    "nextOpenTime": "2026-10-25T14:00:00Z"},
            "timeZone": {"id": "America/New_York", "version": "2026a"}, "utcOffsetMinutes": -240,
            "attributions": [{"provider": "Synthetic credit", "providerUri": "https://example.org/credit"}]}


def normalize(raw=None, activity="bowling", **kwargs):
    return normalize_google_place(enriched() if raw is None else raw, activity, observed_at=NOW, **kwargs)


class NormalizationTests(unittest.TestCase):
    def test_supported_facts_and_json_round_trip(self):
        facts = normalize()
        self.assertEqual((facts.id, facts.name, facts.provider, facts.evidence),
                         ("original-google-id", "Example test venue", "google_places", "provider_supplied"))
        self.assertEqual(facts.resourceName, "places/" + facts.id)
        self.assertEqual(facts.address, "123 Example St, Baltimore, MD")
        self.assertEqual((facts.coordinates.latitude, facts.coordinates.longitude), (39.28, -76.6))
        self.assertEqual(facts.activity, ActivityType.bowling)
        self.assertEqual(facts.providerTypes, ["bowling_alley", "point_of_interest"])
        self.assertEqual((facts.rating, facts.ratingCount), (4.3, 123))
        self.assertEqual(str(facts.websiteUrl), "https://example.org/venue")
        self.assertEqual(str(facts.mapsUrl), "https://maps.google.com/?cid=123")
        self.assertEqual(facts.priceLevel, "moderate")
        self.assertEqual(facts.priceRange.start.amount, Decimal("12.5"))
        self.assertEqual(facts.priceRange.end.amount, Decimal("25"))
        self.assertEqual(facts.timeZone.id, "America/New_York")
        self.assertEqual(facts.utcOffsetMinutes, -240)
        self.assertEqual(facts.observedAt["rating"], NOW)
        self.assertEqual(VenueFacts.model_validate_json(facts.model_dump_json()), facts)

    def test_all_activity_contexts_are_buildings_not_event_sessions(self):
        for activity in ActivityType:
            facts = normalize(activity=activity)
            self.assertEqual(facts.activity, activity)
            self.assertNotIsInstance(facts, ScheduledEvent)
            for field in ("start", "eventDate", "availability", "price", "experience", "openingWindows"):
                self.assertNotIn(field, facts.model_dump())

    def test_minimal_and_missing_optional_values(self):
        facts = normalize({"id": "x" * 300, "displayName": {"text": "Real readable name"}})
        self.assertEqual(facts.id, "x" * 300)  # No generated IDs or provider-unsupported length cap.
        for field in ("address", "coordinates", "providerTypes", "rating", "ratingCount", "regularOpeningHours",
                      "currentOpeningHours", "websiteUrl", "mapsUrl", "priceLevel", "priceRange", "timeZone",
                      "utcOffsetMinutes", "attributions"):
            self.assertIsNone(getattr(facts, field))
        self.assertEqual(facts.observedAt, {"name": NOW})

    def test_nulls_and_unknown_price_do_not_become_zero(self):
        raw = {**place(), "rating": None, "userRatingCount": None, "websiteUri": None,
               "regularOpeningHours": None, "priceLevel": "PRICE_LEVEL_UNSPECIFIED"}
        facts = normalize(raw)
        self.assertIsNone(facts.rating)
        self.assertIsNone(facts.ratingCount)
        self.assertIsNone(facts.priceLevel)
        self.assertIsNone(facts.regularOpeningHours)
        raw.update(userRatingCount=0, priceLevel="PRICE_LEVEL_FREE")
        self.assertEqual((normalize(raw).ratingCount, normalize(raw).priceLevel), (0, "free"))

    def test_hours_keep_overnight_current_and_regular_separate(self):
        facts = normalize()
        self.assertEqual(facts.regularOpeningHours.periods[0].close.day, 0)
        self.assertEqual(facts.currentOpeningHours.periods, [])
        self.assertFalse(facts.currentOpeningHours.openNow)
        self.assertIsNone(facts.regularOpeningHours.openNow)
        self.assertEqual(facts.currentOpeningHours.specialDays[0].isoformat(), "2026-10-24")
        raw = {**place(), "regularOpeningHours": {"periods": [{"open": {"day": 0, "hour": 0, "minute": 0}}]}}
        self.assertIsNone(normalize(raw).regularOpeningHours.periods[0].close)
        raw["regularOpeningHours"] = {}
        self.assertIsNone(normalize(raw).regularOpeningHours)
        raw["regularOpeningHours"] = {"weekdayDescriptions": ["Hours vary"]}
        self.assertIsNone(normalize(raw).regularOpeningHours.periods)

    def test_dated_truncated_points_and_timezone_not_guessed(self):
        point = {"day": 6, "hour": 0, "minute": 0,
                 "date": {"year": 2026, "month": 10, "day": 24}, "truncated": True}
        raw = {**place(), "currentOpeningHours": {"periods": [{"open": point}]}, "utcOffsetMinutes": 0}
        facts = normalize(raw)
        self.assertTrue(facts.currentOpeningHours.periods[0].open.truncated)
        self.assertIsNone(facts.timeZone)
        self.assertEqual(facts.utcOffsetMinutes, 0)

    def test_price_ranges_are_exact_and_may_have_no_upper_bound(self):
        raw = enriched()
        del raw["priceRange"]["endPrice"]
        self.assertIsNone(normalize(raw).priceRange.end)
        raw["priceRange"]["startPrice"] = {"currencyCode": "EUR", "nanos": 1}
        self.assertEqual(normalize(raw).priceRange.start.amount, Decimal("0.000000001"))
        raw["priceRange"]["startPrice"] = {"currencyCode": "USD", "units": "0"}
        self.assertEqual(normalize(raw).priceRange.start.amount, 0)

    def test_names_and_resource_names_are_not_interchangeable(self):
        for raw in ({"id": "x", "name": "places/x"}, {**place(), "displayName": "Display"},
                    {**place(), "displayName": {"text": "   "}}, {**place(), "name": "places/wrong"},
                    {**place(), "id": " original-google-id "}):
            with self.subTest(raw=raw), self.assertRaises(NormalizationError):
                normalize(raw)

    def test_invalid_detail_fields_fail_safely(self):
        invalid = [("rating", v) for v in (0, 5.1, True, "4.5", float("nan"), float("inf"))]
        invalid += [("userRatingCount", v) for v in (-1, True, 1.2, "12")]
        invalid += [("location", v) for v in ({"latitude": 91, "longitude": 0}, {"latitude": True, "longitude": 0},
                                               {"latitude": 0}, {"latitude": 0, "longitude": float("nan")} )]
        invalid += [("websiteUri", v) for v in ("javascript:alert(1)", "no-url", "ftp://example.org", "https://user:password@example.org")]
        invalid += [("types", "bowling_alley"), ("types", [""]), ("formattedAddress", "  "),
                    ("priceLevel", "FUTURE_UNKNOWN_LEVEL"), ("timeZone", {"id": "Invented/Zone"}),
                    ("utcOffsetMinutes", True), ("utcOffsetMinutes", 841), ("attributions", [{"providerUri": "bad"}]),
                    ("attributions", [{}]), ("googleMapsUri", "data:text/plain,x")]
        for key, value in invalid:
            with self.subTest(key=key, value=value), self.assertRaises(NormalizationError) as error:
                normalize({**place(), key: value})
            self.assertEqual(str(error.exception), "Google venue data is incomplete or invalid.")

    def test_malformed_hours_and_prices(self):
        invalid_hours = [{"periods": "bad"}, {"periods": [{}]}, {"periods": [{"open": {"day": 7, "hour": 2, "minute": 0}}]},
                         {"periods": [{"open": {"day": 0, "hour": 24, "minute": 0}}]},
                         {"periods": [{"open": {"day": 0, "hour": 0, "minute": 60}}]},
                         {"openNow": "true"}, {"nextOpenTime": "2026-10-24T12:00:00"},
                         {"nextOpenTime": 0}, {"nextCloseTime": "123456"},
                         {"specialDays": [{"date": {"year": 2026, "month": 2, "day": 30}}]}]
        for hours in invalid_hours:
            with self.subTest(hours=hours), self.assertRaises(NormalizationError):
                normalize({**place(), "currentOpeningHours": hours})
        for money in ({"currencyCode": "USD"}, {"currencyCode": "usd", "units": "1"},
                      {"currencyCode": "USD", "units": "-1"}, {"currencyCode": "USD", "units": 12},
                      {"currencyCode": "USD", "nanos": True}, {"currencyCode": "USD", "nanos": 1000000000}):
            with self.subTest(money=money), self.assertRaises(NormalizationError):
                normalize({**place(), "priceRange": {"startPrice": money}})
        for end in ({"currencyCode": "EUR", "units": "20"}, {"currencyCode": "USD", "units": "1"}):
            raw = enriched()
            raw["priceRange"]["endPrice"] = end
            with self.assertRaises(NormalizationError):
                normalize(raw)

    def test_collection_isolation_no_dedup_or_fabrication(self):
        raw = [enriched(), {}, None, "bad", {**place(), "rating": 9}, enriched()]
        original = deepcopy(raw)
        venues, rejected = normalize_google_places(raw, "bowling", observed_at=NOW)
        self.assertEqual((len(venues), rejected), (2, 4))
        self.assertEqual(venues[0], venues[1])  # Task 42 deduplication deliberately deferred.
        self.assertEqual(raw, original)
        self.assertEqual(normalize_google_places([], "coffee"), ([], 0))
        with self.assertRaises(NormalizationError):
            normalize_google_places({}, "coffee")

    def test_attributions_unknown_extensions_and_no_expensive_content(self):
        raw = enriched()
        raw.update(reviews=[{"text": "must not retain"}], photos=[{}], generativeSummary={"text": "ignore"}, futureField=True)
        facts = normalize(raw)
        self.assertEqual(facts.attributions[0].provider, "Synthetic credit")
        self.assertEqual(str(facts.attributions[0].uri), "https://example.org/credit")
        self.assertNotIn("must not retain", facts.model_dump_json())
        self.assertNotIn("futureField", facts.model_dump())

    def test_partial_enrichment_retains_nonmissing_facts_and_freshness(self):
        original = normalize()
        before = original.model_dump()
        later = NOW + timedelta(minutes=1)
        result = normalize_google_place({"id": original.id, "rating": 4.8, "userRatingCount": 0,
                                         "websiteUri": None, "priceLevel": "PRICE_LEVEL_UNSPECIFIED"},
                                        "bowling", observed_at=later, existing=original)
        self.assertEqual((result.id, result.name, result.rating, result.ratingCount), (original.id, original.name, 4.8, 0))
        self.assertEqual(result.websiteUrl, original.websiteUrl)
        self.assertEqual(result.priceLevel, original.priceLevel)
        self.assertEqual(result.observedAt["websiteUrl"], NOW)
        self.assertEqual(result.observedAt["rating"], later)
        self.assertEqual(original.model_dump(), before)
        older = normalize_google_place({"id": original.id, "rating": 1}, "bowling", observed_at=NOW, existing=result)
        self.assertEqual(older.rating, 4.8)

    def test_merge_identity_validation_and_attribution_retention(self):
        original = normalize()
        for identity, activity in (("wrong", "bowling"), (original.id, "food")):
            with self.assertRaises(NormalizationError):
                normalize_google_place({"id": identity, "rating": 4}, activity, observed_at=NOW, existing=original)
        for raw in ({"id": original.id, "rating": 8}, {"id": original.id, "displayName": {"text": ""}}):
            with self.assertRaises(NormalizationError):
                normalize(raw, existing=original)
        for field in ("rating", "websiteUri", "types", "userRatingCount"):
            with self.subTest(field=field), self.assertRaises(NormalizationError):
                normalize({"id": original.id, field: {"bad": {"nested": True}}}, existing=original)
        updated = normalize({"id": original.id, "attributions": []}, existing=original)
        self.assertEqual(updated.attributions, original.attributions)
        updated = normalize({"id": original.id, "attributions": enriched()["attributions"]}, existing=original)
        self.assertEqual(updated.attributions, original.attributions)
        with self.assertRaises(NormalizationError):
            normalize_google_place(place(), "bowling", observed_at=NOW.replace(tzinfo=None))
        with self.assertRaises(NormalizationError):
            normalize_google_place(place(), "bowling", observed_at=0)

    def test_nested_partial_enrichment_retains_missing_values_and_observation_times(self):
        original = normalize()
        later = NOW + timedelta(minutes=1)
        updated = normalize_google_place({"id": original.id,
            "currentOpeningHours": {"openNow": True},
            "priceRange": {"startPrice": {"currencyCode": "USD", "units": "15"}},
            "timeZone": {"version": "2026b"}}, "bowling", existing=original, observed_at=later)
        self.assertEqual(updated.currentOpeningHours.periods, [])
        self.assertEqual(updated.priceRange.end, original.priceRange.end)
        self.assertEqual(updated.timeZone.id, original.timeZone.id)
        self.assertTrue(updated.currentOpeningHours.openNow)
        self.assertEqual(updated.observedAt["currentOpeningHours.openNow"], later)
        self.assertEqual(updated.observedAt["currentOpeningHours.periods"], NOW)
        self.assertEqual(updated.observedAt["priceRange.end.amount"], NOW)
        updated = normalize_google_place({"id": original.id, "regularOpeningHours": {"periods": []}},
                                         "bowling", existing=updated, observed_at=later)
        self.assertEqual(updated.regularOpeningHours.periods, [])

    def test_discovery_bridge_no_requests_and_unchanged_field_mask(self):
        expected_mask = "places.id,places.displayName,places.formattedAddress,places.location,places.addressComponents,places.attributions,places.types,places.primaryType,nextPageToken"
        self.assertEqual(FIELD_MASK, expected_mask)
        with patch("backend.places_transport.text_search", side_effect=AssertionError("network")), \
             patch("backend.places_transport.access_token", side_effect=AssertionError("auth")), \
             patch("backend.provider_budget.OutingBudget.reserve", side_effect=AssertionError("budget")):
            discovered = parse_response({"places": [place()]}, SearchArea(name="Baltimore, MD"), 3)
            venues, rejected = normalize_discovery_candidates(discovered, "bowling", observed_at=NOW)
            self.assertEqual(rejected, 0)
            self.assertEqual(venues[0].id, discovered.candidates[0].provider_id)
            self.assertIsNone(venues[0].rating)
            normalize()  # Enriched mock parsing also makes no requests.

    def test_disabled_defaults_and_single_discovery_attempt(self):
        with patch.dict(os.environ, {}, clear=True), patch("backend.places_transport.text_search") as send:
            self.assertEqual(ProviderSettings.from_env().mode, "mock")
            with self.assertRaises(DiscoveryError):
                PlacesDiscovery(ProviderBudget().outing()).discover(request())
            send.assert_not_called()
        with patch.dict(os.environ, {"WHERETO_PLACES_DEV": "1"}), \
             patch("backend.places_transport.text_search", return_value={"places": [place()]}) as send:
            discovered = PlacesDiscovery(ProviderBudget().outing()).discover(request())
            normalize_discovery_candidates(discovered, "bowling", observed_at=NOW)
            send.assert_called_once()

    def test_mock_provider_isolation_and_planner_preservation(self):
        records = load_mock_venues()
        before = [r.model_dump() for r in records]
        with patch("backend.places_transport.text_search", side_effect=AssertionError("Google")), \
             patch("backend.venue_normalization.normalize_google_place", side_effect=AssertionError("normalizer")):
            result = recommend_plans(OutingRequest(activities=["bowling", "drinks", "food"], date="2026-11-07"))
        self.assertTrue(result.provisionalPlans)
        self.assertEqual([r.model_dump() for r in records], before)
        self.assertTrue(all(r.dataQuality.identity.value == "fictional" for r in records))
        with self.assertRaises(ValidationError):
            VenueFacts.model_validate(records[0].model_dump())


if __name__ == "__main__":
    unittest.main()
