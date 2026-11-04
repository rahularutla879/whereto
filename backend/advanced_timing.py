"""Task 50D: pure, transient timing over server-owned Task 50C evidence.

No network, persistence, venue selection, waiting policy or activity defaults.
Decimal offsets retain route nanoseconds; clocks conservatively enclose offsets
at Python's microsecond resolution. Feasibility is conditional on supplied route
estimates and user dwell bounds, never a reservation or real-world guarantee.
"""
from datetime import date as CalendarDate, datetime, timedelta, timezone
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
import re
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import AwareDatetime, Field, model_validator

from backend.journey import Duration, JourneyModel
from backend.feasibility import State, EvidenceStop, _hours, _local_instant

UTC = timezone.utc
Seconds = Decimal


def explicit_departure(raw):
    """Bounded explicit departure grammar, reusing the existing clock parser.

    'After 2 PM' and default calendar windows are not exact departures. Conflicting
    explicit clocks remain unresolved. Never interpret stop appointment clocks.
    """
    from backend.date_resolution import CLOCK, _clock
    matches = list(re.finditer(r'\b(?:start(?:ing)?|leave|depart)(?:\s+at)?\s+('+CLOCK+r')\b', raw, re.I))
    values = []
    for match in matches:
        try:
            values.append((_clock(match[1]), match[0]))
        except ValueError:
            return None, None
    if not values or len({m for m, _ in values}) != 1:
        return None, None
    return values[0]


class DurationRange(JourneyModel):
    lower: Seconds = Field(ge=0)
    upper: Seconds | None = Field(default=None, ge=0)
    upper_exclusive: bool = False

    @model_validator(mode='after')
    def consistent(self):
        if self.upper is None and self.upper_exclusive:
            raise ValueError('An exclusive upper bound needs a value.')
        if self.upper is not None and (self.upper < self.lower or self.upper == self.lower and self.upper_exclusive):
            raise ValueError('Empty duration range.')
        return self

    @property
    def exact(self):
        return self.upper == self.lower


def _bounds(duration):
    if duration is None or duration.relation == 'approximate':
        return DurationRange(lower=0)
    seconds = Decimal(duration.minutes) * 60
    return DurationRange(lower=seconds if duration.relation in ('exact', 'minimum') else 0,
                         upper=seconds if duration.relation in ('exact', 'maximum', 'under') else None,
                         upper_exclusive=duration.relation == 'under')


def _plus(a, b):
    upper = None if a.upper is None or b.upper is None else a.upper + b.upper
    return DurationRange(lower=a.lower+b.lower, upper=upper,
                         upper_exclusive=upper is not None and (a.upper_exclusive or b.upper_exclusive))


class TimingReason(JourneyModel):
    code: str
    state: State
    message: str
    occurrence: int | None = None


class Projection(JourneyModel):
    offsets: DurationRange
    earliest: AwareDatetime | None = None
    latest: AwareDatetime | None = None
    # Precise clocks exist only for exact offsets representable in microseconds.
    estimate: Literal['route_estimate_and_user_constraints'] = 'route_estimate_and_user_constraints'

    @model_validator(mode='after')
    def consistent(self):
        if self.latest is not None and self.earliest is None:
            raise ValueError('Latest projection needs an earliest bound.')
        if self.latest and self.latest.astimezone(UTC) < self.earliest.astimezone(UTC):
            raise ValueError('Reversed projection.')
        if self.latest is not None and self.offsets.upper is None:
            raise ValueError('Unbounded duration cannot have a latest projection.')
        return self


class TimedVisit(JourneyModel):
    occurrence: int = Field(ge=0, lt=4)
    place_id: str
    dwell_constraint: Duration | None
    dwell: DurationRange
    arrival: Projection
    departure: Projection
    hours_state: State
    hours_exception: bool = False
    hours_code: str
    hours_observed_at: AwareDatetime | None = None
    hours_timezone: str | None = None
    special_day: bool = False


