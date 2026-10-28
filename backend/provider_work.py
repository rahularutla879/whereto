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

def wait_for_capacity(capacity,seconds=2):
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
    def work():
        token=cancelled.set(event)
        try:return operation()
        finally:cancelled.reset(token)
    task=asyncio.create_task(asyncio.to_thread(work))
    try:
        while not task.done():
            done,_=await asyncio.wait({task},timeout=.1)
            if not done and await request.is_disconnected():
                event.set()
        return await task
    except asyncio.CancelledError:
        event.set()
        raise
