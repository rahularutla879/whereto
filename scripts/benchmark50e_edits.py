import sys,json,statistics,math,argparse,os
from pathlib import Path
from time import perf_counter
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));os.chdir(ROOT)
p=argparse.ArgumentParser(description='Model/provider-free invented-evidence structured edit benchmark');p.add_argument('--output',required=True);args=p.parse_args()
from backend.test_editable_preferences import EditablePreferencesTests
from backend.test_advanced_routing import start
h=EditablePreferencesTests();h.setUp()
try:
 s=h.session();h.h.run_session(s,startingLocation=start())
 h.run_edit(s,dwell=[dict(occurrence=0,minutes=20,relation='exact')]);before=h.counts();rows=[]
 with patch('backend.interpretation.create_provider',side_effect=AssertionError('No Qwen')),patch('requests.sessions.Session.send',side_effect=AssertionError('No Google')):
  for i in range(40):
   kind='duration' if i%2==0 else 'scope'
   edit={'dwell':[dict(occurrence=0,minutes=10 if i%4==0 else 20,relation='exact')]} if kind=='duration' else {'budgetScope':'travel' if i%4==1 else 'outing'}
   t=perf_counter();r=h.run_edit(s,**edit);ms=(perf_counter()-t)*1000
   assert r.options and len(r.options[0].stops)==2 and r.options[0].stops[1].duration.minutes==5 and r.options[0].ending=='origin' and r.options[0].totalConstraint.minutes==45
   rows.append({'kind':kind,'milliseconds':round(ms,3),'edit':edit,'scope':r.options[0].budgetScope,'elapsedLowerSeconds':r.options[0].elapsedLowerSeconds})
 assert h.counts()==before
 result={'method':'Forty sequential local session regeneration actions over invented cached directional evidence; no model or actual provider sends. Not browser end-to-end latency.','modelCalls':0,'additionalSearches':0,'additionalMatrixRequests':0,'rows':rows,'summary':{}}
 for kind in ('duration','scope'):
  vals=sorted(r['milliseconds'] for r in rows if r['kind']==kind)
  result['summary'][kind]={'n':len(vals),'medianMs':statistics.median(vals),'p90Ms':vals[math.ceil(.9*len(vals))-1],'maxMs':max(vals)}
 open(args.output,'w').write(json.dumps(result,indent=2)+'\n');print(json.dumps(result['summary']))
finally:h.doCleanups()