class TimedCandidate(JourneyModel):
    # Snapshot retains exact order, legs, provenance, omissions and source constraints.
    route: 'AdvancedRouteCandidate'
    candidate_index: int = Field(ge=0, lt=256)
    known_travel_seconds: Seconds = Field(ge=0)
    travel: DurationRange
    dwell: DurationRange
    elapsed: DurationRange
    start: AwareDatetime | None
    start_source: str | None
    deadline: AwareDatetime | None
    finish: Projection
    visits: list[TimedVisit] = Field(min_length=1, max_length=4)
    routing_state: State
    travel_preference_state: State
    budget_scope: Literal['outing','travel'] = 'outing'
    duration_state: State
    deadline_state: State
    hours_state: State
    state: State
    reasons: list[TimingReason]
    execution: Literal['unavailable'] = 'unavailable'

    @model_validator(mode='after')
    def consistent(self):
        if [(v.occurrence, v.place_id, v.dwell_constraint) for v in self.visits] != [
                (v.occurrence, v.selected.place_id, v.requested.duration) for v in self.route.visits]:
            raise ValueError('Timing must preserve the selected route occurrences.')
        if self.elapsed != _plus(self.travel, self.dwell) or self.finish.offsets != self.elapsed:
            raise ValueError('Elapsed time must include all travel and dwell.')
        if self.known_travel_seconds != self.travel.lower:
            raise ValueError('Known travel must equal its proven lower bound.')
        travel = DurationRange(lower=0, upper=0)
        dwell = DurationRange(lower=0, upper=0)
        offset = DurationRange(lower=0, upper=0)
        zone = self.start.tzinfo if self.start else None
        for leg in self.route.legs:
            travel = _plus(travel, _leg_range(leg.evidence))
        for visit, timed in zip(self.route.visits, self.visits):
            incoming = next((l for l in self.route.legs if l.to_occurrence == visit.occurrence), None)
            if incoming:
                offset = _plus(offset, _leg_range(incoming.evidence))
            if timed.hours_exception and (timed.hours_state!='infeasible' or visit.requested.kind!='named_place' or visit.requested.requirement!='required'):
                raise ValueError('A closure exception must retain a failed mandatory named-visit hours check.')
            expected_dwell = _bounds(visit.requested.duration)
            if timed.dwell != expected_dwell or timed.arrival != _project(offset, self.start, zone):
                raise ValueError('Arrival/dwell disagree with original route evidence.')
            offset = _plus(offset, expected_dwell)
            dwell = _plus(dwell, expected_dwell)
            if timed.departure != _project(offset, self.start, zone):
                raise ValueError('Departure disagrees with original route evidence.')
        if travel != self.travel or dwell != self.dwell or self.finish != _project(self.elapsed, self.start, zone):
            raise ValueError('Timing breakdown must agree with original evidence.')
        if self.duration_state != _limit(self.travel if self.budget_scope=='travel' else self.elapsed, self.route.journey.total_duration)[0]:
            raise ValueError('Duration verdict disagrees with the source constraint.')
        expected_hours = _combine(*('unverified' if v.hours_exception else v.hours_state for v in self.visits), *(['unverified'] if self.route.endpoint else []))
        expected_routing = ('infeasible' if any(l.evidence.status == 'unreachable' for l in self.route.legs)
                            else 'unverified' if self.route.missing_leg_indexes else 'feasible')
        expected_preference = ('infeasible' if self.route.route_status == 'beyond_limit'
                               else 'unverified' if self.route.route_status == 'unverified' else 'feasible')
        if (self.hours_state, self.routing_state, self.travel_preference_state) != (expected_hours, expected_routing, expected_preference):
            raise ValueError('Component verdicts must agree with their evidence.')
        if self.state != _combine(self.routing_state, self.travel_preference_state, self.duration_state,
                                  self.deadline_state, self.hours_state):
            raise ValueError('Temporal verdict disagrees with component checks.')
        return self


# Import after helpers to avoid an interpretation-time cycle.
from backend.advanced_routing import AdvancedRouteCandidate, AdvancedRouter  # noqa: E402
TimedCandidate.model_rebuild()


