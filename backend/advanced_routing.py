"""Task 50C: bounded backend-only route construction, never temporal feasibility.

Consumes a live server-owned StopResolver. No public DTO, persistence, discovery,
interpretation, geocoding, retry, or new production capability switch.
"""
from itertools import combinations
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from backend.journey import Journey, JourneyModel, RequestedStop
from backend.interpretation import InterpretationContext
from backend.location_policy import FirstTravel, exceeds, first_measure, effective_max
from backend.routes import (AuthorizedStart, DirectedRouteRequest, GoogleRouteCalculator,
                            Mode, RouteError, RouteLeg, RoutePoint)
from backend.stop_resolution import ResolvedCandidate, StopResolver
from backend.venue_geography import distance_m

MAX_STOPS = 4
POOL_WIDTH = 4
BEAM_WIDTH = 24
MAX_ELEMENTS = 27


def _ancestors(journey):
    ancestors = {i: set() for i in range(len(journey.stops))}
    for edge in journey.order:
        ancestors[edge.after].add(edge.before)
    for _ in journey.stops:
        for i in ancestors:
            if ancestors[i]:
                ancestors[i] |= set().union(*(ancestors[j] for j in list(ancestors[i])))
    return ancestors


class Visit(JourneyModel):
    occurrence: int = Field(strict=True, ge=0, lt=MAX_STOPS)
    requested: RequestedStop
    selected: ResolvedCandidate
    visit_order: int = Field(strict=True, ge=0, lt=MAX_STOPS)
    optional_included: bool


class OmittedStop(JourneyModel):
    occurrence: int = Field(strict=True, ge=0, lt=MAX_STOPS)
    requested: RequestedStop
    reason: Literal['identity_unavailable', 'known_closed', 'routing_cost_or_applicability']


class AdvancedLeg(JourneyModel):
    role: Literal['origin_to_first', 'inter_activity', 'return_to_origin', 'final_destination']
    from_occurrence: int | None = None
    to_occurrence: int | None = None
    evidence: RouteLeg


class TravelCheck(JourneyModel):
    leg_index: int
    preference: FirstTravel
    state: Literal['matching', 'outside_preference', 'beyond_limit', 'unknown']
    actual: float | None = None
    preferred: float
    maximum: float
    excess_over_preferred: float | None = None
    excess_over_maximum: float | None = None


class TotalBetweenCheck(JourneyModel):
    maximum_minutes: int = Field(strict=True, ge=0, le=1440)
    exclusive: bool = False
    state: Literal['matching', 'beyond_limit', 'unknown']
    known_seconds: float = Field(ge=0)
    total_seconds: float | None = Field(default=None, ge=0)


class OriginEvidence(JourneyModel):
    source: Literal['device', 'manual', 'suggested', 'mock']
    precision: Literal['device', 'address_or_place', 'postal_area', 'neighborhood', 'city', 'approximate_area']
    explicitly_authorized: Literal[True] = True


