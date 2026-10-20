"""Model validation plus contract checks against the unchanged TypeScript planner."""

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import subprocess
import unittest

from fastapi import FastAPI
from pydantic import ValidationError

from backend.models import (
    ActivityType, CostPreference, DataQuality, DataStatus, Itinerary,
    ItineraryStop, OutingRequest, PlanningError, PlanningResult, ScheduledEvent,
    TransportationMode, Venue,
)


def venue():
    return dict(id="coffee-0", name="Daylight Coffee", activity="coffee",
                kind="venue", neighborhood="Harbor East", price=4, duration=30,
                zone=0, experience=1, capacity=4)


def event():
    return {**venue(), "id": "concert-0-2026-11-07", "activity": "concert",
            "kind": "event", "eventDate": "2026-11-07", "start": 1140,
            "duration": 120, "price": 20}


def itinerary(record=None):
    record = record or venue()
    start = record.get("start", 600)
    return dict(id="plan-1", title="Sample", description="Fictional outing",
                theme="peach", label="THE BUDGET PICK", venues=[record],
                stops=[dict(venue=record, start=start, end=start + record["duration"])],
                price=record["price"], travel=0, duration=record["duration"],
                people=4, date=record.get("eventDate", "Any day"))


class RequestTests(unittest.TestCase):
    def test_defaults_optional_values_and_order(self):
        request = OutingRequest(activities=["museum", "coffee"])
        self.assertEqual(request.people, 4)
        self.assertEqual(request.location, "Baltimore")
        self.assertEqual(request.cost, CostPreference.balanced)
        self.assertEqual(request.activities, [ActivityType.museum, ActivityType.coffee])
        for field in ("budget", "travel", "date", "transport"):
            self.assertIsNone(getattr(request, field))
        self.assertEqual(OutingRequest(activities=["coffee"], location=" Boston ").location, "Boston")

    def test_all_preferences_and_boundaries(self):
        for cost in CostPreference:
            for mode in TransportationMode:
                request = OutingRequest(activities=["coffee"], people=100,
                                        budget=100000, travel=1440, cost=cost,
                                        transport=mode, dinner=True, date="2026-11-07")
                self.assertEqual(request.date, date(2026, 11, 7))
        request = OutingRequest(activities=["outdoors"], people=1, budget=0, travel=0)
        self.assertEqual((request.budget, request.travel), (0, 0))
        # Accepted requests can still be infeasible; catalog capacity is not a request limit.
        self.assertEqual(OutingRequest(activities=["coffee"], people=21).people, 21)

    def test_request_json_round_trip(self):
        data = dict(activities=["miniGolf", "concert"], people=8,
                    location="Baltimore", date="2026-11-07", budget=35.50,
                    travel=0, cost="experience", transport=None, dinner=False)
        request = OutingRequest.model_validate_json(json.dumps(data))
        self.assertEqual(request.model_dump(mode="json", exclude_unset=True), data)
        self.assertEqual(OutingRequest.model_validate_json(request.model_dump_json()), request)
        with self.assertRaises(ValidationError):
            OutingRequest(activities=["coffee"], budget="")

    def test_invalid_inputs(self):
        cases = [
            {"activities": []}, {"activities": ["coffee"] * 5},
            {"activities": ["skydiving"]}, {"allowRevisits": "yes"},
            {"people": 0}, {"people": -1}, {"people": 101}, {"people": 2.5},
            {"people": True}, {"people": "4"}, {"budget": -1},
            {"budget": 100001}, {"budget": float("inf")}, {"budget": float("nan")},
            {"budget": True}, {"travel": -1}, {"travel": 1441}, {"travel": 1.5},
            {"travel": True}, {"location": " "}, {"date": "2026-02-30"},
            {"date": "20261107"}, {"date": "2026-11-07T00:00:00"}, {"date": 0},
            {"cost": "premium"}, {"transport": "teleport"}, {"dinner": "yes"},
            {"budegt": 10},
        ]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                OutingRequest.model_validate({"activities": ["coffee"], **changes})

    def test_event_date_required_but_not_limited_to_mock_fixtures(self):
        for activity in ("baseball", "basketball", "football", "soccer", "hockey",
                         "sports", "concert", "theater", "musical", "ballet", "opera", "comedy"):
            with self.subTest(activity=activity):
                with self.assertRaises(ValidationError):
                    OutingRequest(activities=[activity])
                self.assertEqual(OutingRequest(activities=[activity], date="2027-01-01").date,
                                 date(2027, 1, 1))


