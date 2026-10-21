"""Task 27: evaluate Task 26 candidates before deterministic ranking.

All default quotes are fictional. No I/O beyond the shared candidate loader,
external routing, parsing of free-form hours, or frontend integration occurs.
"""
from collections import Counter
from collections.abc import Callable, Iterable
from decimal import Decimal

from backend.models import (
    CandidateItinerary, ConstraintIssue, DataStatus, OutingRequest, PlannedStop,
    PlanningError, PriceQuote, RankedItinerary, RankingResult, RecommendationReason,
    ScheduledEvent, TimeWindow, TravelQuote, Venue,
)
from backend.planner import generate_candidates, supports_location

PriceProvider = Callable[[Venue, OutingRequest], PriceQuote]
TravelProvider = Callable[[Venue, Venue, OutingRequest], TravelQuote]


def mock_price(venue: Venue, request: OutingRequest) -> PriceQuote:
    return PriceQuote(amount=venue.price, status=venue.dataQuality.price, source=venue.source)


def simulated_travel(a: Venue, b: Venue, request: OutingRequest) -> TravelQuote:
    """Same invented zone convention as TypeScript; transport-independent."""
    minutes = None if a.zone is None or b.zone is None else 5 + abs(a.zone - b.zone) * 8
    return TravelQuote(minutes=minutes, status=DataStatus.fictional,
                       source="Fictional zone simulation: 5 + abs(zone difference) * 8; no real route")


def _windows(windows: list[TimeWindow] | None, request: OutingRequest):
    if windows is None:
        return None
    # A date-specific schedule cannot establish feasibility on a flexible day.
    if request.date is None and any(w.date is not None for w in windows):
        return None
    return [(w.start, w.end) for w in windows if w.date is None or w.date == request.date]


