"""Opt-in actual local model/service smoke; no model downloads."""
import json
from time import perf_counter
from backend.ai import create_provider
from backend.interpretation import InterpretationInput, interpret_request
from backend.ranking import recommend_plans

SAMPLES = [
    ('Four people want bowling then dinner in Baltimore tomorrow under $60 each.', {}, ['bowling', 'food']),
    ('Two people want coffee, museum, then coffee in Baltimore tomorrow.', {}, ['coffee', 'museum', 'coffee']),
    ('Two people want lunch and dinner in Baltimore tomorrow.', {}, ['food', 'food']),
    ('Six friends in Baltimore want something competitive then cocktails.', {}, None),
    ('People want a quiet indoor activity tomorrow.', {}, None),
    ('A group wants coffee.', {}, None),
    ('Two people want coffee in Baltimore tomorrow.', {'date': '2026-11-07'}, ['coffee']),
    ('Two people want coffee in Baltimore, under $20 each, at most 15 minutes total travel, walking.', {'date': '2026-11-07'}, ['coffee']),
    ('Two people want coffee, museum, then coffee in Baltimore tomorrow, under $100 each and $200 total, with at most 30 minutes total travel and 10 minutes per leg. Best experience. From 6 PM to 11 PM.', {}, ['coffee', 'museum', 'coffee']),
    ('Two people want art in Baltimore tomorrow under $0 each, with at most 0 minutes total travel. Budget-friendly.', {}, ['art']),
]


def main():
    provider = create_provider()
    failures = []
    for text, preferences, expected in SAMPLES:
        start = perf_counter()
        result = interpret_request(InterpretationInput(text=text, preferences=preferences), provider)
        plans = recommend_plans(result.request) if result.request else None
        output = {'text': text, 'seconds': round(perf_counter() - start, 2), **result.model_dump(mode='json'),
                  'python_plan_count': len(plans.plans) + len(plans.provisionalPlans) if plans else 0}
        print(json.dumps(output), flush=True)
        if expected is not None and (result.request is None or result.request.activities != expected):
            failures.append(text)
        if result.request is not None:
            request = result.request
            if 'under $20 each' in text and (request.budget, request.travel, request.transport) != (20, 15, 'walking'):
                failures.append('lost USD budget, total travel or transport')
            if '$200 total' in text and (request.budget, request.groupBudget, request.travel, request.maxLegTravel,
                    request.cost, request.startTime, request.endTime) != (100, 200, 30, 10, 'experience', 1080, 1380):
                failures.append('lost repeated-outing hard constraints')
            if '$0 each' in text and (request.budget, request.travel, request.cost) != (0, 0, 'budget'):
                failures.append('lost explicit zero constraints')
        if expected is None and result.request is not None:
            failures.append(text)
        if 'tomorrow' in text and 'tomorrow' not in result.interpretation.date_expressions:
            failures.append('lost tomorrow')
        if text == 'A group wants coffee.' and (result.interpretation.people is not None or result.interpretation.location is not None):
            failures.append('invented missing fields')
    print(json.dumps({'failures': failures, 'note': 'Finite semantic smoke only. Dates now resolve deterministically; see smoke_dates for focused Task 32 coverage.'}), flush=True)
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
