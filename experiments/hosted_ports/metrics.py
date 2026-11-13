"""External local structural timing only; never packaged or publicly exposed."""
from functools import wraps
from threading import Lock
from time import perf_counter_ns
import json
_LOCK=Lock();_COUNT=0

def wrap(owner,name,stage):
 original=getattr(owner,name)
 @wraps(original)
 def measured(*args,**kwargs):
  global _COUNT
  begin=perf_counter_ns();ok=False
  try:result=original(*args,**kwargs);ok=True;return result
  finally:
   elapsed=perf_counter_ns()-begin
   with _LOCK:
    if _COUNT<10000:
     _COUNT+=1
     with open('/tmp/private-role-spans.jsonl','a') as output:output.write(json.dumps(dict(stage=stage,nanoseconds=elapsed,ok=ok))+'\n')
 setattr(owner,name,measured)

def install(role):
 from private_runtime.connections import SQLPool
 from private_runtime.registry import Lease
 from experiments.hosted_identity.auth import _Boundary
 wrap(SQLPool,'_take','sql.connection_acquisition');wrap(SQLPool,'_check','sql.enrollment_check');wrap(Lease,'execute','sql.protected_statement');wrap(_Boundary,'check','authentication.with_nonce')
 if role in ('factory','dispatcher'):
  from private_runtime.redis_port import EvidenceRedis
  from experiments.shared_state.application_grants import GrantService
  from experiments.shared_state.redis_evidence import EvidenceStore
  wrap(EvidenceRedis,'_run','redis.operation');wrap(GrantService,'sync','witness.history_check');wrap(GrantService,'prepare','financial.prepare');wrap(GrantService,'send','financial.dispatch');wrap(EvidenceStore,'recover','native.evidence_recovery')
 if role=='factory':
  from experiments.shared_state.action_bridge import Broker
  wrap(Broker,'_check','admission.revalidation')
