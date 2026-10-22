"""Opt-in Task 36 acceptance matrix: local Qwen, validator and fictional planner.

Run from the repository: backend/.venv/bin/python -m backend.ai.smoke_reliability
Add --cold to unload only the configured model before each timing pair.
Ordinary unit tests never require Ollama. No models are downloaded.
"""
import argparse
import json
from time import perf_counter
from unittest.mock import Mock, patch
from urllib.request import Request, urlopen

from backend.ai import AISettings, create_provider
from backend.interpretation import InterpretationInput, interpret_request
from backend.ranking import recommend_plans
import backend.ranking as ranking

CASES = [
    ('one-stop', 'Coffee for four in Baltimore on November 7, 2026.', ['coffee']),
    ('missing-essentials', 'Coffee.', None),
    ('four-stops', 'Two people want coffee, museum, coffee, then dinner in Baltimore on November 7, 2026.', ['coffee', 'museum', 'coffee', 'food']),
    ('synonyms', 'Cinema then cocktails for two in Baltimore on November 7, 2026.', ['movie', 'drinks']),
    ('constraints', 'Four friends want bowling then dinner in Baltimore on November 7, 2026, maximum $60 each and 15 minutes between stops.', ['bowling', 'food']),
    ('independent', 'Two people want coffee, museum, then coffee in Baltimore tomorrow, under $100 each and $200 total, with at most 30 minutes total travel and 10 minutes per leg. Best experience. From 6 PM to 11 PM.', ['coffee', 'museum', 'coffee']),
    ('zero', 'Two people want art in Baltimore tomorrow under $0 each, with at most 0 minutes total travel. Budget-friendly.', ['art']),
    ('manual', 'Coffee for four in Baltimore on November 7, 2026, maximum $70 each.', ['coffee']),
    ('today', 'Coffee for two in Baltimore today.', ['coffee']),
    ('this-weekday', 'Coffee for two in Baltimore this Saturday.', ['coffee']),
    ('next-weekday', 'Coffee for two in Baltimore next Friday.', ['coffee']),
    ('ambiguous-day', 'Coffee for two in Baltimore this weekend.', None),
    ('dst-fold', 'Coffee for two in Baltimore on November 1, 2026 from 1 AM to 2 AM.', None),
    ('original-conflict', 'Dinner for four in Baltimore on November 7, 2026, maximum $30 but minimum $80 per person.', None),
    ('non-usd', 'Coffee for two in Baltimore on November 7, 2026 under EUR 30 each.', None),
    ('ambiguous-money', 'Coffee for two in Baltimore on November 7, 2026 under $30.', None),
    ('venue-requirement', 'Dinner for two in Baltimore on November 7, 2026. We need a wheelchair accessible venue.', None),
    ('unsupported', 'Skydiving for two in Baltimore on November 7, 2026.', None),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cold', action='store_true')
    args = parser.parse_args()
    settings = AISettings.from_env()
    provider = create_provider(settings)
    failed = 0
    total = 0
    for name, text, expected in CASES:
        pair = name in {'one-stop', 'missing-essentials'}
        if pair and args.cold:
            req = Request(settings.base_url.rstrip('/') + '/api/generate',
                data=json.dumps({'model': settings.model, 'keep_alive': 0}).encode(),
                headers={'Content-Type': 'application/json'})
            with urlopen(req, timeout=30) as response:
                json.load(response)
        for run in range(2 if pair else 1):
            total += 1
            record = {'case': name, 'residency': ('cold' if run == 0 and args.cold else 'warm') if pair else 'warm'}
            manual = {'budget': '0', 'people': '3', 'date': '2026-11-14', 'cost': 'balanced', 'costExplicit': True} if name == 'manual' else {}
            try:
                start = perf_counter()
                extraction = provider.interpret(text)
                record['model_s'] = round(perf_counter() - start, 3)
                fake = Mock(); fake.interpret.return_value = extraction
                start = perf_counter()
                result = interpret_request(InterpretationInput(text=text, preferences=manual), fake)
                record['validation_ms'] = round((perf_counter() - start) * 1000, 3)
                assert bool(result.request) == bool(expected), result.issues
                if expected:
                    request = result.request
                    assert request.activities == expected, request.activities
                    if name == 'constraints':
                        assert (request.people, request.budget, request.maxLegTravel) == (4, 60, 15)
                    if name == 'independent':
                        assert (request.budget, request.groupBudget, request.travel, request.maxLegTravel, request.cost, request.startTime, request.endTime) == (100, 200, 30, 10, 'experience', 1080, 1380)
                    if name == 'zero':
                        assert (request.budget, request.travel, request.cost) == (0, 0, 'budget')
                    if name == 'manual':
                        assert (request.budget, request.people, str(request.date), request.cost) == (0, 3, '2026-11-14', 'balanced')
                    if name in {'one-stop', 'four-stops', 'synonyms', 'today', 'this-weekday', 'next-weekday'}:
                        assert request.people == (4 if name == 'one-stop' else 2)
                    with patch('backend.ranking.generate_candidates', wraps=ranking.generate_candidates) as candidates:
                        start = perf_counter(); plans = recommend_plans(request)
                        record['planner_ms'] = round((perf_counter() - start) * 1000, 3)
                        candidates.assert_called_once()
                    options = plans.plans + plans.provisionalPlans
                    assert options or plans.errors
                    for plan in options:
                        assert [v.activity for v in plan.candidate.venues] == expected
                        assert request.budget is None or plan.costPerPerson <= request.budget
                        assert request.travel is None or plan.totalTravel <= request.travel
                    record['plans'] = len(options)
                    record['planner_errors'] = [error.message for error in plans.errors]
                else:
                    assert result.issues
                    if name == 'original-conflict':
                        assert result.interpretation.people == 4
                        assert not result.questions
                        assert len(result.issues) == 1 and 'Minimum spending' in result.issues[0]
                    if name == 'missing-essentials':
                        assert {q.field for q in result.questions} == {'date', 'people', 'location'}
                        # Invalid answer, correction and structured edit must never call AI.
                        fake.interpret.reset_mock()
                        start = perf_counter()
                        bad = interpret_request(InterpretationInput(text=text, pending=result.pending,
                            answers={'date': '2026-02-30', 'people': 'two', 'location': 'Baltimore'}), fake)
                        assert bad.request is None and bad.pending
                        fixed = interpret_request(InterpretationInput(text=text, pending=bad.pending,
                            answers={'date': 'November 7, 2026'}), fake)
                        assert fixed.request and fixed.request.people == 2
                        record['followup_pair_ms'] = round((perf_counter() - start) * 1000, 3)
                        start = perf_counter()
                        edited = interpret_request(InterpretationInput(text=text, pending=fixed.pending,
                            preferences={'budget': '40'}, answers={'activities': 'museum, coffee, coffee'}), fake)
                        assert edited.request.activities == ['museum', 'coffee', 'coffee']
                        recommend_plans(edited.request)
                        record['regeneration_ms'] = round((perf_counter() - start) * 1000, 3)
                        fake.interpret.assert_not_called()
                record.update(passed=True, issues=result.issues, questions=[q.field for q in result.questions])
            except Exception as error:
                failed += 1
                record.update(passed=False, failure=str(error))
            print(json.dumps(record), flush=True)
    print(json.dumps({'runs': total, 'passed': total - failed, 'failed': failed}), flush=True)
    return bool(failed)


if __name__ == '__main__':
    raise SystemExit(main())
