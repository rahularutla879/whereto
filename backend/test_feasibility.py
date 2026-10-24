"""Invented provider fixtures only. All network/auth/calculation is forbidden."""
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from backend.feasibility import (EvidenceStop, FeasibilityInput, FeasibilityResult,
                                 evaluate_feasibility, filter_feasible_candidates)
from backend.routes import AuthorizedStart, RoutePoint, RouteLeg, parse_matrix
from backend.test_routes import element, point
from backend.venue_normalization import normalize_google_place

NOW = datetime(2026, 10, 24, 12, tzinfo=timezone.utc)


def endpoint(day, hour, minute=0):
    d = date.fromisoformat(day)
    return {"day": (d.weekday() + 1) % 7, "hour": hour, "minute": minute,
            "date": {"year": d.year, "month": d.month, "day": d.day}}


def period(start="2026-10-24", opening=9, end="2026-10-24", closing=22):
    return {"open": endpoint(start, opening), "close": endpoint(end, closing)}


def stop(identity="a", arrival="2026-10-24T14:00:00Z", departure="2026-10-24T15:00:00Z",
         periods=None, now=NOW, activity="bowling", zone="America/New_York"):
    venue = normalize_google_place({"id": identity, "displayName": {"text": "Synthetic venue"},
                                    "timeZone": {"id": zone},
                                    "currentOpeningHours": {"periods": [period()] if periods is None else periods}},
                                   activity, observed_at=now)
    return EvidenceStop(venue=venue, arrival=arrival, departure=departure,
                        hours_request_date=now.astimezone(ZoneInfo(zone)).date())


def route(a="a", b="b", seconds="600s", mode="drive", **changes):
    return parse_matrix([element(duration=seconds, **changes)], [point(a)], [point(b)], mode)[0]


def request(stops=None, routes=None, **changes):
    return FeasibilityInput(candidate_id="synthetic", mode="drive", evaluated_at=NOW,
                            stops=stops or [stop(), stop("b", "2026-10-24T15:10:00Z", "2026-10-24T16:00:00Z")],
                            routes=[route()] if routes is None else routes, **changes)


