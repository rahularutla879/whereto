"""Shared fictional catalog access only; no scheduling, routing or planning.

Run from any working directory. Python adds provenance without changing the
legacy frontend payload. Missing hours/availability stay unknown (None).
"""

from datetime import date
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, model_validator

from backend.models import (
    ActivityType, Capacity, ContractModel, DataQuality, DataStatus,
    DurationMinutes, Money, Nonblank, OutingDate, ScheduledEvent,
    StartMinute, Venue, VenueInformation,
)

FIXTURE_PATH = Path(__file__).resolve().parent.parent / "data" / "mock-venues.json"
SUPPORTED_ACTIVITIES = tuple(ActivityType)
_RECORDS = TypeAdapter(list[VenueInformation])
_DATE = TypeAdapter(OutingDate)


class _Definition(ContractModel):
    label: Nonblank
    names: list[Nonblank] = Field(min_length=3, max_length=3)
    prices: list[Money] = Field(min_length=3, max_length=3)
    duration: DurationMinutes
    eventStart: StartMinute | None = None


class _Tier(ContractModel):
    neighborhood: Nonblank
    zone: Annotated[int, Field(strict=True, ge=0)]
    experience: Money
    capacity: Capacity


class _Fixture(ContractModel):
    fictional: Literal[True]
    notice: Nonblank
    timezone: Literal["America/New_York"]
    currency: Literal["USD"]
    eventDates: list[OutingDate]
    tiers: list[_Tier] = Field(min_length=3, max_length=3)
    catalog: dict[ActivityType, _Definition]

    @model_validator(mode="after")
    def unique_dates(self):
        if len(set(self.eventDates)) != len(self.eventDates):
            raise ValueError("Duplicate mock event dates")
        return self


def load_mock_venues(path: Path = FIXTURE_PATH) -> list[Venue | ScheduledEvent]:
    """Read and validate fresh records; never cache mutable model instances.

    Errors in JSON/schema/data propagate rather than returning partial data.
    Supported categories without definitions simply have no sample records.
    """
    fixture = _Fixture.model_validate_json(Path(path).read_text(encoding="utf-8"))
    records = []
    for activity, definition in fixture.catalog.items():
        for tier, name in enumerate(definition.names):
            event = definition.eventStart is not None
            quality = DataQuality(
                identity=DataStatus.fictional, price=DataStatus.fictional,
                capacity=DataStatus.fictional, duration=DataStatus.fictional,
                schedule=DataStatus.fictional if event else DataStatus.unknown,
                travel=DataStatus.fictional, experience=DataStatus.fictional,
            )
            base = dict(
                id=f"{activity.value}-{tier}", name=name, activity=activity,
                price=definition.prices[tier], duration=definition.duration,
                **fixture.tiers[tier].model_dump(), dataQuality=quality,
                source="data/mock-venues.json (fictional prototype)",
            )
            if event:
                records.extend(
                    {**base, "id": f"{base['id']}-{day.isoformat()}",
                     "kind": "event", "eventDate": day, "start": definition.eventStart}
                    for day in fixture.eventDates
                )
            else:
                records.append({**base, "kind": "venue"})
    venues = _RECORDS.validate_python(records)
    if len({venue.id for venue in venues}) != len(venues):
        raise ValueError("Duplicate mock venue IDs")
    return venues


def get_mock_venues(
    activity: ActivityType | str | None = None, *,
    event_date: date | str | None = None,
    kind: Literal["venue", "event"] | None = None,
    venues: list[Venue | ScheduledEvent] | None = None,
) -> list[Venue | ScheduledEvent]:
    """Retrieve by category, kind and/or event date, preserving fixture order.

    No date returns all dated events. A date selects exact event occurrences
    and retains ordinary venues, whose real opening hours are unknown.
    Unknown activity IDs/invalid dates raise ValueError; no matches returns [].
    No capacity, budget, travel feasibility or ranking logic is performed here.
    """
    selected = ActivityType(activity) if activity is not None else None
    day = _DATE.validate_python(event_date) if event_date is not None else None
    if kind not in (None, "venue", "event"):
        raise ValueError("kind must be venue or event")
    records = load_mock_venues() if venues is None else venues
    return [venue for venue in records
            if (selected is None or venue.activity == selected)
            and (kind is None or venue.kind == kind)
            and (day is None or not isinstance(venue, ScheduledEvent)
                 or venue.eventDate == day)]


def get_mock_venue(venue_id: str) -> Venue | ScheduledEvent | None:
    """Exact stable ID lookup; missing IDs never substitute another record."""
    return next((venue for venue in load_mock_venues() if venue.id == venue_id), None)


def available_activities(
    venues: list[Venue | ScheduledEvent] | None = None,
) -> tuple[ActivityType, ...]:
    """Categories with sample records, separate from SUPPORTED_ACTIVITIES."""
    records = load_mock_venues() if venues is None else venues
    present = {venue.activity for venue in records}
    return tuple(activity for activity in SUPPORTED_ACTIVITIES if activity in present)
