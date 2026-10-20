"""Task 24 contract; no parsing, catalog lookup, routing, or plan generation.

Requests contain resolved inputs, not the UI's blank/string form controls.
JSON response names match lib/planner.ts and lib/mock-data.ts. All clock values
are whole minutes after midnight in Baltimore (America/New_York).
"""

from datetime import date as CalendarDate
from enum import Enum
from math import isclose
from typing import Annotated, Literal

from pydantic import (
    BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints,
    model_validator,
)


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


Nonblank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
# These upper limits come from the working frontend, not venue availability.
GroupSize = Annotated[int, Field(strict=True, ge=1, le=100)]
Money = Annotated[float, Field(strict=True, ge=0)]
TravelMinutes = Annotated[int, Field(strict=True, ge=0, le=1440)]
StartMinute = Annotated[int, Field(strict=True, ge=0, lt=1440)]
EndMinute = Annotated[int, Field(strict=True, ge=0, le=1440)]
DurationMinutes = Annotated[int, Field(strict=True, gt=0, le=1440)]
Capacity = Annotated[int, Field(strict=True, gt=0)]
Location = Nonblank


def calendar_date(value):
    # Pydantic otherwise also accepts Unix timestamps and midnight datetimes.
    if type(value) is CalendarDate:
        return value
    if isinstance(value, str) and len(value) == 10:
        parsed = CalendarDate.fromisoformat(value)
        if parsed.isoformat() == value:
            return parsed
    raise ValueError("Use a calendar date in YYYY-MM-DD format")


OutingDate = Annotated[CalendarDate, BeforeValidator(calendar_date)]


class ActivityType(str, Enum):
    bowling = "bowling"
    drinks = "drinks"
    movie = "movie"
    food = "food"
    coffee = "coffee"
    outdoors = "outdoors"
    art = "art"
    museum = "museum"
    karaoke = "karaoke"
    arcade = "arcade"
    escape = "escape"
    mini_golf = "miniGolf"
    shopping = "shopping"
    zoo = "zoo"
    hiking = "hiking"
    picnic = "picnic"
    skating = "skating"
    baseball = "baseball"
    basketball = "basketball"
    football = "football"
    soccer = "soccer"
    hockey = "hockey"
    sports = "sports"
    concert = "concert"
    theater = "theater"
    musical = "musical"
    ballet = "ballet"
    opera = "opera"
    comedy = "comedy"


EVENT_ACTIVITIES = frozenset({
    ActivityType.baseball, ActivityType.basketball, ActivityType.football,
    ActivityType.soccer, ActivityType.hockey, ActivityType.sports,
    ActivityType.concert, ActivityType.theater, ActivityType.musical,
    ActivityType.ballet, ActivityType.opera, ActivityType.comedy,
})


class CostPreference(str, Enum):
    budget = "budget"          # Budget-friendly
    balanced = "balanced"      # Balanced
    experience = "experience"  # Best experience


class TransportationMode(str, Enum):
    walking = "walking"
    cycling = "cycling"
    driving = "driving"
    transit = "transit"
    # No default mode: the current mock travel formula has no transport mode.


class DataStatus(str, Enum):
    unknown = "unknown"
    fictional = "fictional"
    estimated = "estimated"
    verified = "verified"


class DataQuality(ContractModel):
    """Status applies to supplied values; None always means unknown/unprovided.

    A future producer must label fixtures fictional explicitly. Defaults never
    claim verification. This metadata does not verify a value or availability.
    """

    identity: DataStatus = DataStatus.unknown
    price: DataStatus = DataStatus.unknown
    capacity: DataStatus = DataStatus.unknown
    duration: DataStatus = DataStatus.unknown
    schedule: DataStatus = DataStatus.unknown
    travel: DataStatus = DataStatus.unknown
    experience: DataStatus = DataStatus.unknown


class OutingRequest(ContractModel):
    """Resolved mandatory constraints plus optional ranking/mode preferences.

    Defaults match makePlans. Activities stay in requested order. None budget
    or travel means no cap; zero is a real cap. None date means flexible day.
    Text interpretation and UI override precedence remain outside this model.
    """

    activities: list[ActivityType] = Field(min_length=1, max_length=4)
    location: Location = "Baltimore"
    people: GroupSize = 4
    date: OutingDate | None = None
    budget: Annotated[Money, Field(le=100000)] | None = None
    travel: TravelMinutes | None = None
    cost: CostPreference = CostPreference.balanced
    transport: TransportationMode | None = None
    dinner: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def validate_activities(self):
        if len(set(self.activities)) != len(self.activities):
            raise ValueError("Activities must be distinct and remain in requested order")
        if any(activity in EVENT_ACTIVITIES for activity in self.activities) and self.date is None:
            raise ValueError("Scheduled events require an exact outing date")
        return self


