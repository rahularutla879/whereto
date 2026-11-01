"""Offline provider timing harness. --local-ai uses only installed local Qwen.
No Google authentication or sends; no SQL/owner ledger. Output contains timings
and counts, never requests, coordinates, provider content or capabilities.
"""
import argparse
from contextlib import ExitStack
from datetime import datetime,timezone
import json
import os
from time import perf_counter
from unittest.mock import patch

def run(local_ai=False):
 from backend.test_real_planning import ENV
 from backend.interpretation import InterpretationInput,interpret_request
 from backend.ai import Interpretation
 from backend.real_planning import real_plans,PlannerInput
 from backend.provider_budget import ProviderBudget
 from backend.refinement_fixtures import search_fixture
 from backend.real_fixtures import matrix_fixture
 from backend.ranking import recommend_plans
 from backend.performance import snapshot
 rows=[]
 for activities,text in [(['food'],'Dinner in Jersey City'),(['food','coffee'],'Dinner then coffee tomorrow in Jersey City')]:
  for iteration in range(3):
   timings={};counts={'search':0,'matrixElements':0}
   def timed(name,operation):
    def wrapped(*args,**kwargs):
     start=perf_counter()
     try:return operation(*args,**kwargs)
     finally:timings[name]=timings.get(name,0)+(perf_counter()-start)*1000
    return wrapped
   def search(body,**kwargs):counts['search']+=1;return search_fixture(body,**kwargs)
   def matrix(body):counts['matrixElements']+=len(body['origins'])*len(body['destinations']);return matrix_fixture(body)
   with ExitStack() as stack:
    stack.enter_context(patch.dict(os.environ,ENV|{'WHERETO_RATINGS_DEV':'1'},clear=True))
    stack.enter_context(patch('requests.Session.send',side_effect=AssertionError('External HTTP forbidden')))
    stack.enter_context(patch('backend.places_transport.text_search',timed('placesFixtureMs',search)))
    stack.enter_context(patch('backend.routes_transport.compute_matrix',timed('routesFixtureMs',matrix)))
    import backend.real_planning as planner
    for name in ('score_candidates','evaluate_candidate','_select'):
     stack.enter_context(patch.object(planner,name,timed(name+'Ms',getattr(planner,name))))
    import backend.routing_shortlist as shortlists
    stack.enter_context(patch.object(shortlists,'shortlist',timed('shortlistMs',shortlists.shortlist)))
    from backend.places import PlacesDiscovery
    stack.enter_context(patch.object(PlacesDiscovery,'discover_many',timed('discoveryAndNormalizationMs',PlacesDiscovery.discover_many)))
    started=perf_counter();parse_started=started
    value=InterpretationInput(text=text,preferences={'date':'2026-11-07'})
    timings['inputValidationMs']=(perf_counter()-parse_started)*1000
    if local_ai:interpreted=interpret_request(value,now=datetime(2026,11,1,tzinfo=timezone.utc))
    else:
     from unittest.mock import Mock
     provider=Mock();provider.interpret.return_value=Interpretation(activities=['Dinner'] if len(activities)==1 else ['Dinner','coffee'],budget_per_person=None,date=None,location='Jersey City',preferences=[])
     interpreted=interpret_request(value,provider,now=datetime(2026,11,1,tzinfo=timezone.utc))
    timings['interpretationAndCalendarMs']=(perf_counter()-parse_started)*1000
    if not interpreted.request:raise RuntimeError('Benchmark interpretation needs clarification')
    # Original public semantics, with deliberate fixture-only Surprise Me start.
    req=PlannerInput(**{**interpreted.request.model_dump(),'planningMode':'surprise','activities':activities,'locationFirst':False})
    plan_started=perf_counter();result=real_plans(req,ProviderBudget());timings['planningMs']=(perf_counter()-plan_started)*1000
    serialize_started=perf_counter();result.model_dump_json();timings['serializationMs']=(perf_counter()-serialize_started)*1000
    timings['totalMs']=(perf_counter()-started)*1000
    mock_started=perf_counter();recommend_plans(req);timings['fictionalPlannerMs']=(perf_counter()-mock_started)*1000
    rows.append({'activityCount':len(activities),'iteration':iteration+1,'localAi':local_ai,'options':len(result.provisionalPlans),'timings':{k:round(v,3) for k,v in timings.items()},'ai':snapshot() if local_ai else {},'simulatedRequests':counts,'actualGoogleRequests':0,'actualGoogleCostUsd':0,'simulatedGrossUsd':round(counts['search']*.035+counts['matrixElements']*.005,3)})
    print(json.dumps(rows[-1]),flush=True)
 return rows

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--local-ai',action='store_true');args=parser.parse_args();run(args.local_ai)
