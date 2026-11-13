"""Public request JSON may have whitespace; signed original bytes stay unchanged."""
import json,math
from experiments.shared_state.contracts import Denied

def decode(raw):
 def pairs(values):
  out={}
  for k,v in values:
   if k in out:raise ValueError()
   out[k]=v
  return out
 def bounded(v,depth=0):
  if depth>32:raise ValueError()
  if type(v) is float and not math.isfinite(v):raise ValueError()
  if isinstance(v,dict):
   for x in v.values():bounded(x,depth+1)
  elif isinstance(v,list):
   for x in v:bounded(x,depth+1)
 try:
  if len(raw)>65536:raise ValueError()
  value=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError()));bounded(value)
  if not isinstance(value,dict):raise ValueError()
  return value
 except (ValueError,TypeError,UnicodeError,RecursionError):raise Denied('public_json') from None
