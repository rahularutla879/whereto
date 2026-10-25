"""Task 46 orchestration: shared combinations/evaluator/ranking, real evidence only."""
from datetime import datetime, timezone
from math import ceil
from time import perf_counter

from pydantic import Field

from backend.evidence import distinct_venue_labels, feasibility_labels, route_labels, venue_source
from backend.feasibility import EvidenceStop, FeasibilityInput, evaluate_feasibility
from backend.models import (PlanningRequest, RankingResult, PlanningError, Venue, DataQuality,
                            ConstraintIssue, PriceQuote, TravelQuote, DataStatus)
from backend.places import DiscoveryError, DiscoveryRequest, PlacesDiscovery, SearchArea
from backend.planner import _walk
from backend.provider_budget import ProviderBudget, ProviderLimitError
from backend.ranking import evaluate_candidate, score_candidates, _select
from backend.routes import AuthorizedStart, GoogleRouteCalculator, RoutePoint, RouteRequest, RouteError


class PlannerInput(PlanningRequest):
    manualStartingPlace: str | None = Field(default=None, max_length=200, exclude=True, repr=False)
    startingLocation: AuthorizedStart | None = Field(default=None, repr=False, exclude=True)
    currentArea: SearchArea | None = Field(default=None, repr=False, exclude=True)
    searchRadius: float | None = Field(default=None, gt=0, le=50000, strict=True, allow_inf_nan=False)
    maxFirstLegTravel: int | None = Field(default=None, ge=0, le=1440, strict=True)


