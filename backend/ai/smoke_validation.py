"""Opt-in Task 34 local-model acceptance + deterministic validation timing.

Run: backend/.venv/bin/python -m backend.ai.smoke_validation
Never part of the automated suite; does not download or change a model.
"""
import json
from statistics import median
from time import perf_counter
from unittest.mock import Mock

from backend.ai import create_provider
from backend.interpretation import InterpretationInput, interpret_request
from backend.ranking import recommend_plans

CASES = [
    ('A', 'Four friends want bowling then dinner in Baltimore on November 7, 2026, maximum $60 each and 15 minutes between stops.', {}, ['bowling', 'food'], 60),
    ('B', 'Two people want coffee, a museum, and coffee again in Baltimore on November 7, 2026.', {}, ['coffee', 'museum', 'coffee'], None),
    ('C', 'Four friends want bowling and dinner in Baltimore, under $70 each.', {}, ['bowling', 'food'], 70),
    ('D', 'Four friends want bowling and dinner in Baltimore on November 7, 2026, maximum $70 each.', {'budget': '50'}, ['bowling', 'food'], 50),
    ('E', 'Four people want dinner in Baltimore on November 7, 2026, maximum $40 per person but minimum $80 per person.', {}, ['food'], None),
]


def main():
    provider = create_provider()
    report = []
    for name, text, manual, activities, budget in CASES:
        start = perf_counter()
        extraction = provider.interpret(text)
        ai_ms = (perf_counter() - start) * 1000
        fake = Mock(); fake.interpret.return_value = extraction
        value = InterpretationInput(text=text, preferences=manual)
        timings = []
        for _ in range(100):
            start = perf_counter()
            result = interpret_request(value, fake)
            timings.append((perf_counter() - start) * 1000)
        record = dict(case=name, ai_ms=round(ai_ms, 3), validation_median_ms=round(median(timings), 3),
                      issues=result.issues, questions=[q.field for q in result.questions])
        if name == 'E':
            assert result.request is None and any('Minimum spending' in i for i in result.issues)
        else:
            if name == 'C':
                assert result.request is None and [q.field for q in result.questions] == ['date']
                start = perf_counter()
                result = interpret_request(InterpretationInput(text=text, pending=result.pending,
                    preferences=manual, answers={'date': 'November 7, 2026'}), fake)
                record['followup_ms'] = round((perf_counter() - start) * 1000, 3)
                assert fake.interpret.call_count == 100
            assert not result.issues, result.issues
            request = result.request
            assert request.activities == activities and request.budget == budget
            assert request.date.isoformat() == '2026-11-07' and request.location == 'Baltimore'
            assert request.people == (2 if name == 'B' else 4)
            if name == 'A':
                assert request.maxLegTravel == 15
            plans = recommend_plans(request)
            options = plans.plans + plans.provisionalPlans
            assert options or plans.errors
            for plan in options:
                assert [v.activity for v in plan.candidate.venues] == activities
                assert budget is None or plan.costPerPerson <= budget
                if name == 'A':
                    assert all(leg.minutes <= 15 for leg in plan.legs)
            record.update(request=request.model_dump(mode='json'), plans=len(options),
                          planner_errors=[e.message for e in plans.errors])
        report.append(record)
        print(json.dumps(record), flush=True)
    print(json.dumps({'passed': len(report)}))


if __name__ == '__main__':
    main()
