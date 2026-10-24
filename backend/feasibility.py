"""Pure Task 44 evidence evaluation. No generation, ranking or provider I/O.

Results concern travel/hours only, never prices, bookings or overall availability.
All instants are explicit; uncertainty never supplies a duration or schedule.
"""
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, Field, model_validator

from backend.models import ContractModel, EVENT_ACTIVITIES, OutingDate
from backend.routes import AuthorizedStart, Mode, RouteLeg
from backend.venue_models import VenueFacts

UTC = timezone.utc
Limit = Annotated[Decimal, Field(ge=0, allow_inf_nan=False)]
State = Literal["feasible", "infeasible", "unverified"]


class EvidenceStop(ContractModel):
    venue: VenueFacts
    arrival: AwareDatetime | None = None
    departure: AwareDatetime | None = None
    # Trusted request context, not inferred from local receipt time. A response
    # received just after midnight may belong to the preceding request date.
    hours_request_date: OutingDate | None = None

    @model_validator(mode="after")
    def interval(self):
        if (self.arrival is None) != (self.departure is None):
            raise ValueError("Supply both arrival and departure, or neither.")
        if self.arrival is not None and self.departure.astimezone(UTC) <= self.arrival.astimezone(UTC):
            raise ValueError("Departure must follow arrival in absolute time.")
        return self


class FeasibilityInput(ContractModel):
    candidate_id: str
    stops: Annotated[list[EvidenceStop], Field(min_length=1, max_length=4)]
    mode: Mode
    routes: list[RouteLeg] = Field(default_factory=list)
    max_leg_minutes: Limit | None = None
    max_total_minutes: Limit | None = None  # Inter-stop only, like the existing request.
    starting_location: AuthorizedStart | None = Field(default=None, repr=False)
    max_first_leg_minutes: Limit | None = None
    evaluated_at: AwareDatetime  # Explicit clock makes evaluation reproducible.


class EvidenceCheck(ContractModel):
    kind: Literal["travel", "hours", "session"]
    state: State
    code: str
    evidence_ref: str  # Input path, not raw payload or precise user location.
    stop_index: int


class FeasibilityResult(ContractModel):
    candidate_id: str
    state: State
    travel_state: State
    hours_state: State
    checks: list[EvidenceCheck]


def _state(checks) -> State:
    states = {c.state for c in checks}
    return "infeasible" if "infeasible" in states else "unverified" if "unverified" in states else "feasible"


def _local_instant(day, hour, minute, zone):
    """Reject nonexistent or repeated wall-clock boundaries rather than guess fold."""
    wall = datetime.combine(day, time(hour, minute))
    instants = {wall.replace(tzinfo=zone, fold=fold).astimezone(UTC) for fold in (0, 1)
                if wall.replace(tzinfo=zone, fold=fold).astimezone(UTC).astimezone(zone).replace(tzinfo=None) == wall}
    return next(iter(instants)) if len(instants) == 1 else None


def _covers(intervals, arrival, departure):
    cursor = arrival
    for start, end in sorted(intervals):
        if start > cursor:
            break
        if end > cursor:
            cursor = end
        if cursor >= departure:
            return True
    return False


def _hours(stop, evaluated_at):
    venue = stop.venue
    if venue.evidence != "provider_supplied" or venue.provider != "google_places":
        return "unverified", "unsupported_hours_source", "venue.evidence"
    if stop.arrival is None:
        return "unverified", "missing_schedule", "arrival"
    if venue.timeZone is None:
        return "unverified", "missing_timezone", "venue.timeZone"
    zone = ZoneInfo(venue.timeZone.id)
    arrival, departure = stop.arrival.astimezone(UTC), stop.departure.astimezone(UTC)
    current = venue.currentOpeningHours
    stamp = venue.observedAt.get("currentOpeningHours.periods")
    ref = "venue.currentOpeningHours.periods"
    # openNow receipt must never freshen a retained periods snapshot.
    usable = (current is not None and current.periods is not None and stamp is not None
              and stop.hours_request_date is not None
              and stamp <= evaluated_at and stamp.astimezone(zone).date() == evaluated_at.astimezone(zone).date()
              and stop.hours_request_date <= stamp.astimezone(zone).date() <= stop.hours_request_date + timedelta(days=1)
              and arrival >= evaluated_at.astimezone(UTC))
    if usable:
        first_day = stop.hours_request_date
        lower = _local_instant(first_day, 0, 0, zone)
        upper = _local_instant(first_day + timedelta(days=7), 0, 0, zone)
        usable = lower is not None and upper is not None and lower <= arrival < departure <= upper
    if not usable:
        code = "regular_hours_only" if venue.regularOpeningHours is not None else "missing_applicable_hours"
        return "unverified", code, "venue.regularOpeningHours" if code == "regular_hours_only" else ref
    intervals = []
    for period in current.periods:
        a, b = period.open, period.close
        if b is None:
            # Google's unique always-open sentinel. Other open-ended periods are ambiguous.
            if len(current.periods) == 1 and (a.day, a.hour, a.minute, a.date, a.truncated) in (
                    (0, 0, 0, None, None), (0, 0, 0, None, False)):
                intervals.append((lower, upper))
                continue
            return "unverified", "ambiguous_hours", ref
        if a.date is None or b.date is None or a.truncated or b.truncated:
            return "unverified", "ambiguous_hours", ref
        start = _local_instant(a.date, a.hour, a.minute, zone)
        end = _local_instant(b.date, b.hour, b.minute, zone)
        if start is None or end is None or end <= start or start < lower or end > upper:
            return "unverified", "ambiguous_hours", ref
        intervals.append((start, end))
    if _covers(intervals, arrival, departure):
        return "feasible", "hours_cover_activity", ref
    return "infeasible", "closed_during_activity", ref


