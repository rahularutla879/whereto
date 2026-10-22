"""Focused continuation contract tests; no running model needed."""
import unittest
from datetime import datetime, timezone, date
from unittest.mock import Mock

from backend.ai import Interpretation
from backend.interpretation import InterpretationInput, interpret_request
from backend.ranking import recommend_plans

NOW = datetime(2026, 10, 21, 15, tzinfo=timezone.utc)


class ClarificationTests(unittest.TestCase):
    def initial(self, text='coffee', **fields):
        values = dict(activities=['coffee'], people=None, location=None, date=None,
                      budget_per_person=None, preferences=[])
        values.update(fields)
        provider = Mock()
        provider.interpret.return_value = Interpretation(**values)
        result = interpret_request(InterpretationInput(text=text), provider, now=NOW)
        provider.interpret.assert_called_once()
        return result

    def answer(self, result, answers, preferences=None):
        provider = Mock()
        provider.interpret.side_effect = AssertionError('Continuation must not call AI')
        response = interpret_request(InterpretationInput(text=result.pending.text,
            pending=result.pending, answers=answers, preferences=preferences or {}), provider,
            now=NOW)
        provider.interpret.assert_not_called()
        return response

    def test_complete_text_only_and_optional_budget(self):
        r = self.initial('coffee in Baltimore for 2 people on 2026-11-07', location='Baltimore', people=2)
        self.assertFalse(r.questions)
        self.assertIsNone(r.request.budget)
        self.assertEqual(r.request.date, date(2026, 11, 7))
        self.assertTrue(recommend_plans(r.request).provisionalPlans)

    def test_absent_optional_model_uncertainty_does_not_trigger_question(self):
        r = self.initial('coffee in Baltimore for 2 people on 2026-11-07', location='Baltimore', people=2,
            uncertainties=['No budget specified', 'Experience preference unknown'])
        self.assertFalse(r.issues)
        self.assertFalse(r.questions)
        self.assertIsNotNone(r.request)

    def test_stated_ambiguous_optional_constraint_is_not_treated_as_absent(self):
        r = self.initial('coffee in Baltimore for 2 people under 50 each on 2026-11-07', location='Baltimore', people=2,
            uncertainties=['Budget unknown: currency is unclear'])
        self.assertIsNone(r.request)
        self.assertIn('currency', ' '.join(r.issues))

    def test_group_answer_cannot_clear_an_ambiguous_group_budget(self):
        r = self.initial('coffee in Baltimore with group budget under 50 total on 2026-11-07', location='Baltimore',
            uncertainties=['Group budget currency is unclear'])
        done = self.answer(r, {'people': '4'})
        self.assertIsNone(done.request)
        self.assertIn('currency', ' '.join(done.issues))

    def test_activity_answer_keeps_original_stop_time_ambiguity(self):
        r = self.initial('something fun then coffee at 7 PM in Baltimore for 2 people on 2026-11-07',
            activities=['something fun', 'coffee'], location='Baltimore', people=2)
        done = self.answer(r, {'activities': 'museum'})
        self.assertIsNone(done.request)
        self.assertEqual([q.field for q in done.questions], ['time'])
        complete = self.answer(done, {'time': 'from 6 PM to 10 PM'})
        self.assertEqual(complete.request.activities, ['museum', 'coffee'])

    def test_missing_city(self):
        r = self.initial('coffee for 2 people on 2026-11-07', people=2)
        self.assertEqual([q.field for q in r.questions], ['location'])
        done = self.answer(r, {'location': 'Baltimore'})
        self.assertFalse(done.issues)
        self.assertTrue(recommend_plans(done.request).provisionalPlans)
        self.assertEqual(done.request.location, 'Baltimore')

    def test_missing_group_and_invalid_answers_remain_recoverable(self):
        r = self.initial('coffee in Baltimore on 2026-11-07', location='Baltimore')
        for invalid in ['many', '0', '101', '2.5']:
            r = self.answer(r, {'people': invalid})
            self.assertIsNone(r.request)
            self.assertEqual(r.questions[0].field, 'people')
            self.assertEqual(r.pending.text, 'coffee in Baltimore on 2026-11-07')
        done = self.answer(r, {'people': '6 people'})
        self.assertEqual(done.request.people, 6)

    def test_simple_word_answer_needs_no_model(self):
        r = self.initial('coffee in Baltimore on 2026-11-07', location='Baltimore')
        self.assertEqual(self.answer(r, {'people': 'four people'}).request.people, 4)

    def test_events_require_date_and_no_matching_date_is_feasibility(self):
        r = self.initial('concert in Baltimore for 2 people', activities=['concert'], location='Baltimore', people=2)
        self.assertEqual([q.field for q in r.questions], ['date'])
        bad = self.answer(r, {'date': 'whenever'})
        self.assertIsNone(bad.request)
        done = self.answer(bad, {'date': '2026-11-07'})
        self.assertTrue(recommend_plans(done.request).plans)
        none = self.answer(r, {'date': '2026-11-08'})
        self.assertFalse(none.questions)
        self.assertFalse(recommend_plans(none.request).plans)

    def test_weekend_keeps_next_semantics_and_time_bounds(self):
        r = self.initial('coffee next weekend after 6 PM until 10 PM in Baltimore for 2 people', location='Baltimore', people=2)
        self.assertEqual([q.field for q in r.questions], ['date'])
        done = self.answer(r, {'date': 'Saturday'})
        self.assertEqual((done.request.date, done.request.startTime, done.request.endTime), (date(2026, 10, 31), 1081, 1320))

    def test_date_correction_preserves_evening_and_dinner_occurrences(self):
        r = self.initial('lunch and dinner tomorrow evening or next weekend in Baltimore for 2 people',
            activities=['lunch', 'dinner'], location='Baltimore', people=2)
        done = self.answer(r, {'date': '2026-11-07'})
        self.assertFalse(done.issues)
        self.assertEqual((done.request.startTime, done.request.dinnerStops, done.request.activities), (1080, [1], ['food', 'food']))

    def test_combined_essentials_and_repeated_activities_constraints_survive(self):
        text = 'coffee, museum, then coffee tomorrow under $80 each, $200 total, 30 minutes total travel, 20 minutes between stops, driving, best experience'
        r = self.initial(text, activities=['coffee', 'museum', 'coffee'], budget_per_person=80,
            budget_group=200, currency='USD', travel_total_minutes=30, travel_leg_minutes=20,
            transport='driving', cost='experience', preferences=['best experience'])
        self.assertEqual({q.field for q in r.questions}, {'location', 'people'})
        done = self.answer(r, {'location': 'Baltimore', 'people': '3'})
        req = done.request
        self.assertFalse(done.issues)
        self.assertEqual(req.activities, ['coffee', 'museum', 'coffee'])
        self.assertEqual((req.date, req.budget, req.groupBudget, req.travel, req.maxLegTravel, req.cost, req.transport),
            (date(2026, 10, 22), 80, 200, 30, 20, 'experience', 'driving'))
        self.assertIn('best experience', ' '.join(done.notes))
        self.assertEqual(done.pending.text, text)

    def test_group_ambiguity_does_not_ask_for_activities(self):
        r = self.initial('coffee in Baltimore for four or six people on 2026-11-07', location='Baltimore',
            uncertainties=['Group size is ambiguous'])
        self.assertEqual([q.field for q in r.questions], ['people'])
        self.assertEqual(self.answer(r, {'people': '4'}).request.activities, ['coffee'])

    def test_manual_precedence_including_zero_and_balanced(self):
        r = self.initial('coffee tomorrow under $50 each, best experience', budget_per_person=50, currency='USD', cost='experience')
        done = self.answer(r, {'location': 'Boston', 'people': '6', 'date': '2026-11-14'},
            {'location': 'Baltimore', 'people': '3', 'date': '2026-11-07', 'budget': '0', 'travel': '0', 'cost': 'balanced', 'costExplicit': True})
        self.assertFalse(done.issues)
        self.assertEqual((done.request.location, done.request.people, done.request.date, done.request.budget, done.request.travel, done.request.cost),
            ('Baltimore', 3, date(2026, 11, 7), 0, 0, 'balanced'))

    def test_unclear_choice_keeps_previously_chosen_stop(self):
        r = self.initial('something competitive then cocktails in Baltimore for 6 people on 2026-11-07',
            activities=['something competitive', 'cocktails'], location='Baltimore', people=6,
            preferences=['competitive'], suggested_activities=['bowling'])
        self.assertEqual([q.field for q in r.questions], ['activities'])
        done = self.answer(r, {'activities': 'bowling'})
        self.assertFalse(done.issues)
        self.assertEqual(done.request.activities, ['bowling', 'drinks'])

    def test_activity_alternatives_and_no_activity(self):
        r = self.initial('coffee or museum in Baltimore for 2 people on 2026-11-07', activities=['coffee', 'museum'], location='Baltimore', people=2)
        done = self.answer(r, {'activities': 'coffee, museum, then coffee'})
        self.assertEqual(done.request.activities, ['coffee', 'museum', 'coffee'])
        r = self.initial('an outing in Baltimore for 2 people on 2026-11-07', activities=[], location='Baltimore', people=2)
        self.assertEqual(self.answer(r, {'activities': 'museum'}).request.activities, ['museum'])

    def test_unsupported_does_not_start_question_loop(self):
        for text, fields in [('skydiving', {'activities': ['skydiving']}),
                ('coffee overnight', {}), ('coffee €20 each', {'budget_per_person': 20, 'currency': 'EUR'})]:
            r = self.initial(text, **fields)
            self.assertIsNone(r.request)
            if r.unsupported:
                self.assertIsNone(r.pending)
                self.assertFalse(r.questions)

    def test_time_correction_keeps_calendar_and_other_constraints(self):
        r = self.initial('coffee on 2026-11-07 at 7 in Baltimore for 2 people', location='Baltimore', people=2)
        done = self.answer(r, {'time': 'from 6 PM to 10 PM'})
        self.assertFalse(done.issues)
        self.assertEqual((done.request.date, done.request.startTime, done.request.endTime), (date(2026, 11, 7), 1080, 1320))

    def test_delayed_answer_keeps_relative_date_and_rejects_past_outing(self):
        r = self.initial('coffee tomorrow for 2 people', people=2)
        provider = Mock()
        done = interpret_request(InterpretationInput(text=r.pending.text, pending=r.pending,
            answers={'location': 'Baltimore'}), provider,
            now=datetime(2026, 10, 23, 15, tzinfo=timezone.utc))
        self.assertIsNone(done.request)
        self.assertIn('past', ' '.join(done.issues))
        provider.interpret.assert_not_called()

    def test_invalid_activity_answer_keeps_original(self):
        r = self.initial('an outing in Baltimore for 2 people on 2026-11-07', activities=[], location='Baltimore', people=2)
        invalid = self.answer(r, {'activities': 'banana'})
        self.assertIsNotNone(invalid.pending)
        done = self.answer(invalid, {'activities': 'museum'})
        self.assertEqual(done.request.activities, ['museum'])

    def test_missing_location_is_neutral_and_another_city_reaches_planner(self):
        text = 'coffee, museum, then coffee for 2 people under $80 each on 2026-11-07'
        for uncertainties in ([], ['Location is unknown']):
            with self.subTest(uncertainties=uncertainties):
                r = self.initial(text, people=2, activities=['coffee', 'museum', 'coffee'],
                    budget_per_person=80, currency='USD', uncertainties=uncertainties)
                self.assertIsNone(r.interpretation.location)
                self.assertEqual([q.field for q in r.questions], ['location'])
                self.assertEqual(r.questions[0].question,
                    'Where would you like to go? Enter a city or location to continue.')
                self.assertNotIn('Baltimore', ' '.join(r.issues + [q.question for q in r.questions]))
                done = self.answer(r, {'location': 'Boston'})
                self.assertFalse(done.issues)
                self.assertFalse(done.questions)
                self.assertEqual(done.pending.text, text)
                self.assertEqual(done.request.location, 'Boston')
                self.assertEqual(done.request.activities, ['coffee', 'museum', 'coffee'])
                self.assertEqual((done.request.people, done.request.budget), (2, 80))
                result = recommend_plans(done.request)
                self.assertEqual(result.request.location, 'Boston')
                self.assertFalse(result.plans)
                self.assertFalse(result.provisionalPlans)
                self.assertTrue(any(error.code == 'unsupported_location' for error in result.errors))

    def test_changed_original_is_new_request_and_calls_provider(self):
        r = self.initial()
        provider = Mock()
        provider.interpret.return_value = Interpretation(activities=['museum'], location='Baltimore', people=2,
            date=None, budget_per_person=None, preferences=[])
        done = interpret_request(InterpretationInput(text='museum in Baltimore for 2 people on 2026-11-07', pending=r.pending), provider, now=NOW)
        provider.interpret.assert_called_once()
        self.assertEqual(done.request.activities, ['museum'])


if __name__ == '__main__':
    unittest.main()
