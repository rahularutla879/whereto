"""Bounded synthetic test timings only; never log source, SQL, tokens or payloads."""
import json,time,os
from functools import wraps
from threading import Lock
PATH='/tmp/network-spans.jsonl';MAX=5000;count=0;lock=Lock()

def timed(owner,name,stage):
 original=getattr(owner,name)
 @wraps(original)
 def call(*a,**k):
  global count
  start=time.perf_counter_ns();ok=False
  try:
   result=original(*a,**k);ok=True;return result
  finally:
   with lock:
    admit=count<MAX
    if admit:count+=1
   if admit:
    fd=os.open(PATH,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
    with os.fdopen(fd,'a') as f:f.write(json.dumps(dict(stage=stage,nanoseconds=time.perf_counter_ns()-start,ok=ok))+'\n')
 setattr(owner,name,call)
def install():
 import psycopg,http.client
 from experiments.hosted_identity.auth import _Boundary
 from experiments.ordinary_hosted.request_auth import RequestVerifier
 from experiments.hosted_identity.tokens import Tokens
 from experiments.service_isolation.factory import Factory
 from experiments.shared_state.redis_evidence import RedisEvidence
 from experiments.shared_state.application_grants import GrantStore
 from experiments.service_isolation.runtime import ScopedWitness
 from backend.planning_admission import AdmissionRegistry
 from private_runtime.service_client import ServiceClient
 from experiments.service_isolation import synthetic,server
 for owner,name,stage in [(Tokens,'verify','identity'),(_Boundary,'check','serviceAuthentication'),(RequestVerifier,'check','publicAuthentication'),(http.client.HTTPSConnection,'connect','tlsConnect'),(Factory,'get','sessionLookup'),(RedisEvidence,'get','redisRead'),(RedisEvidence,'publish','redisWrite'),(psycopg.Connection,'execute','sqlExecute'),(ScopedWitness,'call','witnessProtocol'),(AdmissionRegistry,'validate','admission'),(GrantStore,'reserve','reservation'),(ServiceClient,'request','authenticatedRPC'),(synthetic,'respond','fakeProvider'),(server,'dispatch','providerDispatch')]:timed(owner,name,stage)