def evaluate_candidate(
    request: OutingRequest, candidate: CandidateItinerary, *,
    price_provider: PriceProvider = mock_price,
    travel_provider: TravelProvider = simulated_travel,
) -> RankedItinerary:
    """Keep violations and missing evidence separate; never fill missing facts.

    Known lower bounds can still prove a violation when a total is incomplete.
    Earliest-finish scheduling is sufficient for ordered stops, fixed events,
    and single-day windows: waiting later never makes a later stop easier.
    """
    venues = candidate.venues
    issues = []

    def issue(code, field, message, venue=None, unknown=False):
        issues.append(ConstraintIssue(code=code, field=field, message=message,
                                      venueId=venue.id if venue else None,
                                      status="unknown" if unknown else "violation"))

    if not supports_location(request.location):
        issue("unsupported_location", "location", "The fictional catalog only covers Baltimore; choose Baltimore.")
    if ([v.activity for v in venues] != request.activities
            or candidate.people != request.people or candidate.date != request.date
            or candidate.allowRevisits != request.allowRevisits):
        issue("request_mismatch", "activities", "Candidate must preserve activities, order, date, group and revisit permission.")
    prices = [price_provider(v, request) for v in venues]
    legs = [travel_provider(a, b, request) for a, b in zip(venues, venues[1:])]
    # Decimal arithmetic keeps inclusive dollar limits correct (e.g. 0.1 + 0.2).
    known = sum((Decimal(str(q.amount)) for q in prices if q.amount is not None), Decimal(0))
    cost = known if all(q.amount is not None for q in prices) else None
    for field, limit, total in (("budget", request.budget, known),
                                 ("groupBudget", request.groupBudget, known * request.people)):
        if limit is not None and total > Decimal(str(limit)):
            issue("budget_exceeded", field, f"Known activity costs exceed {field}; increase the cap or choose cheaper activities.")
    for v, quote in zip(venues, prices):
        if quote.amount is None or quote.status == DataStatus.unknown:
            issue("unknown_price", "budget", "Price is incomplete or unsourced; obtain a price before confirming costs.", v, True)
    for v in venues:
        if v.capacity is None or v.dataQuality.capacity == DataStatus.unknown:
            issue("unknown_capacity", "people", "Obtain group capacity before confirming this stop.", v, True)
        if v.capacity is not None and v.capacity < request.people:
            issue("capacity_exceeded", "people", f"{v.name} cannot fit {request.people} people; reduce the group or change activities.", v)
        if isinstance(v, ScheduledEvent) and v.eventDate != request.date:
            issue("event_date", "date", "Scheduled event date differs from the outing; choose a matching fixture date.", v)
    for leg in legs:
        if leg.minutes is None or leg.status == DataStatus.unknown:
            issue("unknown_travel", "travel", "Travel evidence is missing; obtain a travel estimate before confirming timing.", unknown=True)
        if request.maxLegTravel is not None and leg.minutes is not None and leg.minutes > request.maxLegTravel:
            issue("leg_travel_exceeded", "maxLegTravel", "A leg exceeds the travel cap; increase it or choose closer stops.")
    known_travel = sum(q.minutes for q in legs if q.minutes is not None)
    travel = known_travel if all(q.minutes is not None for q in legs) else None
    if request.travel is not None and known_travel > request.travel:
        issue("total_travel_exceeded", "travel", "Total inter-stop travel exceeds the cap; allow more travel or fewer/closer activities.")

    stops = []
    earliest = request.startTime
    exact = True
    for i, v in enumerate(venues):
        if i:
            leg = legs[i - 1]
            earliest += leg.minutes or 0
            exact = exact and leg.minutes is not None
        if (i in request.dinnerStops if request.dinnerStops is not None else request.dinner and v.activity == "food"):
            earliest = max(earliest, 17 * 60)
        duration = v.duration
        if duration is None or v.dataQuality.duration == DataStatus.unknown:
            issue("unknown_duration", "duration", "Obtain the activity duration before confirming the schedule.", v, True)
        minimum_duration = duration if duration is not None else 1
        # Opening hours and required availability are independent constraints.
        intervals = [(0, request.endTime)]
        required = ([("openingHours", v.openingWindows)]
                    if not isinstance(v, ScheduledEvent) or v.openingWindows is not None or v.openingHours is not None else [])
        if (isinstance(v, ScheduledEvent) or v.openingWindows is not None
                or v.availabilityWindows is not None) and v.dataQuality.schedule == DataStatus.unknown:
            issue("unknown_schedule_evidence", "schedule", "Schedule provenance is unknown; obtain schedule evidence before confirmation.", v, True)
        # Supplied availability is always honored, even when not explicitly requested.
        if request.requireAvailability or v.availabilityWindows is not None or v.availability is not None:
            required.append(("availability", v.availabilityWindows))
        for field, supplied in required:
            windows = _windows(supplied, request)
            if windows is None:
                issue("unknown_" + field, field, f"{field} cannot be checked; obtain structured windows for the requested day.", v, True)
            else:
                intervals = [(max(a, c), min(b, d)) for a, b in intervals for c, d in windows
                             if max(a, c) < min(b, d)]
        event = isinstance(v, ScheduledEvent)
        if event:
            start = v.start
            if start < earliest:
                issue("event_conflict", "startTime", "Earlier stops and travel cannot reach the fixed event start; change order or activities.", v)
            fits = any(a <= start and start + minimum_duration <= b for a, b in intervals)
            exact = True  # A fixed event anchors subsequent known times again.
        else:
            starts = [max(earliest, a) for a, b in intervals if max(earliest, a) + minimum_duration <= b]
            start = min(starts) if starts else earliest
            fits = bool(starts)
        if not fits:
            issue("time_window", "schedule", "Stop cannot fit opening/availability windows or the outing end; change the day, time or activities.", v)
        if start + minimum_duration > request.endTime:
            issue("end_time", "endTime", "Outing cannot finish by its end time (at most midnight); start earlier or shorten activities.", v)
        if not exact and required:
            issue("uncertain_timing", "schedule", "An earlier unknown duration or travel time prevents confirming this stop's windows.", v, True)
        end = start + duration if duration is not None else None
        stops.append(PlannedStop(venue=v, start=start if exact and start < 1440 else None,
                                 end=end if exact and end is not None and end <= 1440 else None,
                                 duration=duration))
        earliest = start + minimum_duration
        exact = exact and duration is not None

    complete_duration = all(v.duration is not None for v in venues)
    activity_duration = sum(v.duration for v in venues) if complete_duration else None
    elapsed = (stops[-1].end - stops[0].start
               if stops[0].start is not None and stops[-1].end is not None
               and complete_duration and travel is not None else None)
    # Violated routes can exceed one day; no invalid scalar totals are emitted.
    state = "violated" if any(i.status == "violation" for i in issues) else "provisional" if issues else "confirmed"
    return RankedItinerary(
        candidate=candidate, feasibility=state, issues=issues, stops=stops, prices=prices, legs=legs,
        knownCostPerPerson=float(known), knownGroupCost=float(known * request.people), costPerPerson=float(cost) if cost is not None else None,
        groupCost=float(cost * request.people) if cost is not None else None,
        totalTravel=travel if travel is None or travel <= 1440 else None,
        activityDuration=activity_duration if activity_duration is None or activity_duration <= 1440 else None,
        elapsedDuration=elapsed if elapsed is not None and 0 < elapsed <= 1440 else None,
    )


