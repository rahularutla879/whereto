"""Synthetic provider responses only; evidence labeling cannot access the network."""
from datetime import date, timedelta
import os
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from backend.evidence import (EvidenceLabels, FeasibilityLabels, distinct_venue_labels, feasibility_labels,
                              fictional_labels, route_labels, user_detail_label, venue_labels)
from backend.feasibility import evaluate_feasibility
from backend.mock_data import load_mock_venues
from backend.models import DataStatus
from backend.places import FIELD_MASK, DiscoveryError, require_development_discovery
from backend.routes import FIELD_MASK as ROUTE_MASK, RouteError, require_development_routes
from backend.routes import RouteLeg
from backend.test_feasibility import NOW, request, route, stop
from backend.test_places import place
from backend.test_venue_normalization import enriched
from backend.venue_models import VenueFacts
from backend.venue_quality import assess_candidates
from backend.venue_normalization import normalize_google_place


def venue(raw=None, activity="bowling", **kwargs):
    return normalize_google_place(place() if raw is None else raw, activity, observed_at=NOW, **kwargs)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        for target in ("socket.socket", "backend.places_transport.text_search",
                       "backend.places_transport.access_token", "backend.routes_transport.compute_matrix",
                       "backend.routes.GoogleRouteCalculator.calculate"):
            guard = patch(target, side_effect=AssertionError("Task 45 must remain offline"))
            guard.start()
            self.addCleanup(guard.stop)

    def test_identity_facts_are_reported_not_whole_venue_verified(self):
        facts = venue()
        labels = venue_labels(facts)
        for path in ("id", "name", "address", "coordinates.latitude", "coordinates.longitude"):
            claim = labels.claims[path]
            self.assertEqual((claim.certainty, claim.basis, claim.source.provider, claim.source.place_id),
                             ("reported", "supplied", "google_places", facts.id))
            self.assertIn("Google Maps", claim.message)
        self.assertEqual(labels.claims["activity"].source.kind, "local")
        self.assertEqual(labels.claims["availability"].certainty, "requires_confirmation")
        self.assertNotIn("verified", labels.model_dump())
        self.assertEqual(EvidenceLabels.model_validate_json(labels.model_dump_json()), labels)
        self.assertEqual(VenueFacts.model_validate_json(facts.model_dump_json()), facts)

    def test_google_brand_and_third_party_credits_preserved(self):
        facts = venue(enriched())
        attr = venue_labels(facts).attribution
        self.assertTrue(attr.google_maps_required)
        self.assertEqual(attr.brand, "Google Maps")
        self.assertTrue(attr.logo_preferred)
        self.assertTrue(attr.text_only_when_space_limited)
        self.assertEqual(attr.third_party, facts.attributions)
        self.assertEqual(str(attr.third_party[0].uri), "https://example.org/credit")
        self.assertTrue(str(attr.policy_url).endswith("places/web-service/policies"))
        # Empty provider credits are not proof that Google branding can be omitted.
        self.assertTrue(venue_labels(venue()).attribution.google_maps_required)

    def test_merged_alias_facts_retain_contributor_place_ids(self):
        raw = enriched()
        raw["displayName"] = {"text": "Synthetic Bowling Lanes"}
        first = venue(raw)
        raw2 = {**raw, "id": "second-id", "name": "places/second-id", "rating": 4.9}
        second = normalize_google_place(raw2, "bowling", observed_at=NOW + timedelta(minutes=1))
        merged = assess_candidates([first, second]).venues[0]
        self.assertEqual(len(merged.sources), 2)
        labels = distinct_venue_labels(merged)
        self.assertEqual(labels.claims["rating"].source.place_id, "second-id")
        self.assertEqual({s.place_id for s in labels.claims["name"].contributing_sources}, {first.id, second.id})
        self.assertEqual(labels.attribution.third_party, merged.facts.attributions)

    def test_official_links_preserved_or_documented_encoded_link(self):
        supplied = venue(enriched())
        source = venue_labels(supplied).claims["name"].source
        self.assertEqual((source.url, source.link_origin), (supplied.mapsUrl, "provider"))
        generated = venue({"id": "ID_1-&x", "displayName": {"text": "A & B / Café"}})
        source = venue_labels(generated).claims["name"].source
        self.assertEqual(source.link_origin, "documented_maps_url")
        link = urlsplit(str(source.url))
        self.assertEqual(link.netloc, "www.google.com")
        self.assertEqual(parse_qs(link.query), {"api": ["1"], "query": [generated.name], "query_place_id": [generated.id]})
        huge = venue({"id": "x" * 2100, "displayName": {"text": "Synthetic"}})
        self.assertIsNone(venue_labels(huge).claims["name"].source.url)

    def test_missing_optional_fields_never_become_false_free_or_closed(self):
        facts = venue()
        labels = venue_labels(facts)
        for key in ("rating", "ratingCount", "websiteUrl", "regularOpeningHours", "currentOpeningHours", "priceLevel", "priceRange", "businessStatus", "price"):
            self.assertEqual(labels.claims[key].certainty, "unknown")
        self.assertEqual(labels.claims["rating"].basis, "not_retrieved")
        self.assertEqual(labels.claims["availability"].basis, "not_checked")
        self.assertEqual(labels.claims["price"].message, "Price information unavailable.")
        self.assertIsNone(facts.priceLevel)
        self.assertIsNone(facts.currentOpeningHours)

    def test_partial_enterprise_style_fields_and_missing_nested_values(self):
        original = venue({**place(), "rating": 4.5, "userRatingCount": 0,
                          "priceLevel": "PRICE_LEVEL_FREE", "currentOpeningHours": {"openNow": False},
                          "priceRange": {"startPrice": {"units": "0", "currencyCode": "USD"}}})
        labels = venue_labels(original)
        for key in ("rating", "ratingCount", "priceLevel", "priceRange.start.amount", "currentOpeningHours.openNow"):
            self.assertEqual(labels.claims[key].certainty, "provisional")
            self.assertEqual(labels.claims[key].observed_at, NOW)
        for key in ("currentOpeningHours.periods", "priceRange.end", "websiteUrl"):
            self.assertEqual(labels.claims[key].certainty, "unknown")
        self.assertEqual(labels.claims["price"].certainty, "unknown")
        later = NOW + timedelta(minutes=5)
        updated = normalize_google_place({"id": original.id, "rating": 4.8}, "bowling", existing=original, observed_at=later)
        newer = venue_labels(updated)
        self.assertEqual(newer.claims["rating"].observed_at, later)
        self.assertEqual(newer.claims["currentOpeningHours.openNow"].observed_at, NOW)
        self.assertEqual(newer.claims["ratingCount"].observed_at, NOW)
        self.assertEqual(original.ratingCount, 0)

    def test_regular_hours_and_explicit_dates_are_not_session_availability(self):
        regular = venue(enriched(), "movie")
        labels = venue_labels(regular)
        self.assertIn("holidays", labels.claims["regularOpeningHours.periods"].message)
        self.assertEqual(labels.claims["regularOpeningHours.periods"].explicit_dates, [])
        self.assertEqual(labels.claims["currentOpeningHours.specialDays"].explicit_dates, [date(2026, 10, 24)])
        dated = venue_labels(stop().venue)
        self.assertEqual(dated.claims["currentOpeningHours.periods"].explicit_dates, [date(2026, 10, 24)])
        self.assertEqual(dated.claims["currentOpeningHours.periods"].certainty, "provisional")
        self.assertEqual(labels.claims["session"].message, "Movie showtime not verified.")
        food = venue_labels(venue(enriched(), "food"))
        self.assertEqual(food.claims["reservation"].certainty, "requires_confirmation")
        self.assertEqual(food.claims["availability"].certainty, "requires_confirmation")

    def test_unknown_hours_and_supplied_empty_periods_are_distinct(self):
        empty = venue_labels(venue({**place(), "currentOpeningHours": {"periods": []}}))
        absent = venue_labels(venue())
        self.assertEqual(empty.claims["currentOpeningHours.periods"].certainty, "provisional")
        self.assertEqual(empty.claims["currentOpeningHours.periods"].basis, "supplied")
        self.assertEqual(absent.claims["currentOpeningHours"].certainty, "unknown")
        # Actual rejection is decided by Task 44 with date/receipt/schedule context.
        result = evaluate_feasibility(request(stops=[stop(periods=[])]))
        public = feasibility_labels(result)
        self.assertEqual(public.state, "infeasible")
        self.assertIn("conflict", public.checks[0].label.message)

    def test_routes_estimates_direction_mode_and_limitations(self):
        for mode in ("drive", "walk"):
            leg = route(a="b", b="a", seconds="720s", mode=mode)
            before = leg.model_dump()
            labels = route_labels(leg)
            self.assertEqual(labels.claims["duration_seconds"].certainty, "estimated")
            self.assertEqual(labels.claims["distance_meters"].basis, "computed")
            self.assertIn("12.0 minutes", labels.claims["duration_seconds"].message)
            self.assertEqual(leg.model_dump(), before)
            self.assertEqual((leg.origin_id, leg.destination_id, leg.mode), ("b", "a", mode))
            self.assertEqual(leg.estimate_type, "traffic_unaware" if mode == "drive" else "walking")
            self.assertTrue(labels.attribution.google_maps_required)
            self.assertIn("not guaranteed", labels.attribution.notices[0])
            self.assertIn("live traffic" if mode == "drive" else "beta", labels.attribution.notices[0])

    def test_unreachable_and_missing_routes_are_not_zero(self):
        for leg in (route(condition="ROUTE_NOT_FOUND"), route(status={"code": 7})):
            labels = route_labels(leg)
            self.assertIsNone(leg.duration_minutes)
            self.assertEqual(labels.claims["duration_seconds"].certainty, "unknown")
        self.assertEqual(route_labels(route(condition="ROUTE_NOT_FOUND")).claims["status"].certainty, "reported")
        self.assertEqual(route_labels(route(status={"code": 7})).claims["status"].certainty, "unknown")

    def test_same_location_is_local_and_inconsistent_metadata_is_unverified(self):
        local = RouteLeg(origin_id="a", destination_id="a", mode="walk", status="same_location",
                         provider="local_identity", estimate_type="same_location", duration_seconds=0,
                         duration_minutes=0, distance_meters=0)
        labels = route_labels(local)
        self.assertEqual(labels.claims["duration_seconds"].source.kind, "local")
        self.assertFalse(labels.attribution.google_maps_required)
        self.assertIn("Same venue", labels.claims["duration_seconds"].message)
        inconsistent = route().model_copy(update={"estimate_type": "walking"})
        self.assertEqual(route_labels(inconsistent).claims["duration_seconds"].certainty, "unknown")

    def test_feasibility_states_reuse_task44_without_inventing_verification(self):
        for req, expected in ((request(), "feasible"), (request(max_leg_minutes=1), "infeasible"), (request(routes=[]), "unverified")):
            result = evaluate_feasibility(req)
            before = result.model_dump()
            labels = feasibility_labels(result)
            self.assertEqual(labels.state, expected)
            self.assertEqual([c.state for c in labels.checks], [c.state for c in result.checks])
            self.assertIn("availability are not verified", labels.scope)
            self.assertEqual(result.model_dump(), before)
            self.assertEqual(FeasibilityLabels.model_validate_json(labels.model_dump_json()), labels)

    def test_known_violation_survives_other_unknown_and_messages_are_safe(self):
        req = request(max_leg_minutes=1)
        req.stops[0].venue.currentOpeningHours = None
        result = evaluate_feasibility(req)
        labels = feasibility_labels(result)
        self.assertEqual(labels.state, "infeasible")
        self.assertIn("unverified", {c.state for c in labels.checks})
        self.assertIn("other details may remain unverified", labels.message)
        for check in result.checks:
            self.assertNotIn(check.code, labels.model_dump_json())
            self.assertNotIn(check.evidence_ref, labels.model_dump_json())
        result.checks[0].code = "sensitive_unknown_future_code"
        self.assertNotIn("sensitive", feasibility_labels(result).model_dump_json())

    def test_stale_hours_and_movie_remain_unverified(self):
        req = request(stops=[stop(activity="movie", now=NOW - timedelta(days=1))])
        labels = feasibility_labels(evaluate_feasibility(req))
        self.assertEqual(labels.state, "unverified")
        self.assertEqual({c.state for c in labels.checks}, {"unverified"})

    def test_fictional_and_user_sources_do_not_become_google(self):
        records = load_mock_venues()
        for record in records:
            before = record.model_dump()
            labels = fictional_labels(record)
            self.assertEqual(labels.claims["name"].certainty, "fictional")
            self.assertEqual(labels.claims["price"].source.kind, "fixture")
            self.assertEqual(labels.claims["openingWindows"].certainty, "unknown")
            self.assertFalse(labels.attribution.google_maps_required)
            self.assertEqual(record.model_dump(), before)
        event = next(v for v in records if v.kind == "event")
        self.assertEqual(fictional_labels(event).claims["start"].certainty, "fictional")
        records[0].dataQuality.price = DataStatus.unknown
        self.assertEqual(fictional_labels(records[0]).claims["price"].certainty, "unverified")
        records[0].dataQuality.identity = DataStatus.unknown
        with self.assertRaises(ValueError):
            fictional_labels(records[0])
        self.assertEqual(user_detail_label().source.kind, "user")
        self.assertEqual(user_detail_label().certainty, "unverified")

    def test_default_gates_and_masks_unchanged(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(RouteError):
                require_development_routes()
            with self.assertRaises(DiscoveryError):
                require_development_discovery()
        self.assertEqual(FIELD_MASK, "places.id,places.displayName,places.formattedAddress,places.location,places.addressComponents,places.attributions")
        self.assertEqual(ROUTE_MASK, "originIndex,destinationIndex,status,condition,distanceMeters,duration")
