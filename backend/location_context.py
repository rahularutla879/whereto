"""Location intent and calendar provenance, without coordinates or provider I/O."""
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

RELATIVE=re.compile(r"\b(?:near\s+(?:me|my current location)|around\s+(?:me|here|my location)|close to me|in my area|nearby)\b",re.I)

def relative_destination(text):
    # A named "in …" clause overrides relative wording, irrespective of case.
    return bool(RELATIVE.search(text)) and not re.search(
        r"\bin\s+(?!my area\b|my location\b|the (?:evening|morning|afternoon|city)\b|a\b|an\b|walking distance\b|driving distance\b)[a-z]", text, re.I)

def timezone_for(location):
    text=re.sub(r'[^a-z ]',' ',str(location or '').replace('.', '').casefold())
    if re.search(r'\bhyderabad\b',text):return 'Asia/Kolkata'
    if re.search(r'\b(?:baltimore|washington *(?:dc|district of columbia)|manhattan|new york|nyc|brooklyn|queens|bronx|staten island)\b',text):return 'America/New_York'
    return 'UTC'

class DestinationContext(BaseModel):
    model_config=ConfigDict(extra='forbid')
    originalText: str = Field(max_length=200)
    intent: Literal['explicit','current_relative','missing','unresolved'] = 'explicit'
    status: Literal['resolved','ambiguous','unresolved','verification_unavailable'] = 'verification_unavailable'
    source: Literal['request','confirmed_anchor','provider_components','browser'] = 'request'
    precision: Literal['named_area','representative_point','unknown'] = 'unknown'
    timezone: str | None = Field(default=None,max_length=100)

    @field_validator('timezone')
    @classmethod
    def valid_zone(cls,value):
        if value:
            try: ZoneInfo(value)
            except (KeyError, ValueError): raise ValueError("Use a valid IANA timezone.") from None
        return value

def outing_problem(request,now=None):
    zone=ZoneInfo(request.calendarTimezone or timezone_for(request.location))
    reference=now or datetime.now(timezone.utc)
    if reference.tzinfo is None or reference.utcoffset() is None:
        raise ValueError("The reference clock must include a timezone.")
    local=reference.astimezone(zone)
    if request.date < local.date():
        return 'outing_date_expired',f'The outing date {request.date} has ended in {zone.key}. You can still view saved pages or explicitly choose another date.'
    if request.date==local.date():
        minute=local.hour*60+local.minute+local.second/60
        explicit_start=request.explicitStart if request.explicitStart is not None else request.startTime!=600
        explicit_end=request.explicitEnd if request.explicitEnd is not None else request.endTime!=1440
        if explicit_end and request.endTime<=minute or explicit_start and request.startTime<minute:
            return 'outing_time_expired',f'The explicitly requested outing time has passed in {zone.key} on {request.date}. Saved pages remain available; choose another date or time.'
    return None

def anchor_compatible(destination, description):
    """Shared named parent evidence, never an invented neighborhood polygon."""
    words=re.findall(r"\w+", destination.casefold())
    evidence=re.findall(r"\w+", (description or "").casefold())
    if not words or not evidence:return False
    if all(w in evidence for w in words):return True
    # NYC's borough alias is an administrative relationship, not a polygon.
    if "manhattan" in words and ("manhattan" in evidence or "new york" in " ".join(evidence)):return True
    # Qualified neighborhood + supported parent (e.g. Shoreditch, London).
    return len(words)>1 and words[-1] in evidence and len(words[-1])>3
