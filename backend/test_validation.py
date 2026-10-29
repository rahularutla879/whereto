"""Task 34 trust-boundary regressions, deterministic and provider independent."""
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from pydantic import ValidationError
from backend.ai import Interpretation, parse_interpretation
from backend.interpretation import InterpretationInput, interpret_request
from backend.main import interpret_outing
from backend.ranking import recommend_plans

NOW = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)
BASE = dict(activities=['coffee'], people=2, location='Baltimore', date=None,
            budget_per_person=None, preferences=[])
TEXT = 'Two people want coffee in Baltimore on November 7, 2026'


class ValidationTests(unittest.TestCase):
    def run_case(self, suffix='', manual=None, **fields):
        provider = Mock()
        provider.interpret.return_value = Interpretation(**{**BASE, **fields})
        result = interpret_request(InterpretationInput(text=TEXT + suffix,
            preferences=manual or {}), provider, now=NOW)
        provider.interpret.assert_called_once()
        return result

    def test_complete_and_zero_constraints(self):
        for amount in [None, 0, 60]:
            result = self.run_case('' if amount is None else f', maximum ${amount} each, 0 minutes between stops',
                budget_per_person=amount, currency='USD' if amount is not None else None,
                travel_leg_minutes=0 if amount is not None else None)
            self.assertFalse(result.issues)
            self.assertEqual(result.request.budget, amount)
            self.assertEqual(result.request.maxLegTravel, 0 if amount is not None else None)

    def test_malformed_shapes_types_enums_and_nonfinite(self):
        invalid = [[], None, 'coffee', {}, {**BASE, 'activities': {'coffee': 1}}]
        changes = [dict(people=v) for v in ['2', True, 2.5, 0, -1]]
        changes += [dict(budget_per_person=v) for v in ['60', True, -1, float('inf'), float('nan')]]
        changes += [dict(travel_leg_minutes=v) for v in [-1, 1.5, '15', True, float('inf')]]
        changes += [dict(transport='flying'), dict(cost='luxury'), dict(suggested_activities=['skydiving']),
                    dict(activities=[{'activity': 'coffee'}]), dict(activities=('coffee',)),
                    dict(preferences='quiet'), dict(location='X' * 201), dict(minimum_budget=80)]
        invalid += [{**BASE, **change} for change in changes]
        for body in invalid:
            with self.subTest(body=body), self.assertRaises(ValidationError):
                Interpretation.model_validate(body)

    def test_duplicate_json_keys_and_malformed_json(self):
        for content in ['bad', '[]', json.dumps(BASE)[:-1] + ', "people": 8}',
                        json.dumps({**BASE, 'budget_per_person': float('nan')})]:
            with self.subTest(content=content), self.assertRaises((ValueError, ValidationError)):
                parse_interpretation(content)

    def test_provider_instance_is_revalidated_and_not_mutated(self):
        ai = Interpretation(**BASE)
        ai.people = True
        provider = Mock(); provider.interpret.return_value = ai
        with self.assertRaises(ValidationError):
            interpret_request(InterpretationInput(text=TEXT), provider, now=NOW)
        ai.people = 2; ai.location = 'Boston'
        result = interpret_request(InterpretationInput(text=TEXT), provider, now=NOW)
        self.assertIsNone(result.interpretation.location)
        self.assertEqual(ai.location, 'Boston')

    def test_equivalent_caps_and_independent_group_values(self):
        result = self.run_case(', no more than $60 each and $200 total, 15 minutes between stops',
            budget_per_person=60, budget_group=200, currency='USD', travel_leg_minutes=15)
        self.assertFalse(result.issues)
        invented = self.run_case(', maximum $60 each', budget_per_person=60, budget_group=120, currency='USD')
        self.assertIsNone(invented.request)

    def test_budget_scope_swaps_and_independent_omissions(self):
        for fields in [dict(budget_per_person=200, budget_group=60),
                       dict(budget_per_person=60), dict(budget_group=200)]:
            result = self.run_case(', maximum $60 each and $200 total', currency='USD', **fields)
            self.assertIsNone(result.request)
            self.assertIn('budget', ' '.join(result.issues).lower())
        # A manual per-person cap does not erase the independent group cap.
        result = self.run_case(', maximum $70 each and $100 total', manual={'budget': '50'},
                               budget_per_person=70, currency='USD')
        self.assertIsNone(result.request)
        result = self.run_case(', maximum $70 each and $100 total', manual={'budget': '50'},
                               budget_per_person=70, budget_group=100, currency='USD')
        self.assertFalse(result.issues)
        self.assertEqual((result.request.budget, result.request.groupBudget), (50, 100))

    def test_equivalent_money_expressions(self):
        for phrase in ['maximum $60 per head', 'under 60 dollars each', 'maximum USD 60 per-person', 'maximum $1,000 each']:
            amount = 1000 if '1,000' in phrase else 60
            result = self.run_case(', ' + phrase, budget_per_person=amount, currency='USD')
            self.assertFalse(result.issues, result.issues)
            self.assertEqual(result.request.budget, amount)

    def test_malformed_money_grouping_does_not_invent_amounts(self):
        self.assertIsNone(self.run_case(', maximum $1,2 each', budget_per_person=12, currency='USD').request)

    def test_explicit_non_usd_cannot_be_labelled_usd(self):
        for wording in ['₹60 each', 'CAD $60 each', 'CHF $60 each', '€60 each']:
            result = self.run_case(', maximum ' + wording, budget_per_person=60, currency='USD')
            self.assertIsNone(result.request)
            self.assertIn('cannot convert currency', ' '.join(result.issues))

    def test_minimum_spending_cannot_become_maximum(self):
        for suffix in [', maximum $40 per person but minimum $80 per person',
                       ', minimum $40 each', ', at least 80 dollars each']:
            result = self.run_case(suffix, budget_per_person=40, currency='USD')
            self.assertIsNone(result.request)
            self.assertIn('Minimum spending', ' '.join(result.issues))

    def test_travel_scope_conversion_and_inventions(self):
        valid = self.run_case(', 0.5 hours total travel and 15 minutes between stops',
                              travel_total_minutes=30, travel_leg_minutes=15)
        self.assertFalse(valid.issues)
        for suffix, fields in [('', dict(travel_total_minutes=15)),
                (', we have only 60 minutes total', dict(travel_total_minutes=60)),
                (', 15 minutes total travel', dict(travel_leg_minutes=15)),
                (', 15 minutes between stops', dict(travel_total_minutes=15)),
                (', 0.5 hours total travel', dict(travel_total_minutes=1)),
                (', 15 miles between stops', dict()),
                (', 30 seconds between stops', dict()),
                (', 1e3 minutes between stops', dict(travel_leg_minutes=3)),
                (', minimum 15 minutes total travel', dict(travel_total_minutes=15)),
                (', -15 minutes total travel', dict())]:
            with self.subTest(suffix=suffix, fields=fields):
                self.assertIsNone(self.run_case(suffix, **fields).request)

    def test_group_mismatch_and_conflict_reuse_followup(self):
        result = self.run_case(', and four friends are coming')
        self.assertIsNotNone(result.request)
        self.assertIsNone(result.request.people)
        self.assertFalse(result.questions)

    def test_location_conflict_reuses_location_answer(self):
        provider = Mock(); provider.interpret.return_value = Interpretation(**BASE)
        text = 'Two people want coffee in Baltimore or Boston on November 7, 2026'
        result = interpret_request(InterpretationInput(text=text), provider, now=NOW)
        self.assertIsNone(result.request)
        self.assertIn('location', [q.field for q in result.questions])
        self.assertEqual([q.field for q in result.questions], ['location'])
        fixed = interpret_request(InterpretationInput(text=text, pending=result.pending,
            answers={'location': 'Baltimore'}), provider, now=NOW)
        self.assertFalse(fixed.issues)
        self.assertEqual(fixed.request.location, 'Baltimore')
        provider.interpret.assert_called_once()

    def test_invented_modes_and_unverifiable_required_qualities_block(self):
        for fields in [dict(cost='experience'), dict(transport='driving')]:
            self.assertIsNone(self.run_case(**fields).request)
        self.assertIsNone(self.run_case('; we require wheelchair accessible venues').request)
        self.assertFalse(self.run_case('; best experience, driving', cost='experience', transport='driving').issues)

    def test_numeric_budget_is_not_evidence_of_a_spending_preference(self):
        self.assertIsNone(self.run_case(', budget $60 each', budget_per_person=60, currency='USD', cost='budget').request)

    def test_explicit_modes_cannot_silently_become_defaults(self):
        for text in [', best experience', ', affordable', ', driving']:
            self.assertIsNone(self.run_case(text).request)
        self.assertFalse(self.run_case(', best experience', manual={'cost': 'balanced', 'costExplicit': True}).issues)

    def test_only_exact_grounded_resolved_mode_uncertainty_can_clear(self):
        self.assertFalse(self.run_case(', best experience', cost='experience', uncertainties=['best experience']).issues)
        for issue in ['best experience or budget-friendly?', 'experience availability is unclear', 'experience preference unknown']:
            self.assertIsNone(self.run_case(', best experience', cost='experience', uncertainties=[issue]).request)

    def test_validation_is_not_feasibility(self):
        result = self.run_case(', maximum $0 each', budget_per_person=0, currency='USD')
        self.assertFalse(result.issues)
        plans = recommend_plans(result.request)
        self.assertFalse(plans.plans + plans.provisionalPlans)
        self.assertTrue(plans.errors)

    def test_invalid_pending_shape_is_rejected_without_ai(self):
        initial = self.run_case().pending.model_dump(mode='json')
        initial['interpretation']['travel_total_minutes'] = '15'
        with patch('backend.interpretation.create_provider') as factory, self.assertRaises(ValidationError):
            InterpretationInput(text=TEXT, pending=initial, answers={'date': 'tomorrow'})
        factory.assert_not_called()

    def test_semantic_failure_during_answer_keeps_pending_and_never_calls_ai(self):
        provider = Mock()
        provider.interpret.return_value = Interpretation(**{**BASE, 'travel_leg_minutes': 15})
        text = 'Two people want coffee in Baltimore'
        initial = interpret_request(InterpretationInput(text=text), provider, now=NOW)
        self.assertIsNotNone(initial.pending)
        provider.reset_mock()
        result = interpret_request(InterpretationInput(text=text, pending=initial.pending,
            answers={'date': '2026-11-07'}), provider, now=NOW)
        self.assertIsNone(result.request)
        self.assertIsNotNone(result.pending)
        self.assertEqual(result.pending.answers.date, '2026-11-07')
        self.assertEqual(initial.pending.answers.date, '')
        provider.interpret.assert_not_called()

    def test_provider_diagnostics_never_become_website_explanations(self):
        for diagnostic in ['Traceback: private exception details', '{"internal_field": "bad"}',
                           'budget_per_person invalid', 'location schema ValidationError']:
            result = self.run_case(uncertainties=[diagnostic])
            self.assertIsNone(result.request)
            self.assertTrue(result.issues)
            explanation = ' '.join(result.issues)
            for private in ['Traceback', 'private exception', 'internal_field', 'budget_per_person', 'ValidationError']:
                self.assertNotIn(private, explanation)

    def test_invalid_provider_never_invokes_planning_or_leaks_details(self):
        for body in [None, {}, {**BASE, 'secret_field': 'private details'}]:
            with patch('backend.interpretation.create_provider') as factory, patch('backend.main.recommend_plans') as planner:
                factory.return_value.interpret.return_value = body
                response = interpret_outing(InterpretationInput(text=TEXT))
            self.assertEqual(response.status_code, 503)
            self.assertNotIn(b'private details', response.body)
            planner.assert_not_called()
            factory.return_value.interpret.assert_called_once()


if __name__ == '__main__':
    unittest.main()
