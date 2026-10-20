"""Fixture integrity, Task 24 validation, retrieval and frontend parity."""

from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from pydantic import ValidationError

from backend.mock_data import (
    FIXTURE_PATH, SUPPORTED_ACTIVITIES, available_activities, get_mock_venue,
    get_mock_venues, load_mock_venues,
)
from backend.models import ActivityType, DataStatus, ScheduledEvent, Venue

ROOT = Path(__file__).resolve().parent.parent


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


class MockDataTests(unittest.TestCase):
    def test_load_and_validate_all_records(self):
        records = load_mock_venues()
        self.assertEqual(len(records), 123)
        self.assertEqual(len({record.id for record in records}), 123)
        self.assertEqual(sum(type(record) is Venue for record in records), 51)
        self.assertEqual(sum(isinstance(record, ScheduledEvent) for record in records), 72)
        for record in records:
            with self.subTest(id=record.id):
                self.assertEqual(type(record).model_validate_json(record.model_dump_json()), record)
                for field in ("identity", "price", "capacity", "duration", "travel", "experience"):
                    self.assertEqual(getattr(record.dataQuality, field), DataStatus.fictional)
                self.assertIsNone(record.openingHours)
                self.assertIsNone(record.availability)
                self.assertIn("fictional", record.source)
                self.assertEqual(record.dataQuality.schedule, DataStatus.fictional
                                 if record.kind == "event" else DataStatus.unknown)

    def test_all_supported_categories_have_current_samples(self):
        self.assertEqual(len(SUPPORTED_ACTIVITIES), 29)
        self.assertEqual(set(SUPPORTED_ACTIVITIES), set(ActivityType))
        self.assertEqual(available_activities(), SUPPORTED_ACTIVITIES)
        for activity in SUPPORTED_ACTIVITIES:
            records = get_mock_venues(activity)
            self.assertTrue(records)
            self.assertTrue(all(record.activity == activity for record in records))
        self.assertEqual(len(get_mock_venues("miniGolf")), 3)

    def test_exact_lookup_and_no_substitution(self):
        self.assertEqual(get_mock_venue("bowling-0").name, "Lucky Duck Lanes")
        self.assertEqual(get_mock_venue("concert-0-2026-11-07").start, 1140)
        self.assertIsNone(get_mock_venue("missing"))
        self.assertIsNone(get_mock_venue("concert-0-2026-11-08"))

    def test_scheduled_events_dates_and_times(self):
        events = get_mock_venues(kind="event")
        self.assertEqual({event.eventDate for event in events},
                         {date(2026, 11, 7), date(2026, 11, 14)})
        self.assertEqual(len(get_mock_venues("baseball", event_date="2026-11-07")), 3)
        self.assertTrue(all(event.start == 840 for event in get_mock_venues("baseball")))
        self.assertEqual(len(get_mock_venues(kind="event", event_date=date(2026, 11, 14))), 36)
        self.assertEqual(get_mock_venues("concert", event_date="2026-11-08"), [])
        self.assertEqual(get_mock_venues("concert", kind="venue"), [])
        self.assertEqual(len(get_mock_venues("coffee", event_date="2026-11-08")), 3)

    def test_missing_samples_are_separate_from_supported_categories(self):
        fixture = json.loads(FIXTURE_PATH.read_text())
        del fixture["catalog"]["coffee"]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.json"
            path.write_text(json.dumps(fixture))
            records = load_mock_venues(path)
        self.assertIn(ActivityType.coffee, SUPPORTED_ACTIVITIES)
        self.assertNotIn(ActivityType.coffee, available_activities(records))
        self.assertEqual(get_mock_venues("coffee", venues=records), [])
        self.assertEqual(available_activities([]), ())
        self.assertEqual(get_mock_venues(venues=[]), [])
        with self.assertRaises(ValueError):
            get_mock_venues("skydiving")

    def test_invalid_retrieval_criteria(self):
        for day in ("2026-02-30", "20261107", 0):
            with self.subTest(day=day), self.assertRaises(ValueError):
                get_mock_venues(event_date=day)
        with self.assertRaises(ValueError):
            get_mock_venues(kind="anything")

    def test_invalid_fixture_fails_instead_of_partial_records(self):
        fixture = json.loads(FIXTURE_PATH.read_text())
        mutations = [
            lambda f: f["catalog"]["coffee"]["prices"].__setitem__(0, -1),
            lambda f: f["catalog"]["coffee"].update(eventStart=600),
            lambda f: f["catalog"]["concert"].pop("eventStart"),
            lambda f: f["eventDates"].append("2026-02-30"),
            lambda f: f["eventDates"].append("2026-11-07"),
            lambda f: f["tiers"][0].update(capacity=0),
            lambda f: f.update(fictional=False),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            for mutate in mutations:
                bad = deepcopy(fixture)
                mutate(bad)
                path.write_text(json.dumps(bad))
                with self.subTest(mutation=mutate), self.assertRaises((ValidationError, ValueError)):
                    load_mock_venues(path)
            path.write_text("{broken")
            with self.assertRaises(ValidationError):
                load_mock_venues(path)

    def test_loads_are_independent(self):
        first = load_mock_venues()
        first[0].name = "Changed by caller"
        self.assertEqual(load_mock_venues()[0].name, "Lucky Duck Lanes")

    def test_frontend_record_parity_and_pre_migration_baseline(self):
        script = """
import { CATALOG, MOCK_EVENT_DATES, VENUES } from './lib/mock-data';
import { makePlans, EMPTY_PREFERENCES, EXAMPLE_REQUEST } from './lib/legacy/planner';
const cases = [EXAMPLE_REQUEST, ...Object.values(CATALOG).map(v => v.label + ' on 2026-11-07'),
  'Dinner and karaoke', 'Baseball and concert on 2026-11-14', 'Art and outdoors'];
console.log(JSON.stringify({venues:VENUES, activities:Object.keys(CATALOG), dates:MOCK_EVENT_DATES,
  results:cases.map(text => makePlans(text, EMPTY_PREFERENCES, {today:'2026-11-01'}))}));
"""
        completed = subprocess.run([str(ROOT / "node_modules/.bin/tsx"), "-e", script],
                                   cwd=ROOT, check=True, capture_output=True, text=True, timeout=30)
        frontend = json.loads(completed.stdout)
        self.assertEqual(set(frontend["activities"]), {a.value for a in SUPPORTED_ACTIVITIES})
        records = load_mock_venues()
        self.assertEqual(len(records), len(frontend["venues"]))
        for record, original in zip(records, frontend["venues"]):
            serialized = record.model_dump(mode="json")
            self.assertEqual({key: serialized[key] for key in original}, original)
        # Fixed hashes of actual Task 24 outputs, captured before this migration.
        # Deliberate future data/result changes must explicitly update this baseline.
        self.assertEqual(fingerprint(frontend["venues"]), "63606d6dd1ace2e7edce102cc27647e7fb61cd3dbb1db321526ebcedcae7f40f")
        self.assertEqual(fingerprint(frontend["results"]), "22b5012d12a65ff2592cf72b507fe4919db82694edb79f70a9029eb8e377b9c0")


if __name__ == "__main__":
    unittest.main()
