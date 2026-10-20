"""Task 26 generation against the validated shared fixture, with no new dataset."""

from datetime import date
from itertools import islice, product
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from backend.mock_data import FIXTURE_PATH, get_mock_venues, load_mock_venues
from backend.models import (
    ActivityType, CandidateGenerationResult, CandidateItinerary, CandidateStop,
    DataStatus, OutingRequest, ScheduledEvent,
)
from backend.planner import generate_candidates, iter_itinerary_candidates


class CandidateTests(unittest.TestCase):
    def test_single_activity_and_every_supported_category(self):
        for activity in ActivityType:
            request = OutingRequest(activities=[activity], date="2026-11-07")
            result = generate_candidates(request)
            with self.subTest(activity=activity):
                self.assertEqual(len(result.candidates), 3)
                self.assertFalse(result.errors)
                self.assertEqual([c.venues[0] for c in result.candidates],
                                 get_mock_venues(activity, event_date=request.date))

    def test_order_completeness_and_determinism(self):
        request = OutingRequest(activities=["bowling", "drinks", "movie", "coffee"])
        result = generate_candidates(request)
        expected = list(product(*(get_mock_venues(a) for a in request.activities)))
        self.assertEqual([tuple(c.venues) for c in result.candidates], expected)
        self.assertEqual(len(result.candidates), 81)  # No top-three selection.
        self.assertEqual(len({c.id for c in result.candidates}), 81)
        self.assertEqual(result, generate_candidates(request))
        for candidate in result.candidates:
            self.assertEqual([v.activity for v in candidate.venues], request.activities)

    def test_repeated_categories_and_identity_prevention(self):
        request = OutingRequest(activities=["coffee", "museum", "coffee"])
        result = generate_candidates(request)
        self.assertEqual(len(result.candidates), 18)
        for candidate in result.candidates:
            self.assertEqual([v.activity for v in candidate.venues], request.activities)
            self.assertEqual(len({v.id for v in candidate.venues}), 3)
        self.assertEqual(len(generate_candidates(OutingRequest(activities=["coffee"] * 4)).candidates), 0)

    def test_revisits_must_be_explicit(self):
        result = generate_candidates(OutingRequest(activities=["coffee", "coffee"], allowRevisits=True))
        self.assertEqual(len(result.candidates), 9)
        self.assertEqual(sum(c.venues[0].id == c.venues[1].id for c in result.candidates), 3)
        self.assertTrue(all(c.allowRevisits for c in result.candidates))

    def test_exact_event_dates_and_times(self):
        for day in ("2026-11-07", "2026-11-14"):
            request = OutingRequest(activities=["coffee", "baseball", "concert"], date=day)
            result = generate_candidates(request)
            self.assertEqual(len(result.candidates), 27)
            for candidate in result.candidates:
                self.assertEqual(candidate.date, date.fromisoformat(day))
                self.assertIsNone(candidate.stops[0].start)
                self.assertIsNone(candidate.stops[0].end)
                for stop in candidate.stops[1:]:
                    self.assertIsInstance(stop.venue, ScheduledEvent)
                    self.assertEqual(stop.venue.eventDate, candidate.date)
                    self.assertEqual(stop.start, stop.venue.start)
                    self.assertEqual(stop.end, stop.start + stop.venue.duration)
                    self.assertEqual(stop.venue.dataQuality.schedule, DataStatus.fictional)

    def test_missing_event_date_has_no_alternative_showtimes(self):
        result = generate_candidates(OutingRequest(activities=["coffee", "concert"], date="2026-11-08"))
        self.assertEqual(result.candidates, [])
        self.assertEqual(result.errors[0].code, "no_availability")
        self.assertIn("concert", result.errors[0].message)
        self.assertEqual(list(iter_itinerary_candidates(result.request)), [])
        with self.assertRaises(ValidationError):
            OutingRequest(activities=["concert"])

    def test_conflicting_and_reversed_events(self):
        for activities in (["concert", "theater"], ["concert", "baseball"], ["concert", "concert"]):
            with self.subTest(activities=activities):
                result = generate_candidates(OutingRequest(activities=activities, date="2026-11-07", allowRevisits=True))
                self.assertEqual(result.candidates, [])
                self.assertEqual(result.errors[0].code, "infeasible")

    def test_known_intervening_durations_cannot_fit_between_events(self):
        # Baseball ends at 17:00; concert starts at 19:00. Two hikes need more than two hours.
        request = OutingRequest(activities=["baseball", "hiking", "hiking", "concert"], date="2026-11-07")
        self.assertEqual(generate_candidates(request).candidates, [])

    def test_missing_samples_uses_loader_without_fabrication(self):
        fixture = json.loads(FIXTURE_PATH.read_text())
        del fixture["catalog"]["coffee"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"
            path.write_text(json.dumps(fixture))
            with patch("backend.planner.load_mock_venues", return_value=load_mock_venues(path)):
                result = generate_candidates(OutingRequest(activities=["museum", "coffee"]))
        self.assertEqual(result.candidates, [])
        self.assertEqual(result.errors[0].code, "no_availability")
        self.assertIn("coffee", result.errors[0].message)

    def test_invalid_categories_and_empty_requests_rejected_at_boundary(self):
        for activities in ([], ["skydiving"], ["coffee"] * 5):
            with self.subTest(activities=activities), self.assertRaises(ValidationError):
                OutingRequest(activities=activities)

    def test_location_is_not_silently_substituted(self):
        result = generate_candidates(OutingRequest(activities=["coffee"], location="Boston"))
        self.assertEqual(result.candidates, [])
        self.assertEqual(result.errors[0].code, "unsupported_location")
        for location in ("Baltimore", "baltimore, MD", "Baltimore Maryland"):
            self.assertTrue(generate_candidates(OutingRequest(activities=["coffee"], location=location)).candidates)

    def test_no_task27_filtering_or_ranking(self):
        request = OutingRequest(activities=["food", "coffee"], people=100, budget=0,
                                travel=0, dinner=True, cost="experience")
        result = generate_candidates(request)
        self.assertEqual(len(result.candidates), 9)
        self.assertTrue(any(v.price > 0 and v.capacity < request.people
                            for c in result.candidates for v in c.venues))
        self.assertTrue(all(s.start is None and s.end is None for c in result.candidates for s in c.stops))
        self.assertEqual(result.request, request)
        self.assertIn("feasibility has not been evaluated", result.message)

    def test_unknown_fields_preserved_and_no_invented_totals(self):
        records = load_mock_venues()
        coffee = next(v for v in records if v.activity == ActivityType.coffee)
        coffee = coffee.model_copy(update={"duration": None, "price": None, "capacity": None})
        with patch("backend.planner.load_mock_venues", return_value=[coffee]):
            candidate = generate_candidates(OutingRequest(activities=["coffee"])).candidates[0]
        self.assertEqual(candidate.venues[0], coffee)
        self.assertIsNone(candidate.stops[0].start)
        self.assertIsNone(candidate.venues[0].openingHours)
        self.assertIsNone(candidate.venues[0].availability)
        self.assertNotIn("travel", candidate.model_dump())
        self.assertNotIn("price", candidate.model_dump())
        self.assertEqual(candidate.venues[0].source, coffee.source)
        self.assertEqual(candidate.venues[0].dataQuality, coffee.dataQuality)

    def test_unknown_event_duration_keeps_end_unknown(self):
        event = get_mock_venues("concert", event_date="2026-11-07")[0].model_copy(update={"duration": None})
        with patch("backend.planner.load_mock_venues", return_value=[event]):
            candidate = generate_candidates(OutingRequest(activities=["concert"], date="2026-11-07")).candidates[0]
        self.assertEqual(candidate.stops[0].start, event.start)
        self.assertIsNone(candidate.stops[0].end)

    def test_pydantic_output_and_invalid_candidate_rejection(self):
        result = generate_candidates(OutingRequest(activities=["coffee", "museum"]))
        self.assertEqual(CandidateGenerationResult.model_validate_json(result.model_dump_json()), result)
        bad = result.model_dump(mode="json")
        bad["request"]["activities"].reverse()
        with self.assertRaises(ValidationError):
            CandidateGenerationResult.model_validate(bad)
        candidate = result.candidates[0].model_dump(mode="json")
        candidate["venues"][1] = candidate["venues"][0]
        candidate["stops"][1] = candidate["stops"][0]
        with self.assertRaises(ValidationError):
            CandidateItinerary.model_validate(candidate)
        with self.assertRaises(ValidationError):
            CandidateStop(venue=result.candidates[0].venues[0], start=600, end=630)
        event = get_mock_venues("concert", event_date="2026-11-07")[0]
        with self.assertRaises(ValidationError):
            CandidateStop(venue=event, start=event.start + 1, end=event.start + event.duration)

    def test_lazy_iteration_and_independent_candidates(self):
        request = OutingRequest(activities=["bowling", "drinks", "movie", "coffee"])
        with patch("backend.planner.CandidateItinerary", wraps=CandidateItinerary) as constructor:
            iterator = iter_itinerary_candidates(request)
            self.assertEqual(constructor.call_count, 0)
            first_two = list(islice(iterator, 2))
            self.assertEqual(constructor.call_count, 2)
        first_two[0].venues[0].name = "Changed by caller"
        self.assertNotEqual(first_two[0].venues[0].name, first_two[1].venues[0].name)
        self.assertEqual(len(list(iterator)), 79)


if __name__ == "__main__":
    unittest.main()
