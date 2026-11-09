"""Explicit test fixtures only; production startup never imports this module.

Keep the Nov7 Saturday venue/event data. Freeze named calendar lookups, and
explicitly opt into a route-evidence clock only for cache-reuse scenarios.
Monotonic TTLs, quota windows, billing clocks and explicit `now=` arguments
remain independent. No suite-wide clock or production clock flag is installed.
"""
from contextlib import asynccontextmanager
from datetime import datetime,timezone
from unittest.mock import patch

FIXTURE_NOW=datetime(2026,11,1,12,tzinfo=timezone.utc)


def _datetime_at(instant):
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError('Test reference time must be timezone-aware')

    class FrozenCalendar(datetime):
        @classmethod
        def now(cls,tz=None):
            return instant.astimezone(tz) if tz else instant.replace(tzinfo=None)

    return FrozenCalendar


def calendar_clock(instant=FIXTURE_NOW):
    """Scoped calendar freshness; pair with TestCase.enterContext/with."""
    return patch('backend.location_context.datetime',_datetime_at(instant))


def route_evidence_clock(instant=FIXTURE_NOW):
    """Explicit route reuse scenario clock; never changes the 300s policy."""
    return patch('backend.routes.datetime',_datetime_at(instant))


def fixture_api():
    """Explicit uvicorn --factory test target, same real application/routes.

    One clock for the child server's lifespan, restored at shutdown. Never
    selected by normal dev/start commands; no production clock/environment flag.
    """
    from backend.main import app
    original=app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application):
        with calendar_clock():
            async with original(application):yield

    app.router.lifespan_context=lifespan
    return app
