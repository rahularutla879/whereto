"""Opt-in installed-Qwen semantic accuracy/latency check. No Google or SQL.

python -m backend.ai.smoke_journey [--case 1 --case 4] [--repeat 2]
Only fixed public example texts are printed; no user requests/configuration.
"""
import argparse
import json
from datetime import datetime, timezone
from statistics import median
from time import perf_counter
from unittest.mock import patch
from backend.ai import create_provider
from backend.interpretation import InterpretationInput, interpret_request, activity_category
from backend.journey import LIMITATION
from backend.journey_fixtures import CASES
from backend.performance import record_ai


def semantic_errors(ai, result, expected, outcome):
    errors=[]
    j=result.interpretation.journey
    if j is None: return ['missing journey']
    target=expected['journey']
    if [activity_category(s.source) for s in j.stops] != [activity_category(s['source']) for s in target['stops']]: errors.append('stop identities/count')
    if [s.kind for s in j.stops] != [s.get('kind','activity') for s in target['stops']]: errors.append('destination kind')
    if [s.requirement for s in j.stops] != [s.get('requirement','required') for s in target['stops']]: errors.append('required/optional')
    contradictory = target['clarification'].casefold().count('before')>1
    if contradictory:
        # A conflict can be represented by flagged edges or the complete source
        # conflict clause. Neither selects an executable order.
        if not (j.order_conflict or j.clarification): errors.append('order conflict')
    elif j.ordering!=target['ordering'] or {(e.before,e.after) for e in j.order}!={(e['before'],e['after']) for e in target['order']}: errors.append('ordering')
    if (j.endpoint.kind if j.endpoint else None)!=(target['endpoint']['kind'] if target['endpoint'] else None): errors.append('endpoint')
    for got,want in zip(j.stops,target['stops']):
        duration=want.get('duration')
        if ((got.duration.minutes,got.duration.relation) if got.duration else None)!=((duration['minutes'],duration.get('relation','exact')) if duration else None): errors.append('stop duration')
    d=target['total_duration']
    if ((j.total_duration.minutes,j.total_duration.relation) if j.total_duration else None)!=((d['minutes'],d.get('relation','exact')) if d else None):errors.append('whole duration')
    if bool(j.deadline)!=bool(target['deadline']):errors.append('deadline')
    if j.deadline and result.interpretation.journey.deadline.minute!=1080:errors.append('deadline clock')
    if bool(j.shared_place)!=bool(target.get('shared_place')):errors.append('shared place')
    if expected.get('transport') and result.interpretation.transport!=expected['transport']:errors.append('travel mode')
    if outcome=='simple' and result.request is None:errors.append('simple planning regression')
    if outcome!='simple' and result.request is not None:errors.append('unsafe planning request')
    if outcome=='advanced' and result.unsupported!=[LIMITATION]:errors.append('limitation response')
    if outcome in ('clarify','missing') and not result.issues:errors.append('missing clarification')
    return errors


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',action='append',type=int,choices=range(1,26))
    parser.add_argument('--repeat',type=int,default=1,choices=range(1,4))
    args=parser.parse_args()
    provider=create_provider(); rows=[]; metadata={}
    def measured(result,wall,validation):
        metadata.clear()
        metadata.update({k:result.get(k) for k in ('prompt_eval_count','eval_count','load_duration','prompt_eval_duration','eval_duration')})
        record_ai(result,wall,validation)
    for repetition in range(args.repeat):
        for number in args.case or range(1,26):
            text,expected,outcome=CASES[number-1]
            started=perf_counter();row={'case':number,'run':repetition+1}
            try:
                with patch('requests.sessions.Session.send',side_effect=AssertionError('No live providers')),patch('backend.performance.record_ai',side_effect=measured):
                    ai=provider.interpret(text)
                class Fixed:
                    def interpret(self,text):return ai
                result=interpret_request(InterpretationInput(text=text),Fixed(),now=datetime(2026,11,2,15,tzinfo=timezone.utc))
                row['errors']=semantic_errors(ai,result,expected,outcome)
                # Public fixed test-data only, for reproducible semantic review.
                row['journey']=result.interpretation.journey.model_dump(mode='json',exclude_defaults=True) if result.interpretation.journey else None
                row['issues']=result.issues
                row['transport']=result.interpretation.transport
                row['timing']=dict(metadata)
            except Exception as error:
                row['errors']=[type(error).__name__]
                if error.__cause__:
                    row['error_reason']=str(error.__cause__)[:1500]
            row['seconds']=round(perf_counter()-started,3);rows.append(row)
            print(json.dumps(row),flush=True)
    print(json.dumps({'passed':sum(not r['errors'] for r in rows),'total':len(rows),'median_seconds':round(median(r['seconds'] for r in rows),3)}),flush=True)
    raise SystemExit(any(r['errors'] for r in rows))

if __name__=='__main__':main()
