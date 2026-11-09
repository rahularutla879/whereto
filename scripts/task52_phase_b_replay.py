"""Offline Phase B characterization. Reads synthetic records and paid journal RO.

No CLI writer, dispatch, scoring replacement, or runtime import of this module.
"""
from contextlib import ExitStack
from datetime import datetime, timezone
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from unittest.mock import Mock, patch

from backend.ai import Interpretation
from backend.interpretation import InterpretationInput, interpret_request
from backend import journey, interpretation
from backend.journey_fixtures import CASES, reply
from backend.test_real_planning import ENV
from backend.testing_clock import calendar_clock
from backend.validation_phases import validate_legacy

ROOT=Path(__file__).resolve().parents[1]
NOW=datetime(2026,11,8,12,tzinfo=timezone.utc)


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def scenarios():
    rows=[{'id':f'journey-{i:02}', 'text':text,'ai':data} for i,(text,data,_) in enumerate(CASES,1)]
    extras=[
        ('ordinary','Dinner and drinks in Jersey City tomorrow.',None,{}),
        ('manual','Dinner and drinks in Jersey City tomorrow.',None,
         {'preferences':{'location':'New York','date':'2026-11-10'}}),
        ('repeated','Coffee, museum, then coffee in Jersey City tomorrow.',
         reply(['Coffee','museum','coffee'],location='Jersey City',order=[(1,2,'museum, then coffee')]),{}),
        ('home-stop','Museum, then go home tomorrow in Jersey City.',
         reply(['Museum','go home'],location='Jersey City',order=[(0,1,'Museum, then go home')]),{}),
        ('punctuation','Coffee shop → museum in Jersey City tomorrow.',
         reply(['Coffee shop','museum'],location='Jersey City',order=[(0,1,'Coffee shop -> museum')]),{}),
        ('duration','Spend 20 minutes at the museum in Jersey City tomorrow.',
         reply(['museum'],location='Jersey City'),{}),
        ('repeated-count','Coffee twice in Jersey City tomorrow.',reply(['Coffee','Coffee'],location='Jersey City'),{}),
        ('omitted','Coffee and museum in Jersey City tomorrow.',reply(['Coffee'],location='Jersey City'),{}),
        ('duplicate','Coffee in Jersey City tomorrow.',reply(['Coffee','Coffee'],location='Jersey City'),{}),
        ('named','Visit SUNY College of Optometry and then coffee.',
         reply(['SUNY College of Optometry','coffee'],kinds={0:'named_place'},order=[(0,1,'SUNY College of Optometry and then coffee')]),{}),
        ('finish','Start with groceries and finish at the pharmacy.',reply(['groceries','pharmacy'],order=[(0,1,'Start with groceries and finish at the pharmacy')]),{}),
        ('dst','Dinner in Jersey City on November 1, 2026 at 1:30 AM.',reply(['Dinner'],location='Jersey City'),{}),
        ('kolkata','Dinner in Hyderabad tomorrow.',reply(['Dinner'],location='Hyderabad'),{'calendarTimezone':'Asia/Kolkata'}),
        ('invalid-fields','Dinner in Jersey City tomorrow.',{'unexpected':'invalid'},{}),
    ]
    ordinary=dict(CASES[0][1]);ordinary.pop('journey')
    for name,text,ai,extra in extras:rows.append({'id':name,'text':text,'ai':ordinary if ai is None else ai,**extra})
    actual=json.loads((ROOT/'backend/evaluation/results-task50e-model-investigation.json').read_text())
    reviews=json.loads((ROOT/'docs/task52-ordering-qwen-review-v2.json').read_text())['rows']
    for i,review in enumerate(reviews):
        rows.append({'id':f'qwen-{i}', 'text':review['source'],'ai':actual[review['cohort']]['rows'][review['row']]['raw']})
    from scripts import cloud_model52 as e
    cases=e.corpus()['cases']
    with sqlite3.connect(f'file:{e.STATE}/journal.sqlite?mode=ro',uri=True) as db:
        for i,row in enumerate(db.execute("select * from attempts where provider='openai' order by rowid")):
            content,_,_=e.Adapter('openai',None).decode(json.loads(row[5])['response'])
            rows.append({'id':f'openai-{i}', 'text':next(c['text'] for c in cases if c['id']==row[1]),
                         'ai':json.loads(content)})
    # Pending is an effective legacy snapshot, not another raw-model event.
    p=Mock(interpret=Mock(return_value=Interpretation.model_validate(ordinary)))
    saved=interpret_request(InterpretationInput(text=CASES[0][0]),p,now=NOW).pending
    rows.append({'id':'pending','text':CASES[0][0],'ai':ordinary,'pending':saved.model_dump(mode='json')})
    rows.append({'id':'pending-answer','text':CASES[0][0],'ai':ordinary,'pending':saved.model_dump(mode='json'),
                 'answers':{'activities':'Coffee and museum'}})
    return rows


def run(row, *, direct=False):
    events=[];provider=Mock()
    def generate(text):
        events.append({'helper':'provider','inputHash':digest(text)})
        return Interpretation.model_validate(row['ai'])
    provider.interpret.side_effect=generate
    value=InterpretationInput.model_validate({k:v for k,v in row.items() if k not in ('id','ai')})
    def wrapper(name,fn,model_index):
        @wraps(fn)
        def call(*args,**kwargs):
            model=args[model_index];before=model.model_dump(mode='json')
            result=fn(*args,**kwargs)
            events.append({'helper':name,'before':digest(before),'after':digest(model.model_dump(mode='json'))})
            return result
        return call
    with ExitStack() as stack:
        stack.enter_context(patch.dict(os.environ,ENV,clear=True))
        stack.enter_context(calendar_clock(NOW))
        stack.enter_context(patch('requests.sessions.Session.send',side_effect=AssertionError('Offline only')))
        for module,name,index in [(journey,'normalize_extracted_references',1),
                                  (journey,'normalize_explicit_durations',2),
                                  (interpretation,'normalize_verbatim_travel',1)]:
            stack.enter_context(patch.object(module,name,wrapper(name,getattr(module,name),index)))
        try:
            result=(interpret_request(value,provider,now=NOW) if direct else validate_legacy(value,provider,now=NOW).result)
            full=result.model_dump(mode='json')
            trace={'id':row['id'],'dtoSHA256':digest(full),'events':events,'providerCalls':provider.interpret.call_count,
                   'status':result.executionStatus,'error':None}
        except Exception as exc:
            full={'errorType':type(exc).__name__,'message':str(exc)}
            trace={'id':row['id'],'dtoSHA256':digest(full),'events':events,'providerCalls':provider.interpret.call_count,
                   'status':None,'error':type(exc).__name__}
    return trace,full


def characterize():
    rows=scenarios()
    return {'version':'52b-phase-b-legacy-characterization-v1','referenceTime':NOW.isoformat(),
            'baselineCommit':'87145d597a0be395942745deb1a3f14d5ea5cdd0',
            'rows':[run(row)[0] for row in rows]}
