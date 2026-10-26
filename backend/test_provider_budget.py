"""No provider traffic: exercise admission and failures with local counters."""
import os
from threading import Event, Thread
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from backend.models import OutingRequest
from backend.provider_budget import ProviderBudget, ProviderLimitError, ProviderSettings
from backend.ranking import recommend_plans


class ProviderBudgetTests(unittest.TestCase):
    def test_mock_default_and_no_live_environment_switch(self):
        with patch.dict(os.environ, {}, clear=True):
            settings = ProviderSettings.from_env()
        self.assertEqual(settings.mode, "mock")
        with self.assertRaisesRegex(ProviderLimitError, "disabled"):
            settings.require_live_provider()
        for mode in ("google", "live", "", "MOCK"):
            with self.subTest(mode=mode), patch.dict(os.environ, {"VENUE_DATA_MODE": mode}):
                with self.assertRaises(ValidationError):
                    ProviderSettings.from_env()

    def test_configuration_rejects_invalid_values_and_increases(self):
        for field in ("searches_per_outing", "candidates_per_activity", "matrix_elements_per_outing",
                      "requests_per_outing", "concurrent_requests", "requests_per_session",
                      "matrix_elements_per_session"):
            for value in (-1, True, 1.5, "3", getattr(ProviderSettings(), field) + 1):
                with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                    ProviderSettings(**{field: value})
        for args in ({"retries": 1}, {"unknown": 1}, {"mode": "live"}):
            with self.assertRaises(ValidationError):
                ProviderSettings(**args)
        with self.assertRaises(ValidationError):
            ProviderSettings().searches_per_outing = 10

    def test_ten_searches_and_twenty_candidates(self):
        outing = ProviderBudget().outing()
        outing.check_candidates(20)
        with self.assertRaisesRegex(ProviderLimitError, "candidates"):
            outing.check_candidates(21)
        for n in range(10):
            with outing.reserve("search", str(n)):
                pass
        with self.assertRaisesRegex(ProviderLimitError, "search limit"):
            with outing.reserve("search", "eleventh"):
                self.fail("Must reject before provider I/O")

    def test_matrix_products_accumulate_and_rejected_attempt_does_not_consume(self):
        outing = ProviderBudget(ProviderSettings(matrix_elements_per_outing=27)).outing()
        for n in range(3):
            with outing.reserve("matrix", str(n), origins=3, destinations=3):
                pass
        with self.assertRaisesRegex(ProviderLimitError, "element limit"):
            with outing.reserve("matrix", "excess", origins=1, destinations=1):
                self.fail("Over budget")
        other = ProviderBudget(ProviderSettings(matrix_elements_per_outing=27)).outing()
        with self.assertRaises(ProviderLimitError):
            with other.reserve("matrix", "same", origins=6, destinations=6):
                pass
        with other.reserve("matrix", "same", origins=3, destinations=3):
            pass

    def test_failed_attempt_counts_and_cannot_retry(self):
        session = ProviderBudget(ProviderSettings(requests_per_session=1))
        outing = session.outing()
        with self.assertRaises(TimeoutError):
            with outing.reserve("route", "leg"):
                raise TimeoutError("simulated provider failure")
        with self.assertRaisesRegex(ProviderLimitError, "already attempted"):
            with outing.reserve("route", "leg"):
                self.fail("Retry")
        with self.assertRaisesRegex(ProviderLimitError, "session request limit"):
            with session.outing().reserve("search", "new"):
                self.fail("A new outing must not reset session counters")

    def test_outing_request_limit_covers_details_and_route_calls(self):
        outing = ProviderBudget(ProviderSettings(requests_per_outing=2)).outing()
        for operation in ("details", "route"):
            with outing.reserve(operation, operation):
                pass
        with self.assertRaisesRegex(ProviderLimitError, "outing's provider request limit"):
            with outing.reserve("details", "another"):
                pass

    def test_session_matrix_limit_across_outings(self):
        session = ProviderBudget(ProviderSettings(matrix_elements_per_session=9))
        with session.outing().reserve("matrix", "one", origins=3, destinations=3):
            pass
        with self.assertRaisesRegex(ProviderLimitError, "session route matrix"):
            with session.outing().reserve("matrix", "two", origins=1, destinations=1):
                pass

    def test_concurrency_shared_across_threads_and_released_after_error(self):
        session = ProviderBudget()
        entered, finish = Event(), Event()
        def hold():
            with session.outing().reserve("search", "one"):
                entered.set()
                finish.wait(5)
        worker = Thread(target=hold)
        worker.start()
        try:
            self.assertTrue(entered.wait(3))
            with self.assertRaisesRegex(ProviderLimitError, "Another external request"):
                with session.outing().reserve("details", "two"):
                    pass
        finally:
            finish.set()
            worker.join(3)
        with self.assertRaises(RuntimeError):
            with session.outing().reserve("route", "failure"):
                raise RuntimeError("fake provider error")
        with session.outing().reserve("route", "after"):
            pass

    def test_invalid_operations_dimensions_and_candidate_counts(self):
        outing = ProviderBudget().outing()
        for operation, identity, dimensions in (
            ("other", "id", {}), ("search", "", {}), ("route", "x" * 201, {}),
            ("matrix", "id", {}), ("matrix", "id", {"origins": True, "destinations": 3}),
            ("matrix", "id", {"origins": -1, "destinations": 3}),
            ("matrix", "id", {"origins": 1.5, "destinations": 3}),
            ("search", "id", {"origins": 1, "destinations": 1}),
        ):
            with self.subTest(operation=operation, dimensions=dimensions), self.assertRaises(ValueError):
                with outing.reserve(operation, identity, **dimensions):
                    pass
        for count in (-1, True, 1.5):
            with self.assertRaises(ValueError):
                outing.check_candidates(count)

    def test_mock_planner_does_not_use_external_budget_or_network(self):
        request = OutingRequest(activities=["bowling", "drinks", "food"], date="2026-11-07")
        expected = recommend_plans(request).model_dump()
        with patch("backend.provider_budget.OutingBudget.reserve", side_effect=AssertionError("external budget")), \
             patch("socket.socket", side_effect=AssertionError("network")):
            self.assertEqual(recommend_plans(request).model_dump(), expected)
        # Four fixture activities still enumerate normally; no new live candidate cap.
        with patch("socket.socket", side_effect=AssertionError("network")):
            result = recommend_plans(OutingRequest(activities=["coffee", "museum", "art", "drinks"], date="2026-11-07"))
        self.assertTrue(result.plans or result.provisionalPlans)


if __name__ == "__main__":
    unittest.main()