class AdvancedTimingResult(JourneyModel):
    candidates: list[TimedCandidate] = Field(max_length=256)
    routing_status: Literal['constructed', 'unresolved', 'unsupported', 'no_candidates']
    routing_reasons: list[str]
    evaluated_at: AwareDatetime
    date: CalendarDate | None = None
    timezone: str | None = None
    timezone_basis: Literal['destination_calendar', 'browser_reported', 'unknown'] = 'unknown'
    incremental_provider_requests: Literal[0] = 0
    incremental_estimated_cost_usd: Literal[0] = 0
    execution: Literal['unavailable'] = 'unavailable'


def _combine(*states):
    return 'infeasible' if 'infeasible' in states else 'unverified' if 'unverified' in states else 'feasible'


def _limit(bounds, constraint):
    if constraint is None or constraint.relation == 'approximate':
        return 'feasible', 'no_hard_duration_limit' if constraint is None else 'soft_duration_preference'
    n = Decimal(constraint.minutes)*60
    if constraint.relation in ('maximum', 'under', 'exact'):
        exclusive = constraint.relation == 'under'
        if bounds.lower > n or exclusive and bounds.lower >= n:
            return 'infeasible', 'duration_lower_bound_exceeds_limit'
        fits = bounds.upper is not None and (bounds.upper < n or bounds.upper == n and (not exclusive or bounds.upper_exclusive))
        if constraint.relation != 'exact':
            return ('feasible', 'duration_upper_bound_fits') if fits else ('unverified', 'duration_upper_bound_unknown_or_exceeds')
    if constraint.relation in ('minimum', 'exact'):
        if bounds.upper is not None and (bounds.upper < n or bounds.upper == n and bounds.upper_exclusive):
            return 'infeasible', 'duration_upper_bound_below_requirement'
        if bounds.lower >= n and (constraint.relation != 'exact' or bounds.exact and bounds.lower == n):
            return 'feasible', 'duration_requirement_met'
    return 'unverified', 'duration_not_established'


def _project(bounds, anchor, zone):
    def clock(seconds, rounding):
        micros = int((seconds*10**6).to_integral_value(rounding=rounding))
        return (anchor.astimezone(UTC)+timedelta(microseconds=micros)).astimezone(zone)
    return Projection(offsets=bounds,
        earliest=clock(bounds.lower, ROUND_FLOOR) if anchor else None,
        latest=clock(bounds.upper, ROUND_CEILING) if anchor and bounds.upper is not None else None)


def _leg_range(leg):
    if leg.status not in ('ok', 'same_location'):
        if leg.provider != 'google_routes':
            raise ValueError('Unsupported failed-route evidence provenance.')
        return DurationRange(lower=0)
    valid = (leg.status == 'ok' and leg.provider == 'google_routes' and
             leg.estimate_type in (('walking',) if leg.mode == 'walk' else ('traffic_aware', 'traffic_unaware')) or
             leg.status == 'same_location' and leg.provider == 'local_identity' and
             leg.estimate_type == 'same_location' and leg.duration_seconds == leg.distance_meters == 0)
    if not valid:
        raise ValueError('Unsupported travel evidence provenance.')
    n = Decimal(leg.duration_nanoseconds)/10**9 if leg.duration_nanoseconds is not None else Decimal(str(leg.duration_seconds))
    return DurationRange(lower=n, upper=n)


