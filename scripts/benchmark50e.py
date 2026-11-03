import argparse,json,sys,os,hashlib,io,statistics,math,subprocess,types
from pathlib import Path
from time import perf_counter
from datetime import datetime,timezone
from unittest.mock import patch
from urllib.request import build_opener,ProxyHandler,Request
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
os.chdir(ROOT)
from backend.ai import AISettings
from backend.ai.ollama import OllamaProvider
from backend.interpretation import InterpretationInput,interpret_request
CASES=[
('A','go to suny college of optometry first and then head out for coffee and be back within 3 hours'),
('B','go to suny college of optometry first and then head out for coffee now'),
('C','Go to SUNY College of Optometry, then get coffee tomorrow.'),
('D','Buy groceries, stop at an ATM for 5 minutes, and return to where I started within 45 minutes tomorrow.'),
('E','dinner and bowling tomorrow in jersey city'),
('F','Go grocery shopping tomorrow and return to where I started.'),
('repeat','Coffee, museum, then coffee in New York tomorrow.'),
('mall','Visit Zara and Nike in the same mall tomorrow.'),
('flex','Visit the bank and grocery store, whichever is closer first, tomorrow in New York.'),
('ambiguous','Go to the college and finish at Penn Station tomorrow.')]
p=argparse.ArgumentParser(description="Controlled installed-local-Qwen 50E benchmark; Google blocked, no downloads.");p.add_argument('--output',required=True);p.add_argument('--repeat',type=int,default=2);p.add_argument('--baseline-ref',choices=['227833e']);a=p.parse_args()
if not 2 <= a.repeat <= 5:p.error('--repeat must be between 2 and 5')
settings=AISettings.from_env();assert settings.base_url in ('http://127.0.0.1:11434','http://localhost:11434')
opener=build_opener(ProxyHandler({}))
def admin(path,body=None):
 req=Request(settings.base_url+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
 with opener.open(req,timeout=30) as r:return json.load(r)
installed=admin('/api/tags')['models'];assert any(m['name']==settings.model for m in installed),'No model download allowed'
report={'adapterSha256':hashlib.sha256(Path('backend/ai/ollama.py').read_bytes()).hexdigest(),'model':settings.model,'installed':[{'name':m['name'],'size':m.get('size'),'digest':m.get('digest')} for m in installed],'started':datetime.now(timezone.utc).isoformat(),'memoryMeasurement':'Ollama reported allocation, not peak process or system memory','sourceHashes':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in map(Path,['backend/ai/ollama.py','backend/ai/__init__.py','backend/journey.py','backend/interpretation.py','backend/date_resolution.py'])},'rows':[]}
adapter=OllamaProvider
if a.baseline_ref:
 baseline_source=subprocess.check_output(['git','show',a.baseline_ref+':backend/ai/ollama.py'],text=True)
 baseline=types.ModuleType('verified_baseline');exec(compile(baseline_source,'<verified repository baseline>','exec'),baseline.__dict__)
 adapter=baseline.OllamaProvider;report['baselineRef']=a.baseline_ref;report['adapterSha256']=hashlib.sha256(baseline_source.encode()).hexdigest()
provider=adapter(settings);original=provider._opener;observed={}
class Meter:
 def open(self,req,**kwargs):
  t=perf_counter()
  with original.open(req,**kwargs) as r:data=r.read()
  observed['httpSeconds']=perf_counter()-t;observed['response']=json.loads(data)
  observed['requestBytes']=len(req.data);observed['options']=json.loads(req.data)['options'];return io.BytesIO(data)
provider._opener=Meter()
# Owner-requested controlled cold sample: only the installed selected model.
admin('/api/generate',{'model':settings.model,'keep_alive':0})
report['coldInventory']=admin('/api/ps')
if any(m['name']==settings.model for m in report['coldInventory']['models']):
 raise RuntimeError('Selected model is still busy/loaded; no cold sample taken. Wait for the current local request to finish before deliberately rerunning.')
sequence=[('cold','E',dict(CASES)['E'])]+[('warm',key,text) for _ in range(a.repeat) for key,text in CASES]
for state,key,text in sequence:
 observed.clear();row={'state':state,'case':key,'text':text};t=perf_counter()
 try:
  with patch('requests.sessions.Session.send',side_effect=AssertionError('No live Google')):
   raw=provider.interpret(text)
   row['raw']=raw.model_dump(mode='json')
   class Fixed:
    def interpret(self,text):return raw
   with patch.dict(os.environ,VENUE_DATA_MODE='real',WHERETO_REAL_DEV='1',WHERETO_ENV='development',WHERETO_ADVANCED_DEV='1',WHERETO_STOP_RESOLUTION_DEV='1'):
    result=interpret_request(InterpretationInput(text=text),Fixed(),now=datetime.now(timezone.utc))
   row['pipeline']={'executionStatus':result.executionStatus,'issues':result.issues,'unsupported':result.unsupported,'journey':result.interpretation.journey.model_dump(mode='json') if result.interpretation.journey else None,'context':result.context.model_dump(mode='json') if result.context else None,'hasRequest':result.request is not None,'questions':[q.model_dump(mode='json') for q in result.questions]}
 except Exception as e:row['error']={'type':type(e).__name__,'message':str(e),'cause':str(e.__cause__) if e.__cause__ else None}
 row['wallSeconds']=round(perf_counter()-t,3)
 r=observed.get('response',{});row['metrics']={k:r.get(k) for k in ('prompt_eval_count','eval_count','load_duration','prompt_eval_duration','eval_duration','total_duration','done_reason')}
 row['options']=observed.get('options');row['rawContent']=r.get('message',{}).get('content');row['requestBytes']=observed.get('requestBytes');row['httpSeconds']=observed.get('httpSeconds')
 row['allocation']=admin('/api/ps');report['rows'].append(row)
 warm=sorted(r['wallSeconds'] for r in report['rows'] if r['state']=='warm')
 report['summary']={'warmMedianSeconds':statistics.median(warm) if warm else None,'warmP90Seconds':warm[math.ceil(.9*len(warm))-1] if warm else None,'warmWorstSeconds':max(warm) if warm else None,'coldSeconds':report['rows'][0]['wallSeconds']}
 Path(a.output).write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({k:row.get(k) for k in ['state','case','wallSeconds','error']}),flush=True)
