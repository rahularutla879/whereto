"""One local startup preparation, never a provider call, timer or retry loop."""
from threading import Thread, Lock
from urllib.parse import urlsplit
import os
from time import perf_counter

_lock=Lock()
_started=False
_status={'state':'not_requested'}

def snapshot():
    with _lock:return dict(_status)

def start():
    global _started
    from backend.provider_budget import local_real_enabled
    if (not local_real_enabled() or os.environ.get('WHERETO_AI_WARMUP_DEV')!='1'
            or os.environ.get('CI')):return
    from backend.ai import AISettings
    try:
        settings=AISettings.from_env()
        if settings.provider!='ollama' or urlsplit(settings.base_url).hostname not in ('localhost','127.0.0.1','::1'):return
    except (ValueError,TypeError):
        with _lock:_status.update(state='unavailable')
        return
    with _lock:
        if _started:return
        _started=True
        _status.update(state='preparing')
    def prepare():
        started=perf_counter()
        try:
            from backend.ai.ollama import OllamaProvider
            # Same schema/system prefix as actual extraction: prepares its prompt
            # cache too. No private user text, planning, Google or database work.
            OllamaProvider(settings).interpret('Coffee in Jersey City')
            state='ready'
        except Exception:state='unavailable' # Health stays available; actual request gives actionable errors.
        with _lock:_status.update(state=state,durationMs=round((perf_counter()-started)*1000))
    Thread(target=prepare,name='local-ai-readiness',daemon=True).start()