def _visit_hours(facts, arrival, departure, evaluated_at):
    # Envelope containment proves all bounded visits fit. A failed envelope alone
    # does not prove every possible bounded visit fails.
    zone = ZoneInfo(facts.timeZone.id) if facts.timeZone else None
    stamp = facts.observedAt.get('currentOpeningHours.periods')
    request_date = stamp.astimezone(zone).date() if stamp and zone else None

    def mandatory_core_fails():
        # This remains useful with an unbounded latest departure: an explicit
        # minimum visit can already prove an opening-hours conflict.
        if arrival.latest and departure.earliest and arrival.latest.astimezone(UTC) < departure.earliest.astimezone(UTC):
            core_state, _, _ = _hours(EvidenceStop(venue=facts, arrival=arrival.latest,
                departure=departure.earliest, hours_request_date=request_date), evaluated_at)
            return core_state == 'infeasible'
        return False

    # Even an unknown dwell cannot make a known-closed exact arrival open.
    # A one-microsecond probe checks that boundary without inventing visit time.
    if arrival.offsets.exact and arrival.earliest is not None:
        state, code, _ = _hours(EvidenceStop(venue=facts, arrival=arrival.earliest,
            departure=arrival.earliest+timedelta(microseconds=1), hours_request_date=request_date), evaluated_at)
        if state == 'infeasible':return state, code
    if arrival.earliest is None or departure.latest is None:
        if mandatory_core_fails():
            return 'infeasible', 'closed_during_mandatory_visit_core'
        return 'unverified', 'missing_bounded_visit_schedule'
    if arrival.earliest.astimezone(UTC) >= departure.latest.astimezone(UTC):
        return 'unverified', 'zero_length_visit_hours_unverified'
    state, code, _ = _hours(EvidenceStop(venue=facts, arrival=arrival.earliest, departure=departure.latest,
        hours_request_date=request_date), evaluated_at)
    if state == 'infeasible' and not (arrival.offsets.exact and departure.offsets.exact):
        # Every possible visit contains this nonempty core. Its closure proves
        # failure even when the broader arrival/departure envelope is uncertain.
        if mandatory_core_fails():
            return 'infeasible', 'closed_during_mandatory_visit_core'
        return 'unverified', 'bounded_visit_hours_overlap_uncertain'
    return state, code