# Normalized weights sum to one; every component uses 0..1, higher is better.
WEIGHTS = {"budget": (0.75, 0.10, 0.15), "balanced": (0.35, 0.40, 0.25),
           "experience": (0.10, 0.75, 0.15)}


def score_candidates(request: OutingRequest, candidates: list[RankedItinerary]) -> list[RankedItinerary]:
    """Normalize against the entire eligible pool, independent of input order.

    Unknown components earn zero, not a fabricated average. Unknown quality
    affects preference scoring only; it cannot establish mandatory feasibility.
    """
    if any(p.feasibility == "violated" for p in candidates):
        raise ValueError("Only candidates without known violations may be scored")

    def quality(p):
        values = [v.experience for v in p.candidate.venues]
        return sum(values) / len(values) if all(v is not None for v in values) else None

    measures = [(p.costPerPerson, quality(p), p.totalTravel) for p in candidates]
    bounds = [(min(v, default=0), max(v, default=0)) for v in
              ([m[i] for m in measures if m[i] is not None] for i in range(3))]
    weights = WEIGHTS[request.cost.value]
    for p, values in zip(candidates, measures):
        normalized = []
        for i, value in enumerate(values):
            low, high = bounds[i]
            n = 0 if value is None else 1 if high == low else (value - low) / (high - low)
            normalized.append(1 - n if value is not None and high != low and i in (0, 2) else n)
        p.components = dict(zip(("affordability", "quality", "convenience"), normalized))
        p.score = sum(w * n for w, n in zip(weights, normalized))
        p.explanations = [RecommendationReason(code="score", message=f"{request.cost.value} mode score {p.score:.3f}; normalized affordability, quality and travel weights {weights}.")]
        if p.costPerPerson is not None:
            p.explanations.append(RecommendationReason(code="cost", message=f"USD {p.costPerPerson:g}/person; USD {p.groupCost:g} for {request.people} people, activity costs only."))
        if p.totalTravel is not None:
            p.explanations.append(RecommendationReason(code="travel", message=f"{p.totalTravel} inter-stop travel minutes; data status is retained on every travel quote."))
        if values[1] is not None:
            p.explanations.append(RecommendationReason(code="quality", message=f"Mean supplied experience value {values[1]:g}; fixture values are fictional tiers, not reviews."))
        if p.feasibility == "provisional":
            p.explanations.append(RecommendationReason(code="feasibility", message="Provisional alternative only: unresolved constraints are listed in issues; feasibility is not confirmed."))
        else:
            p.explanations.append(RecommendationReason(code="feasibility", message="All evaluated constraints fit the supplied data; fictional data does not establish real-world availability."))
    return sorted(candidates, key=lambda p: (-p.score, tuple(v.id for v in p.candidate.venues), p.candidate.id))


