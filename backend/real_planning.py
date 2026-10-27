"""Task 46 orchestration: shared combinations/evaluator/ranking, real evidence only."""
from datetime import datetime, timezone
from math import ceil
from typing import Literal
import os
import json
from time import perf_counter

from pydantic import Field

from backend.evidence import distinct_venue_labels, feasibility_labels, route_labels, venue_source
from backend.feasibility import EvidenceStop, FeasibilityInput, evaluate_feasibility
from backend.models import (PlanningRequest, RankingResult, PlanningError, Venue, DataQuality,
                            ConstraintIssue, PriceQuote, TravelQuote, DataStatus)
from backend.places import DiscoveryError, DiscoveryRequest, PlacesDiscovery, SearchArea
from backend.planner import _walk
from backend.planning_diagnostics import empty_coverage, planning_coverage, merge_discovery_audits, coverage_notes
from backend.provider_budget import ProviderBudget, ProviderLimitError
from backend.routing_shortlist import expansion_width
from backend.ranking import evaluate_candidate, score_candidates, _select
from backend.routes import AuthorizedStart, GoogleRouteCalculator, RoutePoint, RouteRequest, RouteError
from backend.routes import PlaceID


class PlannerInput(PlanningRequest):
    recentSurpriseIds: list[PlaceID] = Field(default_factory=list,max_length=120,exclude=True,repr=False)
    locationFirst: bool = Field(default=False, strict=True)
    referenceToken: str | None = Field(default=None, min_length=1, max_length=100, exclude=True, repr=False)
    manualStartingPlace: str | None = Field(default=None, max_length=200, exclude=True, repr=False)
    startingLocation: AuthorizedStart | None = Field(default=None, repr=False, exclude=True)
    currentArea: SearchArea | None = Field(default=None, repr=False, exclude=True)
    searchRadius: float | None = Field(default=None, gt=0, le=50000, strict=True, allow_inf_nan=False)
    maxFirstLegTravel: int | None = Field(default=None, ge=0, le=1440, strict=True)