def _evaluate(route, index, context, evaluated_at, budget_scope='outing', hours_exceptions=frozenset()):
    reasons = []
    def reason(state, code, message, occurrence=None):
        reasons.append(TimingReason(state=state, code=code, message=message, occurrence=occurrence))
        return state
    zone = ZoneInfo(context.timezone) if context and context.timezone else None
    anchor = None
    if (context and context.date and zone and context.timezoneBasis == 'destination_calendar'
            and context.departureMinute is not None and context.departureSource):
        minute, source = explicit_departure(context.departureSource)
        if minute != context.departureMinute or source != context.departureSource:
            raise ValueError('Departure must agree with explicit source clock evidence.')
        anchor = _local_instant(context.date, minute//60, minute%60, zone)
        if anchor: anchor = anchor.astimezone(zone)
    if context and context.departureNow and context.departureInstant and zone and context.timezoneBasis == 'destination_calendar':
        anchor=context.departureInstant.astimezone(zone)
        if anchor.date()!=context.date:raise ValueError('Current departure must use the destination-local date.')
    if anchor is None:
        reason('unverified', 'missing_or_ambiguous_departure', 'An explicit departure, destination date and unambiguous local timezone are needed for clock projections.')
    travel = DurationRange(lower=0, upper=0)
    for leg in route.legs:
        travel = _plus(travel, _leg_range(leg.evidence))
    elapsed = DurationRange(lower=0, upper=0)
    dwell = DurationRange(lower=0, upper=0)
    visits = []
    for visit in route.visits:
        incoming = next((l for l in route.legs if l.to_occurrence == visit.occurrence), None)
        if incoming: elapsed = _plus(elapsed, _leg_range(incoming.evidence))
        arrival = _project(elapsed, anchor, zone)
        duration = _bounds(visit.requested.duration)
        dwell = _plus(dwell, duration)
        elapsed = _plus(elapsed, duration)
        departure = _project(elapsed, anchor, zone)
        facts = visit.selected.facts
        state, code = _visit_hours(facts, arrival, departure, evaluated_at)
        exception=(index,visit.occurrence,visit.selected.place_id) in hours_exceptions and state=='infeasible' and visit.requested.kind=='named_place' and visit.requested.requirement=='required'
        reason('unverified' if exception else state, 'user_closed_visit' if exception else code,
            'Closed at the planned visit time. Included at your request; access is not confirmed.' if exception else
            'Current dated hours cover the visit bounds; sessions, inventory and reservations remain unverified.' if state == 'feasible' else
            'Current dated hours prove this visit conflicts with opening periods.' if state == 'infeasible' else
            'Visit hours need applicable current periods, venue timezone and a bounded arrival/departure schedule.', visit.occurrence)
        if duration.upper is None:
            reason('unverified', 'unbounded_dwell', 'Supply an exact visit duration or a justified upper bound to establish completion time.', visit.occurrence)
        visits.append(TimedVisit(occurrence=visit.occurrence, place_id=visit.selected.place_id,
            dwell_constraint=visit.requested.duration, dwell=duration, arrival=arrival, departure=departure,
            hours_state=state, hours_exception=exception, hours_code=code, hours_observed_at=facts.observedAt.get('currentOpeningHours.periods'),
            hours_timezone=facts.timeZone.id if facts.timeZone else None,
            special_day=bool(facts.currentOpeningHours and anchor and facts.timeZone and
                arrival.earliest and arrival.earliest.astimezone(ZoneInfo(facts.timeZone.id)).date() in (facts.currentOpeningHours.specialDays or []))))
    # Explicit final endpoint is an arrival obligation, with no invented visit dwell.
    elapsed = _plus(travel, dwell)
    finish = _project(elapsed, anchor, zone)
    duration_state, code = _limit(travel if budget_scope=='travel' else elapsed, route.journey.total_duration)
    reason(duration_state, code, 'Travel-only budget includes every selected travel leg and excludes visit time; independent finish deadlines still include visits.' if budget_scope=='travel' else 'Whole-trip time includes every selected travel leg and explicit dwell bound; approximate durations are soft preferences.')
    deadline = None
    deadline_state = 'feasible'
    if route.journey.deadline:
        d = route.journey.deadline
        day = context.date if context else None
        # Explicit ISO date / following-day wording is supported without silently
        # rolling an earlier clock to tomorrow. Other date grammar stays unresolved.
        from backend.date_resolution import DATE_WORDING
        dates = list(DATE_WORDING.finditer(d.source))
        if dates:
            day = CalendarDate.fromisoformat(dates[0][0]) if len(dates) == 1 and re.fullmatch(r'\d{4}-\d{2}-\d{2}', dates[0][0]) else None
        elif day and re.search(r'\b(?:next|following) day\b', d.source, re.I):
            day += timedelta(days=1)
        if day and zone and d.minute is not None:
            deadline = _local_instant(day, d.minute//60, d.minute%60, zone)
            if deadline: deadline = deadline.astimezone(zone)
        if anchor is None or deadline is None:
            deadline_state = reason('unverified', 'deadline_missing_anchor_or_calendar', 'Deadline needs a validated departure, date and destination-local timezone.')
        elif deadline.astimezone(UTC) < anchor.astimezone(UTC) and not dates and day == context.date:
            deadline_state = reason('unverified', 'clarify_overnight_deadline', 'The deadline clock precedes departure; clarify its date rather than assuming tomorrow.')
        else:
            delta = deadline.astimezone(UTC)-anchor.astimezone(UTC)
            available = Decimal(delta.days*86400+delta.seconds)+Decimal(delta.microseconds)/10**6
            exclusive = d.relation == 'before'
            fail = elapsed.lower > available or exclusive and elapsed.lower >= available
            fits = elapsed.upper is not None and (elapsed.upper < available or elapsed.upper == available and (not exclusive or elapsed.upper_exclusive))
            deadline_state = reason('infeasible' if fail else 'feasible' if fits else 'unverified',
                'deadline_proven_impossible' if fail else 'deadline_bounds_fit' if fits else 'deadline_completion_unknown',
                'Deadline compares full journey elapsed seconds with the explicit destination-local clock, including the final leg.')
    routing_state = 'infeasible' if any(l.evidence.status == 'unreachable' for l in route.legs) else 'unverified' if route.missing_leg_indexes else 'feasible'
    preference = 'infeasible' if route.route_status == 'beyond_limit' else 'unverified' if route.route_status == 'unverified' else 'feasible'
    hours = _combine(*('unverified' if v.hours_exception else v.hours_state for v in visits))
    if route.endpoint:
        # Endpoint arrival is preserved, but opening for an actual endpoint visit
        # cannot be established without endpoint service/visit-duration semantics.
        hours = _combine(hours, reason('unverified', 'endpoint_visit_hours_unspecified', 'Named endpoint arrival is projected; its service and visit hours are not established.'))
    reason(routing_state, 'route_evidence_'+routing_state, 'Routing evidence remains distinct from temporal feasibility.')
    reason(preference, 'travel_preferences_'+preference, 'Original scoped travel checks are retained without relaxation.')
    return TimedCandidate(route=route, candidate_index=index, known_travel_seconds=travel.lower,
        travel=travel, dwell=dwell, elapsed=elapsed, start=anchor,
        start_source=context.departureSource if context else None, deadline=deadline, finish=finish,
        visits=visits, routing_state=routing_state, travel_preference_state=preference,
        budget_scope=budget_scope,duration_state=duration_state, deadline_state=deadline_state, hours_state=hours,
        state=_combine(routing_state, preference, duration_state, deadline_state, hours), reasons=reasons)


def evaluate_advanced_timing(router: AdvancedRouter, *, evaluated_at: datetime, dwell_answers=None, departure_minute=None, budget_scope='outing', allow_overrides=False, hours_exceptions=frozenset()) -> AdvancedTimingResult:
    """Consume only an active backend router, rechecking authorization and expiry.

    No client evidence input. Evaluates up to three existing routes of four stops;
    does not resolve, route, reorder, drop optional stops, save or call the model.
    """
    if not isinstance(router, AdvancedRouter):
        raise TypeError('A server-owned AdvancedRouter is required.')
    if not isinstance(evaluated_at, datetime) or evaluated_at.tzinfo is None or evaluated_at.utcoffset() is None:
        raise ValueError('An aware evaluation clock is required.')
    if budget_scope not in ('outing','travel'):raise ValueError('Choose a supported budget scope.')
    result = router.timing_snapshot()
    # Only app-owned duration/departure answers amend a copy of trusted routes.
    # Identity, routing, topology and provider evidence stay in the original session.
    if dwell_answers:
        for route in result.candidates:
            journey = route.journey.model_copy(deep=True)
            for occurrence, duration in dwell_answers.items():
                if type(occurrence) is not int or not 0 <= occurrence < len(journey.stops) or journey.stops[occurrence].duration is not None and not allow_overrides:
                    raise ValueError('Only missing occurrence durations can be clarified.')
                journey.stops[occurrence].duration = Duration.model_validate(duration.model_dump())
            route.journey = journey
            for visit in route.visits:
                visit.requested = journey.stops[visit.occurrence]
            for omission in route.omitted:
                omission.requested = journey.stops[omission.occurrence]
            AdvancedRouteCandidate.model_validate(route.model_dump())
    if departure_minute is not None:
        if type(departure_minute) is not int or not 0 <= departure_minute < 1440 or result.context is None or result.context.departureMinute is not None and not allow_overrides:
            raise ValueError('Only a missing explicit departure can be clarified.')
        result.context.departureNow = False
        result.context.departureInstant = None
        result.context.departureMinute = departure_minute
        result.context.departureSource = f'depart at {departure_minute//60:02d}:{departure_minute%60:02d}'
    return AdvancedTimingResult(candidates=[_evaluate(route, i, result.context, evaluated_at,budget_scope,hours_exceptions)
        for i, route in enumerate(result.candidates)], routing_status=result.status,
        routing_reasons=result.reasons, evaluated_at=evaluated_at,
        date=result.context.date if result.context else None, timezone=result.timezone,
        timezone_basis=result.context.timezoneBasis if result.context else 'unknown')
