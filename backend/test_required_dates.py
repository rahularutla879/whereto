"""Finalization policy and deterministic, model-free date continuations."""
import unittest
from datetime import datetime, timezone, date
from unittest.mock import Mock, patch

from pydantic import ValidationError
from backend.ai import Interpretation
from backend.interpretation import InterpretationInput, interpret_request
from backend.models import OutingRequest, PlanningRequest
from backend.ranking import recommend_plans, rank_candidates

NOW = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)


class RequiredDateTests(unittest.TestCase):
    def initial(self, text, **fields):
        provider = Mock()
        values = dict(activities=['coffee', 'museum', 'coffee'], people=2,
            location='Baltimore', date=None, budget_per_person=None, preferences=[])
        values.update(fields)
        provider.interpret.return_value = Interpretation(**values)
        result = interpret_request(InterpretationInput(text=text), provider, now=NOW)
        provider.interpret.assert_called_once_with(text)
        return result

    def answer(self, previous, answers, manual=None):
        with patch('backend.interpretation.create_provider') as factory:
            result = interpret_request(InterpretationInput(text=previous.pending.text,
                pending=previous.pending, answers=answers, preferences=manual or {}), now=NOW)
        factory.assert_not_called()
        return result

    def test_ordinary_missing_date_asks_only_for_day_and_never_plans(self):
        with patch('backend.ranking.generate_candidates') as candidates:
            result = self.initial('coffee, museum, then coffee in Baltimore for 2 people',
                uncertainties=['Date not specified'])
        candidates.assert_not_called()
        self.assertIsNone(result.request)
        self.assertEqual([(q.field, q.question) for q in result.questions],
                         [('date', 'What day are you planning to go?')])
        self.assertIsNone(result.interpretation.date)
        self.assertIsNone(result.interpretation.budget_per_person)

    def test_supported_natural_language_date_answers(self):
        initial = self.initial('coffee, museum, then coffee in Baltimore for 2 people')
        for expression, day in [('Today', '2026-10-21'), ('Tomorrow', '2026-10-22'),
                ('This Saturday', '2026-10-24'), ('Next Saturday', '2026-10-31'),
                ('Next Friday', '2026-10-30'), ('November 7, 2026', '2026-11-07'),
                ('2026-11-07', '2026-11-07')]:
            with self.subTest(expression=expression):
                done = self.answer(initial, {'date': expression})
                self.assertFalse(done.issues)
                self.assertFalse(done.questions)
                self.assertEqual(done.request.date.isoformat(), day)
                plans = recommend_plans(done.request).provisionalPlans
                self.assertTrue(plans)
                self.assertTrue(all(p.candidate.date.isoformat() == day for p in plans))
                self.assertTrue(all([v.activity for v in p.candidate.venues] == ['coffee', 'museum', 'coffee'] for p in plans))

    def test_explicit_date_in_original_skips_question(self):
        done = self.initial('coffee, museum, then coffee for 2 people in Baltimore on November 7, 2026')
        self.assertFalse(done.questions)
        self.assertEqual(done.request.date, date(2026, 11, 7))

    def test_ambiguous_invalid_and_past_answers_are_recoverable(self):
        initial = self.initial('coffee, museum, then coffee in Baltimore for 2 people')
        for expression in ['this weekend', '2026-02-30', '2026-10-20', 'March 11', 'whenever']:
            with self.subTest(expression=expression):
                invalid = self.answer(initial, {'date': expression})
                self.assertIsNone(invalid.request)
                self.assertIn('date', [q.field for q in invalid.questions])
                done = self.answer(invalid, {'date': 'Tomorrow'})
                self.assertEqual(done.request.date, date(2026, 10, 22))
                self.assertEqual(done.pending.text, initial.pending.text)

    def test_missing_city_and_date_are_collected_together(self):
        initial = self.initial('coffee, museum, then coffee for 2 people', location=None)
        self.assertEqual({q.field for q in initial.questions}, {'location', 'date'})
        done = self.answer(initial, {'location': 'Baltimore', 'date': 'Tomorrow'})
        self.assertEqual((done.request.location, done.request.people, done.request.date),
                         ('Baltimore', 2, date(2026, 10, 22)))

    def test_missing_date_and_unclear_time_are_collected_together(self):
        initial = self.initial('coffee, museum, then coffee in Baltimore for 2 people at 7')
        self.assertEqual({q.field for q in initial.questions}, {'date', 'time'})
        done = self.answer(initial, {'date': 'Tomorrow', 'time': 'from 6 PM to 11 PM'})
        self.assertFalse(done.issues)
        self.assertEqual((done.request.date, done.request.startTime, done.request.endTime),
            (date(2026, 10, 22), 1080, 1380))

    def test_group_date_and_constraints_survive_sequential_answers(self):
        text = ('coffee, museum, then coffee in Baltimore under $80 each, $200 total, '
                'at most 30 minutes total travel, best experience, from 6 PM to 11 PM')
        initial = self.initial(text, people=None, budget_per_person=80, budget_group=200,
            currency='USD', travel_total_minutes=30, cost='experience', preferences=['best experience'])
        self.assertEqual({q.field for q in initial.questions}, {'people', 'date'})
        second = self.answer(initial, {'people': 'three'})
        self.assertEqual([q.field for q in second.questions], ['date'])
        done = self.answer(second, {'date': 'Tomorrow'})
        req = done.request
        self.assertEqual((req.people, req.budget, req.groupBudget, req.travel, req.cost,
            req.startTime, req.endTime), (3, 80, 200, 30, 'experience', 1080, 1380))
        plans = recommend_plans(req).provisionalPlans
        self.assertTrue(plans)
        self.assertTrue(all(p.costPerPerson <= 80 and p.groupCost <= 200 and p.totalTravel <= 30 for p in plans))
        self.assertTrue(all(s.start >= 1080 and s.end <= 1380 for p in plans for s in p.stops))

    def test_manual_date_overrides_answer_and_original_without_extra_question(self):
        initial = self.initial('coffee, museum, then coffee tomorrow for 2 people in Baltimore', location=None)
        done = self.answer(initial, {'location': 'Baltimore', 'date': 'this weekend'},
            {'date': '2026-11-07', 'people': '3', 'budget': '0', 'travel': '0', 'cost': 'balanced', 'costExplicit': True})
        self.assertFalse(done.issues)
        self.assertEqual((done.request.date, done.request.people, done.request.budget,
            done.request.travel, done.request.cost), (date(2026, 11, 7), 3, 0, 0, 'balanced'))

    def test_watch_baseball_phrase_asks_for_date_without_substituting_activity(self):
        initial = self.initial('Four friends want to watch a baseball game in Baltimore.',
            activities=['watch a baseball game'], people=4)
        self.assertEqual([(q.field, q.question) for q in initial.questions],
            [('date', 'What day are you planning to go?')])
        done = self.answer(initial, {'date': '2026-11-07'})
        self.assertEqual(done.request.activities, ['baseball'])
        self.assertTrue(recommend_plans(done.request).plans)

    def test_explicit_dollar_policy_restores_currency_without_inventing_caps(self):
        result = self.initial('coffee, museum, then coffee in Baltimore for 2 people tomorrow under $80 each',
            budget_per_person=80)
        self.assertFalse(result.issues)
        self.assertEqual((result.request.budget, result.interpretation.currency), (80, 'USD'))
        for marker, currency in [('€80', None), ('$80 CAD', None), ('$80', 'CAD')]:
            blocked = self.initial('coffee, museum, then coffee in Baltimore for 2 people tomorrow under '+marker+' each',
                budget_per_person=80, currency=currency)
            self.assertIsNone(blocked.request)

    def test_public_contract_rejects_missing_null_and_invalid_dates(self):
        for fields in [{}, {'date': None}, {'date': 'Any day'}, {'date': '2026-02-30'}]:
            with self.subTest(fields=fields), self.assertRaises(ValidationError):
                PlanningRequest(activities=['coffee'], **fields)

    def test_engine_refuses_undated_finalization_before_candidate_generation(self):
        # Internal candidate-analysis contracts remain backward compatible;
        # publication through either ranking entry point requires a date.
        req = OutingRequest(activities=['coffee'])
        with patch('backend.ranking.generate_candidates') as candidates, patch('backend.ranking.evaluate_candidate') as evaluate:
            for result in [recommend_plans(req), rank_candidates(req, iter([object()]))]:
                self.assertFalse(result.plans)
                self.assertFalse(result.provisionalPlans)
                self.assertEqual(result.errors[0].code, 'missing_date')
        candidates.assert_not_called()
        evaluate.assert_not_called()
