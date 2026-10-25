"""Backend contracts; no parsing, catalog lookup, routing, or plan generation.

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
    travel: TravelMinutes | None = None  # Existing total inter-stop cap.
    groupBudget: Money | None = None
    maxLegTravel: TravelMinutes | None = None
    maxFirstLegTravel: TravelMinutes | None = None
    startTime: StartMinute = 600
    endTime: EndMinute = 1440
    requireAvailability: bool = Field(default=False, strict=True)
    cost: CostPreference = CostPreference.balanced
    transport: TransportationMode | None = None
    dinner: bool = Field(default=False, strict=True)
    dinnerStops: list[Annotated[int, Field(strict=True, ge=0, le=3)]] | None = None
    # Repeating a category requests another stop; repeating an ID needs permission.
    allowRevisits: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def validate_activities(self):
        if self.dinnerStops is not None and any(
                i >= len(self.activities) or self.activities[i] != ActivityType.food for i in self.dinnerStops):
            raise ValueError("Dinner stop indexes must identify requested food stops")
        if self.endTime <= self.startTime:
            raise ValueError("Outing end must be after its earliest start")
        if any(activity in EVENT_ACTIVITIES for activity in self.activities) and self.date is None:
            raise ValueError("Scheduled events require an exact outing date")
        return self


class PlanningRequest(OutingRequest):
    """Public/final planning requires a date; partial candidate analysis may not."""
    date: OutingDate = Field(...)


class TimeWindow(ContractModel):
    """Single-day local window; null date means a daily recurring window.

    None window list means unknown; an empty list explicitly means closed.
    Windows do not span midnight. Date-scoped windows need an exact request date.
    """
    date: OutingDate | None = None
    start: StartMinute
    end: EndMinute

    @model_validator(mode="after")
    def validate_window(self):
        if self.end <= self.start:
            raise ValueError("Window must end after its start")
        return self


class VenueIdentity(ContractModel):
    """Shared identity/category only; a building is not a scheduled event."""
    id: Nonblank
    name: Nonblank
    activity: ActivityType


class Venue(VenueIdentity):
    kind: Literal["venue"] = "venue"
    neighborhood: Nonblank | None = None
    price: Money | None = None  # USD/person; None is unknown, never free.
    duration: DurationMinutes | None = None
    zone: Annotated[int, Field(strict=True, ge=0)] | None = None  # Mock routing only.
    experience: Annotated[float, Field(strict=True, ge=0)] | None = None
    capacity: Capacity | None = None  # Unknown capacity is not proof of suitability.
    dataQuality: DataQuality = Field(default_factory=DataQuality)
    source: Nonblank | None = None  # Source/reference when known; no lookup occurs.
    # Explicit bridge for physical Google buildings, including event categories.
    # A physical place never supplies an invented ScheduledEvent.
    providerPlaceId: Nonblank | None = None
    address: Nonblank | None = None
    mapsUrl: Nonblank | None = None
    evidenceLabels: dict = Field(default_factory=dict)
    openingHours: Nonblank | None = None
    availability: Nonblank | None = None
    openingWindows: list[TimeWindow] | None = None
    availabilityWindows: list[TimeWindow] | None = None

    @model_validator(mode="after")
    def validate_kind(self):
        if self.providerPlaceId is not None:
            if self.id != self.providerPlaceId or self.kind != "venue" or self.dataQuality.identity != DataStatus.verified:
                raise ValueError("Physical provider venues require original identity and explicit provenance")
            return self
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


class CandidateStop(ContractModel):
    """Only dataset event times are assigned; ordinary stop times stay unknown."""

    venue: VenueInformation
    start: StartMinute | None = None
    end: EndMinute | None = None

    @model_validator(mode="after")
    def validate_fixed_times(self):
        if isinstance(self.venue, ScheduledEvent):
            expected_end = (self.venue.start + self.venue.duration
                            if self.venue.duration is not None else None)
            if self.start != self.venue.start or self.end != expected_end:
                raise ValueError("Candidate event times must match the supplied record")
        elif self.start is not None or self.end is not None:
            raise ValueError("Ordinary candidate stop times must remain unknown")
        return self


def fixed_times_compatible(venues: list[Venue | ScheduledEvent]) -> bool:
    """Necessary timing check only; no travel or ordinary opening-hour claims.

    Known intervening durations must fit between fixed events. Unknown durations
    use only the model's positive-duration lower bound, never a fabricated time.
    """
    earliest = None
    for venue in venues:
        if isinstance(venue, ScheduledEvent):
            if earliest is not None and venue.start < earliest:
                return False
            earliest = venue.start + (venue.duration if venue.duration is not None else 1)
        elif earliest is not None:
            earliest += venue.duration if venue.duration is not None else 1
    return True


class CandidateItinerary(ContractModel):
    """Unranked outing, deliberately separate from a fully scheduled Itinerary.

    Budget, capacity, travel and ordinary schedules have not been evaluated.
    Venue records retain all source fields and data-quality labels.
    """

    id: Nonblank
    venues: list[VenueInformation] = Field(min_length=1, max_length=4)
    stops: list[CandidateStop] = Field(min_length=1, max_length=4)
    people: GroupSize
    date: OutingDate | None = None
    allowRevisits: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def validate_candidate(self):
        if self.venues != [stop.venue for stop in self.stops]:
            raise ValueError("Candidate venues must match stop order")
        if not self.allowRevisits and len({v.id for v in self.venues}) != len(self.venues):
            raise ValueError("Repeated record identity requires explicit revisit permission")
        if any(isinstance(v, ScheduledEvent) and v.eventDate != self.date for v in self.venues):
            raise ValueError("Candidate events must match the requested date")
        if not fixed_times_compatible(self.venues):
            raise ValueError("Candidate fixed event times conflict in requested order")
        return self


class CandidateGenerationResult(ContractModel):
    request: OutingRequest
    candidates: list[CandidateItinerary] = Field(default_factory=list)
    errors: list[PlanningError] = Field(default_factory=list)
    message: Nonblank

    @model_validator(mode="after")
    def validate_candidates(self):
        if bool(self.candidates) == bool(self.errors):
            raise ValueError("Return candidates or structured errors")
        if len({c.id for c in self.candidates}) != len(self.candidates):
            raise ValueError("Candidate IDs must be distinct")
        for candidate in self.candidates:
            if ([v.activity for v in candidate.venues] != self.request.activities
                    or candidate.people != self.request.people
                    or candidate.date != self.request.date
                    or candidate.allowRevisits != self.request.allowRevisits):
                raise ValueError("Candidates must preserve the resolved request")
        return self


class ConstraintIssue(ContractModel):
    code: Nonblank
    field: Nonblank
    message: Nonblank
    status: Literal["unknown", "violation"]
    venueId: str | None = None


class PriceQuote(ContractModel):
    amount: Money | None = None  # USD/person, same inclusions as the fixture.
    status: DataStatus = DataStatus.unknown
    source: Nonblank | None = None


class TravelQuote(ContractModel):
    minutes: Annotated[int, Field(strict=True, ge=0)] | None = None
    status: DataStatus = DataStatus.unknown
    source: Nonblank | None = None


class PlannedStop(ContractModel):
    venue: VenueInformation
    start: StartMinute | None = None
    end: EndMinute | None = None
    duration: DurationMinutes | None = None


    @model_validator(mode="after")
    def validate_calculated_stop(self):
        if self.duration != self.venue.duration:
            raise ValueError("Calculated duration must preserve the venue evidence")
        if self.start is not None and self.end is not None:
            if self.end <= self.start or self.duration != self.end - self.start:
                raise ValueError("Calculated stop times must match the supplied duration")
        if isinstance(self.venue, ScheduledEvent) and self.start != self.venue.start:
            raise ValueError("Calculated event start must preserve the fixed schedule")
        return self


class RecommendationReason(ContractModel):
    code: Literal["score", "cost", "travel", "quality", "feasibility", "diversity"]
    message: Nonblank


class RankedItinerary(ContractModel):
    candidate: CandidateItinerary
    feasibility: Literal["confirmed", "provisional", "violated"]
    issues: list[ConstraintIssue]
    stops: list[PlannedStop]
    prices: list[PriceQuote]
    legs: list[TravelQuote]
    knownCostPerPerson: Money
    knownGroupCost: Money
    costPerPerson: Money | None
    groupCost: Money | None
    totalTravel: TravelMinutes | None
    activityDuration: DurationMinutes | None
    elapsedDuration: DurationMinutes | None
    score: Annotated[float, Field(ge=0, le=1)] = 0
    components: dict[str, float] = Field(default_factory=dict)
    explanations: list[RecommendationReason] = Field(default_factory=list)
    routeEvidence: list[dict] = Field(default_factory=list)
    firstLeg: dict | None = None
    feasibilityEvidence: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_evaluation(self):
        expected = ("violated" if any(i.status == "violation" for i in self.issues)
                    else "provisional" if self.issues else "confirmed")
        if self.feasibility == "confirmed" and any(value is None for value in (
                self.costPerPerson, self.groupCost, self.totalTravel, self.activityDuration,
                self.elapsedDuration, *(s.start for s in self.stops), *(s.end for s in self.stops))):
            raise ValueError("Confirmed evaluations require complete calculations")
        if self.feasibility != expected:
            raise ValueError("Feasibility must agree with constraint evidence")
        if [s.venue for s in self.stops] != self.candidate.venues:
            raise ValueError("Evaluated stops must preserve candidate venues")
        if len(self.prices) != len(self.stops) or len(self.legs) != len(self.stops) - 1:
            raise ValueError("A quote is required for every stop and leg, including unknown quotes")
        return self


class RankingResult(ContractModel):
    request: OutingRequest
    plans: list[RankedItinerary] = Field(default_factory=list, max_length=3)
    provisionalPlans: list[RankedItinerary] = Field(default_factory=list, max_length=3)
    errors: list[PlanningError] = Field(default_factory=list)
    rejectionReasons: dict[str, int] = Field(default_factory=dict)
    message: Nonblank
    notes: list[str] = Field(default_factory=list)
    dataMode: Literal["mock", "real"] = "mock"
    diagnostics: dict = Field(default_factory=dict)
    detailsToken: str | None = None
    alternativeBatches: list[Annotated[list[RankedItinerary], Field(min_length=1, max_length=3)]] = Field(default_factory=list, max_length=2)

    @model_validator(mode="after")
    def validate_selection(self):
        initial = self.plans + self.provisionalPlans
        selected = initial + [p for batch in self.alternativeBatches for p in batch]
        if len(initial) > 3:
            raise ValueError("At most three total options")
        if self.alternativeBatches and (self.dataMode != "real" or not initial or any(p.feasibility != "provisional" for batch in self.alternativeBatches for p in batch)):
            raise ValueError("Additional options require provisional real plans")
        if selected and self.request.date is None:
            raise ValueError("Final itinerary options require an exact outing date")
        identities = [tuple(v.id for v in p.candidate.venues) for p in selected]
        if len(set(identities)) != len(identities):
            raise ValueError("Options must have distinct ordered venues")
        if any(p.feasibility != "confirmed" for p in self.plans):
            raise ValueError("Recommended plans must have confirmed constraint feasibility")
        if any(p.feasibility != "provisional" for p in self.provisionalPlans):
            raise ValueError("Provisional alternatives must remain explicit")
        for plan in selected:
            c = plan.candidate
            if ([v.activity for v in c.venues] != self.request.activities
                    or c.people != self.request.people or c.date != self.request.date
                    or c.allowRevisits != self.request.allowRevisits):
                raise ValueError("Selected plans must preserve request")
        if self.plans and self.errors:
            raise ValueError("Successful recommendations cannot have failure errors")
        return self