class AdvancedRouteCandidate(JourneyModel):
    journey: Journey
    visits: list[Visit] = Field(min_length=1, max_length=MAX_STOPS)
    omitted: list[OmittedStop] = Field(max_length=MAX_STOPS)
    endpoint: ResolvedCandidate | None = None
    origin_status: Literal['confirmed', 'not_supplied']
    origin: OriginEvidence | None = None
    ending: Literal['last_activity', 'origin', 'named_destination']
    mode: Mode
    legs: list[AdvancedLeg] = Field(max_length=MAX_STOPS + 1)
    checks: list[TravelCheck]
    between_total_check: TotalBetweenCheck | None = None
    route_status: Literal['verified', 'unverified', 'beyond_limit']
    known_travel_seconds: float = Field(ge=0)
    known_distance_meters: int = Field(ge=0)
    travel_total_seconds: float | None = Field(default=None, ge=0)
    missing_leg_indexes: list[int]
    temporal_status: Literal['not_evaluated'] = 'not_evaluated'
    execution: Literal['unavailable'] = 'unavailable'

    @model_validator(mode='after')
    def coherent(self):
        indexes = [v.occurrence for v in self.visits]
        omitted = [o.occurrence for o in self.omitted]
        if (len(indexes + omitted) != len(self.journey.stops)
                or len(set(indexes + omitted)) != len(self.journey.stops)
                or set(indexes + omitted) != set(range(len(self.journey.stops)))
                or [v.visit_order for v in self.visits] != list(range(len(self.visits)))):
            raise ValueError('Every original occurrence must be visited once or explicitly omitted.')
        for v in self.visits:
            if v.requested != self.journey.stops[v.occurrence]:
                raise ValueError('Original occurrence changed.')
            if v.optional_included != (v.requested.requirement == 'optional'):
                raise ValueError('Optionality changed.')
            if v.requested.kind == 'named_place' and v.selected.eligibility != 'identity_verified':
                raise ValueError('Named identity must be verified.')
        for o in self.omitted:
            if o.requested != self.journey.stops[o.occurrence] or o.requested.requirement != 'optional':
                raise ValueError('Required stops cannot be omitted.')
        if self.journey.order_conflict:
            raise ValueError('Conflicting precedence cannot produce a route.')
        positions = {n: i for i, n in enumerate(indexes)}
        if any(positions[before] >= positions[after] for after, parents in _ancestors(self.journey).items()
               for before in parents if before in positions and after in positions):
            raise ValueError('Precedence violation.')
        points = [v.selected.place_id for v in self.visits]
        if len(set(points)) != len(points):
            raise ValueError('Repeated venue identities are prohibited.')
        if (self.origin is not None) != (self.origin_status == 'confirmed'):
            raise ValueError('Origin evidence must agree with its status.')
        if self.journey.endpoint:
            if self.ending == 'last_activity' or (self.journey.endpoint.kind == 'origin' and self.ending != 'origin'):
                raise ValueError('Required endpoint cannot be omitted.')
        elif self.ending != 'last_activity':
            raise ValueError('An endpoint cannot be invented.')
        if self.journey.endpoint and self.journey.endpoint.kind not in ('origin', 'home') and self.ending != 'named_destination':
            raise ValueError('A named endpoint cannot become a return to origin.')
        if self.endpoint and self.endpoint.eligibility != 'identity_verified':
            raise ValueError('Final identity must be verified.')
        if self.ending == 'origin' and (self.origin is None or self.endpoint is not None):
            raise ValueError('Return requires a distinct confirmed origin role.')
        if (self.endpoint is not None) != (self.ending == 'named_destination'):
            raise ValueError('Named ending requires verified endpoint identity.')
        expected = [('inter_activity', i, j, a, b) for i, j, a, b in zip(indexes, indexes[1:], points, points[1:])]
        if self.origin_status == 'confirmed':
            expected.insert(0, ('origin_to_first', None, indexes[0], 'advanced_origin', points[0]))
        if self.ending == 'origin':
            expected.append(('return_to_origin', indexes[-1], None, points[-1], 'advanced_origin'))
        elif self.endpoint:
            expected.append(('final_destination', indexes[-1], None, points[-1], self.endpoint.place_id))
        if [(l.role, l.from_occurrence, l.to_occurrence, l.evidence.origin_id, l.evidence.destination_id) for l in self.legs] != expected:
            raise ValueError('Incomplete route topology.')
        if any(l.evidence.mode != self.mode for l in self.legs):
            raise ValueError('Cross-mode evidence is prohibited.')
        checked = set()
        for check in self.checks:
            if check.leg_index in checked or not 0 <= check.leg_index < len(self.legs):
                raise ValueError('Travel checks need distinct valid leg indexes.')
            checked.add(check.leg_index)
            leg = self.legs[check.leg_index]
            if leg.role not in ('origin_to_first', 'inter_activity') or check != _check(check.leg_index, leg.evidence, check.preference):
                raise ValueError('Travel checks must agree with scoped directional evidence.')
        missing = [i for i, l in enumerate(self.legs) if l.evidence.status not in ('ok', 'same_location')]
        known = sum(l.evidence.duration_seconds for l in self.legs if l.evidence.duration_seconds is not None)
        distance = sum(l.evidence.distance_meters for l in self.legs if l.evidence.distance_meters is not None)
        if self.between_total_check and self.between_total_check != _total_check(self.legs, self.between_total_check.maximum_minutes, self.between_total_check.exclusive):
            raise ValueError('Total between-stop check must agree with inter-activity evidence.')
        state = ('beyond_limit' if any(c.state == 'beyond_limit' for c in self.checks) or self.between_total_check and self.between_total_check.state == 'beyond_limit' else
                 'unverified' if missing or any(c.state == 'unknown' for c in self.checks) else 'verified')
        if (self.missing_leg_indexes != missing or self.known_travel_seconds != known
                or self.known_distance_meters != distance or self.route_status != state
                or self.travel_total_seconds != (None if missing else known)):
            raise ValueError('Route totals/status must agree with actual evidence.')
        return self


