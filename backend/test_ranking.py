"""Constraint correctness and integration; test variations reuse shared records."""
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from backend.mock_data import get_mock_venues, load_mock_venues
from backend.models import (
    CandidateItinerary, CandidateStop, DataStatus, OutingRequest, PriceQuote, RankingResult,
    TimeWindow, TravelQuote,
)
from backend.ranking import evaluate_candidate, rank_candidates, recommend_plans


def candidate(request, venues):
    return CandidateItinerary(id="test-" + "-".join(v.id for v in venues), venues=venues,
                              people=request.people, date=request.date,
                              allowRevisits=request.allowRevisits,
                              stops=[CandidateStop(venue=v, start=getattr(v, "start", None),
                                                   end=v.start + v.duration if v.kind == "event" and v.duration is not None else None)
                                     for v in venues])


def ordinary(activity="coffee", tier=0, **updates):
    v = get_mock_venues(activity)[tier]
    # Test-only evidence, never added to the shared fictional catalog.
    quality = v.dataQuality.model_copy(update={"schedule": DataStatus.fictional})
    return v.model_copy(update={"openingWindows": [TimeWindow(start=0, end=1440)],
                                "dataQuality": quality, **updates})


def evaluate(request, venues, **providers):
    return evaluate_candidate(request, candidate(request, venues), **providers)