def real_plans(request: PlannerInput, session: ProviderBudget, *, context=None) -> RankingResult:
    session.settings.require_live_provider()
    started = perf_counter()
    if context is None and request.startingLocation and request.startingLocation.source=='suggested' and not request.referenceToken:
        raise DiscoveryError('unverified_origin','Choose and confirm a verified starting-area suggestion before planning from it.')
    if request.planningMode=='surprise':
        from backend.surprise import validate_beginning
        validate_beginning(request)
        request=request.model_copy(update={'locationFirst':True})
    if request.startingLocation is None and request.planningMode!='surprise':
        return empty(PlanningRequest.model_validate(request.model_dump(exclude={'searchRadius','locationFirst'})), 'Choose and confirm where your outing starts using current/manual location, or select Surprise Me.')
    if request.startingLocation and request.startingLocation.source=="mock":
        raise DiscoveryError("invalid_origin","A fictional starting reference cannot be used for real planning.")
    preflight = None
    if context is None and request.referenceToken:
        from backend.starting_areas import references
        identity = request.startingLocation.point.id.removeprefix('reference_') if request.startingLocation else ''
        preflight, origin = references.confirm(request.referenceToken, identity, session)
        q = preflight['query']
        if (q.destination.casefold()!=request.location.casefold() or q.activities!=request.activities
                or q.geography!=request.geography or q.firstTravel!=request.firstTravel
                or (q.maxLegTravel,q.maxLegTravelExclusive,q.travel,q.travelExclusive)!=(request.maxLegTravel,request.maxLegTravelExclusive,request.travel,request.travelExclusive)
                or q.transport!=('walking' if request.transport=='walking' else 'driving')):
            raise DiscoveryError('changed_origin_request','Outing details changed since this suggestion. Choose a starting area again.')
        request=request.model_copy(update={'startingLocation':origin})
    outing = context["outing"] if context else preflight['outing'] if preflight else session.outing()
    # Do not echo precise authorized starting coordinates in result/request IDs.
    public = PlanningRequest.model_validate(request.model_dump(exclude={"searchRadius", "locationFirst"}))
    if request.manualStartingPlace and request.manualStartingPlace.strip():
        return empty(public, "Find and confirm your manual starting place before planning, or choose another starting method. Your destination was not changed.")
    if request.allowRevisits:
        return empty(public, "Real outings currently require distinct venues. Repeated activity types are supported, but returning to the same venue is not yet supported.")
    if request.transport is not None and request.transport.value not in ("driving", "walking"):
        return empty(public, "Real planning supports driving or walking. Select one of these modes.")
    if (request.maxFirstLegTravel is not None or request.firstTravel is not None) and request.startingLocation is None:
        return empty(public, "Choose current location, confirm a manual starting place, or choose a suggested starting area before checking first-stop travel.")
    near = request.location.strip().casefold() in ("near me", "current location", "nearby")
    if near and (request.currentArea is None or request.currentArea.coordinates is None):
        return empty(public, "Choose Use my current location, or enter a destination city/neighborhood in Set preferences.")
    area = request.currentArea if near else SearchArea(name=request.location)
    if request.searchRadius is not None:
        # A destination must never inherit unrelated device coordinates/radius.
        if not near:
            return empty(public, "A search radius needs an explicit search point. Use near me with a shared location, or omit the radius for a named destination.")
        area = area.model_copy(update={"radius_m": request.searchRadius})
    if context is None and request.locationFirst:
        from backend.sequential_discovery import initialize
        try:context=initialize(request,outing,preflight['inventory'] if preflight else None,preflight['routes'] if preflight else None)
        except (DiscoveryError,ProviderLimitError,RouteError) as error:
            from backend.provider_errors import attach_accounting
            raise attach_accounting(error,outing)
        context.update(session=session,routes=preflight['routes'] if preflight else {},seen=set(),
            width=6 if len(request.activities)<=2 else 4,expanded=False,area=area,matrixRequests=preflight['matrixRequests'] if preflight else 0,usedPrimary=set(),referenceScoring=preflight.get('referenceScoring') if preflight else None)
    if context is None:
        try:
            discovery = PlacesDiscovery(outing).discover_many([
                DiscoveryRequest(activity=a, destination=area, meal="dinner" if a == "food" and (request.dinner or request.dinnerStops) else None) for a in dict.fromkeys(request.activities)])
        except (DiscoveryError, ProviderLimitError) as error:
            error.diagnostics = {**getattr(error,"diagnostics",{}),**outing.usage(), "providerLatencyMs": round((perf_counter() - started) * 1000)}
            raise
        context = {"outing": outing, "request": request, "session": session, "discovery": discovery,
                   "routes": {}, "seen": set(), "width": 6 if len(request.activities) <= 2 else 4,
                   "expanded": False, "discoveryPages": {a: 1 for a in dict.fromkeys(request.activities)}, "area": area, "matrixRequests": 0, "usedPrimary": set()}
    else:
        discovery = context["discovery"]
    surprise=request.planningMode=='surprise'
    if surprise:context.setdefault('recent',set(request.recentSurpriseIds))
    pools, facts = [], {}
    for position, activity in enumerate(request.activities):
        pool = []
        for distinct in discovery.venues:
            if activity not in distinct.activities or context.get("locationFirst") and distinct.facts.id not in context["positionIds"][position]:
                continue
            fact = distinct.facts.model_copy(update={"activity": activity})
            labels = distinct_venue_labels(distinct).model_dump(mode="json")
            facts[fact.id] = fact
            pool.append(Venue(id=fact.id, name=fact.name, activity=activity,
                              providerPlaceId=fact.id, address=fact.address, rating=fact.rating, ratingCount=fact.ratingCount,
                              relevanceStrength=distinct.relevance[activity].status,
                              mapsUrl=str(venue_source(fact).url), evidenceLabels=labels,
                              dataQuality=DataQuality(identity=DataStatus.verified), source="Google Maps"))
        pools.append(pool)
    diagnostics = {"placesSearchRequests": len(set(request.activities)), "placesDetailsRequests": 0,
                   "excludedCandidates": discovery.excluded_count,
                   "discoveryStages": discovery.stages, "discoveryReasons": discovery.diagnostics,
                   "usageCategories": ["Text Search Enterprise" if os.environ.get("WHERETO_RATINGS_DEV") == "1" else "Text Search Pro", "Compute Route Matrix Essentials"]}
    diagnostics['venuePipeline'] = empty_coverage(discovery, {a.value: {v.id for v in p} for a, p in zip(request.activities, pools)})
    diagnostics['configuredLimits'] = {'candidatesPerActivity': None if outing.settings.exploration else outing.settings.candidates_per_activity,
        'searchesPerOuting': None if outing.settings.exploration else outing.settings.searches_per_outing, 'matrixElementsPerOuting': None if outing.settings.exploration else outing.settings.matrix_elements_per_outing}
    if any(not pool for pool in pools):
        from backend.option_sessions import option_sessions
        if "token" not in context:
            context["token"] = option_sessions.create(context)
        diagnostics.update(outing.usage(), discoveredCounts=[len(p) for p in pools])
        result = empty(public, "Too few matching real venues in the checked search. Search for more venues if available, or choose a different area/activity; no fictional stops were added.", diagnostics)
        result.optionsToken = context["token"]
        result.canDiscover = can_discover(context)
        result.notes += coverage_notes(diagnostics["venuePipeline"])
        return result
    from backend.routing_shortlist import shortlist
    all_pools = pools
    if surprise:
        from backend.surprise import venue_order
        if 'surpriseOrder' not in context:
            context['surpriseOrder']=[v.id for v in venue_order(pools[0],context['usedPrimary']|context['recent'],facts)]
        priority={identity:i for i,identity in enumerate(context['surpriseOrder'])}
        pools[0]=sorted(pools[0],key=lambda v:priority.get(v.id,len(priority)))
    frontier = all_pools
    if outing.settings.exploration:
        # Finite computation, not a retention ceiling. Prefer venues with fewer
        # checked routes; retain this action's frontier through its one recursion.
        if not context.get("actionFrontier"):
            width = expansion_width(outing.settings, len(pools))
            known = context["routes"]
            frontiers = []
            for pool in pools:
                previous = frontiers[-1] if frontiers else None
                chosen = (pool if surprise and not frontiers else sorted(pool, key=lambda v: (
                    sum((a, v.id) in known for a in previous) if previous else sum(v.id == a for a, _ in known), v.id))[:width]
                )
                chosen=chosen[:width]
                if surprise and frontiers:
                    from backend.routing_shortlist import balanced_following
                    previous_pool=[v for v in all_pools[len(frontiers)-1] if v.id in frontiers[-1]]
                    chosen=balanced_following(pool,previous_pool,facts,width)
                frontiers.append({v.id for v in chosen})
            context["actionFrontier"] = frontiers
        frontier = [[v for v in pool if v.id in ids] for pool, ids in zip(pools, context["actionFrontier"])]
    pools = shortlist(frontier, facts, context["width"], request.startingLocation)
    if surprise:pools[0]=frontier[0][:context['width']]
    if surprise:
        from backend.routing_shortlist import balanced_following
        for i in range(1,len(pools)):pools[i]=balanced_following(frontier[i],pools[i-1],facts,context['width'])
    for activity, row in diagnostics['venuePipeline'].items():
        count = len({v.id for pool in pools for v in pool if v.activity == activity})
        row.update(shortlistedForRouting=count, notInCheckedCompletePath=count)
    # Reuse Task 26 ordered product and identity checks. A multi-activity physical
    # venue can serve either category, but is never presented as two visits.
    # Explicit revisits are currently deliberately unsupported for real outings.
    distinct_request = public.model_copy(update={"allowRevisits": False})
    candidates = None if context.get("locationFirst") else list(_walk(distinct_request, pools))
    if candidates == []:
        return empty(public, "No complete outing uses distinct real venues in the requested order. Multi-activity venues are not duplicated.", diagnostics)
    mode = "walk" if request.transport and request.transport.value == "walking" else "drive"
    from backend.routes import plan_matrices, RouteResult
    route_request = RouteRequest(activity_groups=[[RoutePoint(id=v.id, place_id=v.id) for v in pool] for pool in pools],
                                 mode=mode, starting_location=request.startingLocation)
    if context.get('locationFirst'):
        # Route only spatially promising consecutive transitions, plus every
        # retained authorized origin leg. Distances here are search heuristics.
        from backend.venue_geography import distance_m
        possible,_=plan_matrices(route_request)
        desired=[]
        for (a,b),(origin,destination) in possible.items():
            if request.startingLocation and a==request.startingLocation.point.id:
                desired.append((a,b));continue
            from backend.location_policy import effective_max,radius
            threshold=radius(request.betweenTravel,effective_max(request.betweenTravel),mode) if request.betweenTravel else max(250,(request.maxLegTravel if request.maxLegTravel is not None else 10)*(80 if mode=='walk' else 600))
            if (facts[a].coordinates and facts[b].coordinates and distance_m(facts[a].coordinates,facts[b].coordinates)<=threshold) or any(x==a and y==b for _,x,y in context['spatialEdges']):
                desired.append((a,b))
        route_request=route_request.model_copy(update={'required_pairs':desired})
    from backend.routing_expansion import select_stage
    required, _ = plan_matrices(route_request)
    missing = [key for key in required if key not in context["routes"]]
    # Reuse evaluated alternatives. A bounded stage fills a checked pool with
    # fewer than three options; initial infeasibility may expand once below.
    primary_evidence_needed = context.get('eligiblePrimary', 3) < min(3, len(all_pools[0]))
    if missing and (context.get("unseenEligible", 0) < 3 or primary_evidence_needed) and not context.get("routedThisAction") and not context.get("stopped") and (not (outing.settings.exploration or context.get("locationFirst")) or context.get("actionRouteStages", 0) < 2):
        selected, _, _ = select_stage(route_request, context["routes"], outing, facts)
        context["routedThisAction"] = True
        if selected:
            context["actionRouteStages"] = context.get("actionRouteStages", 0) + 1
            try:
                additional = GoogleRouteCalculator(outing).calculate(route_request.model_copy(update={"required_pairs": selected}))
                context["matrixRequests"] += additional.matrix_requests
                if any(leg.error_code in ("quota", "authentication", "permission", "provider", "timeout", "invalid_response", "invalid_request", "not_requested") for leg in additional.legs):
                    context["stopped"] = True
                context["routes"].update({(leg.origin_id, leg.destination_id): leg for leg in additional.legs})
            except RouteError as error:
                error.diagnostics = {**getattr(error,"diagnostics",{}),**outing.usage(), "providerLatencyMs": round((perf_counter() - started) * 1000)}
                raise
    capacity = outing.routing_capacity()
    pending = sum(key not in context["routes"] for key in required)
    diagnostics.update(unroutedPairs=pending, routingCapacity=capacity)
    coverage_pending = pending or any(len(p) > len(q) for p, q in zip(all_pools, pools))
    route_notice = ("The remaining route budget limits checked coverage. Other suitable venues may exist." if coverage_pending and (not capacity['elements'] or not capacity['attempts']) else
                    "The local route minute allowance is used. Wait at least a minute, then choose Show different options to check unsent routes. No retry is scheduled." if pending and not capacity['minuteElements'] else
                    "More routes can be checked in bounded stages within this outing's remaining budget." if pending else "")
    failures=[leg for leg in context['routes'].values() if leg.error_message]
    if failures:
        route_notice=failures[0].error_message
        diagnostics['providerFailure']=failures[0].error_context
    routes = context["routes"]
    routed = RouteResult(legs=list(routes.values()), matrix_elements=outing.usage()["reservedMatrixElements"], matrix_requests=context["matrixRequests"])
    diagnostics.update(outing.usage())
    diagnostics.update(matrixElements=routed.matrix_elements, matrixRequests=routed.matrix_requests,
                       shortlistedCounts=[len(p) for p in pools], discoveredCounts=[len(p) for p in all_pools],
                       providerLatencyMs=round((perf_counter() - started) * 1000))

    def travel(a, b, _request):
        leg = routes[a.id, b.id]
        return TravelQuote(minutes=int(leg.duration_minutes) if leg.duration_minutes is not None else None,
                           status=DataStatus.estimated if leg.status in ("ok", "same_location") else DataStatus.unknown,
                           source="Google Maps route estimate; display rounded up to whole minutes")

    if context.get('locationFirst'):
        from backend.spatial_beam import candidates as beam_candidates
        candidates=beam_candidates(distinct_request,pools,routes,context['seen'])
    evaluated, rejections, rejection_codes = [], {}, {}
    checked = 0
    travel_sets = {state: {} for state in ('compatible', 'violated', 'unverified')}
    for candidate in candidates:
        needed = [(a.id, b.id) for a, b in zip(candidate.venues, candidate.venues[1:])]
        if request.startingLocation:
            needed.append((request.startingLocation.point.id, candidate.venues[0].id))
        if any(key not in routes for key in needed):
            continue  # No guessed routes and no recommendation without required evidence.
        checked += 1
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
            max_leg_exclusive=request.maxLegTravelExclusive, max_total_exclusive=request.travelExclusive,
            max_first_leg_exclusive=request.maxFirstLegTravelExclusive,
            first_preference=request.firstTravel,
            between_preference=request.betweenTravel,
            starting_location=request.startingLocation, max_first_leg_minutes=request.maxFirstLegTravel,
            evaluated_at=datetime.now(timezone.utc)))
        travel_checks = [c for c in evidence.checks if c.kind == 'travel']
        travel_state = ('violated' if any(c.state == 'infeasible' for c in travel_checks) else
                        'compatible' if all(routes[key].status in ('ok', 'same_location') for key in needed) else 'unverified')
        for v in candidate.venues:
            travel_sets[travel_state].setdefault(v.activity.value, set()).add(v.id)
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
        failures = {leg.error_code for leg in routed.legs if leg.status == "error"}
        for code in sorted(failures & {"quota", "authentication", "permission", "provider", "timeout", "invalid_response", "invalid_request"}):
            reason = {"quota": "quota was reached", "authentication": "authentication failed", "permission": "permission or billing was unavailable"}.get(code, "could not return valid route data")
            plan.issues.append(ConstraintIssue(code="route_provider_" + code, field="travel", status="unknown",
                message=f"Google routing {reason}. Some required travel estimates are unavailable; no automatic retry was made."))
        plan.feasibility = "violated" if any(i.status == "violation" for i in plan.issues) else "provisional"
        plan.routeEvidence = [{"route": routes[a.id, b.id].model_dump(mode="json"),
                               "labels": route_labels(routes[a.id, b.id]).model_dump(mode="json")}
                              for a, b in zip(candidate.venues, candidate.venues[1:])]
        if request.betweenTravel and request.betweenTravel.mode=='flexible':
            from backend.location_policy import exceeds
            for i,(a,b) in enumerate(zip(candidate.venues,candidate.venues[1:])):
                if exceeds(routes[a.id,b.id],request.betweenTravel,original=True):
                    plan.issues.append(ConstraintIssue(code='extra_between_travel',field='travel',status='unknown',
                        message=f'Journey {i+1} between activities exceeds your original preference, within the doubled flexible maximum.'))
        plan.feasibility="violated" if any(i.status=="violation" for i in plan.issues) else "provisional"
        if request.startingLocation:
            first = routes[request.startingLocation.point.id, candidate.venues[0].id]
            plan.firstLeg = {"source":request.startingLocation.source,"originLabel":request.startingLocation.label,
                             "miles":round(first.distance_meters/1609.344,2) if first.distance_meters is not None else None,
                             "exceedsPreference":False,
                             "minutes": ceil(first.duration_minutes) if first.duration_minutes is not None else None,
                             "labels": route_labels(first).model_dump(mode="json"),
                             "accuracyMeters":request.startingLocation.accuracy_m, "approximate": request.startingLocation.source=='suggested' or bool(request.startingLocation.accuracy_m and request.startingLocation.accuracy_m>100) or request.startingLocation.precision not in ("device", "address_or_place")}
            if request.firstTravel:
                from backend.location_policy import exceeds
                extra=exceeds(first,request.firstTravel,original=True)
                plan.firstLeg['exceedsPreference']=bool(extra)
                plan.firstLeg['preference']=request.firstTravel.model_dump(exclude={'originText'})
                if extra and request.firstTravel.mode=='flexible':
                    plan.issues.append(ConstraintIssue(code='extra_first_travel',field='travel',status='unknown',message='This option requires extra travel beyond your original flexible first-stop preference. The estimate is from the confirmed starting point.'))
        plan.feasibilityEvidence = labels.model_dump(mode="json")
        if plan.feasibility == "violated":
            for issue in plan.issues:
                if issue.status == "violation":
                    rejection_codes[issue.code] = rejection_codes.get(issue.code, 0) + 1
                    rejections[issue.message] = rejections.get(issue.message, 0) + 1
        else:
            evaluated.append(plan)
    diagnostics.update(candidateCombinations=len(candidates), evaluatedCombinations=checked,
                       uncheckedCombinations=len(candidates) - checked, eligibleCombinations=len(evaluated),
                       eligiblePrimaryCandidates=len({p.candidate.venues[0].id for p in evaluated}),
                       routeOutcomeCounts={status: sum(leg.status == status for leg in routed.legs) for status in {leg.status for leg in routed.legs}},
                       rejectedConstraints=rejection_codes, previouslyOfferedCombinations=len(context["seen"]),
                       primaryCandidates=len({v.id for v in pools[0]}))
    from backend.surprise import quality_qualified
    qualified=[p for p in evaluated if not surprise or quality_qualified(p)]
    if surprise:diagnostics['surpriseQualityExcluded']=len(evaluated)-len(qualified)
    ranked = [p for p in score_candidates(public, qualified) if p.candidate.id not in context["seen"]]
    if request.betweenTravel and request.betweenTravel.mode=='flexible':
        for plan in ranked:
            if not any(i.code=='extra_between_travel' for i in plan.issues):plan.score=min(1,plan.score+.05)
        ranked.sort(key=lambda p:-p.score)
    # Modest preference bonus: quality can still outweigh extra first-leg travel.
    if request.firstTravel and request.firstTravel.mode=='flexible':
        for plan in ranked:
            if not plan.firstLeg['exceedsPreference']:plan.score+=.05
        ranked.sort(key=lambda plan:(-plan.score,plan.candidate.id))
    diagnostics["unseenEligibleCombinations"] = len(ranked)
    # Keep genuinely useful shared stops when only one activity has alternatives.
    varying = sum(len({p.candidate.venues[i].id for p in ranked}) > 1 for i in range(len(request.activities)))
    min_changed = max(1, min(varying, (len(request.activities) + 1) // 2))
    if surprise:
        from backend.surprise import select
        diverse=select(ranked,3,context,facts)
    else:diverse = _select(ranked, 3, min_changed=min_changed, prefer_primary=True, primary_used=context["usedPrimary"])
    diagnostics["selectedPrimaryCandidates"] = len({p.candidate.venues[0].id for p in diverse})
    context['eligiblePrimary'] = diagnostics['eligiblePrimaryCandidates']
    primary_shortage = context['eligiblePrimary'] < min(3, len(all_pools[0]))
    if (len(diverse) < 3 or primary_shortage) and not context["expanded"] and not context.get("stopped") and any(len(p) > len(q) for p, q in zip(all_pools, pools)):
        context["expanded"] = True
        context["primaryCoverageExpanded"] = primary_shortage
        context["routedThisAction"] = False
        context["width"] = expansion_width(session.settings, len(request.activities))
        return real_plans(request, session, context=context)
    batches, shown = [], {p.candidate.id for p in diverse}
    primary_used = context["usedPrimary"] | {p.candidate.venues[0].id for p in diverse}
    # At most six extra pre-evaluated combinations, no new searches/routes.
    for _ in range(0 if surprise else 2):
        previous = [p for p in ranked if p.candidate.id in shown]
        remaining = [p for p in ranked if p.candidate.id not in shown and all(
            sum(a.id != b.id for a, b in zip(p.candidate.venues, old.candidate.venues)) >= min_changed for old in previous)]
        batch = _select(remaining, 3, min_changed=min_changed, prefer_primary=True, primary_used=primary_used)
        if not batch:
            break
        if len(batch) < 3 and capacity["elements"] > 0 and capacity["attempts"] > 0 and (pending or ((outing.settings.exploration or not context["expanded"]) and any(len(p) > len(q) for p, q in zip(all_pools, pools)))):
            break  # Retain leftovers for a full batch after the next explicit stage.
        batches.append(batch)
        primary_used.update(p.candidate.venues[0].id for p in batch)
        shown.update(p.candidate.id for p in batch)
    from backend.venue_details import details_sessions
    from backend.option_sessions import option_sessions
    context["usedPrimary"].update(p.candidate.venues[0].id for p in ranked if p.candidate.id in shown)
    context["seen"].update(shown)
    if surprise:
        from backend.surprise import record
        record(context,diverse,facts)
        context['eligiblePrimary']=len({p.candidate.venues[0].id for p in ranked}-context['usedPrimary'])
        diagnostics['surprise']={'eligibleFirstVenues':len({p.candidate.venues[0].id for p in ranked}),'offeredFirstVenues':len(context['usedPrimary']),'offeredCompleteItineraries':len(context['seen']),'offeredActivityRegions':len(context.get('usedRegions',()))}
    if "detailsToken" not in context:
        context["detailsToken"] = details_sessions.create(list(facts), outing)
    if "token" not in context:
        context["token"] = option_sessions.create(context)
    details_token = context["detailsToken"]
    details_sessions.extend(details_token, list(facts))
    context["unseenEligible"] = sum(p.candidate.id not in context["seen"] for p in qualified)
    context["routedThisAction"] = False
    if outing.settings.exploration:
        diagnostics.update(outing.usage())
    diagnostics['venuePipeline'] = planning_coverage(discovery, all_pools, pools, request.activities,
        routes, travel_sets, evaluated, ranked, diverse, [p for p in ranked if p.candidate.id in shown], context)
    diagnostics['primaryCoverageExpansion'] = context.get('primaryCoverageExpanded', False)
    if context.get('referenceScoring'):diagnostics['referenceScoring']=context['referenceScoring']
    can_expand = not context.get("stopped") and (context["unseenEligible"] > 0 or (
        capacity['elements'] > 0 and capacity['attempts'] > 0 and (pending > 0 or
        ((outing.settings.exploration or not context["expanded"]) and any(len(p) > len(q) for p, q in zip(all_pools, pools))))))
    if outing.settings.exploration or context.get("locationFirst"):
        can_expand = can_expand or can_discover(context)
    return RankingResult(request=distinct_request, dataMode="real", provisionalPlans=diverse, detailsToken=details_token,
        alternativeBatches=batches, optionsToken=context["token"], canExpand=can_expand, canDiscover=can_discover(context),
        diagnostics=diagnostics, message=route_notice if not diverse and route_notice else f"{len(diverse)} provisional real-venue options. Prices, hours and availability need confirmation.",
        errors=[] if diverse else [PlanningError(code="infeasible", message=m) for m in rejections] or [PlanningError(code="no_availability", message="No more eligible combinations in the checked route pool. Other venues may exist; search expansion or remaining budgets can limit coverage.")],
        notes=(["Surprise Me begins at the first activity; no journey from your location is planned. Quality-qualified weighted sampling favors unseen first venues. Repeated first venues may be needed when the checked pool is exhausted; further suitable venues may exist.",
                "Development Surprise coverage: "+json.dumps(diagnostics['surprise'],sort_keys=True)+f"; quality-excluded complete paths {diagnostics['surpriseQualityExcluded']}."] if surprise else []) + (["Development starting-area comparison: "+json.dumps(context['referenceScoring'],sort_keys=True)] if context.get('referenceScoring') else []) + (["Location-first discovery: multiple earlier-stop anchors and bounded route-evidence beam. Flexible first-stop maximum is twice the entered preference. Search coverage is not city-wide exhaustion.",
                   "Destination is a preference with a bounded nearby search unless Only within or explicit regional exclusions were requested."] if context.get('locationFirst') else []) + (["Development exploration active: finite discovery/route batches, persistent local daily estimated spending guard. Cloud quota remaining is unknown.",
            f"Development usage — Text Searches {outing._dispatched['search']} dispatched ({outing._pagination} pagination reservations), Details {outing._dispatched['details']}, Matrix requests {outing._dispatched['matrix']}, elements {outing._dispatched['matrixElements']}. "
            f"Conservative reserved work: {outing._searches} searches, {outing._details} Details, {outing._matrix_requests} matrices / {outing._elements} elements. "
            f"Estimated gross: outing ${outing._gross/1000000:.3f}, local day ${diagnostics['estimatedDayGrossUsd']:.3f}; remaining local allowance ${diagnostics['estimatedAllowanceRemainingUsd']:.3f}. "
            "Estimates include failed/unsent batch reservations, exclude allowances/credits and unrelated usage; not verified Cloud billing."] if outing.settings.exploration else [f"Current application ceilings: {outing.settings.candidates_per_activity} retained venues per activity; {outing.settings.searches_per_outing} searches and {outing.settings.matrix_elements_per_outing} route elements per outing."]) + coverage_notes(diagnostics["venuePipeline"]) + ([route_notice] if route_notice else []) + ["Matching venue coverage: " + "; ".join(f"{activity.value}: {len(pool)}" for activity, pool in zip(request.activities, all_pools)) + ". This is limited search coverage, not a city-wide venue count.",
               "Real venues from Google Maps; activity categories reflect search context and need confirmation.",
               "Real prices, group capacity, activity durations, hours, showtimes and reservations are unknown. No budget is confirmed.",
               "Driving excludes live traffic. Walking routes are beta and may omit sidewalks or pedestrian paths.",
               "Inter-stop travel excludes the first trip and return home. An explicitly shared start is shown separately.",
               ("Exploration retains eligible candidates across finite actions; searched coverage is not city-wide exhaustion." if outing.settings.exploration else f"Up to {session.settings.candidates_per_activity} relevant candidates per activity can be retained through explicit search expansion. These results do not cover every venue in the city.")])


def empty(request, message, diagnostics=None):
    return RankingResult(request=request, dataMode="real", message=message,
                         errors=[PlanningError(code="insufficient_data", message=message)], diagnostics=diagnostics or {},
                         notes=["Search coverage is limited; these results do not cover every venue in the city."] if diagnostics and diagnostics.get("placesSearchRequests") else [])


def more_real_plans(token, *, expand_discovery=False):
    from backend.option_sessions import option_sessions
    context, lock = option_sessions.get(token)
    if context.get('mockSurprise'):raise DiscoveryError('mode_changed','This outing uses mock data. Generate again in the current data mode.')
    context["session"].settings.require_live_provider()
    if context["request"].startingLocation is None and context["request"].planningMode!='surprise':
        raise DiscoveryError("origin_required","This older outing needs a confirmed starting point. Choose where your outing starts and generate again.")
    if not lock.acquire(blocking=False):
        raise DiscoveryError("busy", "Another options request is running. Wait for it to finish.")
    try:
        from backend.date_resolution import resolve_datetime
        r = context["request"]
        start = f"{r.startTime // 60:02d}:{r.startTime % 60:02d}"
        end = "midnight" if r.endTime == 1440 else f"{r.endTime // 60:02d}:{r.endTime % 60:02d}"
        if resolve_datetime("", [], [f"from {start} to {end}"], r.location, manual_date=r.date.isoformat()).issues:
            raise DiscoveryError("date_expired", "The outing date or time window is no longer valid. Start a new search with a future date.")
        if context.get("stopped"):
            raise DiscoveryError("stopped", "Search expansion stopped after an earlier provider or budget failure. No automatic retry is available.")
        context["routedThisAction"] = False
        context["actionRouteStages"] = 0
        context["actionDiscoveryCalls"] = 0
        context["continuationAction"] = True
        if context["request"].planningMode=='surprise':
            context.pop('surpriseOrder',None);context.pop('actionFrontier',None);context['expanded']=False
        if context['outing'].settings.exploration:
            if expand_discovery or context.get('unseenEligible', 0) < 3:
                context.pop('actionFrontier', None)
            context['expanded'] = False
        if expand_discovery:
            expand_venue_discovery(context)
        elif (context['outing'].settings.exploration or context.get("locationFirst")) and (context.get('unseenEligible', 0) < 3 or context.get('eligiblePrimary', 3) < 3) and can_discover(context):
            expand_venue_discovery(context)
        result = real_plans(context["request"], context["session"], context=context)
        if not result.provisionalPlans and not context["expanded"]:
            context["expanded"] = True
            # Larger inventory is staged, never sent as an all-pairs matrix.
            context["width"] = expansion_width(context["session"].settings, len(context["request"].activities))
            result = real_plans(context["request"], context["session"], context=context)
        return result
    except (DiscoveryError, ProviderLimitError, RouteError) as error:
        context["stopped"] = True
        context['outing'].stop_reason = str(error)
        from backend.provider_errors import attach_accounting
        raise attach_accounting(error,context['outing'])
    finally:
        lock.release()


def discovery_activities(context):
    settings = context['session'].settings
    return [a for a in dict.fromkeys(context['request'].activities)
            if sum(a in v.activities for v in context['discovery'].venues) < settings.ceiling('candidates_per_activity')
            and (settings.exploration or context['discoveryPages'].get(a, 0) < 6)
            and (context['discovery'].paging.get(a, {}).get('next')
                 or context['discovery'].paging.get(a, {}).get('variant', 'initial') == 'initial'
                 or (settings.exploration and context['discovery'].paging.get(a, {}).get('variant') == 'alternative'))]


def can_discover(context):
    if context.get('stopped'):
        return False
    settings = context['session'].settings
    usage = context['outing'].usage()
    return (usage['placesSearchRequests'] < settings.ceiling('searches_per_outing')
            and usage['providerAttempts'] < settings.ceiling('requests_per_outing') -
                (settings.details_per_outing - usage['placesDetailsRequests'])
            and (sequential_can_discover(context) if context.get('locationFirst') else bool(discovery_activities(context))))


def sequential_can_discover(context):
    from backend.sequential_discovery import can_expand
    return can_expand(context)


def expand_venue_discovery(context):
    """Explicit same-area pages/refinement, ORIGINAL budget and retained IDs.

    Ten results/page; preserve all query parameters when following a token.
    No automatic page loop, widened geography or replenished budget. At most
    six pages/category across initial and alternative queries, also bounded by
    the shared search ceiling. Tokens stay in the expiring active computation.
    """
    if not can_discover(context):
        raise DiscoveryError('coverage_limit', 'More venue searches are unavailable within the retained-candidate or request limits. Other venues may exist.')
    if context.get('locationFirst'):
        from backend.sequential_discovery import expand
        expand(context)
        return
    request, outing = context['request'], context['outing']
    old = context['discovery']
    counts = {a: sum(a in v.activities for v in old.venues) for a in dict.fromkeys(request.activities)}
    available = min(outing.settings.ceiling('searches_per_outing') - outing.usage()['placesSearchRequests'],
                    outing.settings.ceiling('requests_per_outing') - outing.usage()['providerAttempts'] -
                    (outing.settings.details_per_outing - outing.usage()['placesDetailsRequests']))
    activities = discovery_activities(context)[:min(2, available)]
    queries = []
    for a in activities:
        cursor = old.paging.get(a, {})
        queries.append(DiscoveryRequest(activity=a, destination=context['area'],
            meal='dinner' if a == 'food' and (request.dinner or request.dinnerStops) else None,
            search_variant=cursor.get('variant', 'initial') if cursor.get('next') else ('mixed' if outing.settings.exploration and cursor.get('variant') == 'alternative' else 'alternative'),
            page_token=cursor.get('next')))
        context['discoveryPages'][a] = context['discoveryPages'].get(a, 0) + 1
    found = PlacesDiscovery(outing).discover_many(queries)
    from backend.venue_quality import assess_candidates
    # Retain every source/credit, while keeping rejected activity associations
    # out of the union. A new accepted observation may add an activity later.
    observations = old.venues + found.venues
    allowed = {(source.provider, source.id, a) for v in observations for source in v.sources for a in v.activities}
    merged = assess_candidates([source for v in observations for source in v.sources])
    accepted_venues = []
    for v in merged.venues:
        accepted = [a for a in v.activities if any((source.provider, source.id, a) in allowed for source in v.sources)]
        if accepted:
            accepted_venues.append(v.model_copy(update={'activities':accepted}))
    merged = merged.model_copy(update={'venues':accepted_venues})
    retained, used = [], {a: 0 for a in counts}
    for venue in merged.venues:
        accepted = [a for a in venue.activities if a in used and used[a] < outing.settings.ceiling('candidates_per_activity')]
        if accepted:
            retained.append(venue.model_copy(update={'activities': accepted}))
            for a in accepted:
                used[a] += 1
    from backend.places import DiscoveryResult
    context['discovery'] = DiscoveryResult(candidates=[], venues=retained, audit=merge_discovery_audits(old, found, retained), paging={**old.paging, **found.paging},
        excluded_count=old.excluded_count + found.excluded_count,
        diagnostics={key: old.diagnostics.get(key, 0) + found.diagnostics.get(key, 0) for key in old.diagnostics.keys() | found.diagnostics.keys()},
        stages={**({} if outing.settings.exploration else {'initial': old.stages}), 'expansion': found.stages,
                'retainedCounts': {a.value: n for a, n in used.items()},
                'newAssociations': sum(used[a] - counts[a] for a in counts),
                'candidateCapExcludedAssociations': sum(len(v.activities) for v in merged.venues) - sum(used.values())})
    context['unseenEligible'] = 0
    context['expanded'] = False
    context['width'] = 6 if len(request.activities) <= 2 else 4