class HoursExclusion(JourneyModel):
    occurrence: int
    candidate: ResolvedCandidate
    date: str
    timezone: str
    status: Literal['closed'] = 'closed'
    reason: str


class AdvancedRoutingResult(JourneyModel):
    journey: Journey
    status: Literal['constructed', 'unresolved', 'unsupported', 'no_candidates']
    candidates: list[AdvancedRouteCandidate] = Field(default_factory=list, max_length=3)
    reasons: list[str] = Field(default_factory=list)
    hours_exclusions: list[HoursExclusion] = Field(default_factory=list)
    context: InterpretationContext | None = Field(default=None, exclude=True, repr=False)
    # Only public calendar/preference metadata. Private origin/home text is absent.
    date: str | None = None
    timezone: str | None = None
    matrix_elements: int = Field(default=0, ge=0, le=MAX_ELEMENTS)
    matrix_requests: int = Field(default=0, ge=0)
    considered_paths: int = 0
    admitted_paths: int = 0
    coverage: Literal['bounded_shortlist'] = 'bounded_shortlist'
    temporal_status: Literal['not_evaluated'] = 'not_evaluated'
    execution: Literal['unavailable'] = 'unavailable'


def _signature(path):
    return tuple((i, c.place_id) for i, c in path)


def _shortlist(resolved, origin, endpoint, pool_width=POOL_WIDTH):
    """Precedence-aware beam; geographic gaps only prune, never verify travel."""
    journey = resolved.journey
    ancestors = _ancestors(journey)
    optional = [s.occurrence for s in resolved.stops if s.requested.requirement == 'optional']
    required = {s.occurrence for s in resolved.stops if s.requested.requirement == 'required'}
    paths = []
    for count in range(len(optional) + 1):
        for subset in combinations(optional, count):
            included = required | set(subset)
            if not included:
                continue
            beam = [()]
            for _ in included:
                expanded = []
                for path in beam:
                    visited = {i for i, _ in path}
                    available = sorted(included - visited)
                    if journey.ordering == 'unspecified':
                        available = available[:1]  # Source order is retained without claiming optimization intent.
                    for i in available:
                        if not (ancestors[i] & included) <= visited:
                            continue
                        group = resolved.stops[i]
                        if group.status not in ('resolved', 'candidates'):
                            continue
                        for candidate in group.candidates[:pool_width]:
                            if any(c.place_id == candidate.place_id for _, c in path):
                                continue
                            extended = path + ((i, candidate),)
                            shared = journey.shared_place
                            if shared:
                                members = [c for n, c in extended if n in shared.stops]
                                if members and not set.intersection(*[{p.id for p in c.facts.containingPlaces or []} for c in members]):
                                    continue
                            expanded.append(extended)
                beam = sorted(expanded, key=lambda p: (_gap(p, origin, endpoint), _signature(p)))[:BEAM_WIDTH]
            paths.extend(beam)
    # Keep a balanced finite slice across optional-inclusion patterns and first venues.
    paths.sort(key=lambda p: (_gap(p, origin, endpoint), _signature(p)))
    unique = {}
    for path in paths:
        unique.setdefault(tuple(c.place_id for _, c in path), path)
    paths = list(unique.values())
    selected, usage = [], {}
    while paths and len(selected) < BEAM_WIDTH:
        path = min(paths, key=lambda p: (usage.get((tuple(i for i, _ in p), p[0][1].place_id), 0),
                                         _gap(p, origin, endpoint), _signature(p)))
        paths.remove(path)
        selected.append(path)
        key = (tuple(i for i, _ in path), path[0][1].place_id)
        usage[key] = usage.get(key, 0) + 1
    return selected


