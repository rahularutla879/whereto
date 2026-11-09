"""Current-runtime behavioral reconstruction only. No historical code execution."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from backend import journey
from backend.journey_fixtures import reply
from backend.ai import Interpretation

ROOT=Path(__file__).resolve().parents[1]
BASELINE_ID='52b-behavior-reconstruction-duration-b2-v1'


def sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def duration_cases():
    cases=[]
    for relation,word in [('exact','Spend'),('minimum','Spend at least'),('maximum','Spend at most'),
                          ('under','Spend less than'),('approximate','Spend about')]:
        cases.append({'id':relation,'raw':f'{word} 20 minutes at the museum.', 'data':reply(['museum'])})
    for i,raw in enumerate(['I have 2 hours for coffee.', 'Return within 45 minutes.',
                           'Get groceries and return home within 45 minutes.',
                           'Spend 20 minutes at coffee and 10 minutes at the museum.',
                           'Spend 20 minutes at coffee and coffee.',
                           'Coffee twice for 20 minutes.', 'Spend 20 minutes and 10 minutes at the museum.',
                           'Spend -2 minutes at the museum.', 'Spend 10081 minutes at the museum.',
                           'Spend 1.1 minutes at the museum.', 'Spend half an hour at the museum.',
                           'Spend 20 minutes driving at the museum.']):
        phrases=['groceries'] if 'groceries' in raw else ['coffee','museum'] if 'coffee and 10' in raw else ['coffee','coffee'] if 'coffee and coffee' in raw or 'twice' in raw else ['coffee'] if 'coffee' in raw else ['museum']
        endpoint={'kind':'home','source':'return home'} if 'return home' in raw else None
        cases.append({'id':f'contrast-{i}','raw':raw,'data':reply(phrases,endpoint=endpoint)})
    cases += [
        {'id':'existing-dwell','raw':'Spend 20 minutes at the museum.',
         'data':reply(['museum'],durations={0:{'minutes':10,'source':'10 minutes'}})},
        {'id':'existing-total','raw':'I have 2 hours for coffee.',
         'data':reply(['coffee'],total={'minutes':30,'source':'30 minutes'})},
        {'id':'masked-travel','raw':'Travel within 20 minutes to the museum.',
         'guarded':' '*len('Travel within 20 minutes')+' to the museum.','data':reply(['museum'])},
        {'id':'long-clause','raw':'Spend 20 minutes at the museum '+('very '*130), 'data':reply(['museum'])},
    ]
    for dependency in ['duration_value','duration_relation','unresolved_return_clause','Duration']:
        cases.append({'id':'raising-'+dependency,'raw':'Spend 20 minutes at the museum.',
                      'data':reply(['museum']),'raiseDependency':dependency})
    return cases


def duration_trace(case):
    model=Interpretation.model_validate(deepcopy(case['data'])).journey
    before=model.model_dump(mode='json');calls=[]
    target=case.get('raiseDependency')
    def observe(name,fn):
        def call(*a,**kw):
            calls.append(name)
            if name==target:raise ValueError('Synthetic dependency failure: '+name)
            return fn(*a,**kw)
        return call
    from contextlib import ExitStack
    error=None
    with ExitStack() as stack:
        for name in ['duration_value','duration_relation','unresolved_return_clause','Duration']:
            stack.enter_context(patch.object(journey,name,observe(name,getattr(journey,name))))
        try:result=journey.normalize_explicit_durations(case['raw'],case.get('guarded',case['raw']),model)
        except Exception as exc:error={'type':type(exc).__name__,'message':str(exc)};result=None
    return {'id':case['id'],'before':before,'after':model.model_dump(mode='json'),
            'return':result,'error':error,'dependencyCallOrder':calls}
