"""Last sanitized local AI timing only. No text, places, tokens or response bodies."""
from threading import Lock
from math import isfinite
_lock=Lock()
_ai={}
def record_ai(result,wall_ms,validation_ms):
    global _ai
    names={'load_duration':'modelLoadMs','prompt_eval_duration':'promptProcessingMs','eval_duration':'responseGenerationMs','total_duration':'ollamaTotalMs'}
    values={label:round(result[key]/1e6,3) for key,label in names.items() if type(result.get(key)) in (int,float) and isfinite(result[key]) and 0<=result[key]<=86400*1e9}
    values.update(aiHttpMs=round(wall_ms,3),structuredValidationMs=round(validation_ms,3),repairAttempts=0)
    with _lock:_ai=values

def snapshot():
    with _lock:return dict(_ai)

# Fixed category timings only. No text, identities, coordinates or payloads.
from contextlib import contextmanager
from time import perf_counter
_stages={}
@contextmanager
def stage(name):
    if name not in {'search','lookup','details','matrix','route'}:raise ValueError('Unknown timing category.')
    start=perf_counter()
    try:yield
    finally:
        elapsed=round((perf_counter()-start)*1000,3)
        with _lock:
            previous=_stages.get(name,{'count':0,'totalMs':0})
            _stages[name]={'count':previous['count']+1,'totalMs':round(previous['totalMs']+elapsed,3),'lastMs':elapsed}
def provider_snapshot():
    with _lock:return {k:dict(v) for k,v in _stages.items()}
