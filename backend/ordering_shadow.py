"""Default-OFF, local-test-only observer. No result can authorize planning.

No environment switch, logs, network or persistence. One daemon worker maximum,
no queue, bounded wait; a stuck worker disables further observation until done.
Only enum/count diagnostics reach the test context. Raw data stays in memory.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
import threading

_sink = ContextVar('local_ordering_shadow_diagnostics', default=None)
_worker_slot = threading.BoundedSemaphore(1)
_diagnostic_lock = threading.Lock()
WAIT_SECONDS = .025
MAX_DIAGNOSTICS = 16


def _record(sink,diagnostic):
    with _diagnostic_lock:
        if len(sink)<MAX_DIAGNOSTICS:sink.append(diagnostic)


@contextmanager
def capture_local_test():
    """Explicit local test scope; never configure this in ordinary startup."""
    diagnostics=[]
    token=_sink.set(diagnostics)
    try:yield diagnostics
    finally:_sink.reset(token)


def _compute(source,snapshot):
    # Experimental policy is loaded only inside an explicitly enabled observer.
    from scripts.cloud_model52_ordering_v4 import inspect_order
    return inspect_order(source,snapshot)


def interpret_observed(value,operation):
    """API boundary decorator: original parsed output before pinned normalization.

    OFF calls the original operation unchanged. ON wraps only its lazy provider;
    no alternate provider, retry, fallback or extra interpretation. Saved pending
    snapshots may already be normalized, so explicitly skip observing those.
    """
    sink=_sink.get()
    if sink is None:return operation(value)
    if value.pending and value.pending.text==value.text:
        _record(sink,{'status':'saved_snapshot_skip'})
        return operation(value)

    class ObservedProvider:
        def interpret(self,text):
            from backend.interpretation import create_provider
            from backend.ai import Interpretation
            extracted=create_provider().interpret(text)
            try:
                parsed=Interpretation.model_validate(deepcopy(extracted))
                observe(text,parsed)
            except Exception:
                # Original strict validation still runs in the pinned operation.
                # Never rerun a model after an observer failure.
                _record(sink,{'status':'error'})
            return extracted

    return operation(value,provider=ObservedProvider())


def observe(source,parsed):
    """Return NOTHING; failures must not change the active interpretation."""
    sink=_sink.get()
    if sink is None or len(sink)>=MAX_DIAGNOSTICS:return
    try:
        if len(source)>8000 or not parsed.journey or len(parsed.journey.stops)>32 or len(parsed.model_dump_json())>32768:
            _record(sink,{'status':'bounded_skip'});return
        if not _worker_slot.acquire(blocking=False):
            _record(sink,{'status':'busy'});return
        try:snapshot=parsed.model_copy(deep=True)
        except Exception:
            _worker_slot.release();raise
        done=threading.Event()
        diagnostic={}

        def worker():
            try:
                result=_compute(source,snapshot)
                category=result['source']['category']
                outcome=result['outcome']
                if category not in ('explicit','partial','unordered','unknown') or outcome not in (
                    'verified_order','verified_no_mandatory_order','clarification_required'):
                    raise ValueError('Invalid observer result')
                diagnostic.update(status='observed',category=category,outcome=outcome,
                    rawEdges=min(32,len(result['originalGraph'])),
                    unsupportedEdges=min(32,len(result['unsupportedModelEdges'])),
                    normalized=bool(result['normalization']),issues=min(32,len(result['issues'])))
            except BaseException:
                # Never print exception text/tracebacks from private user input.
                diagnostic.clear();diagnostic['status']='error'
            finally:
                _worker_slot.release();done.set()

        thread=threading.Thread(target=worker,name='local-order-shadow',daemon=True)
        try:thread.start()
        except Exception:
            _worker_slot.release();raise
        if done.wait(WAIT_SECONDS):_record(sink,dict(diagnostic))
        else:_record(sink,{'status':'timeout'})
    except Exception:
        _record(sink,{'status':'error'})
