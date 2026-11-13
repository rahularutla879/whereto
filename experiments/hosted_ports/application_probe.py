"""External synthetic frontend proof driver; never shipped in service images.

Only aggregate timings/counts are returned. No token, source graph or credential
is printed. This probes actual HTTPS/FastAPI/native operations, not a browser.
"""
import json,time,secrets,ssl,http.client
from datetime import datetime,timedelta
from pathlib import Path
import jwt
from experiments.hosted_identity.auth import signed,digest
from experiments.hosted_startup.public_auth import binding,REQUEST,FORWARD
from experiments.service_isolation.auth import b64
from experiments.shared_state.evidence_models import canonical

def run(config):
 c=config['frontend'];c.update(build=config['cohort'],identityBuild=config['cohort'],ordinaryBuild=config['cohort'])
 timings=[];captured=None
 def inference_count():
  from experiments.shared_state.test_store import admin
  with admin() as connection:return connection.execute("SELECT count(*) FROM synthetic_state.operations WHERE provider='synthetic_ai'").fetchone()[0]
 def call(path,value=None,user='alice',backend='backend-a',headers_change=None):
  nonlocal captured
  raw=canonical(value) if value is not None else b'';method='POST' if value is not None else 'GET';now=int(time.time())
  iap=jwt.encode(dict(iss='https://cloud.google.com/iap',aud=c['iapAudience'],sub='accounts.google.com:synthetic-'+user,email=user+'@example.invalid',iat=now,exp=now+600),config['signer'],algorithm='ES256',headers={'kid':'task52-offline-iap'})
  base=dict(sub='frontend',iat=now,exp=now+60,jti=secrets.token_hex(16),build=c['identityBuild'],environment=c['identityEnvironment'],epoch=c['epoch'])
  forward=signed(c,dict(base,iss=FORWARD,aud='public-user-pipeline',request=binding('public-user-pipeline',method,path,raw),iap=digest(iap.encode())))
  token=c['oidcTokens'][c['audiences']['backend']]
  proof=signed(c,dict(base,jti=secrets.token_hex(16),iss=REQUEST,aud='backend',request=binding('backend',method,path,raw),oidc=digest(token.encode()),iap=digest(iap.encode()),forward=digest(forward.encode())))
  headers={'Content-Type':'application/json','Authorization':'Bearer '+token,'X-Whereto-Context':b64(canonical(dict(forward=forward,iap=iap,proof=proof)))}
  if headers_change:headers.update(headers_change)
  context=ssl.create_default_context(cafile='/tmp/hosted-ports-ca.pem');connection=http.client.HTTPSConnection(backend+'.task52.invalid',8080,context=context,timeout=120)
  start=time.perf_counter()
  try:
   connection.request(method,path,raw,headers);response=connection.getresponse();body=response.read(1048577);assert len(body)<=1048576
   result=json.loads(body);timings.append(dict(path=path,milliseconds=round((time.perf_counter()-start)*1000,3),status=response.status));captured=(method,path,raw,headers);Path('/tmp/native-probe-attempt.json').write_text(json.dumps({'requests':timings,'scope':'Synthetic local HTTPS requests only; excludes controller setup; concurrent local recovery/security workload may contend'}))
   return response.status,result
  finally:connection.close()
 def assert_status(actual,expected):
  if actual[0]!=expected:raise AssertionError('Private application request refused: '+str(actual[0]))
  return actual[1]
 # Two independent browser-like outing handles with one fixed source each.
 source={'text':'Coffee and museum in Baltimore','calendarTimezone':'America/New_York'}
 initial=call('/api/interpret',source)
 if config.get('onlyInitial'):return {'status':initial[0],'requests':timings}
 first=assert_status(initial,200)
 assert first['request'] is None and first.get('privateOuting')
 handle=first['privateOuting'];assert call('/api/interpret',{**source,'privateOuting':handle,'answers':{'date':'tomorrow'}},user='bob')[0]!=200
 second=assert_status(call('/api/interpret',source),200);assert second['privateOuting']['handle']!=handle['handle']
 before_clarification=inference_count()
 continued=assert_status(call('/api/interpret',{**source,'privateOuting':handle,'answers':{'date':'tomorrow'}},backend='backend-b'),200)
 assert continued['request'] is not None
 assert inference_count()==before_clarification
 request={**continued['request'],'privateOuting':continued['privateOuting'],'startingLocation':{'point':{'id':'authorized-start','coordinates':{'latitude':39.29,'longitude':-76.61}},'explicitly_authorized':True,'source':'manual','precision':'address_or_place'}}
 result=assert_status(call('/api/plans/generate',request,backend='backend-b'),200);cards=result.get('plans',[])+result.get('provisionalPlans',[]);assert len(cards)>0
 assert inference_count()==before_clarification
 assert call('/api/plans/generate',request)[0]!=200
 for path in ('/api/plans/advanced','/api/plans/options','/api/venues/details','/api/plans/save'):
  assert call(path,{})[0]!=200
 assert call('/api/interpret',source,headers_change={'Authorization':'Bearer forged'})[0]!=200
 return dict(requests=timings,workflow='interpret, independent outing, other-user refusal, cross-factory clarification, generation, duplicate refusal, unsupported routes and forged workload refusal',confirmedPlans=len(result.get('plans',[])),provisionalPlans=len(result.get('provisionalPlans',[])),inferenceOperations=before_clarification,deterministicClarificationAddedInference=False)

if __name__=='__main__':
 value=json.loads(Path('/tmp/native-probe-control.json').read_text());result=run(value);print(json.dumps(result))
