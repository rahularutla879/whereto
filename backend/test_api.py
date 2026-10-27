"""Task 28 real HTTP boundary tests, no additional test dependencies."""
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class PlanningApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.listener = socket.socket()
        cls.listener.bind(("127.0.0.1", 0))
        cls.url = f"http://127.0.0.1:{cls.listener.getsockname()[1]}"
        cls.process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:app", "--fd",
             str(cls.listener.fileno()), "--log-level", "warning"],
            cwd=Path(__file__).resolve().parent.parent, pass_fds=(cls.listener.fileno(),))
        cls.addClassCleanup(cls.stop)
        deadline = time.monotonic() + 10
        while True:
            try:
                with urlopen(cls.url + "/health", timeout=1):
                    break
            except (URLError, TimeoutError):
                if time.monotonic() > deadline:
                    raise RuntimeError("API failed to start")
                time.sleep(.05)

    @classmethod
    def stop(cls):
        cls.process.terminate()
        cls.process.wait(timeout=5)
        cls.listener.close()

    def post(self, payload, status=200):
        payload={"startingLocation":{"point":{"id":"Mock_origin_0","coordinates":{"latitude":0,"longitude":0}},"explicitly_authorized":True,"source":"mock"},**payload}
        request = Request(self.url + "/api/plans/generate", data=json.dumps(payload).encode(),
                          headers={"Content-Type": "application/json"})
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            self.assertEqual(response.status, status)
            return json.load(response)

    def options(self, payload):
        data = self.post({"date": "2026-11-07", **payload})
        return data, data["plans"] + data["provisionalPlans"]

    def test_mandatory_origin_and_fictional_first_leg_boundaries(self):
        missing=self.post({'activities':['coffee'],'date':'2026-11-07','startingLocation':None},422)
        self.assertEqual(missing['code'],'origin_required')
        for mode,value,exclusive,accepted in [('flexible',2.5,False,True),('flexible',2.49,False,False),('strict',5,True,False),('strict',5,False,True)]:
            result=self.post({'activities':['coffee'],'date':'2026-11-07','firstTravel':{'value':value,'unit':'minutes','mode':mode,'exclusive':exclusive}})
            plans=result['plans']+result['provisionalPlans']
            self.assertEqual(bool(plans),accepted)
            if plans:self.assertTrue(plans[0]['firstLeg']['fictional'])

    def test_multi_activity_keeps_python_evidence_and_order(self):
        data, plans = self.options({"activities": ["bowling", "drinks", "movie"]})
        self.assertEqual(len(plans), 3)
        self.assertFalse(data["plans"])
        for plan in plans:
            self.assertTrue(plan["candidate"]["id"].startswith("candidate-"))
            self.assertEqual([s["venue"]["activity"] for s in plan["stops"]], ["bowling", "drinks", "movie"])
            self.assertEqual(plan["costPerPerson"], sum(q["amount"] for q in plan["prices"]))
            self.assertTrue(all(q["status"] == "fictional" for q in plan["legs"]))
            self.assertTrue(any(i["code"] == "unknown_openingHours" for i in plan["issues"]))

    def test_activities_and_modes_change_first_plan(self):
        identities = []
        for mode in ("budget", "balanced", "experience"):
            _, plans = self.options({"activities": ["coffee"], "cost": mode})
            identities.append(plans[0]["candidate"]["venues"][0]["id"])
        self.assertEqual(identities, ["coffee-0", "coffee-1", "coffee-2"])
        _, plans = self.options({"activities": ["museum"]})
        self.assertEqual(plans[0]["stops"][0]["venue"]["activity"], "museum")

    def test_budget_travel_and_zero_limits(self):
        _, plans = self.options({"activities": ["food", "karaoke"], "budget": 25, "travel": 5})
        self.assertTrue(plans)
        self.assertTrue(all(p["costPerPerson"] <= 25 and p["totalTravel"] <= 5 for p in plans))
        for limits in ({"budget": 0}, {"travel": 0}, {"people": 21}):
            data, plans = self.options({"activities": ["food", "karaoke"], **limits})
            self.assertFalse(plans)
            self.assertTrue(data["errors"])

    def test_scheduled_matching_nonmatching_and_conflicting(self):
        data, plans = self.options({"activities": ["baseball", "concert"], "date": "2026-11-07"})
        self.assertTrue(data["plans"])
        self.assertTrue(all(p["feasibility"] == "confirmed" for p in plans))
        self.assertTrue(all(s["start"] == s["venue"]["start"] for p in plans for s in p["stops"]))
        for payload in ({"activities": ["concert"], "date": "2026-11-08"},
                        {"activities": ["concert", "theater"], "date": "2026-11-07"}):
            data, plans = self.options(payload)
            self.assertFalse(plans)
            self.assertTrue(data["errors"])

    def test_endpoint_preserves_unknown_cost_and_duration(self):
        from unittest.mock import patch
        from backend.main import generate_plan
        from backend.mock_data import get_mock_venues
        from backend.real_planning import PlannerInput as OutingRequest
        records = [v.model_copy(update={"price": None, "duration": None})
                   for v in get_mock_venues("coffee")]
        with patch("backend.planner.load_mock_venues", return_value=records):
            result = generate_plan(OutingRequest(activities=["coffee"], date="2026-11-07",startingLocation={"point":{"id":"Mock_origin_0","coordinates":{"latitude":0,"longitude":0}},"explicitly_authorized":True,"source":"mock"}))
        self.assertFalse(result.plans)
        self.assertTrue(result.provisionalPlans)
        for plan in result.provisionalPlans:
            self.assertIsNone(plan.costPerPerson)
            self.assertIsNone(plan.groupCost)
            self.assertIsNone(plan.stops[0].end)
            self.assertTrue({"unknown_price", "unknown_duration"} <= {i.code for i in plan.issues})

    def test_past_date_is_rejected_before_final_planning(self):
        data = self.post({"activities": ["coffee"], "date": "2000-01-01"}, 422)
        self.assertIn("date or time window", data["message"])
        self.assertNotIn("Traceback", str(data))

    def test_invalid_and_unsupported_requests(self):
        for payload in ({}, {"activities": ["coffee"]}, {"activities": ["coffee"], "date": None}, {"activities": []}, {"activities": ["coffee"], "people": 0},
                        {"activities": ["coffee"], "budget": -1}, {"activities": ["concert"]},
                        {"activities": ["concert"], "date": "2026-02-30"},
                        {"activities": ["coffee"], "unexpected": True}):
            data = self.post(payload, 422)
            self.assertEqual(data["code"], "invalid_request")
            self.assertTrue(data["issues"])
        self.assertEqual(self.post({"activities": ["skydiving"]}, 422)["code"], "unsupported_request")


if __name__ == "__main__":
    unittest.main()