def evaluate_feasibility(value: FeasibilityInput) -> FeasibilityResult:
    value = FeasibilityInput.model_validate(value.model_dump())
    checks = []

    def add(kind, state, code, ref, index):
        checks.append(EvidenceCheck(kind=kind, state=state, code=code, evidence_ref=ref, stop_index=index))

    required = [(a.venue.id, b.venue.id, i + 1, value.max_leg_minutes, False)
                for i, (a, b) in enumerate(zip(value.stops, value.stops[1:]))]
    if value.starting_location is not None:
        required.insert(0, (value.starting_location.point.id, value.stops[0].venue.id, 0,
                            value.max_first_leg_minutes, True))
    # No starting location means no first-leg obligation, even if a cap was supplied.
    known_total = Decimal(0)
    for origin, destination, index, limit, first in required:
        if not first:
            before, after = value.stops[index - 1].departure, value.stops[index].arrival
            if before is not None and after is not None and after.astimezone(UTC) < before.astimezone(UTC):
                add("travel", "infeasible", "overlapping_stops", f"stops[{index}].arrival", index)
        venues = [value.stops[index].venue] if first else [value.stops[index - 1].venue, value.stops[index].venue]
        if any(v.provider != "google_places" or v.evidence != "provider_supplied" for v in venues):
            add("travel", "unverified", "unsupported_route_source", f"stops[{index}].venue.evidence", index)
            continue
        matches = [(i, leg) for i, leg in enumerate(value.routes)
                   if (leg.origin_id, leg.destination_id, leg.mode) == (origin, destination, value.mode)]
        ref = f"required_routes[{index}]" if not matches else f"routes[{matches[0][0]}]"
        if len(matches) != 1:
            add("travel", "unverified", "missing_route" if not matches else "ambiguous_route", ref, index)
            continue
        leg = matches[0][1]
        if leg.status == "unreachable" and leg.provider == "google_routes":
            add("travel", "infeasible", "unreachable_route", ref, index)
            continue
        identity = (leg.status == "same_location" and leg.provider == "local_identity"
                    and leg.estimate_type == "same_location" and origin == destination
                    and leg.duration_seconds == 0 and leg.distance_meters == 0)
        routed = (leg.status == "ok" and leg.provider == "google_routes"
                  and leg.estimate_type == ("walking" if value.mode == "walk" else "traffic_unaware"))
        if not identity and not routed:
            add("travel", "unverified", "route_" + leg.status, ref, index)
            continue
        # Exact protobuf nanos are preferred; legacy float-only evidence retains
        # supplied seconds precision, never rounded minute display values.
        seconds = (Decimal(leg.duration_nanoseconds) / 10**9 if leg.duration_nanoseconds is not None
                   else Decimal(str(leg.duration_seconds)))
        if not first:
            known_total += seconds
        exceeded = limit is not None and seconds > limit * 60
        add("travel", "infeasible" if exceeded else "feasible",
            "first_leg_limit_exceeded" if exceeded and first else "leg_limit_exceeded" if exceeded else "route_verified", ref, index)
        if not first:
            before, after = value.stops[index - 1].departure, value.stops[index].arrival
            if before is None or after is None:
                add("travel", "unverified", "missing_transfer_schedule", ref, index)
            else:
                gap = after.astimezone(UTC) - before.astimezone(UTC)
                available = Decimal(gap.days * 86400 + gap.seconds) + Decimal(gap.microseconds) / 10**6
                if available < seconds:
                    add("travel", "infeasible", "insufficient_transfer_time", ref, index)
    if value.max_total_minutes is not None and known_total > value.max_total_minutes * 60:
        add("travel", "infeasible", "total_travel_limit_exceeded", "max_total_minutes", 0)
    for i, stop in enumerate(value.stops):
        state, code, ref = _hours(stop, value.evaluated_at)
        add("hours", state, code, f"stops[{i}].{ref}", i)
        if stop.venue.activity in EVENT_ACTIVITIES or stop.venue.activity == "movie":
            add("session", "unverified", "session_not_verified", f"stops[{i}].venue.activity", i)
    return FeasibilityResult(candidate_id=value.candidate_id, state=_state(checks),
                             travel_state=_state(c for c in checks if c.kind == "travel"),
                             hours_state=_state(c for c in checks if c.kind == "hours"), checks=checks)


def filter_feasible_candidates(candidates: list[FeasibilityInput]) -> dict[str, list[FeasibilityResult]]:
    """Stable partition with provisional candidates retained; no scoring or I/O."""
    result = {state: [] for state in ("feasible", "infeasible", "unverified")}
    for candidate in candidates:
        evaluated = evaluate_feasibility(candidate)
        result[evaluated.state].append(evaluated)
    return result
