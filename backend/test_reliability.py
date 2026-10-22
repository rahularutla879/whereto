"""Task 36 regressions: source evidence must not discard supplied essentials."""
import unittest
from unittest.mock import Mock

from backend import test_clarification as helpers
from backend.ai import Interpretation
from backend.interpretation import InterpretationInput, interpret_request

ORIGINAL = 'Dinner for four in Baltimore on November 7, 2026, maximum $30 but minimum $80 per person.'


class ReliabilityTests(unittest.TestCase):
    initial = helpers.ClarificationTests.initial
    answer = helpers.ClarificationTests.answer

    def test_original_conflict_keeps_four_and_explains_only_unsupported_spending(self):
        for budget in (None, 30, 80):
            with self.subTest(budget=budget):
                result = self.initial(ORIGINAL, activities=['Dinner'], people=4,
                    location='Baltimore', budget_per_person=budget,
                    currency='USD', uncertainties=['Budget limits conflict'])
                self.assertIsNone(result.request)
                self.assertEqual(result.interpretation.people, 4)
                self.assertEqual(result.questions, [])
                self.assertEqual(len(result.issues), 1)
                self.assertIn('Minimum spending requirements are unsupported', result.issues[0])
                self.assertIn('remove the minimum', result.issues[0])

    def test_party_evidence_is_shared_across_word_numeric_and_nontrailing_forms(self):
        for count, phrase in [(4, 'four'), (4, '4'), (13, 'thirteen'), (20, 'twenty')]:
            for suffix in [' in Baltimore on 2026-11-07', ', in Baltimore on 2026-11-07', ' on 2026-11-07 in Baltimore']:
                with self.subTest(phrase=phrase, suffix=suffix):
                    result = self.initial('Coffee for ' + phrase + suffix,
                        people=count, location='Baltimore')
                    self.assertFalse(result.issues)
                    self.assertEqual(result.request.people, count)

    def test_missing_wrong_conflicting_and_nonparty_numbers_are_not_inferred(self):
        for text, count in [
            ('Coffee for four in Baltimore on 2026-11-07', None),
            ('Coffee for four in Baltimore on 2026-11-07', 3),
            ('Coffee for four in Baltimore with six friends on 2026-11-07', 4),
            ('Coffee for 4 hours in Baltimore on 2026-11-07', 4),
            ('Coffee for 2.5 hours in Baltimore on 2026-11-07', 2),
            ('Coffee for 4,000 dollars in Baltimore on 2026-11-07', 4),
        ]:
            with self.subTest(text=text, count=count):
                result = self.initial(text, people=count, location='Baltimore')
                self.assertIsNone(result.request)
                self.assertIn('people', [q.field for q in result.questions])

    def test_nontrailing_party_survives_date_correction_and_model_free_regeneration(self):
        result = self.initial('Coffee for four in Baltimore', people=4, location='Baltimore')
        self.assertEqual([q.field for q in result.questions], ['date'])
        invalid = self.answer(result, {'date': '2026-02-30'})
        self.assertEqual(invalid.interpretation.people, 4)
        fixed = self.answer(invalid, {'date': '2026-11-07'})
        self.assertFalse(fixed.issues)
        edited = self.answer(fixed, {'activities': 'museum, coffee, coffee'}, {'budget': '40'})
        self.assertFalse(edited.issues)
        self.assertEqual(edited.request.people, 4)
        self.assertEqual(edited.request.budget, 40)
        self.assertEqual(edited.request.activities, ['museum', 'coffee', 'coffee'])

    def test_existing_maximum_only_guards_and_provider_ownership_are_preserved(self):
        result = self.initial('Dinner for four in Baltimore on 2026-11-07, maximum $30 per person',
            activities=['Dinner'], people=4, location='Baltimore', budget_per_person=80, currency='USD')
        self.assertIsNone(result.request)
        self.assertTrue(any('not captured correctly' in issue for issue in result.issues))
        extraction = Interpretation(activities=['Dinner'], people=4, location='Baltimore',
            budget_per_person=30, currency='USD', date=None, preferences=[])
        provider = Mock(); provider.interpret.return_value = extraction
        result = interpret_request(InterpretationInput(text=ORIGINAL), provider, now=helpers.NOW)
        self.assertEqual(extraction.people, 4)
        self.assertEqual(extraction.budget_per_person, 30)
        self.assertIsNone(result.request)

    def test_ungrounded_model_activity_diagnostics_are_never_displayed(self):
        for phrase in ['PRIVATE_DIAGNOSTIC_DO_NOT_DISPLAY', 'something PRIVATE_DIAGNOSTIC_DO_NOT_DISPLAY']:
            result = self.initial('Coffee for four in Baltimore on 2026-11-07',
                people=4, location='Baltimore', activities=[phrase])
            self.assertIsNone(result.request)
            visible = str(result.issues + result.notes + result.unsupported + [q.question for q in result.questions])
            self.assertNotIn('PRIVATE_DIAGNOSTIC', visible)
            self.assertTrue(result.issues)
