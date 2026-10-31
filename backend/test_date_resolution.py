"""Fixed clocks, local calendars and actual interpreter-to-planner regressions."""
import unittest
from datetime import date, datetime, timezone
from unittest.mock import Mock
from zoneinfo import ZoneInfo

from backend.ai import Interpretation
from backend.date_resolution import resolve_datetime, complete_year_answer
from backend.interpretation import InterpretationInput, interpret_request
from backend.ranking import recommend_plans

REFERENCE = datetime(2026, 10, 21, 12, tzinfo=ZoneInfo('America/New_York'))


class DateResolutionTests(unittest.TestCase):
    def test_qualified_weekday_dates_and_independent_conflicts(self):
        for text in ('Saturday, November 7, 2026', 'Saturday November 7 2026', 'Saturday, 2026-11-07', 'Saturday, 7 Nov 2026'):
            r = self.resolve(text, date_expressions=['Saturday'] if 'Saturday' in text else [])
            self.assertEqual(r.date, date(2026, 11, 7))
            self.assertFalse(r.issues)
        for text in ('Friday, November 7, 2026', 'Saturday and November 7, 2026', 'Saturday, November 7, 2026 and tomorrow'):
            self.assertTrue(self.resolve(text).issues, text)
        self.assertTrue(self.resolve('Saturday, November 31, 2026').issues)
        self.assertEqual(complete_year_answer('Saturday, November 7', '2026'), 'Saturday, november 7, 2026')

    def test_exact_manual_prompt_through_interpretation_and_clarification(self):
        prompt = 'Plan bowling followed by dinner in Baltimore on Saturday, November 7, 2026, for 4 people.'
        for phrases in ([], ['Saturday', 'November 7, 2026'], ['Saturday, November 7, 2026']):
            provider = Mock()
            provider.interpret.return_value = Interpretation(activities=['bowling', 'dinner'], people=4,
                budget_per_person=None, date=None, location='Baltimore', preferences=[], date_expressions=phrases)
            value = InterpretationInput(text=prompt)
            r = interpret_request(value, provider, now=REFERENCE)
            self.assertFalse(r.issues)
            self.assertFalse(r.questions)
            self.assertEqual(r.request.date, date(2026, 11, 7))
            self.assertEqual(r.request.activities, ['bowling', 'food'])
            # Existing continuation and manual priority also retain the date.
            continued = interpret_request(InterpretationInput(text=prompt, pending=r.pending), provider, now=REFERENCE)
            self.assertEqual(continued.request.date, r.request.date)
            manual = interpret_request(InterpretationInput(text=prompt, preferences={'date': '2026-11-14'}), provider, now=REFERENCE)
            self.assertEqual(manual.request.date, date(2026, 11, 14))

    def resolve(self, text, now=REFERENCE, **kw):
        return resolve_datetime(text, kw.pop('date_expressions', []), kw.pop('time_expressions', []),
                                kw.pop('location', 'Baltimore'), now=now, **kw)

    def test_supported_days(self):
        for expression, expected in [('today', '2026-10-21'), ('tonight', '2026-10-21'),
                                     ('tomorrow', '2026-10-22'), ('tomorrow evening', '2026-10-22'),
                                     ('this Friday', '2026-10-23'), ('next Friday', '2026-10-30'),
                                     ('this Saturday', '2026-10-24'), ('next Saturday', '2026-10-31'),
                                     ('this Sunday', '2026-10-25'), ('next Sunday', '2026-11-01')]:
            with self.subTest(expression=expression):
                result = self.resolve(expression)
                self.assertFalse(result.issues)
                self.assertEqual(result.date.isoformat(), expected)

    def test_weekday_today_and_weekend_boundaries(self):
        for reference, expression, expected in [
            ('2026-10-23', 'this Friday', '2026-10-23'),
            ('2026-10-23', 'next Friday', '2026-10-30'),
            ('2026-10-24', 'this Friday', '2026-10-30'),
            ('2026-10-25', 'next Saturday', '2026-10-31'),
            ('2026-10-25', 'this Sunday', '2026-10-25'),
            ('2026-10-26', 'next Sunday', '2026-11-08')]:
            r = self.resolve(expression, now=datetime.fromisoformat(reference).replace(tzinfo=ZoneInfo('America/New_York')))
            self.assertEqual(r.date.isoformat(), expected)
        for day in (23, 24, 25, 26):
            for expression in ('this weekend', 'next weekend'):
                r = self.resolve(expression, now=REFERENCE.replace(day=day))
                self.assertIsNone(r.date)
                self.assertIn('Saturday or Sunday', ' '.join(r.issues))

    def test_month_year_and_leap_boundaries(self):
        for reference, expected in [('2026-01-31', '2026-02-01'), ('2026-12-31', '2027-01-01'),
                                    ('2028-02-28', '2028-02-29'), ('2028-02-29', '2028-03-01'),
                                    ('2027-02-28', '2027-03-01')]:
            r = self.resolve('tomorrow', now=datetime.fromisoformat(reference).replace(tzinfo=ZoneInfo('America/New_York')))
            self.assertEqual(r.date.isoformat(), expected)

    def test_explicit_dates_and_conflicts(self):
        for expression in ('2028-02-29', 'February 29, 2028', 'February 29th 2028', '29th February 2028', 'Feb 29 2028', '29 of February 2028'):
            r = self.resolve(expression)
            self.assertFalse(r.issues)
            self.assertEqual(r.date, date(2028, 2, 29))
        for expression in ('2027-02-29', 'November 31, 2026', 'March 11', 'tomorrow on 2026-11-07', 'next week'):
            self.assertTrue(self.resolve(expression).issues, expression)
        r = self.resolve('tomorrow this weekend', manual_date='2026-11-07')
        self.assertFalse(r.issues)
        self.assertEqual(r.date, date(2026, 11, 7))
        self.assertTrue(self.resolve('coffee', manual_date='2026-02-30').issues)

    def test_location_reference_and_fallback(self):
        now = datetime(2026, 11, 1, 2, 30, tzinfo=timezone.utc)
        baltimore = self.resolve('tomorrow', now=now, location='Baltimore, MD')
        self.assertEqual(baltimore.date, date(2026, 11, 1))
        for location in (None, 'Tokyo', 'Springfield'):
            fallback = self.resolve('tomorrow', now=now, location=location)
            self.assertEqual(fallback.date, date(2026, 11, 2))
            self.assertEqual(fallback.timezone, 'UTC')
            if location:self.assertTrue(any('timezone is not known' in issue for issue in fallback.issues))
            self.assertNotIn('verified local timezone', ' '.join(fallback.notes))
        with self.assertRaises(ValueError):
            self.resolve('tomorrow', now=datetime(2026, 10, 21))

    def test_clocks_and_bounds(self):
        for text, start, end in [('6 PM', 1080, 1440), ('18:00', 1080, 1440), ('noon', 720, 1440),
                                 ('midnight', 0, 1440), ('after 6 PM', 1081, 1440),
                                 ('before 10 PM', 600, 1319), ('between 6 and 9 PM', 1080, 1260),
                                 ('from 18:00 to 21:00', 1080, 1260), ('10 PM–midnight', 1320, 1440),
                                 ('from midnight to noon', 0, 720), ('before noon', 600, 719),
                                 ('before 6 AM', 0, 359), ('at 12 AM', 0, 1440), ('at 12 PM', 720, 1440), ('starts at 6 PM ends at 9 PM', 1080, 1260),
                                 ('tomorrow evening at 7 PM', 1140, 1440), ('Saturday night', 1080, 1440)]:
            r = self.resolve(text)
            self.assertFalse(r.issues, (text, r.issues))
            self.assertEqual((r.start, r.end), (start, end), text)
        self.assertFalse(self.resolve('tomorrow evening', time_expressions=['evening']).issues)
        r = self.resolve('after 6 PM before 10 PM', time_expressions=['6 PM', '10 PM', 'after 6 PM before 10 PM'])
        self.assertFalse(r.issues)
        self.assertEqual((r.start, r.end), (1081, 1319))

    def test_conflicting_overnight_and_invalid_times(self):
        for text in ('between 10 PM and 1 AM', 'from 22:00 to 01:00', 'after 10 PM until 1 AM', 'overnight at 10 PM'):
            self.assertIn('Overnight', ' '.join(self.resolve(text).issues), text)
        for text in ('between 6 PM and 5 PM', 'after 10 PM before 9 PM', 'at 7', '25:00', '13 PM', '18:99',
                     'at 6 PM at 7 PM', 'after 23:59', 'last Friday', 'yesterday', '6 PM PST', 'day after tomorrow', 'tomorrow morning'):
            self.assertTrue(self.resolve(text).issues, text)

    def test_no_silent_past_rollover(self):
        for text in ('today at 6 AM', 'this Wednesday at 6 AM', 'today before noon', '2026-10-20'):
            self.assertTrue(any(word in ' '.join(self.resolve(text).issues) for word in ('past', 'passed')), text)
        r = self.resolve('today', now=REFERENCE.replace(hour=15, minute=1, second=30))
        self.assertFalse(r.issues)
        self.assertEqual(r.start, 902)
        self.assertEqual(r.date, REFERENCE.date())
        r = self.resolve('tonight', now=REFERENCE.replace(hour=20))
        self.assertFalse(r.issues)  # A documented default is not an explicit appointment.
        self.assertFalse(r.explicit_start)
        self.assertEqual(r.start,1200)

    def test_daylight_saving_gaps_folds_and_midnight(self):
        for text in ('2027-03-14 between midnight and noon', '2026-11-01 from midnight to 4 AM', '2027-03-14 at 2:30 AM', '2026-11-01 at 1:30 AM', '2026-11-01 before 1:31 AM'):
            self.assertTrue(self.resolve(text).issues, text)
        for text in ('2027-03-14 at 3:30 AM', '2026-11-01 at 2:30 AM', '2026-11-01 from 10 PM to midnight'):
            self.assertFalse(self.resolve(text).issues, text)
        for reference, expected in [('2027-03-14T06:30:00+00:00', '2027-03-15'),
                                    ('2027-03-14T07:30:00+00:00', '2027-03-15'),
                                    ('2026-11-01T05:30:00+00:00', '2026-11-02'),
                                    ('2026-11-01T06:30:00+00:00', '2026-11-02')]:
            self.assertEqual(self.resolve('tomorrow', now=datetime.fromisoformat(reference)).date.isoformat(), expected)

    def test_manual_date_and_location_win_without_erasing_time_constraints(self):
        provider = Mock()
        provider.interpret.return_value = Interpretation(activities=['coffee'], people=2, location='Boston',
            date='2030-01-01', budget_per_person=None, preferences=[],
            date_expressions=['this weekend'], time_expressions=['between 6 and 9 PM'])
        value = InterpretationInput(text='coffee for 2 people in Boston this weekend between 6 and 9 PM',
                                    preferences={'location': 'Baltimore', 'date': '2026-11-07'})
        result = interpret_request(value, provider, now=REFERENCE)
        self.assertFalse(result.issues)
        self.assertEqual((result.request.location, result.request.date, result.request.startTime, result.request.endTime),
                         ('Baltimore', date(2026, 11, 7), 1080, 1260))
        self.assertIn('America/New_York', ' '.join(result.notes))
        self.assertIn('this weekend', result.interpretation.date_expressions)
        value.text = 'coffee for 2 people in Boston tomorrow from 10 PM to 1 AM'
        provider.interpret.return_value.date_expressions = ['tomorrow']
        provider.interpret.return_value.time_expressions = ['from 10 PM to 1 AM']
        self.assertIsNone(interpret_request(value, provider, now=REFERENCE).request)

    def test_stop_specific_times_cannot_become_overall_bounds(self):
        for text in ('coffee at noon then museum', 'coffee then museum at 18:00'):
            provider = Mock()
            provider.interpret.return_value = Interpretation(activities=['coffee', 'museum'], people=2,
                location='Baltimore', date=None, budget_per_person=None, preferences=[])
            result = interpret_request(InterpretationInput(text=text + ' for 2 people in Baltimore tomorrow'),
                                       provider, now=REFERENCE)
            self.assertIsNone(result.request)
            self.assertIn('Stop-specific', ' '.join(result.issues))

    def test_interpretation_reaches_real_planner_without_ai_arithmetic(self):
        for phrase, expected in [('tomorrow', '2026-10-22'), ('next Saturday between 6 and 9 PM', '2026-10-31'),
                                  ('November 7, 2026 from noon to 9 PM', '2026-11-07')]:
            raw = f'coffee for 2 people in Baltimore {phrase}'
            provider = Mock()
            provider.interpret.return_value = Interpretation(activities=['coffee'], people=2, location='Baltimore',
                date='2030-01-01', start_time=1 if 'PM' in phrase else None, end_time=2 if 'PM' in phrase else None, budget_per_person=None, preferences=[],
                date_expressions=[], time_expressions=[])
            result = interpret_request(InterpretationInput(text=raw), provider, now=REFERENCE)
            self.assertFalse(result.issues)
            self.assertEqual(result.request.date.isoformat(), expected)
            plans = recommend_plans(result.request).provisionalPlans
            self.assertTrue(plans)
            self.assertTrue(all(p.candidate.date.isoformat() == expected for p in plans))
            self.assertTrue(all(p.stops[0].start >= result.request.startTime for p in plans))
        for phrase in ('this weekend', 'between 10 PM and 1 AM', 'today at 6 AM'):
            result = interpret_request(InterpretationInput(text=f'coffee for 2 people in Baltimore {phrase}'), provider, now=REFERENCE)
            self.assertIsNone(result.request)


if __name__ == '__main__':
    unittest.main()