class Venue(ContractModel):
    kind: Literal["venue"] = "venue"
    id: Nonblank
    name: Nonblank
    activity: ActivityType
    neighborhood: Nonblank | None = None
    price: Money | None = None  # USD/person; None is unknown, never free.
    duration: DurationMinutes | None = None
    zone: Annotated[int, Field(strict=True, ge=0)] | None = None  # Mock routing only.
    experience: Annotated[float, Field(strict=True, ge=0)] | None = None
    capacity: Capacity | None = None  # Unknown capacity is not proof of suitability.
    dataQuality: DataQuality = Field(default_factory=DataQuality)
    source: Nonblank | None = None  # Source/reference when known; no lookup occurs.
    openingHours: Nonblank | None = None
    availability: Nonblank | None = None

    @model_validator(mode="after")
    def validate_kind(self):
        if (self.activity in EVENT_ACTIVITIES) != (self.kind == "event"):
            raise ValueError("Scheduled activity categories must use event records")
        return self


class ScheduledEvent(Venue):
    kind: Literal["event"] = "event"
    eventDate: OutingDate
    start: StartMinute

    @model_validator(mode="after")
    def validate_event_end(self):
        if self.duration is not None and self.start + self.duration > 1440:
            raise ValueError("Scheduled events must finish by midnight")
        return self


VenueInformation = Annotated[Venue | ScheduledEvent, Field(discriminator="kind")]


class ItineraryStop(ContractModel):
    venue: VenueInformation
    start: StartMinute
    end: EndMinute

    @model_validator(mode="after")
    def validate_times(self):
        if self.end <= self.start:
            raise ValueError("A stop must end after it starts")
        if self.venue.duration is not None and self.end - self.start != self.venue.duration:
            raise ValueError("Stop length must match venue duration")
        if isinstance(self.venue, ScheduledEvent) and self.start != self.venue.start:
            raise ValueError("Event stops must honor the fixed event start")
        return self


class Itinerary(ContractModel):
    id: Nonblank
    title: Nonblank
    description: Nonblank
    theme: Literal["peach", "lavender", "mint"]
    label: Nonblank
    venues: list[VenueInformation] = Field(min_length=1, max_length=4)
    stops: list[ItineraryStop] = Field(min_length=1, max_length=4)
    price: Money  # Total USD/person; excludes transport, tax, tips, fees, extras.
    travel: TravelMinutes  # Total between stops only; excludes first/last trip.
    duration: DurationMinutes  # Elapsed time including travel and waiting.
    people: GroupSize
    date: OutingDate | Literal["Any day"]
    transport: TransportationMode | None = None
    dataQuality: DataQuality = Field(default_factory=DataQuality)

    @model_validator(mode="after")
    def validate_stops(self):
        if self.venues != [stop.venue for stop in self.stops]:
            raise ValueError("Venues must match stops in the same order")
        activities = [venue.activity for venue in self.venues]
        if len(set(activities)) != len(activities):
            raise ValueError("Itinerary activities must be distinct")
        for index, stop in enumerate(self.stops):
            if index and stop.start < self.stops[index - 1].end:
                raise ValueError("Stops cannot overlap")
            if stop.venue.capacity is not None and stop.venue.capacity < self.people:
                raise ValueError("Group exceeds venue capacity")
            if isinstance(stop.venue, ScheduledEvent) and self.date != stop.venue.eventDate:
                raise ValueError("Event date must match outing date")
        if self.duration != self.stops[-1].end - self.stops[0].start:
            raise ValueError("Duration must include the entire schedule and waiting")
        gaps = sum(b.start - a.end for a, b in zip(self.stops, self.stops[1:]))
        if self.travel > gaps:
            raise ValueError("Travel must fit between scheduled stops")
        prices = [venue.price for venue in self.venues]
        if all(price is not None for price in prices):
            if not isclose(self.price, sum(prices), rel_tol=1e-9, abs_tol=1e-9):
                raise ValueError("Total price must match per-person venue prices")
        return self


class PlanningError(ContractModel):
    code: Literal["invalid_request", "unsupported_request", "unsupported_location",
                  "missing_date", "no_availability", "infeasible", "insufficient_data"]
    message: Nonblank
    field: Nonblank | None = None


class PlanningResult(ContractModel):
    # Same envelope as PlannerResult; errors is optional additive structured detail.
    plans: list[Itinerary] = Field(max_length=3)
    message: Nonblank
    location: Location
    activities: list[ActivityType]
    notes: list[str]
    errors: list[PlanningError] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_result(self):
        if self.plans and self.errors:
            raise ValueError("A failed request cannot return partial plans")
        if len({plan.id for plan in self.plans}) != len(self.plans):
            raise ValueError("Returned plans must be distinct")
        for plan in self.plans:
            if [venue.activity for venue in plan.venues] != self.activities:
                raise ValueError("Plans must preserve every requested activity in order")
        return self