def _gap(path, origin, endpoint):
    coords = [c.facts.coordinates for _, c in path]
    if origin and (origin.reference_coordinates or origin.point.coordinates):
        coords.insert(0, origin.reference_coordinates or origin.point.coordinates)
    if endpoint and endpoint.coordinates:
        coords.append(endpoint.coordinates)
    return sum(distance_m(a, b) for a, b in zip(coords, coords[1:]))


def _topology(path, origin, endpoint, returning):
    points = [(i, RoutePoint.from_venue(c.facts)) for i, c in path]
    legs = [('inter_activity', i, j, a, b) for (i, a), (j, b) in zip(points, points[1:])]
    if origin:
        # A private provider ID or coordinate reference never appears in output IDs.
        start = origin.point.model_copy(update={'id': 'advanced_origin'})
        legs.insert(0, ('origin_to_first', None, points[0][0], start, points[0][1]))
    if returning:
        legs.append(('return_to_origin', points[-1][0], None, points[-1][1], start))
    elif endpoint:
        legs.append(('final_destination', points[-1][0], None, points[-1][1], RoutePoint.from_venue(endpoint)))
    return legs


def _check(index, leg, preference):
    actual = first_measure(leg, preference)
    state = ('unknown' if actual is None else 'beyond_limit' if exceeds(leg, preference) else
             'outside_preference' if exceeds(leg, preference, original=True) else 'matching')
    value = float(actual) if actual is not None else None
    return TravelCheck(leg_index=index, preference=preference.model_copy(update={'originText': None}), state=state,
                       actual=value, preferred=preference.value, maximum=effective_max(preference),
                       excess_over_preferred=None if value is None else max(0, value - preference.value),
                       excess_over_maximum=None if value is None else max(0, value - effective_max(preference)))


def _total_check(legs, maximum, exclusive):
    selected = [l.evidence for l in legs if l.role == 'inter_activity']
    known = sum((Decimal(l.duration_nanoseconds) / 10**9 if l.duration_nanoseconds is not None else
                 Decimal(str(l.duration_seconds)) for l in selected if l.duration_seconds is not None), Decimal(0))
    missing = any(l.status not in ('ok', 'same_location') for l in selected)
    limit = Decimal(maximum) * 60
    violated = known > limit or exclusive and known >= limit
    return TotalBetweenCheck(maximum_minutes=maximum, exclusive=exclusive,
        state='beyond_limit' if violated else 'unknown' if missing else 'matching',
        known_seconds=float(known), total_seconds=None if missing else float(known))


