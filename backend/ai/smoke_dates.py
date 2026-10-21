"""Opt-in finite Qwen extraction + deterministic resolver + real planner smoke."""
import json
from datetime import datetime
from time import perf_counter
from zoneinfo import ZoneInfo

from backend.ai import create_provider
from backend.interpretation import InterpretationInput, interpret_request
from backend.ranking import recommend_plans

SAMPLES = [
    ('today', '2026-10-21', 600, 1440),
    ('tonight', '2026-10-21', 1080, 1440),
    ('tomorrow', '2026-10-22', 600, 1440),
    ('tomorrow evening', '2026-10-22', 1080, 1440),
    ('this Friday at 6 PM', '2026-10-23', 1080, 1440),
    ('next Saturday between 6 and 9 PM', '2026-10-31', 1080, 1260),
    ('this weekend', None, None, None),
    ('next weekend', None, None, None),
    ('Saturday night', '2026-10-24', 1080, 1440),
    ('on November 7, 2026 after 6 PM before 10 PM', '2026-11-07', 1081, 1319),
    ('on 2026-11-07 from noon to 18:00', '2026-11-07', 720, 1080),
    ('tomorrow from 10 PM to 1 AM', None, None, None),
    ('tomorrow from 10 PM to midnight', '2026-10-22', 1320, 1440),
]


def main():
    provider = create_provider()
    failures = []
    reference = datetime(2026, 10, 21, 8, tzinfo=ZoneInfo('America/New_York'))
    for phrase, expected_date, start, end in SAMPLES:
        text = 'Coffee for 2 people in Baltimore ' + phrase
        before = perf_counter()
        extracted = provider.interpret(text)
        raw_dates = list(extracted.date_expressions)
        raw_times = list(extracted.time_expressions)
        # Test actual model fidelity separately from the independent source guard.
        preserved = ' '.join([*extracted.date_expressions, *extracted.time_expressions]).casefold()
        lost = [token for token in phrase.casefold().replace(',', '').split()
                if token not in {'on', 'at', 'from', 'and', 'to'} and token not in preserved]
        class FixedProvider:
            def interpret(self, text):
                return extracted
        result = interpret_request(InterpretationInput(text=text), FixedProvider(), now=reference)
        request = result.request
        actual = (request.date.isoformat(), request.startTime, request.endTime) if request else (None, None, None)
        plans = recommend_plans(request) if request else None
        count = len(plans.plans) + len(plans.provisionalPlans) if plans else 0
        passed = actual == (expected_date, start, end) and not lost and (expected_date is None or count > 0)
        if not passed:
            failures.append(phrase)
        print(json.dumps({'phrase': phrase, 'seconds': round(perf_counter()-before, 2),
                          'extracted_dates': raw_dates, 'extracted_times': raw_times,
                          'lost_tokens': lost, 'resolved': actual, 'issues': result.issues,
                          'plan_count': count, 'passed': passed}), flush=True)
    print(json.dumps({'failures': failures, 'samples': len(SAMPLES)}), flush=True)
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
