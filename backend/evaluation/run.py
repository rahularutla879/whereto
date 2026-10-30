"""Explicit localhost-only benchmark: python -m backend.evaluation.run --output /tmp/results.json.
No model download, configuration changes, Google or hosted inference calls.
"""
import argparse,json,time,statistics,os,hashlib
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import build_opener,ProxyHandler,Request
from urllib.parse import urlsplit
from unittest.mock import patch
from backend.ai import AISettings
from backend.ai.ollama import OllamaProvider
from backend.interpretation import InterpretationInput,interpret_request,activity_category

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--model');p.add_argument('--real-validation',action='store_true');a=p.parse_args()
    settings=AISettings.from_env()
    if a.model:settings=settings.model_copy(update={'model':a.model})
    if urlsplit(settings.base_url).hostname not in ('localhost','127.0.0.1','::1'):raise SystemExit('Evaluation requires an explicitly local Ollama service.')
    opener=build_opener(ProxyHandler({}))
    def admin(path,body=None):
        req=Request(settings.base_url+path,data=json.dumps(body).encode() if body else None,headers={'Content-Type':'application/json'})
        with opener.open(req,timeout=10) as r:return json.load(r)
    installed=admin('/api/tags')['models']
    if not any(m['name']==settings.model for m in installed):raise SystemExit('Selected model is not already installed; no download is authorized.')
    metadata=admin('/api/show',{'model':settings.model});ps_before=admin('/api/ps')
    cases=json.loads(Path(__file__).with_name('cases.json').read_text());provider=OllamaProvider(settings);rows=[]
    for case in cases+cases[:3]:
        start=time.perf_counter();row={'id':case['id'],'repeat':len(rows)>=len(cases)}
        try:
            raw=provider.interpret(case['text']);row['structuredValid']=True
            row['activitiesCorrect']=[activity_category(x) for x in raw.activities]==case['activities']
            row['destinationCorrect']=raw.location==case['location'] if case['location'] is not None else (raw.location is None or case.get('clarify')=='location')
            with patch('requests.sessions.Session.send',side_effect=AssertionError('Google/network forbidden')), patch.dict(os.environ,{'VENUE_DATA_MODE':'real','WHERETO_REAL_DEV':'1','WHERETO_ENV':'development'} if a.real_validation else {}):
                r=interpret_request(InterpretationInput(text=case['text']),type('Supplied',(),{'interpret':lambda self,_:raw})(),now=datetime(2026,10,30,12,tzinfo=timezone.utc))
            fields=[q.field for q in r.questions];row['questions']=fields;row['accepted']=r.request is not None
            row['clarificationCorrect']=(case['clarify'] in fields) if 'clarify' in case else not fields
            checks={}
            if r.request:
                for key,field in [('first','firstTravel'),('between','betweenTravel')]:
                    if key in case:
                        v=getattr(r.request,field);checks[key]=v is not None and all(getattr(v,k)==n for k,n in case[key].items())
                if 'date' in case:checks['date']=str(r.request.date)==case['date']
                if 'geography' in case:checks['geography']=r.request.geography.model_dump()==case['geography']
                if 'wheelchair' in case:checks['wheelchair']=r.request.requireWheelchairAccess==case['wheelchair']
                if 'budget' in case:checks['budget']=r.request.budget==case['budget']
                checks['noInventedPeople']=r.request.people is None
            row['checks']=checks
            row['success']=row['activitiesCorrect'] and row['destinationCorrect'] and row['clarificationCorrect'] and all(checks.values()) and (r.request is not None or 'clarify' in case)
            row['issueCount']=len(r.issues)
            row['safeIssues']=r.issues
            row['extractedDestination']=raw.location
            row['modelUncertainties']=raw.uncertainties
            row['resolvedDestination']=r.request.location if r.request else None
            expected_destination='near me' if case['location'] in ('near me','around me','nearby') else case['location']
            row['resolvedDestinationCorrect']=(r.request.location==expected_destination) if r.request and case['location'] is not None else row['destinationCorrect']
            row['pipelineSuccess']=row['activitiesCorrect'] and row['resolvedDestinationCorrect'] and row['clarificationCorrect'] and all(checks.values()) and (r.request is not None or 'clarify' in case)
        except Exception as error:
            row.setdefault('structuredValid',False)
            row.update(success=False,errorType=type(error).__name__)
        row['seconds']=round(time.perf_counter()-start,3);rows.append(row)
        print(json.dumps(row),flush=True)
    ps_after=admin('/api/ps');base=[r for r in rows if not r['repeat']]
    report={'validationMode':'real' if a.real_validation else 'environment default','casesSha256':hashlib.sha256(Path(__file__).with_name('cases.json').read_bytes()).hexdigest(),'model':settings.model,'installed':next(m for m in installed if m['name']==settings.model),'ollamaVersion':admin('/api/version'),'metadata':{k:metadata.get(k) for k in ('details','parameters','model_info')},'runningBefore':ps_before,'runningAfter':ps_after,'settings':{'num_ctx':8192,'num_predict':1024,'temperature':0,'think':False,'retries':0},'firstCallSeconds':rows[0]['seconds'],'warmMedianSeconds':statistics.median(r['seconds'] for r in rows[1:]),'baseCases':len(base),'successes':sum(r['success'] for r in base),'rows':rows}
    Path(a.output).write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
