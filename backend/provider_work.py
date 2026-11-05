"""Bounded pre-dispatch admission and cooperative disconnect cancellation."""
import asyncio
from contextvars import ContextVar
from threading import Event
from time import monotonic
from backend.provider_budget import ProviderLimitError

cancelled=ContextVar('provider_work_cancelled',default=None)

def check_cancelled():
    event=cancelled.get()
    if event is not None and event.is_set():
        raise ProviderLimitError('Planning was cancelled. No further provider work was admitted.')

def wait_for_capacity(capacity,seconds=15):
    """Wait only before dispatch, never retry a failed provider operation."""
    deadline=monotonic()+seconds
    while True:
        check_cancelled()
        value=capacity()
        if value>0:return value
        remaining=deadline-monotonic()
        if remaining<=0:return 0
        event=cancelled.get()
        if event is None:
            # Direct/offline callers do not create a hidden waiting job.
            return 0
        event.wait(min(.05,remaining))

async def run_work(request,operation):
    event=Event()
    from backend.admission import active_lease
    lease=active_lease.get()
    if lease: lease.retain()
    def work():
        token=cancelled.set(event)
        try:
            check_cancelled()
            return operation()
        finally:
            cancelled.reset(token)
            if lease: lease.release()
    task=asyncio.create_task(asyncio.to_thread(work))
    try:
        while not task.done():
            done,_=await asyncio.wait({task},timeout=.1)
            if not done and await request.is_disconnected():
                event.set()
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        event.set()
        from backend.operations import event as record_event
        record_event("cancelled", "http", reason="cancelled")
        # Keep ownership until the bounded synchronous transport actually ends.
        # Retrieve an eventual exception even if the browser has gone away.
        task.add_done_callback(lambda done: done.exception() if not done.cancelled() else None)
        raise
