import unittest
from unittest.mock import Mock, patch

from backend.ai import AIError, Interpretation
from backend.interpretation import InterpretationInput, interpret_request
from backend.main import interpret_outing
from backend.ranking import recommend_plans


def extraction(**kw):
    return Interpretation(activities=['coffee'], people=2, budget_per_person=None,
                          date=None, location='Baltimore', preferences=[], **kw)


class InterpretationTests(unittest.TestCase):
    def run_request(self, text, manual=None, **kw):
        fields = dict(activities=['coffee'], people=2, budget_per_person=None,
                      date=None, location='Baltimore', preferences=[])
        fields.update(kw)
        if fields["people"] == 2:
            text += " for 2 people"
        if fields["location"] == "Baltimore":
            text += " in Baltimore"
        provider = Mock()
        provider.interpret.return_value = Interpretation(**fields)
        value = InterpretationInput(text=text, preferences=manual or {})
        result = interpret_request(value, provider)
        provider.interpret.assert_called_once_with(text)
        return result

    def test_explicit_order_and_repeats_reach_engine(self):
        r = self.run_request('coffee, museum, then coffee for 2 people in Baltimore', activities=['coffee', 'museum', 'coffee'])
        self.assertFalse(r.issues)
        self.assertEqual(r.request.activities, ['coffee', 'museum', 'coffee'])
        plans = recommend_plans(r.request).provisionalPlans
        self.assertTrue(plans)
        self.assertTrue(all([v.activity for v in p.candidate.venues] == ['coffee', 'museum', 'coffee'] for p in plans))
        self.assertTrue(all(p.candidate.venues[0].id != p.candidate.venues[2].id for p in plans))

    def test_explicit_multiplicity_preserves_occurrences(self):
        r = self.run_request('coffee twice then museum', activities=['coffee', 'coffee', 'museum'])
        self.assertFalse(r.issues)
        self.assertEqual(r.request.activities, ['coffee', 'coffee', 'museum'])
        self.assertIsNone(self.run_request('coffee twice then museum', activities=['coffee', 'museum']).request)

    def test_model_invented_core_values_remain_unknown(self):
        provider = Mock()
        provider.interpret.return_value = Interpretation(
            activities=['coffee'], people=4, location='Boston', date=None, budget_per_person=None, preferences=[])
        r = interpret_request(InterpretationInput(text='A group wants coffee.'), provider)
        self.assertIsNone(r.interpretation.people)
        self.assertIsNone(r.interpretation.location)
        self.assertIsNone(r.request)

    def test_dropped_reordered_or_fabricated_stops_block(self):
        for activities in [['coffee', 'museum'], ['museum', 'coffee', 'coffee'], ['bowling']]:
            r = self.run_request('coffee, museum, then coffee', activities=activities)
            self.assertIsNone(r.request)
            self.assertTrue(r.issues)

    def test_meals_are_separate_and_dinner_timing_is_scoped(self):
        r = self.run_request('lunch and dinner', activities=['lunch', 'dinner'])
        self.assertFalse(r.issues)
        self.assertEqual(r.request.dinnerStops, [1])
        plans = recommend_plans(r.request).provisionalPlans
        self.assertTrue(plans)
        self.assertEqual(plans[0].stops[0].start, 600)
        self.assertGreaterEqual(plans[0].stops[1].start, 1020)

    def test_missing_values_stay_unknown_and_do_not_use_planner_defaults(self):
        r = self.run_request('coffee', people=None, location=None)
        self.assertIsNone(r.interpretation.people)
        self.assertIsNone(r.interpretation.location)
        self.assertIsNone(r.interpretation.budget_per_person)
        self.assertIsNone(r.interpretation.date)
        self.assertIsNone(r.request)
        self.assertIn('Group size is unknown', ' '.join(r.issues))
        self.assertIn('Location is unknown', ' '.join(r.issues))

    def test_indirect_suggestions_never_become_explicit_stops(self):
        r = self.run_request('something competitive then cocktails', activities=['something competitive', 'cocktails'],
                             suggested_activities=['bowling', 'miniGolf'], preferences=['competitive'])
        self.assertIsNone(r.request)
        self.assertEqual(r.interpretation.activities, ['something competitive', 'cocktails'])
        self.assertIn('AI suggestions, not requested stops', ' '.join(r.notes))

    def test_text_caps_and_default_manual_cost(self):
        r = self.run_request('affordable coffee under $20 each, 15 minutes total travel',
                             budget_per_person=20, currency='USD', travel_total_minutes=15, cost='budget')
        self.assertFalse(r.issues)
        self.assertEqual((r.request.budget, r.request.travel, r.request.cost), (20, 15, 'budget'))

    def test_manual_overrides_including_explicit_balanced_and_zero(self):
        r = self.run_request('coffee tomorrow in Boston for 8 people under $40 each',
                             manual={'people': '3', 'location': 'Baltimore', 'date': '2026-11-07',
                                          'budget': '0', 'travel': '0', 'cost': 'balanced', 'costExplicit': True},
                             people=8, location='Boston', budget_per_person=40, currency='USD', cost='experience')
        self.assertFalse(r.issues)
        self.assertEqual((r.request.people, r.request.location, r.request.budget, r.request.travel, r.request.cost),
                         (3, 'Baltimore', 0, 0, 'balanced'))
        self.assertEqual(r.interpretation.date_expressions, ['tomorrow'])

    def test_group_budget_currency_mode_and_time_bounds(self):
        r = self.run_request('coffee with $60 total, driving after 2 pm until 8 pm', budget_group=60, currency='USD',
                             transport='driving', start_time=840, end_time=1200,
                             time_expressions=['after 2 pm', 'until 8 pm'], travel_leg_minutes=10)
        self.assertFalse(r.issues)
        self.assertEqual((r.request.groupBudget, r.request.transport, r.request.startTime, r.request.endTime, r.request.maxLegTravel),
                         (60, 'driving', 840, 1200, 10))
        self.assertIn('mode-independent', ' '.join(r.notes))

    def test_relative_date_guard_repairs_observed_tomorrow_omission(self):
        r = self.run_request('coffee tomorrow')
        self.assertIsNone(r.interpretation.date)
        self.assertIn('tomorrow', r.interpretation.date_expressions)
        self.assertIsNone(r.request)
        self.assertIn('not resolved yet', ' '.join(r.issues))

    def test_unsupported_ambiguous_and_invalid_requests(self):
        for text, fields in [
            ('coffee and skydiving', {'activities': ['coffee', 'skydiving']}),
            ('coffee or museum', {'activities': ['coffee', 'museum']}),
            ('coffee not bowling', {'activities': ['coffee']}),
            ('coffee for four or six', {'uncertainties': ['Group size is ambiguous']}),
            ('coffee at 7', {'time_expressions': ['at 7']}),
            ('coffee €20 each', {'budget_per_person': 20, 'currency': 'EUR'}),
            ('concert', {'activities': ['concert']}),
        ]:
            with self.subTest(text=text):
                r = self.run_request(text, **fields)
                self.assertIsNone(r.request)
                self.assertTrue(r.issues)
        for manual in [{'people': '0'}, {'budget': '-1'}, {'travel': '1.5'}, {'date': '2026-02-30'}]:
            self.assertIsNone(self.run_request('coffee', manual=manual).request)

    def test_dropped_money_or_travel_caps_cannot_be_silently_ignored(self):
        for text in ['coffee under $20 each', 'coffee with 15 minutes total travel']:
            self.assertIsNone(self.run_request(text).request)
        self.assertIsNone(self.run_request('coffee with $20', budget_per_person=20, currency='USD').request)

    def test_no_more_than_is_a_cap_not_an_activity_exclusion(self):
        r = self.run_request('coffee, no more than 15 minutes travel', travel_total_minutes=15)
        self.assertFalse(r.issues)
        self.assertEqual(r.request.travel, 15)

    def test_endpoint_model_errors_are_safe(self):
        for error in [AIError('private detail'), TimeoutError()]:
            with patch('backend.interpretation.create_provider') as factory:
                factory.return_value.interpret.side_effect = error
                response = interpret_outing(InterpretationInput(text='coffee'))
            self.assertEqual(response.status_code, 503)
            self.assertNotIn(b'private detail', response.body)

    def test_endpoint_success_does_not_call_engine(self):
        with patch('backend.interpretation.create_provider') as factory, patch('backend.main.recommend_plans') as engine:
            factory.return_value.interpret.return_value = extraction()
            r = interpret_outing(InterpretationInput(text='coffee for 2 people in Baltimore'))
        self.assertIsNotNone(r.request)
        engine.assert_not_called()


if __name__ == '__main__':
    unittest.main()