class RankingTests(unittest.TestCase):
    def codes(self, plan):
        return {i.code for i in plan.issues}

    def test_inclusive_per_person_and_group_budgets(self):
        v = ordinary(price=10.0)
        for args, state in ((dict(budget=10, groupBudget=40), "confirmed"),
                            (dict(budget=9), "violated"), (dict(groupBudget=39), "violated"),
                            (dict(budget=10, groupBudget=0), "violated")):
            with self.subTest(args=args):
                p = evaluate(OutingRequest(activities=["coffee"], **args), [v])
                self.assertEqual(p.feasibility, state)
                self.assertEqual((p.costPerPerson, p.groupCost), (10, 40))
        p = evaluate(OutingRequest(activities=["art"], budget=0), [ordinary("art", price=0.0)])
        self.assertEqual(p.feasibility, "confirmed")

    def test_decimal_budget_boundary(self):
        req = OutingRequest(activities=["coffee", "museum"], budget=0.3, groupBudget=1.2)
        p = evaluate(req, [ordinary(price=0.1), ordinary("museum", price=0.2)])
        self.assertEqual(p.feasibility, "confirmed")
        self.assertEqual(p.costPerPerson, 0.3)

    def test_total_and_per_leg_travel_are_separate(self):
        venues = [ordinary(), ordinary("museum"), ordinary("art")]
        for args, state in ((dict(travel=10, maxLegTravel=5), "confirmed"),
                            (dict(travel=9), "violated"), (dict(maxLegTravel=4), "violated"),
                            (dict(travel=0), "violated")):
            p = evaluate(OutingRequest(activities=[v.activity for v in venues], **args), venues)
            self.assertEqual(p.feasibility, state)
            self.assertEqual(p.totalTravel, 10)
            self.assertEqual([q.minutes for q in p.legs], [5, 5])
            self.assertTrue(all(q.status == "fictional" and "Fictional" in q.source for q in p.legs))
        req = OutingRequest(activities=["coffee"], travel=0, maxLegTravel=0)
        self.assertEqual(evaluate(req, venues[:1]).feasibility, "confirmed")

    def test_capacity_boundary_and_missing_capacity(self):
        for capacity, state in ((4, "confirmed"), (3, "violated"), (None, "provisional")):
            p = evaluate(OutingRequest(activities=["coffee"]), [ordinary(capacity=capacity)])
            self.assertEqual(p.feasibility, state)
        self.assertFalse(recommend_plans(OutingRequest(activities=["coffee"], people=21)).plans)

    def test_opening_hours_waiting_closure_and_exact_finish(self):
        req = OutingRequest(activities=["coffee"])
        for windows, state, start in (([TimeWindow(start=720, end=750)], "confirmed", 720),
                                      ([TimeWindow(start=720, end=749)], "violated", 600),
                                      ([], "violated", 600), (None, "provisional", 600)):
            p = evaluate(req, [ordinary(duration=30, openingWindows=windows)])
            self.assertEqual(p.feasibility, state)
            self.assertEqual(p.stops[0].start, start)
        p = evaluate(req, [ordinary(openingWindows=None, openingHours="some afternoons")])
        self.assertIn("unknown_openingHours", self.codes(p))

    def test_date_specific_hours_do_not_apply_to_another_day(self):
        v = ordinary(openingWindows=[TimeWindow(date="2026-11-07", start=600, end=720)])
        for day, state in ((None, "provisional"), ("2026-11-07", "confirmed"), ("2026-11-08", "violated")):
            p = evaluate(OutingRequest(activities=["coffee"], date=day), [v])
            self.assertEqual(p.feasibility, state)

    def test_availability_intersects_hours_and_is_never_invented(self):
        req = OutingRequest(activities=["coffee"], requireAvailability=True, date="2026-11-07")
        v = ordinary(openingWindows=[TimeWindow(start=600, end=720)])
        self.assertEqual(evaluate(req, [v]).feasibility, "provisional")
        for windows, state in (([], "violated"), ([TimeWindow(start=700, end=730)], "violated"),
                                ([TimeWindow(start=690, end=720)], "confirmed")):
            p = evaluate(req, [v.model_copy(update={"availabilityWindows": windows})])
            self.assertEqual(p.feasibility, state)
        # Known closure is honored even without requireAvailability.
        self.assertEqual(evaluate(OutingRequest(activities=["coffee"]),
                                  [ordinary(availabilityWindows=[])]).feasibility, "violated")

    def test_fixed_events_travel_conflict_and_waiting(self):
        req = OutingRequest(activities=["baseball", "concert"], date="2026-11-07")
        venues = [get_mock_venues(a, event_date=req.date)[0] for a in req.activities]
        p = evaluate(req, venues)
        self.assertEqual(p.feasibility, "confirmed")
        self.assertEqual(p.elapsedDuration, 420)
        self.assertEqual(p.stops[1].start, venues[1].start)
        p = evaluate(req, venues, travel_provider=lambda *args: TravelQuote(minutes=121, status="fictional"))
        self.assertEqual(p.feasibility, "violated")
        self.assertIn("event_conflict", self.codes(p))
        self.assertFalse(recommend_plans(OutingRequest(activities=["concert", "theater"], date="2026-11-07")).plans)

    def test_hours_can_make_a_pre_event_stop_impossible(self):
        req = OutingRequest(activities=["coffee", "concert"], date="2026-11-07")
        event = get_mock_venues("concert", event_date=req.date)[0]
        p = evaluate(req, [ordinary(openingWindows=[TimeWindow(start=event.start, end=1440)]), event])
        self.assertIn("event_conflict", self.codes(p))

    def test_dinner_and_explicit_start_end_and_midnight(self):
        req = OutingRequest(activities=["food"], dinner=True)
        p = evaluate(req, [ordinary("food")])
        self.assertEqual(p.stops[0].start, 1020)
        p = evaluate(OutingRequest(activities=["coffee"], startTime=1410), [ordinary(duration=30)])
        self.assertEqual(p.stops[0].end, 1440)
        self.assertEqual(p.feasibility, "confirmed")
        p = evaluate(OutingRequest(activities=["coffee"], startTime=1411), [ordinary(duration=30)])
        self.assertEqual(p.feasibility, "violated")
        req = OutingRequest(activities=["food", "baseball"], date="2026-11-07", dinner=True)
        p = evaluate(req, [ordinary("food"), get_mock_venues("baseball", event_date=req.date)[0]])
        self.assertIn("event_conflict", self.codes(p))

    def test_unknown_cost_duration_travel_and_lower_bound_violations(self):
        req = OutingRequest(activities=["coffee", "museum"], budget=1, travel=0)
        p = evaluate(req, [ordinary(price=None, duration=None, zone=None), ordinary("museum")])
        self.assertIsNone(p.costPerPerson)
        self.assertIsNone(p.groupCost)
        self.assertIsNone(p.totalTravel)
        self.assertIsNone(p.stops[1].start)
        self.assertIsNone(p.elapsedDuration)
        self.assertIn("budget_exceeded", self.codes(p))  # Known subtotal already too high.
        self.assertTrue({"unknown_price", "unknown_duration", "unknown_travel"} <= self.codes(p))
        p = evaluate(OutingRequest(activities=["coffee"]), [ordinary(duration=None)])
        self.assertEqual(p.feasibility, "provisional")
        self.assertIsNone(p.stops[0].end)

    def test_unknown_event_duration_and_required_availability(self):
        req = OutingRequest(activities=["concert"], date="2026-11-07", requireAvailability=True)
        event = get_mock_venues("concert", event_date=req.date)[0].model_copy(update={"duration": None})
        p = evaluate(req, [event])
        self.assertEqual(p.feasibility, "provisional")
        self.assertIsNone(p.stops[0].end)
        self.assertIn("unknown_availability", self.codes(p))

    def test_request_order_and_context_mismatch_rejected(self):
        req = OutingRequest(activities=["coffee", "museum"])
        c = candidate(req, [ordinary(), ordinary("museum")])
        for changed in (req.model_copy(update={"activities": list(reversed(req.activities))}),
                        req.model_copy(update={"people": 5}),
                        req.model_copy(update={"allowRevisits": True})):
            self.assertIn("request_mismatch", self.codes(evaluate_candidate(changed, c)))
        self.assertEqual([s.venue.activity for s in evaluate_candidate(req, c).stops], req.activities)

    def test_independent_ranking_checks_catalog_location(self):
        req = OutingRequest(activities=["coffee"], location="Boston")
        result = rank_candidates(req, [candidate(req, [ordinary()])])
        self.assertFalse(result.plans + result.provisionalPlans)
        self.assertIn("unsupported_location", result.rejectionReasons)

    def test_all_modes_and_budget_never_becomes_a_preference(self):
        records = [ordinary(tier=i) for i in range(3)]
        first = {}
        for mode in ("budget", "balanced", "experience"):
            req = OutingRequest(activities=["coffee"], cost=mode)
            result = rank_candidates(req, [candidate(req, [v]) for v in records])
            first[mode] = result.plans[0].candidate.venues[0].experience
            self.assertTrue(all(0 <= n <= 1 for p in result.plans for n in p.components.values()))
            self.assertTrue(all(p.explanations for p in result.plans))
        self.assertEqual(first, {"budget": 1, "balanced": 2, "experience": 3})
        req = OutingRequest(activities=["coffee"], cost="experience", budget=records[0].price)
        result = rank_candidates(req, [candidate(req, [v]) for v in records])
        self.assertTrue(all(p.costPerPerson <= req.budget for p in result.plans))

    def test_stable_ties_independent_of_traversal_order(self):
        req = OutingRequest(activities=["coffee"])
        records = [ordinary(tier=i, price=5.0, experience=2.0, zone=0) for i in range(3)]
        candidates = [candidate(req, [v]) for v in records]
        a = rank_candidates(req, candidates)
        b = rank_candidates(req, reversed(candidates))
        self.assertEqual(a, b)
        self.assertEqual([p.candidate.venues[0].id for p in a.plans], sorted(v.id for v in records))
        self.assertEqual(RankingResult.model_validate_json(a.model_dump_json()), a)

    def test_distinct_top_three_and_no_duplicate_padding(self):
        req = OutingRequest(activities=["coffee", "museum"])
        records = [ordinary(v.activity, int(v.id.rsplit("-", 1)[1])) for v in load_mock_venues() if v.kind == "venue"]
        with patch("backend.planner.load_mock_venues", return_value=records):
            result = recommend_plans(req)
        self.assertEqual(len(result.plans), 3)
        identities = [tuple(v.id for v in p.candidate.venues) for p in result.plans]
        self.assertEqual(len(set(identities)), 3)
        one = result.plans[0].candidate
        self.assertEqual(len(rank_candidates(req, [one, one, one]).plans), 1)
        self.assertTrue(any(sum(a != b for a, b in zip(identities[0], x)) == 2 for x in identities[1:]))

    def test_integration_all_categories_and_repeated_activities(self):
        from backend.models import ActivityType
        for activity in ActivityType:
            result = recommend_plans(OutingRequest(activities=[activity], date="2026-11-07"))
            options = result.plans + result.provisionalPlans
            self.assertEqual(len(options), 3)
            self.assertTrue(all(p.candidate.venues[0].activity == activity for p in options))
        req = OutingRequest(activities=["coffee", "museum", "coffee"])
        result = recommend_plans(req)
        self.assertEqual(len(result.provisionalPlans), 3)
        self.assertTrue(all([v.activity for v in p.candidate.venues] == req.activities for p in result.provisionalPlans))

    def test_mock_unknown_hours_are_never_confirmed(self):
        result = recommend_plans(OutingRequest(activities=["coffee", "museum"]))
        self.assertFalse(result.plans)
        self.assertEqual(result.errors[0].code, "insufficient_data")
        self.assertEqual(len(result.provisionalPlans), 3)
        self.assertTrue(all(p.feasibility == "provisional" for p in result.provisionalPlans))
        self.assertTrue(all("unknown_openingHours" in self.codes(p) for p in result.provisionalPlans))

    def test_no_feasible_result_has_actionable_reasons(self):
        result = recommend_plans(OutingRequest(activities=["coffee"], budget=0))
        self.assertFalse(result.plans + result.provisionalPlans)
        self.assertIn("budget_exceeded", result.rejectionReasons)
        self.assertTrue(any("increase" in e.message for e in result.errors))
        for req, code in ((OutingRequest(activities=["concert"], date="2026-11-08"), "no_availability"),
                          (OutingRequest(activities=["coffee"], location="Boston"), "unsupported_location")):
            result = recommend_plans(req)
            self.assertFalse(result.plans + result.provisionalPlans)
            self.assertEqual(result.errors[0].code, code)

    def test_replaceable_quotes_drive_constraints_and_totals(self):
        req = OutingRequest(activities=["coffee", "museum"], budget=4, maxLegTravel=2)
        venues = [ordinary(), ordinary("museum")]
        p = evaluate(req, venues,
                     price_provider=lambda *args: PriceQuote(amount=2.0, status="estimated", source="test price adapter"),
                     travel_provider=lambda *args: TravelQuote(minutes=2, status="estimated", source="test travel adapter"))
        self.assertEqual(p.feasibility, "confirmed")
        self.assertEqual((p.costPerPerson, p.groupCost, p.totalTravel), (4, 16, 2))
        self.assertTrue(all(q.status == "estimated" for q in p.prices + p.legs))

    def test_confirmed_options_precede_better_scoring_provisional_options(self):
        req = OutingRequest(activities=["coffee"], cost="budget")
        confirmed = ordinary(tier=2)
        provisional = ordinary(tier=0, openingWindows=None)
        result = rank_candidates(req, [candidate(req, [provisional]), candidate(req, [confirmed])])
        self.assertEqual(result.plans[0].candidate.venues[0], confirmed)
        self.assertEqual(result.provisionalPlans[0].candidate.venues[0], provisional)
        self.assertFalse(result.errors)

    def test_missing_quality_does_not_become_an_invented_review(self):
        req = OutingRequest(activities=["coffee"])
        p = rank_candidates(req, [candidate(req, [ordinary(experience=None)])]).plans[0]
        self.assertEqual(p.components["quality"], 0)
        self.assertFalse(any(r.code == "quality" for r in p.explanations))

    def test_split_windows_cannot_be_added_into_a_continuous_visit(self):
        req = OutingRequest(activities=["coffee"])
        v = ordinary(duration=30, openingWindows=[TimeWindow(start=600, end=620),
                                                 TimeWindow(start=640, end=660)])
        self.assertEqual(evaluate(req, [v]).feasibility, "violated")

    def test_scheduled_event_windows_date_and_early_finish(self):
        req = OutingRequest(activities=["concert"], date="2026-11-07", endTime=1200)
        event = get_mock_venues("concert", event_date=req.date)[0]
        self.assertIn("end_time", self.codes(evaluate(req, [event])))
        p = evaluate_candidate(req.model_copy(update={"date": OutingRequest(
            activities=["concert"], date="2026-11-14").date}), candidate(req, [event]))
        self.assertIn("event_date", self.codes(p))
        closed = event.model_copy(update={"openingWindows": []})
        self.assertIn("time_window", self.codes(evaluate(req, [closed])))

    def test_explicit_revisits_survive_evaluation_and_results(self):
        req = OutingRequest(activities=["coffee", "coffee"], allowRevisits=True)
        c = candidate(req, [ordinary(), ordinary()])
        result = rank_candidates(req, [c])
        self.assertEqual(len(result.plans), 1)
        self.assertEqual(result.plans[0].totalTravel, 5)

    def test_supplied_values_with_unknown_evidence_are_provisional(self):
        req = OutingRequest(activities=["coffee"])
        v = ordinary()
        quality = v.dataQuality.model_copy(update={"capacity": DataStatus.unknown, "duration": DataStatus.unknown,
                                                 "schedule": DataStatus.unknown, "price": DataStatus.unknown})
        p = evaluate(req, [v.model_copy(update={"dataQuality": quality})])
        self.assertEqual(p.feasibility, "provisional")
        self.assertTrue({"unknown_capacity", "unknown_duration", "unknown_schedule_evidence", "unknown_price"} <= self.codes(p))

    def test_new_contract_rejects_invalid_windows_and_limits(self):
        for args in (dict(groupBudget=-1), dict(maxLegTravel=-1), dict(startTime=720, endTime=600),
                     dict(requireAvailability="yes"), dict(maxLegTravel=True)):
            with self.assertRaises(ValidationError):
                OutingRequest(activities=["coffee"], **args)
        with self.assertRaises(ValidationError):
            TimeWindow(start=600, end=600)


if __name__ == "__main__":
    unittest.main()