class VenueAndScheduleTests(unittest.TestCase):
    def test_unknown_and_fictional_are_distinct_from_zero_and_verified(self):
        unknown = Venue(id="unknown", name="Unresearched", activity="coffee")
        self.assertIsNone(unknown.price)
        self.assertIsNone(unknown.capacity)
        self.assertIsNone(unknown.openingHours)
        self.assertIsNone(unknown.availability)
        self.assertEqual(unknown.dataQuality.price, DataStatus.unknown)
        fictional = Venue.model_validate({**venue(), "price": 0,
                                         "dataQuality": {"price": "fictional", "capacity": "fictional"}})
        self.assertEqual(fictional.price, 0)
        self.assertEqual(fictional.dataQuality.price, DataStatus.fictional)
        self.assertEqual(DataQuality(travel="estimated").travel, DataStatus.estimated)
        self.assertEqual(DataQuality(identity="verified").identity, DataStatus.verified)

    def test_event_required_fields_and_category(self):
        self.assertEqual(ScheduledEvent.model_validate(event()).start, 1140)
        for field in ("eventDate", "start"):
            data = event()
            del data[field]
            with self.subTest(field=field), self.assertRaises(ValidationError):
                ScheduledEvent.model_validate(data)
        for changes in ({"eventDate": "2026-02-30"}, {"start": -1}, {"start": 1440},
                        {"start": 1140.5}, {"start": 1430}, {"activity": "coffee"}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                ScheduledEvent.model_validate({**event(), **changes})
        with self.assertRaises(ValidationError):
            Venue.model_validate({**venue(), "activity": "concert"})

    def test_venue_numeric_validation(self):
        for changes in ({"capacity": 0}, {"capacity": 2.5}, {"price": -1},
                        {"price": float("nan")}, {"duration": 0}, {"duration": 1441},
                        {"zone": -1}, {"experience": float("inf")}):
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                Venue.model_validate({**venue(), **changes})
        self.assertEqual(Venue.model_validate({**venue(), "capacity": 1000}).capacity, 1000)

    def test_stop_times_and_midnight(self):
        self.assertEqual(ItineraryStop(venue=venue(), start=1410, end=1440).end, 1440)
        for start, end in ((-1, 29), (1440, 1470), (600, 600), (600, 599),
                           (600.5, 630), (600, 631), (1411, 1441)):
            with self.subTest(start=start, end=end), self.assertRaises(ValidationError):
                ItineraryStop(venue=venue(), start=start, end=end)
        with self.assertRaises(ValidationError):
            ItineraryStop(venue=event(), start=1141, end=1261)


class ResultTests(unittest.TestCase):
    def test_itinerary_and_event_round_trip(self):
        for record in (venue(), event()):
            data = itinerary(record)
            parsed = Itinerary.model_validate(data)
            self.assertEqual(parsed.model_dump(mode="json", exclude_unset=True), data)
            self.assertEqual(Itinerary.model_validate_json(parsed.model_dump_json()), parsed)
        self.assertIsInstance(Itinerary.model_validate(itinerary(event())).stops[0].venue, ScheduledEvent)

    def test_inconsistent_itineraries_rejected(self):
        cases = [{"people": 5}, {"duration": 31}, {"price": 5}, {"travel": 1},
                 {"venues": []}, {"stops": []}, {"date": "not-a-date"}]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValidationError):
                Itinerary.model_validate({**itinerary(), **changes})
        for outing_date in ("Any day", "2026-11-14"):
            with self.assertRaises(ValidationError):
                Itinerary.model_validate({**itinerary(event()), "date": outing_date})
        data = itinerary()
        data["venues"][0] = {**venue(), "name": "Different"}
        with self.assertRaises(ValidationError):
            Itinerary.model_validate(data)

    def test_overlap_and_travel_gaps(self):
        data = itinerary()
        second = {**venue(), "id": "food-0", "activity": "food"}
        data.update(venues=[venue(), second],
                    stops=[dict(venue=venue(), start=600, end=630),
                           dict(venue=second, start=640, end=670)],
                    price=8, travel=10, duration=70)
        self.assertEqual(Itinerary.model_validate(data).travel, 10)
        for start, end, duration, travel in ((620, 650, 50, 0), (640, 670, 70, 11)):
            bad = deepcopy(data)
            bad["stops"][1].update(start=start, end=end)
            bad.update(duration=duration, travel=travel)
            with self.assertRaises(ValidationError):
                Itinerary.model_validate(bad)

    def test_errors_empty_results_and_no_partial_plans(self):
        error = PlanningError(code="infeasible", message="No option fits", field="budget")
        data = dict(plans=[], message=error.message, location="Baltimore",
                    activities=["coffee"], notes=[], errors=[error])
        self.assertEqual(PlanningResult(**data).errors[0].field, "budget")
        self.assertEqual(PlanningResult(**{**data, "errors": []}).plans, [])
        with self.assertRaises(ValidationError):
            PlanningResult(**{**data, "plans": [itinerary()]})
        for plans, activities in (([itinerary(), itinerary()], ["coffee"]),
                                   ([itinerary()], ["food"])):
            with self.assertRaises(ValidationError):
                PlanningResult(**{**data, "errors": [], "plans": plans, "activities": activities})

    def test_models_work_in_fastapi_openapi(self):
        app = FastAPI()

        @app.post("/contract-test", response_model=PlanningResult)
        def contract_test(request: OutingRequest):
            raise NotImplementedError  # Schema test only; not part of backend.main.

        schema = app.openapi()
        self.assertIn("OutingRequest", schema["components"]["schemas"])
        self.assertIn("PlanningResult", schema["components"]["schemas"])
        self.assertIn("ScheduledEvent", schema["components"]["schemas"])
        from backend.main import app as actual_app
        self.assertEqual(set(actual_app.openapi()["paths"]), {"/health", "/api/plans/generate"})

    def test_current_typescript_catalog_and_planner_contract(self):
        # Execute the source of truth instead of maintaining a second Python catalog.
        root = Path(__file__).resolve().parent.parent
        script = """
import { CATALOG } from './lib/mock-data';
import { makePlans, EMPTY_PREFERENCES } from './lib/legacy/planner';
const run = (text, prefs = {}) => makePlans(text, {...EMPTY_PREFERENCES, ...prefs}, {today:'2026-11-01'});
console.log(JSON.stringify({activities:Object.keys(CATALOG), results:[
  ...Object.values(CATALOG).map(v => run(v.label + ' on 2026-11-07')),
  run('Bowling, drinks and movie'), run('Baseball and concert on 2026-11-07'),
  run('Art and outdoors', {budget:'0'}), run('Dinner and karaoke', {people:'12'}),
  run('Dinner and karaoke', {people:'21'}), run('Skydiving'),
  run('Coffee in Boston'), run('Concert'), run('Bowling', {travel:'0'})
]}));
"""
        completed = subprocess.run([str(root / "node_modules/.bin/tsx"), "-e", script],
                                   cwd=root, check=True, capture_output=True, text=True, timeout=30)
        data = json.loads(completed.stdout)
        self.assertEqual(set(data["activities"]), {activity.value for activity in ActivityType})
        for result in data["results"]:
            with self.subTest(message=result["message"]):
                model = PlanningResult.model_validate(result)
                self.assertEqual(model.model_dump(mode="json", exclude_unset=True), result)
        self.assertTrue(all(result["plans"] for result in data["results"][:29]))


if __name__ == "__main__":
    unittest.main()