class AdvancedRouter:
    """One active computation, one Matrix admission, no duplicate directed pairs.

    Input authority is the server resolver, not serialized client candidate facts.
    Uses its *same* outing budget. Repeated calls reuse the active result only.
    """
    def __init__(self, resolver: StopResolver):
        if not isinstance(resolver, StopResolver):
            raise TypeError('A server-owned StopResolver is required.')
        self.resolver = resolver
        self._result = None
        self._arguments = None

    def plan(self, *, origin: AuthorizedStart | None = None, allow_beyond_limit: bool = False):
        resolved = self.resolver.routing_snapshot()
        if type(allow_beyond_limit) is not bool:
            raise ValueError('Beyond-limit opt-in must be explicit.')
        if origin:
            origin = AuthorizedStart.model_validate(origin.model_dump())
        arguments = (resolved.model_dump_json(), origin.model_dump_json() if origin else None, allow_beyond_limit)
        if self._result is not None:
            if arguments != self._arguments:
                raise RouteError('computation_used', 'Start a separate computation for changed routing inputs.')
            return self._result.model_copy(deep=True)
        result = self._plan(resolved, origin, allow_beyond_limit)
        self._arguments, self._result = arguments, result
        return result.model_copy(deep=True)

    def _plan(self, resolved, origin, allow_beyond_limit):
        journey, context = resolved.journey, resolved.context
        exclusions = []
        metadata = dict(journey=journey, date=str(context.date) if context and context.date else None,
                        timezone=context.timezone if context else None, context=context, hours_exclusions=exclusions)
        def blocked(status, reason):
            return AdvancedRoutingResult(status=status, reasons=[reason], **metadata)
        if not 1 <= len(journey.stops) <= MAX_STOPS:
            return blocked('unsupported', 'Advanced routing supports one to four stop occurrences.')
        if journey.order_conflict or journey.clarification or context and context.issues:
            return blocked('unresolved', 'Journey constraints require clarification.')
        if len(resolved.stops) != len(journey.stops) or any(s.occurrence != i or s.requested != journey.stops[i] for i, s in enumerate(resolved.stops)):
            return blocked('unresolved', 'Resolved occurrences do not match the original request.')
        for stop in resolved.stops:
            if stop.requested.requirement == 'required' and (stop.status not in ('resolved', 'candidates') or not stop.candidates):
                return blocked('unresolved', 'A required stop identity is unresolved.')
            if stop.requested.kind == 'named_place' and stop.requested.requirement == 'required' and (stop.status != 'resolved' or len(stop.candidates) != 1 or stop.candidates[0].eligibility != 'identity_verified'):
                return blocked('unresolved', 'A named stop needs one verified identity.')
        returning = bool(journey.endpoint and (journey.endpoint.kind == 'origin' or
                         journey.endpoint.kind == 'home' and context and context.endpointStatus == 'origin_confirmed'))
        endpoint = None
        if journey.endpoint and not returning:
            end = resolved.endpoint
            if journey.endpoint.kind == 'home' or not end or end.status != 'resolved' or len(end.candidates) != 1:
                return blocked('unresolved', 'The final destination needs verified identity or clarification.')
            endpoint = end.candidates[0]
            if endpoint.eligibility != 'identity_verified':
                return blocked('unresolved', 'The final destination needs one verified identity.')
        if not origin and (returning or context and (context.firstTravel or context.originText)):
            return blocked('unresolved', 'A confirmed origin is required, separately from route-provider evidence.')
        # Other resolver constraints (e.g. same-mall failure) cannot be discarded.
        return_notes = {'Explicit return to the starting point requires Task 50C routing.',
                        'Return to the confirmed origin requires Task 50C routing.'}
        if any(reason not in return_notes for reason in resolved.unresolved_constraints):
            return blocked('unresolved', 'A resolved journey relationship remains unverified.')
        mode = context.transport.value if context and context.transport else 'driving'
        if mode not in ('driving', 'walking'):
            return blocked('unsupported', 'Only Driving and Walking are supported.')
        mode = 'walk' if mode == 'walking' else 'drive'
        endpoint_facts = endpoint.facts if endpoint else None
        finish = endpoint_facts or (origin if returning else None)
        # Gap helper only receives coordinate-bearing facts, never treats them as routes.
        if returning:
            from types import SimpleNamespace
            finish = SimpleNamespace(coordinates=origin.reference_coordinates or origin.point.coordinates)
        # Reuse only the existing conservative whole-date exclusion. No assumed
        # start, arrival, dwell, deadline evaluation, or operational-status shortcut.
        if context and context.date and context.timezone:
            from backend.planning_hours import venue_hours
            for group in resolved.stops + ([resolved.endpoint] if resolved.endpoint else []):
                retained = []
                for candidate in group.candidates:
                    hours = venue_hours(candidate.facts, context.date, calendar_timezone=context.timezone)
                    if hours['status'] == 'closed':
                        exclusions.append(HoursExclusion(occurrence=group.occurrence, candidate=candidate,
                            date=str(context.date), timezone=context.timezone, reason=hours['message']))
                    else:
                        retained.append(candidate)
                group.candidates = retained
                if not retained and group.requested.requirement == 'required':
                    return blocked('no_candidates', 'Verified current hours exclude a required stop throughout the requested date.')
        paths = _shortlist(resolved, origin, finish, min(POOL_WIDTH, self.resolver.outing.settings.candidates_per_activity))
        selected, pairs = [], {}
        for path in paths:
            topology = _topology(path, origin, endpoint_facts, returning)
            added = {(a.id, b.id): (a, b) for _, _, _, a, b in topology}
            union = pairs | added
            if len(union) <= MAX_ELEMENTS:
                selected.append((path, topology))
                pairs = union
        if not selected:
            return blocked('no_candidates', 'No distinct verified venue assignment satisfies the required stops and ordering.')
        try:
            routed = GoogleRouteCalculator(self.resolver.outing).calculate_directed(
                DirectedRouteRequest(pairs=list(pairs.values()), mode=mode))
            evidence = {(l.origin_id, l.destination_id): l for l in routed.legs}
            elements, requests = routed.matrix_elements, routed.matrix_requests
        except RouteError as error:
            # Admission rejection has no fabricated metrics or retry. Transport partials
            # are already returned by the shared calculator, preserving valid cells.
            evidence = {(a.id, b.id): RouteLeg(origin_id=a.id, destination_id=b.id, mode=mode,
                        status='unknown', estimate_type='walking' if mode == 'walk' else 'traffic_unaware',
                        error_code=error.code) for a, b in pairs.values()}
            elements = requests = 0
        options = []
        for path, topology in selected:
            legs = [AdvancedLeg(role=role, from_occurrence=i, to_occurrence=j, evidence=evidence[a.id, b.id])
                    for role, i, j, a, b in topology]
            checks = []
            for index, leg in enumerate(legs):
                preference = (context.firstTravel if leg.role == 'origin_to_first' else
                              (context.betweenTravel or (FirstTravel(value=float(context.maxLegTravel), exclusive=context.maxLegTravelExclusive)
                               if context.maxLegTravel is not None else None)) if leg.role == 'inter_activity' else None) if context else None
                if preference:
                    checks.append(_check(index, leg.evidence, preference))
            missing = [i for i, l in enumerate(legs) if l.evidence.status not in ('ok', 'same_location')]
            total_check = _total_check(legs, context.travel, context.travelExclusive) if context and context.travel is not None else None
            state = 'beyond_limit' if any(c.state == 'beyond_limit' for c in checks) or total_check and total_check.state == 'beyond_limit' else 'unverified' if missing else 'verified'
            known = sum(l.evidence.duration_seconds for l in legs if l.evidence.duration_seconds is not None)
            seen = {i for i, _ in path}
            option = AdvancedRouteCandidate(journey=journey, visits=[Visit(occurrence=i, requested=journey.stops[i],
                selected=c, visit_order=n, optional_included=journey.stops[i].requirement == 'optional') for n, (i, c) in enumerate(path)],
                omitted=[OmittedStop(occurrence=s.occurrence, requested=s.requested,
                    reason='known_closed' if not s.candidates and any(e.occurrence == s.occurrence for e in exclusions) else
                    'identity_unavailable' if not s.candidates or s.status not in ('resolved', 'candidates') else 'routing_cost_or_applicability')
                    for s in resolved.stops if s.occurrence not in seen], endpoint=endpoint,
                origin_status='confirmed' if origin else 'not_supplied',
                origin=OriginEvidence(source=origin.source, precision=origin.precision) if origin else None,
                ending='origin' if returning else 'named_destination' if endpoint else 'last_activity',
                mode=mode, legs=legs, checks=checks, between_total_check=total_check,
                route_status=state, known_travel_seconds=known,
                known_distance_meters=sum(l.evidence.distance_meters for l in legs if l.evidence.distance_meters is not None),
                travel_total_seconds=None if missing else known, missing_leg_indexes=missing)
            if state != 'beyond_limit' or allow_beyond_limit:
                options.append(option)
        def score(option):
            return (option.route_status != 'verified', option.route_status == 'beyond_limit', len(option.missing_leg_indexes),
                    sum(c.state == 'outside_preference' for c in option.checks),
                    option.travel_total_seconds if option.travel_total_seconds is not None else float('inf'),
                    -sum(v.selected.facts.rating or 0 for v in option.visits),
                    tuple((v.occurrence, v.selected.place_id) for v in option.visits))
        options.sort(key=score)
        # Travel is primary; comparable options prefer different actual venue sets.
        chosen = []
        while options and len(chosen) < 3:
            best = options[0]
            near = [o for o in options if score(o)[:4] == score(best)[:4] and
                    o.known_travel_seconds <= best.known_travel_seconds + 60]
            pick = min(near, key=lambda o: (sum(v.selected.place_id == w.selected.place_id for p in chosen for v in o.visits for w in p.visits), score(o)))
            chosen.append(pick)
            options.remove(pick)
        return AdvancedRoutingResult(status='constructed' if chosen else 'no_candidates', candidates=chosen,
            reasons=[] if chosen else ['All checked routes exceed a hard travel limit.'],
            matrix_elements=elements, matrix_requests=requests,
            considered_paths=len(paths), admitted_paths=len(selected), **metadata)
