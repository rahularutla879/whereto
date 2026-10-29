"""Named calendar dates and contextual follow-ups, with no model arithmetic."""
import unittest
from datetime import date, datetime, timezone
from unittest.mock import Mock
from zoneinfo import ZoneInfo

from backend.ai import Interpretation
from backend.date_resolution import MONTHS, resolve_datetime
from backend.interpretation import InterpretationInput, interpret_request
from backend.ranking import recommend_plans

NOW = datetime(2026, 10, 22, 12, tzinfo=ZoneInfo('America/New_York'))


class NamedCalendarTests(unittest.TestCase):
    def resolve(self, text, now=NOW, **kwargs):
        return resolve_datetime(text, [], [], kwargs.pop('location', 'Baltimore'), now=now, **kwargs)

    def initial(self, text, **fields):
        provider = Mock()
        provider.interpret.return_value = Interpretation(**{
            'activities': ['coffee'], 'people': 2, 'location': 'Baltimore',
            'date': None, 'budget_per_person': None, 'preferences': [], **fields})
        result = interpret_request(InterpretationInput(text=text), provider, now=NOW)
        provider.interpret.assert_called_once_with(text)
        return result

    def answer(self, previous, answer, *, preferences=None, now=NOW):
        provider = Mock()
        provider.interpret.side_effect = AssertionError('A date answer must not call AI')
        result = interpret_request(InterpretationInput(text=previous.pending.text,
            pending=previous.pending, answers=answer, preferences=preferences or {}), provider, now=now)
        provider.interpret.assert_not_called()
        return result

    def test_all_months_full_abbreviated_case_period_and_both_orders(self):
        for month, full in enumerate(MONTHS, 1):
            aliases = [full, full[:3]] + (['sept'] if month == 9 else [])
            for alias in aliases:
                for spelling in [alias.lower(), alias.upper(), alias.title() + '.']:
                    for expression in [f'{spelling} 11 2027', f'{spelling} 11, 2027', f'11 {spelling} 2027']:
                        with self.subTest(expression=expression):
                            result = self.resolve(expression)
                            self.assertFalse(result.issues)
                            self.assertEqual(result.date, date(2027, month, 11))
                            self.assertEqual(result.time_expressions, [])

    def test_yearless_months_use_only_current_local_year(self):
        for month, full in enumerate(MONTHS, 1):
            for expression in [f'{full} 11', f'11 {full[:3]}', f'{full[:3].upper()}. 11']:
                with self.subTest(expression=expression):
                    result = self.resolve(expression)
                    if month >= 11:
                        self.assertFalse(result.issues)
                        self.assertEqual(result.date, date(2026, month, 11))
                    else:
                        self.assertIsNone(result.date)
                        self.assertEqual(result.problems[0].reason, 'missing_year')
        for expression, expected in [('nov 11', '2026-11-11'), ('dec 31', '2026-12-31'), ('oct 22', '2026-10-22')]:
            self.assertEqual(str(self.resolve(expression).date), expected)
        for expression in ['mar 11', 'oct 21', 'Sep 11', 'Sept 11', 'Sept. 11', '11 Sept.']:
            self.assertEqual(self.resolve(expression).problems[0].reason, 'missing_year')

    def test_reference_uses_location_timezone_at_day_and_year_boundaries(self):
        instant = datetime(2026, 10, 23, 2, tzinfo=timezone.utc)
        self.assertEqual(self.resolve('Oct 22', now=instant).date, date(2026, 10, 22))
        self.assertEqual(self.resolve('Oct 22', now=instant, location='unknown').problems[0].reason, 'missing_year')
        instant = datetime(2027, 1, 1, 2, tzinfo=timezone.utc)
        self.assertEqual(self.resolve('Dec 31', now=instant).date, date(2026, 12, 31))
        self.assertEqual(self.resolve('Dec 31', now=instant, location='unknown').date, date(2027, 12, 31))

    def test_explicit_years_past_dates_and_real_calendar_validation(self):
        for expression in ['Nov 11 2027', 'Nov 11, 2027', 'Nov. 11,2027', '11 November 2027', '2027-11-11', 'November 11th 2027', '11th of Nov. 2027']:
            result = self.resolve(expression)
            self.assertFalse(result.issues)
            self.assertEqual(result.date, date(2027, 11, 11))
        for expression in ['Mar 11 2026', '2026-10-21', '11 November 2025', 'Nov 11,2025']:
            result = self.resolve(expression)
            self.assertEqual(result.problems[0].reason, 'past_date')
            self.assertEqual(result.problems[0].question, 'That date has already passed. Please choose today or a future date.')
        for expression in ['Nov 31', 'Apr 31 2027', 'Feb 30', 'Jan 0 2027', '2026-02-30', 'Feb 29 2027']:
            result = self.resolve(expression)
            self.assertEqual(result.problems[0].reason, 'invalid_date', expression)
            self.assertEqual(result.problems[0].question, "That date doesn't exist. Please enter a valid date.")

    def test_leap_day_requires_valid_year_without_rollover(self):
        result = self.resolve('Feb. 29')
        self.assertIsNone(result.date)
        self.assertEqual(result.problems[0].reason, 'missing_year')
        self.assertIn('leap year', result.problems[0].guidance)
        self.assertEqual(self.resolve('29 Feb 2028').date, date(2028, 2, 29))
        before = NOW.replace(year=2028, month=2, day=28)
        self.assertEqual(self.resolve('Feb 29', now=before).date, date(2028, 2, 29))
        self.assertEqual(self.resolve('Feb 29', now=before.replace(day=29)).date, date(2028, 2, 29))
        passed = self.resolve('Feb 29', now=before.replace(month=3, day=1)).problems[0]
        self.assertEqual(passed.reason, 'missing_year')
        self.assertIn('leap year', passed.guidance)
        self.assertIn('2029', self.resolve('Mar 11', now=NOW.replace(year=2028)).problems[0].guidance)

    def test_exact_original_request_and_model_year_uncertainty_reach_planner(self):
        for expressions in [[], ['nov 11']]:
            result = self.initial('dinner for six in baltimore on nov 11',
                activities=['dinner'], people=6, location='baltimore', date_expressions=expressions,
                uncertainties=['Date year unspecified'])
            self.assertFalse(result.issues)
            self.assertFalse(result.questions)
            self.assertEqual((result.request.people, result.request.date, result.request.activities),
                (None, date(2026, 11, 11), ['food']))
            plans = recommend_plans(result.request).provisionalPlans
            self.assertTrue(plans)
            self.assertTrue(all(p.candidate.date == date(2026, 11, 11) and p.candidate.people is None for p in plans))

        uncertain = self.initial('coffee for two in Baltimore on Nov 11',
            uncertainties=['Date has an unresolved condition'])
        self.assertIsNone(uncertain.request)
        self.assertIn('date', [q.field for q in uncertain.questions])

    def test_year_only_answer_keeps_original_details_and_time_without_ai(self):
        initial = self.initial('coffee, museum, coffee for two in Baltimore on mar 11, maximum $60 each, from 6 PM to 11 PM',
            activities=['coffee', 'museum', 'coffee'], budget_per_person=60, currency='USD')
        self.assertEqual(initial.questions[0].reason, 'missing_year')
        wrong = self.answer(initial, {'date': '2026'})
        self.assertIsNone(wrong.request)
        self.assertEqual(wrong.questions[0].reason, 'past_date')
        fixed = self.answer(wrong, {'date': '2027'})
        self.assertFalse(fixed.issues)
        self.assertEqual(fixed.pending.text, initial.pending.text)
        self.assertEqual((fixed.request.date, fixed.request.budget, fixed.request.people,
            fixed.request.startTime, fixed.request.endTime), (date(2027, 3, 11), 60, None, 1080, 1380))
        self.assertEqual(fixed.request.activities, ['coffee', 'museum', 'coffee'])
        edited = self.answer(fixed, {'activities': 'museum, coffee, coffee'}, preferences={'budget': '40'})
        self.assertFalse(edited.issues)
        self.assertEqual(edited.request.date, date(2027, 3, 11))
        self.assertEqual(edited.request.budget, 40)

    def test_date_answer_then_year_only_and_leap_recovery(self):
        original = self.initial('coffee for two in Baltimore')
        future = self.answer(original, {'date': 'nov 11'})
        self.assertFalse(future.issues)
        self.assertEqual(future.request.date, date(2026, 11, 11))
        past = self.answer(original, {'date': '11 Mar'})
        self.assertEqual(past.questions[0].reason, 'missing_year')
        self.assertEqual(self.answer(past, {'date': '2027'}).request.date, date(2027, 3, 11))
        leap = self.answer(original, {'date': '29 Feb.'})
        wrong = self.answer(leap, {'date': '2027'})
        self.assertEqual(wrong.questions[0].reason, 'invalid_date')
        fixed = self.answer(wrong, {'date': '2028'})
        self.assertFalse(fixed.issues)
        self.assertEqual(fixed.request.date, date(2028, 2, 29))
        self.assertEqual(original.pending.answers.date, '')

    def test_year_alone_does_not_invent_month_day_or_choose_between_dates(self):
        for text in ['coffee for two in Baltimore', 'coffee for two in Baltimore on Mar 11 or Apr 12']:
            result = self.answer(self.initial(text), {'date': '2027'})
            self.assertIsNone(result.request)
            self.assertIn('date', [q.field for q in result.questions])

    def test_contextual_questions_and_guidance_for_each_reason(self):
        cases = [
            ('', 'missing_date', 'What day are you planning to go?'),
            (' on mar 11', 'missing_year', 'March 11 has already passed this year. Which year would you like to plan for?'),
            (' this weekend', 'weekend', 'Did you mean Saturday or Sunday?'),
            (' on Mar 11 2026', 'past_date', 'That date has already passed. Please choose today or a future date.'),
            (' on Nov 31', 'invalid_date', "That date doesn't exist. Please enter a valid date."),
            (' on Nov 11 at 7', 'invalid_time', 'What overall time window do you mean? Include AM/PM, for example from 6 PM to 10 PM.'),
        ]
        for suffix, reason, expected in cases:
            with self.subTest(reason=reason):
                result = self.initial('coffee for two in Baltimore' + suffix)
                self.assertIsNone(result.request)
                question = result.questions[0]
                self.assertEqual((question.reason, question.question), (reason, expected))
                self.assertTrue(question.helpText)
                self.assertEqual(question.field, 'time' if reason == 'invalid_time' else 'date')
                if reason != 'weekend':
                    self.assertNotIn('Saturday or Sunday', question.question + question.helpText)
                if reason == 'missing_year':
                    self.assertNotIn('tomorrow', question.helpText)
                    self.assertIn('2027', question.helpText)

    def test_manual_date_has_priority_and_does_not_erase_time_constraints(self):
        initial = self.initial('coffee for two in Baltimore on Mar 11 from 6 PM to 10 PM')
        result = self.answer(initial, {'date': '2027'}, preferences={'date': '2026-11-14'})
        self.assertFalse(result.issues)
        self.assertEqual((result.request.date, result.request.startTime, result.request.endTime), (date(2026, 11, 14), 1080, 1320))
        self.assertEqual(self.resolve('Nov 31', manual_date='2026-11-14').date, date(2026, 11, 14))
        self.assertEqual([p.field for p in self.resolve('day after tomorrow morning', manual_date='2026-11-14').problems], ['time'])

    def test_anchored_year_is_not_advanced_on_delayed_continuation(self):
        initial = self.initial('coffee in Baltimore on Dec 31', people=None)
        late = self.answer(initial, {'people': '2'}, now=NOW.replace(year=2027, month=1, day=1))
        self.assertIsNone(late.request)
        self.assertEqual(late.questions[0].reason, 'past_date')

    def test_iso_relative_weekends_and_dst_still_work(self):
        for expression, expected in [('2026-11-11', '2026-11-11'), ('today', '2026-10-22'),
                ('tomorrow', '2026-10-23'), ('this Saturday', '2026-10-24'), ('next Friday', '2026-10-30')]:
            self.assertEqual(str(self.resolve(expression).date), expected)
        self.assertEqual(self.resolve('Nov 1 from 1 AM to 2 AM').problems[0].reason, 'dst')
        self.assertEqual(self.resolve('Mar 14 2027 at 2:30 AM').problems[0].reason, 'dst')
        initial = self.initial('coffee for two in Baltimore next weekend from 6 PM to 9 PM')
        done = self.answer(initial, {'date': 'Saturday'})
        self.assertEqual((done.request.date, done.request.startTime), (date(2026, 10, 31), 1080))
