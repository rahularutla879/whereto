"""Task 35 uses the existing deterministic validation boundary for corrections."""
import unittest
from backend import test_clarification as helpers
from backend.ranking import recommend_plans


class SummaryEditTests(unittest.TestCase):
    initial = helpers.ClarificationTests.initial
    answer = helpers.ClarificationTests.answer
    def test_validated_summary_edits_preserve_order_repeats_and_caps_without_ai(self):
        initial = self.initial('coffee, museum, coffee in Baltimore for 2 people on 2026-11-07 maximum $60 each and 30 minutes total travel',
            activities=['coffee', 'museum', 'coffee'], location='Baltimore', people=2,
            budget_per_person=60, currency='USD', travel_total_minutes=30)
        self.assertFalse(initial.issues)
        edited = self.answer(initial, {'activities': 'museum, coffee, coffee'},
            {'budget': '40', 'people': '4', 'date': '2026-11-14', 'location': 'Baltimore', 'cost': 'balanced', 'costExplicit': True})
        self.assertFalse(edited.issues)
        self.assertEqual([a.value for a in edited.request.activities], ['museum', 'coffee', 'coffee'])
        self.assertEqual(edited.request.budget, 40)
        self.assertIsNone(edited.request.people)
        self.assertEqual(edited.request.travel, 30)
        self.assertEqual(str(edited.request.date), '2026-11-14')
        result = recommend_plans(edited.request)
        for plan in result.plans + result.provisionalPlans:
            self.assertEqual([v.activity.value for v in plan.candidate.venues], ['museum', 'coffee', 'coffee'])
            self.assertLessEqual(plan.costPerPerson, 40)

    def test_invalid_edits_are_revalidated_without_ai(self):
        initial = self.initial('coffee in Baltimore for 2 people on 2026-11-07', location='Baltimore', people=2)
        for preferences in [{'budget': '-1'}, {'date': '2020-01-01'}, {'date': '2026-02-30'}, {'travel': '-1'}]:
            with self.subTest(preferences=preferences):
                edited = self.answer(initial, {}, preferences)
                self.assertIsNone(edited.request)
                self.assertTrue(edited.issues)
        for activities in [',', 'coffee, coffee, coffee, coffee, coffee']:
            edited = self.answer(initial, {'activities': activities})
            self.assertIsNone(edited.request)
            self.assertTrue(edited.issues)

    def test_acceptance_for_two_is_grounded_but_conflicting_count_is_rejected(self):
        text = 'Coffee, museum, coffee again in Baltimore on November 7, 2026 for two.'
        for count in (None, 2, 4):
            result = self.initial(text, activities=['coffee','museum','coffee'], location='Baltimore', people=count)
            self.assertFalse(result.issues)
            self.assertIsNone(result.request.people)
            self.assertFalse(result.questions)