def real_plans(request: PlannerInput, session: ProviderBudget) -> RankingResult:
    session.settings.require_live_provider()
    started = perf_counter()
    outing = session.outing()
    # Do not echo precise authorized starting coordinates in result/request IDs.
    public = PlanningRequest.model_validate(request.model_dump(exclude={"searchRadius"}))
    if request.manualStartingPlace and request.manualStartingPlace.strip():
        return empty(public, "Manual starting-place lookup is not enabled yet. Use my current location, or clear the starting place to plan without first-stop travel. Your destination was not changed.")
    if request.allowRevisits:
        return empty(public, "Real outings currently require distinct venues. Repeated activity types are supported, but returning to the same venue is not yet supported.")
    if request.transport is not None and request.transport.value not in ("driving", "walking"):
        return empty(public, "Real planning supports driving or walking. Select one of these modes.")
    if request.maxFirstLegTravel is not None and request.startingLocation is None:
        return empty(public, "Share your starting location or provide a starting point before using a first-stop travel limit.")
    near = request.location.strip().casefold() in ("near me", "current location", "nearby")
    if near and (request.currentArea is None or request.currentArea.coordinates is None):
        return empty(public, "Choose Use my current location, or enter a destination city/neighborhood in Set preferences.")
    area = request.currentArea if near else SearchArea(name=request.location)
    if request.searchRadius is not None:
        # A destination must never inherit unrelated device coordinates/radius.
        if not near:
            return empty(public, "A search radius needs an explicit search point. Use near me with a shared location, or omit the radius for a named destination.")
        area = area.model_copy(update={"radius_m": request.searchRadius})
    try:
        discovery = PlacesDiscovery(outing).discover_many([
            DiscoveryRequest(activity=a, destination=area, meal="dinner" if a == "food" and (request.dinner or request.dinnerStops) else None) for a in dict.fromkeys(request.activities)])
    except (DiscoveryError, ProviderLimitError) as error:
        error.diagnostics = {**outing.usage(), "providerLatencyMs": round((perf_counter() - started) * 1000)}
        raise
    pools, facts = [], {}
    for activity in request.activities:
        pool = []
        for distinct in discovery.venues:
            if activity not in distinct.activities:
                continue
            fact = distinct.facts.model_copy(update={"activity": activity})
            labels = distinct_venue_labels(distinct).model_dump(mode="json")
            facts[fact.id] = fact
            pool.append(Venue(id=fact.id, name=fact.name, activity=activity,
                              providerPlaceId=fact.id, address=fact.address,
                              mapsUrl=str(venue_source(fact).url), evidenceLabels=labels,
                              dataQuality=DataQuality(identity=DataStatus.verified), source="Google Maps"))
        pools.append(pool)
    diagnostics = {"placesSearchRequests": len(set(request.activities)), "placesDetailsRequests": 0,
                   "excludedCandidates": discovery.excluded_count,
                   "usageCategories": ["Text Search Pro", "Compute Route Matrix Essentials"]}
    if any(not pool for pool in pools):
        return empty(public, "Too few matching real venues for every requested activity in this area. Try a different area or activity; no fictional stops were added.", diagnostics)
    # Reuse Task 26 ordered product and identity checks. A multi-activity physical
    # venue can serve either category, but is never presented as two visits.
    # Explicit revisits are currently deliberately unsupported for real outings.
    distinct_request = public.model_copy(update={"allowRevisits": False})
    candidates = list(_walk(distinct_request, pools))
    if not candidates:
        return empty(public, "No complete outing uses distinct real venues in the requested order. Multi-activity venues are not duplicated.", diagnostics)
    mode = "walk" if request.transport and request.transport.value == "walking" else "drive"
    try:
        routed = GoogleRouteCalculator(outing).calculate(RouteRequest(
            activity_groups=[[RoutePoint(id=v.id, place_id=v.id) for v in pool] for pool in pools],
            mode=mode, starting_location=request.startingLocation))
    except RouteError as error:
        error.diagnostics = {**outing.usage(), "providerLatencyMs": round((perf_counter() - started) * 1000)}
        raise
    diagnostics.update(outing.usage())
    diagnostics.update(matrixElements=routed.matrix_elements, matrixRequests=routed.matrix_requests,
                       providerLatencyMs=round((perf_counter() - started) * 1000))
    routes = {(leg.origin_id, leg.destination_id): leg for leg in routed.legs}

    def travel(a, b, _request):
        leg = routes[a.id, b.id]
        return TravelQuote(minutes=int(leg.duration_minutes) if leg.duration_minutes is not None else None,
                           status=DataStatus.estimated if leg.status in ("ok", "same_location") else DataStatus.unknown,
                           source="Google Maps route estimate; display rounded up to whole minutes")

    evaluated, rejections = [], {}
    for candidate in candidates:
        # Task 27 schedules known durations and ranks unknown components honestly.
        # Exact Task 44 seconds enforce travel caps, never rounded display minutes.
        uncapped = public.model_copy(update={"travel": None, "maxLegTravel": None, "allowRevisits": False})
        plan = evaluate_candidate(uncapped, candidate,
            price_provider=lambda _v, _r: PriceQuote(status=DataStatus.unknown, source="Real activity price not retrieved"),
            travel_provider=travel, real_data=True)
        # The shared scheduler uses whole minutes: floor travel is a safe lower
        # bound for rejecting impossible time windows, never rounded-up minutes.
        # Task 44 enforces exact travel caps; only presentation rounds upward.
        for quote, (a, b) in zip(plan.legs, zip(candidate.venues, candidate.venues[1:])):
            leg = routes[a.id, b.id]
            quote.minutes = ceil(leg.duration_minutes) if leg.duration_minutes is not None else None
        display_total = sum(q.minutes for q in plan.legs if q.minutes is not None)
        plan.totalTravel = display_total if all(q.minutes is not None for q in plan.legs) and display_total <= 1440 else None
        for stop in plan.stops:
            stop.start = stop.end = None  # Unknown durations cannot establish visit times.
        stops = [EvidenceStop(venue=facts[s.venue.id].model_copy(update={"activity": s.venue.activity})) for s in plan.stops]
        evidence = evaluate_feasibility(FeasibilityInput(
            candidate_id=candidate.id, stops=stops, mode=mode, routes=routed.legs,
            max_leg_minutes=request.maxLegTravel, max_total_minutes=request.travel,
            starting_location=request.startingLocation, max_first_leg_minutes=request.maxFirstLegTravel,
            evaluated_at=datetime.now(timezone.utc)))
        labels = feasibility_labels(evidence)
        for check, label in zip(evidence.checks, labels.checks):
            if check.state != "feasible":
                plan.issues.append(ConstraintIssue(code=check.code, field=check.kind,
                    status="violation" if check.state == "infeasible" else "unknown", message=label.label.message))
        if request.dinner or request.dinnerStops:
            plan.issues.append(ConstraintIssue(code="unverified_dinner", field="availability", status="unknown",
                message="Dinner service and hours are not verified for these restaurants. Confirm they serve dinner before choosing."))
        plan.issues.append(ConstraintIssue(code="unverified_availability", field="availability", status="unknown",
            message="Venue suitability, reservations and activity availability require confirmation. No booking is confirmed."))
        if request.budget is not None or request.groupBudget is not None:
            plan.issues.append(ConstraintIssue(code="unverified_budget", field="budget", status="unknown",
                message="Your hard budget is not verified because real activity prices are unknown. This plan has not passed the budget constraint."))
        plan.feasibility = "violated" if any(i.status == "violation" for i in plan.issues) else "provisional"
        plan.routeEvidence = [{"route": routes[a.id, b.id].model_dump(mode="json"),
                               "labels": route_labels(routes[a.id, b.id]).model_dump(mode="json")}
                              for a, b in zip(candidate.venues, candidate.venues[1:])]
        if request.startingLocation:
            first = routes[request.startingLocation.point.id, candidate.venues[0].id]
            plan.firstLeg = {"minutes": ceil(first.duration_minutes) if first.duration_minutes is not None else None,
                             "labels": route_labels(first).model_dump(mode="json")}
        plan.feasibilityEvidence = labels.model_dump(mode="json")
        if plan.feasibility == "violated":
            for issue in plan.issues:
                if issue.status == "violation":
                    rejections[issue.message] = rejections.get(issue.message, 0) + 1
        else:
            evaluated.append(plan)
    ranked = score_candidates(public, evaluated)
    # Keep genuinely useful shared stops when only one activity has alternatives.
    varying = sum(len({p.candidate.venues[i].id for p in ranked}) > 1 for i in range(len(request.activities)))
    min_changed = max(1, min(varying, (len(request.activities) + 1) // 2))
    diverse = _select(ranked, 3, min_changed=min_changed)
    batches, shown = [], {p.candidate.id for p in diverse}
    # At most six extra pre-evaluated combinations, no new searches/routes.
    for _ in range(2):
        previous = [p for p in ranked if p.candidate.id in shown]
        remaining = [p for p in ranked if p.candidate.id not in shown and all(
            sum(a.id != b.id for a, b in zip(p.candidate.venues, old.candidate.venues)) >= min_changed for old in previous)]
        batch = _select(remaining, 3, min_changed=min_changed)
        if not batch:
            break
        batches.append(batch)
        shown.update(p.candidate.id for p in batch)
    from backend.venue_details import details_sessions
    details_token = details_sessions.create([v.id for p in ranked if p.candidate.id in shown for v in p.candidate.venues], outing) if diverse else None
    return RankingResult(request=distinct_request, dataMode="real", provisionalPlans=diverse, detailsToken=details_token,
        alternativeBatches=batches,
        diagnostics=diagnostics, message=f"{len(diverse)} provisional real-venue options. Prices, hours and availability need confirmation.",
        errors=[] if diverse else [PlanningError(code="infeasible", message=m) for m in rejections] or [PlanningError(code="no_availability", message="No complete real outing is available.")],
        notes=["Real venues from Google Maps; activity categories reflect search context and need confirmation.",
               "Real prices, group capacity, activity durations, hours, showtimes and reservations are unknown. No budget is confirmed.",
               "Driving excludes live traffic. Walking routes are beta and may omit sidewalks or pedestrian paths.",
               "Inter-stop travel excludes the first trip and return home. An explicitly shared start is shown separately.",
               "Only up to three candidates per activity are searched. Fewer distinct options may be available."])


def empty(request, message, diagnostics=None):
    return RankingResult(request=request, dataMode="real", message=message,
                         errors=[PlanningError(code="insufficient_data", message=message)], diagnostics=diagnostics or {})