def _select(ranked: list[RankedItinerary], count: int) -> list[RankedItinerary]:
    """Best first, then greedy diversity among options within 0.15 of best remaining.

    Prefer more different stop identities; never select an ineligible route to
    fill three slots. For a single activity, a different record is distinct.
    """
    selected = []
    remaining = list(ranked)
    while remaining and len(selected) < count:
        if not selected:
            choice = remaining[0]
        else:
            near = [p for p in remaining if p.score >= remaining[0].score - 0.15]
            def distance(p):
                return min(sum(a.id != b.id for a, b in zip(p.candidate.venues, s.candidate.venues))
                           for s in selected)
            choice = min(near, key=lambda p: (-distance(p), -p.score, tuple(v.id for v in p.candidate.venues)))
        if selected:
            changed = min(sum(a.id != b.id for a, b in zip(choice.candidate.venues, s.candidate.venues))
                          for s in selected)
            choice.explanations.append(RecommendationReason(
                code="diversity", message=f"Changes at least {changed} stop identities versus earlier options; selected within 0.15 of the best remaining score."))
        selected.append(choice)
        identity = tuple(v.id for v in choice.candidate.venues)
        remaining = [p for p in remaining if tuple(v.id for v in p.candidate.venues) != identity]
    return selected


def rank_candidates(request: OutingRequest, candidates: Iterable[CandidateItinerary], *,
                    price_provider: PriceProvider = mock_price,
                    travel_provider: TravelProvider = simulated_travel) -> RankingResult:
    evaluated = [evaluate_candidate(request, c, price_provider=price_provider,
                                    travel_provider=travel_provider) for c in candidates]
    reasons = Counter(i.code for p in evaluated for i in
                      {issue.code: issue for issue in p.issues}.values())
    eligible = [p for p in evaluated if p.feasibility != "violated"]
    ranked = score_candidates(request, eligible)
    plans = _select([p for p in ranked if p.feasibility == "confirmed"], 3)
    provisional = _select([p for p in ranked if p.feasibility == "provisional"], 3 - len(plans))
    errors = []
    if not plans:
        errors = [PlanningError(code="insufficient_data" if provisional else "infeasible",
                                message=("No confirmed recommendation. Obtain the missing evidence listed in provisional alternatives."
                                         if provisional else "No candidate satisfies all known limits. Review rejection reasons and adjust the relevant constraint."))]
    if not plans and not provisional:
        errors.extend(PlanningError(code="infeasible" if status == "violation" else "insufficient_data",
                                    field=field, message=message)
                      for _, field, message, status in sorted(
                          {(i.code, i.field, i.message, i.status) for p in evaluated for i in p.issues}))
    return RankingResult(request=request, plans=plans, provisionalPlans=provisional, errors=errors,
                         rejectionReasons=dict(sorted(reasons.items())),
                         message=f"{len(plans)} confirmed mock recommendations; {len(provisional)} provisional alternatives.",
                         notes=["All shared-catalog venues, prices, schedules, capacity and travel are fictional.",
                                "Costs exclude transport, tax, tips, booking fees and extras; shopping excludes purchases and free picnic requires your own food.",
                                "Travel excludes the first/last trip; the default simulation ignores transport mode.",
                                "Confirmed means constraints checked against supplied data, never a real booking or real availability."])


def recommend_plans(request: OutingRequest, *, price_provider: PriceProvider = mock_price,
                    travel_provider: TravelProvider = simulated_travel) -> RankingResult:
    generated = generate_candidates(request)
    if generated.errors:
        return RankingResult(request=request, errors=generated.errors, message=generated.message,
                             notes=["Shared catalog data is fictional; no real availability checked."])
    return rank_candidates(request, generated.candidates, price_provider=price_provider,
                           travel_provider=travel_provider)