class FeasibilityTests(unittest.TestCase):
    def setUp(self):
        for target in ("socket.socket", "backend.routes_transport.compute_matrix",
                       "backend.routes.GoogleRouteCalculator.calculate", "backend.places_transport.access_token"):
            guard = patch(target, side_effect=AssertionError("Task 44 must stay offline"))
            guard.start()
            self.addCleanup(guard.stop)

    def evaluate(self, req=None):
        return evaluate_feasibility(req or request())

    def codes(self, result):
        return {c.code for c in result.checks}

    def test_valid_modes_and_exact_inclusive_boundary(self):
        for mode in ("drive", "walk"):
            req = request(routes=[route(mode=mode)], max_leg_minutes=10)
            req.mode = mode
            self.assertEqual(self.evaluate(req).state, "feasible")
        self.assertEqual(self.evaluate(request(routes=[route(seconds="0s")], max_leg_minutes=0)).state, "feasible")

    def test_nanosecond_violation_never_rounds_down(self):
        for duration in ("600.000000001s", "600.1s"):
            result = self.evaluate(request(routes=[route(seconds=duration)], max_leg_minutes=10))
            self.assertEqual(result.state, "infeasible")
            self.assertIn("leg_limit_exceeded", self.codes(result))

    def test_large_protobuf_duration_retains_exact_nanos(self):
        leg = route(seconds="999999999999.000000001s")
        self.assertEqual(leg.duration_nanoseconds, 999999999999000000001)
        result = self.evaluate(request(routes=[leg], max_leg_minutes=Decimal("999999999999") / 60))
        self.assertIn("leg_limit_exceeded", self.codes(result))

    def test_direction_and_mode_are_required(self):
        for evidence in ([route("b", "a")], [route(mode="walk")]):
            self.assertEqual(self.evaluate(request(routes=evidence)).travel_state, "unverified")
        result = self.evaluate(request(routes=[route(), route("b", "a", "1200s")], max_leg_minutes=10))
        self.assertEqual(result.state, "feasible")
        reverse = request(stops=[stop("b"), stop("a", "2026-10-24T16:00:00Z", "2026-10-24T17:00:00Z")],
                          routes=[route(), route("b", "a", "1200s")], max_leg_minutes=10)
        self.assertEqual(self.evaluate(reverse).state, "infeasible")

    def test_unreachable_failed_missing_and_duplicate_evidence(self):
        cases = [([], "unverified", "missing_route"),
                 ([route(condition="ROUTE_NOT_FOUND")], "infeasible", "unreachable_route"),
                 ([route(status={"code": 14})], "unverified", "route_error"),
                 ([route(), route()], "unverified", "ambiguous_route")]
        for evidence, state, code in cases:
            result = self.evaluate(request(routes=evidence))
            self.assertEqual(result.travel_state, state)
            self.assertIn(code, self.codes(result))
        incomplete = parse_matrix([], [point("a")], [point("b")], "drive")
        self.assertEqual(self.evaluate(request(routes=incomplete)).travel_state, "unverified")

    def test_first_leg_separate_limit_and_no_start_assumption(self):
        req = request(max_first_leg_minutes=0)
        self.assertEqual(self.evaluate(req).state, "feasible")
        req.starting_location = AuthorizedStart(point=RoutePoint(id="start", place_id="Synthetic_start"), explicitly_authorized=True)
        self.assertEqual(self.evaluate(req).travel_state, "unverified")
        req.routes.append(route("start", "a", "60.000000001s"))
        req.max_first_leg_minutes = Decimal(1)
        self.assertIn("first_leg_limit_exceeded", self.codes(self.evaluate(req)))
        req.max_first_leg_minutes = Decimal(2)
        req.max_total_minutes = Decimal(10)
        self.assertEqual(self.evaluate(req).state, "feasible")
        with self.assertRaises(ValidationError):
            AuthorizedStart(point=point("start"), explicitly_authorized=False)

    def test_transfer_gap_compared_in_absolute_seconds(self):
        req = request()
        req.stops[1].arrival -= timedelta(microseconds=1)
        self.assertIn("insufficient_transfer_time", self.codes(self.evaluate(req)))
        req.stops[1].arrival = datetime.fromisoformat("2026-10-24T10:00:00-04:00")
        self.assertEqual(self.evaluate(req).state, "infeasible")

    def test_total_known_lower_bound_and_unknown_precedence(self):
        req = request(stops=[stop(), stop("b", "2026-10-24T16:00:00Z", "2026-10-24T17:00:00Z"),
                             stop("c", "2026-10-24T18:00:00Z", "2026-10-24T19:00:00Z")], max_total_minutes=9)
        result = self.evaluate(req)
        self.assertEqual(result.state, "infeasible")
        self.assertIn("missing_route", self.codes(result))
        self.assertIn("total_travel_limit_exceeded", self.codes(result))

    def test_open_throughout_and_closes_during_activity(self):
        for closing, expected in ((11, "feasible"), (10, "infeasible")):
            s = stop(periods=[period(closing=closing)])
            self.assertEqual(self.evaluate(request(stops=[s], routes=[])).hours_state, expected)

    def test_break_between_periods_is_closed_and_adjacent_periods_merge(self):
        for opening, expected in ((10, "feasible"), (11, "infeasible")):
            s = stop(periods=[period(closing=10), period(opening=opening)])
            self.assertEqual(self.evaluate(request(stops=[s], routes=[])).state, expected)

    def test_overnight_activity_and_midnight_route_schedule(self):
        hours = [period(opening=22, end="2026-10-25", closing=3)]
        a = stop(arrival="2026-10-24T23:00:00-04:00", departure="2026-10-25T00:30:00-04:00", periods=hours)
        b = stop("b", "2026-10-25T00:40:00-04:00", "2026-10-25T02:00:00-04:00", periods=hours)
        self.assertEqual(self.evaluate(request(stops=[a, b])).state, "feasible")
        b.departure = datetime.fromisoformat("2026-10-25T03:01:00-04:00")
        self.assertEqual(self.evaluate(request(stops=[a, b])).state, "infeasible")

    def test_dst_spring_and_fall_elapsed_time(self):
        for day, start, end, expected_seconds in (
                ("2026-03-08", "2026-03-08T01:30:00-05:00", "2026-03-08T03:30:00-04:00", 3600),
                ("2026-11-01", "2026-11-01T00:30:00-04:00", "2026-11-01T02:30:00-05:00", 10800)):
            now = datetime.fromisoformat(day + "T04:00:00Z")
            s = stop(arrival=start, departure=end, periods=[period(day, 0, day, 4)], now=now)
            req = request(stops=[s], routes=[])
            req.evaluated_at = now
            self.assertEqual(self.evaluate(req).state, "feasible")
            self.assertEqual((s.departure.astimezone(timezone.utc) - s.arrival.astimezone(timezone.utc)).total_seconds(), expected_seconds)

    def test_dst_ambiguous_or_nonexistent_hours_are_unknown(self):
        for day, hour, arrival, departure in (
                ("2026-03-08", 2, "2026-03-08T03:00:00-04:00", "2026-03-08T04:00:00-04:00"),
                ("2026-11-01", 1, "2026-11-01T01:30:00-04:00", "2026-11-01T02:30:00-05:00")):
            now = datetime.fromisoformat(day + "T04:00:00Z")
            req = request(stops=[stop(arrival=arrival, departure=departure, periods=[period(day, hour, day, 5)], now=now)], routes=[])
            req.evaluated_at = now
            self.assertEqual(self.evaluate(req).hours_state, "unverified")

    def test_regular_hours_never_prove_future_holiday_status(self):
        s = stop()
        s.venue.regularOpeningHours = s.venue.currentOpeningHours
        s.venue.currentOpeningHours = None
        result = self.evaluate(request(stops=[s], routes=[]))
        self.assertEqual(result.state, "unverified")
        self.assertIn("regular_hours_only", self.codes(result))

    def test_current_overrides_regular_special_day(self):
        s = stop(periods=[])
        s.venue.regularOpeningHours = stop().venue.currentOpeningHours
        self.assertEqual(self.evaluate(request(stops=[s], routes=[])).state, "infeasible")

    def test_date_specific_hours_not_applied_to_unrelated_dates(self):
        s = stop(arrival="2026-11-07T14:00:00Z", departure="2026-11-07T15:00:00Z", periods=[])
        self.assertEqual(self.evaluate(request(stops=[s], routes=[])).state, "unverified")
        s = stop(periods=[period(start="2026-11-07", end="2026-11-07")])
        self.assertEqual(self.evaluate(request(stops=[s], routes=[])).state, "unverified")

    def test_missing_ambiguous_truncated_and_text_only_hours(self):
        for mutation in ("missing", "null_periods", "truncated", "undated", "open_ended", "timezone", "receipt", "request_day"):
            s = stop()
            if mutation == "missing":
                s.venue.currentOpeningHours = None
            elif mutation == "null_periods":
                s.venue.currentOpeningHours.periods = None
                s.venue.currentOpeningHours.weekdayDescriptions = ["Open all day"]
            elif mutation == "truncated":
                s.venue.currentOpeningHours.periods[0].open.truncated = True
            elif mutation == "undated":
                s.venue.currentOpeningHours.periods[0].open.date = None
            elif mutation == "open_ended":
                s.venue.currentOpeningHours.periods[0].close = None
            elif mutation == "timezone":
                s.venue.timeZone = None
                s.venue.utcOffsetMinutes = -240
            elif mutation == "receipt":
                s.venue.observedAt = {"currentOpeningHours.openNow": NOW}
            else:
                s.hours_request_date = None
            self.assertEqual(self.evaluate(request(stops=[s], routes=[])).state, "unverified", mutation)

    def test_always_open_sentinel(self):
        s = stop(periods=[{"open": {"day": 0, "hour": 0, "minute": 0}}])
        self.assertEqual(self.evaluate(request(stops=[s], routes=[])).state, "feasible")

    def test_stale_future_or_missing_observations_and_past_schedule(self):
        for stamp in (NOW - timedelta(days=1), NOW + timedelta(seconds=1), None):
            s = stop()
            s.venue.observedAt = {} if stamp is None else {"currentOpeningHours.periods": stamp}
            self.assertEqual(self.evaluate(request(stops=[s], routes=[])).state, "unverified")
        s = stop(arrival="2026-10-24T06:00:00Z", departure="2026-10-24T07:00:00Z")
        self.assertEqual(self.evaluate(request(stops=[s], routes=[])).state, "unverified")

    def test_session_and_movie_uncertainty_even_when_building_open(self):
        for activity in ("movie", "concert", "theater", "baseball"):
            result = self.evaluate(request(stops=[stop(activity=activity)], routes=[]))
            self.assertEqual((result.state, result.hours_state), ("unverified", "feasible"))
            self.assertIn("session_not_verified", self.codes(result))

    def test_known_violation_wins_over_missing_hours(self):
        req = request(max_leg_minutes=1)
        req.stops[0].venue.currentOpeningHours = None
        result = self.evaluate(req)
        self.assertEqual(result.state, "infeasible")
        self.assertEqual(result.hours_state, "unverified")

    def test_overlap_is_proven_even_without_route_evidence(self):
        req = request(routes=[])
        req.stops[1].arrival = req.stops[0].arrival
        result = self.evaluate(req)
        self.assertEqual(result.state, "infeasible")
        self.assertIn("overlapping_stops", self.codes(result))

    def test_current_seven_day_boundary_and_request_receipt_midnight(self):
        s = stop(arrival="2026-10-30T23:00:00-04:00", departure="2026-10-31T00:00:00-04:00",
                 periods=[{"open": {"day": 0, "hour": 0, "minute": 0}}])
        self.assertEqual(self.evaluate(request(stops=[s], routes=[])).state, "feasible")
        s.departure += timedelta(microseconds=1)
        self.assertEqual(self.evaluate(request(stops=[s], routes=[])).state, "unverified")
        # Request occurred yesterday; receipt today must not extend its coverage.
        s.hours_request_date -= timedelta(days=1)
        s.departure -= timedelta(microseconds=1)
        self.assertEqual(self.evaluate(request(stops=[s], routes=[])).state, "unverified")

    def test_missing_schedule_does_not_hide_travel_cap_or_unreachable_start(self):
        req = request(max_leg_minutes=1)
        req.stops[0].arrival = req.stops[0].departure = None
        self.assertEqual(self.evaluate(req).state, "infeasible")
        req = request()
        req.starting_location = AuthorizedStart(point=point("start"), explicitly_authorized=True)
        req.routes.append(route("start", "a", condition="ROUTE_NOT_FOUND"))
        self.assertEqual(self.evaluate(req).state, "infeasible")

    def test_mock_provider_isolation_and_invalid_route_provenance(self):
        req = request()
        req.stops[0].venue.evidence = "fictional"
        self.assertEqual(self.evaluate(req).state, "unverified")
        req = request()
        req.routes[0] = req.routes[0].model_copy(update={"provider": "local_identity"})
        self.assertEqual(self.evaluate(req).travel_state, "unverified")

    def test_local_identity_zero_only_with_supplied_valid_evidence(self):
        req = request(stops=[stop(), stop("a", "2026-10-24T15:00:00Z", "2026-10-24T16:00:00Z")], routes=[])
        self.assertEqual(self.evaluate(req).travel_state, "unverified")
        req.routes = [RouteLeg(origin_id="a", destination_id="a", mode="drive", status="same_location",
                               provider="local_identity", estimate_type="same_location", duration_seconds=0,
                               duration_minutes=0, distance_meters=0)]
        self.assertEqual(self.evaluate(req).state, "feasible")

    def test_unknown_schedules_and_validated_inputs(self):
        req = request()
        req.stops[0].arrival = req.stops[0].departure = None
        result = self.evaluate(req)
        self.assertIn("missing_schedule", self.codes(result))
        self.assertIn("missing_transfer_schedule", self.codes(result))
        for changes in ({"max_leg_minutes": -1}, {"max_leg_minutes": "NaN"}, {"mode": "transit"}):
            with self.assertRaises(ValidationError):
                FeasibilityInput.model_validate(request().model_dump() | changes)
        for arrival, departure in (("2026-10-24T10:00:00", "2026-10-24T11:00:00"),
                                   ("2026-10-24T10:00:00Z", "2026-10-24T09:00:00Z")):
            with self.assertRaises(ValidationError):
                EvidenceStop(venue=stop().venue, arrival=arrival, departure=departure)

    def test_stable_partition_serialization_no_mutation_and_no_ranking(self):
        a, b, c = request(), request(routes=[]), request(max_leg_minutes=1)
        a.candidate_id, b.candidate_id, c.candidate_id = "a", "b", "c"
        snapshot = a.model_dump_json()
        results = filter_feasible_candidates([c, b, a])
        self.assertEqual({k: [r.candidate_id for r in v] for k, v in results.items()},
                         {"feasible": ["a"], "unverified": ["b"], "infeasible": ["c"]})
        self.assertEqual(snapshot, a.model_dump_json())
        result = results["infeasible"][0]
        self.assertEqual(FeasibilityResult.model_validate_json(result.model_dump_json()), result)
        self.assertTrue(all(c.evidence_ref for c in result.checks))


if __name__ == "__main__":
    unittest.main()
