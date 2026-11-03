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
                            ConstraintIssue, PriceQuote, TravelQuote, DataStatus, ContinuationStatus)
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
    useOriginAsSearchAnchor: bool = Field(default=False, strict=True, exclude=True)
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
    # Pair keys are scoped to one immutable mode-specific outing context.
    # Reject injected/mutated contexts rather than reuse another mode's evidence.
    route_mode = 'walk' if request.transport == 'walking' else 'drive'
    if context.get('routeMode', route_mode) != route_mode or any(leg.mode != route_mode for leg in context['routes'].values()):
        raise RouteError('invalid_request', 'Travel mode changed; regenerate the outing to verify new routes.')
    context['routeMode'] = route_mode
    anchored=bool(context.get('jobs') and context['jobs'][0]['request'].area.anchor_verified)
    if anchored:
        from backend.location_context import DestinationContext
        public.destinationContext=DestinationContext(originalText=request.location,
            intent='unresolved' if request.useOriginAsSearchAnchor else 'explicit',
            status='verification_unavailable',source='confirmed_anchor',precision='representative_point',
            timezone=request.calendarTimezone)
    surprise=request.planningMode=='surprise'
    if surprise:context.setdefault('recent',set(request.recentSurpriseIds))
    pools, facts = [], {}
    hours_closed=set()
    from backend.planning_hours import venue_hours
    from backend.search_fields import enterprise_search
    for position, activity in enumerate(request.activities):
        pool = []
        for distinct in discovery.venues:
            if activity not in distinct.activities:
                continue
            fact = distinct.facts.model_copy(update={"activity": activity})
            if request.requireWheelchairAccess and fact.wheelchairAccessible is False:
                continue  # Known incompatible venues are never usable alternatives.

            hours=venue_hours(fact,request.date,start=request.startTime if request.explicitStart else None,end=request.endTime if request.explicitEnd else None,calendar_timezone=request.calendarTimezone)
            if hours['status']=='closed':
                hours_closed.add((activity.value,fact.id))
                continue
            labels = distinct_venue_labels(distinct).model_dump(mode="json")
            facts[fact.id] = fact
            pool.append(Venue(id=fact.id, name=fact.name, activity=activity,
                              hoursEvidence=hours, providerPlaceId=fact.id, address=fact.address, rating=fact.rating, ratingCount=fact.ratingCount, wheelchairAccessible=fact.wheelchairAccessible,
                              relevanceStrength=distinct.relevance[activity].status,retailParents=[p.model_dump() for p in (fact.containingPlaces or [])] or None,
                              mapsUrl=str(venue_source(fact).url), evidenceLabels=labels,
                              dataQuality=DataQuality(identity=DataStatus.verified), source="Google Maps"))
        pools.append(pool)
    diagnostics = {"placesSearchRequests": len(set(request.activities)), "placesDetailsRequests": 0,
                   "excludedCandidates": discovery.excluded_count,
                   "discoveryStages": discovery.stages, "discoveryReasons": discovery.diagnostics,
                   "usageCategories": ["Text Search Enterprise" if enterprise_search() else "Text Search Pro", "Compute Route Matrix Essentials"]}
    diagnostics['hoursExcludedCandidates']=len(hours_closed)
    diagnostics['venuePipeline'] = empty_coverage(discovery, {a.value: {v.id for v in p} for a, p in zip(request.activities, pools)})
    diagnostics['configuredLimits'] = {'candidatesPerActivity': 100 if outing.settings.exploration else outing.settings.candidates_per_activity,
        'searchesPerOuting': None if outing.settings.exploration else outing.settings.searches_per_outing, 'matrixElementsPerOuting': None if outing.settings.exploration else outing.settings.matrix_elements_per_outing}
    from backend.location_context import timezone_for
    diagnostics['locationContext']={'intent':'current_relative' if near else 'explicit',
        'resolution':'authorized_reference' if near and request.currentArea else 'representative_point' if context.get('jobs') and context['jobs'][0]['request'].area.anchor_verified else 'provider_components_required',
        'searchAnchorAvailable':bool(context.get('jobs') and context['jobs'][0]['request'].area.coordinates),
        'calendarTimezone':request.calendarTimezone or timezone_for(request.location),
        'resolvedDate':request.date.isoformat(),'timeExplicit':bool(request.explicitStart or request.explicitEnd)}
    if request.startingLocation:
        from backend.location_policy import radius,effective_max,exceeds
        from backend.venue_geography import distance_m
        point=request.startingLocation.reference_coordinates or request.startingLocation.point.coordinates
        heuristic=radius(request.firstTravel,effective_max(request.firstTravel),"walk" if request.transport=='walking' else 'drive')
        diagnostics['localCoverage']={a.value:{'nearbyHeuristic':sum(bool(point and facts[v.id].coordinates and distance_m(point,facts[v.id].coordinates)<=heuristic) for v in p),
            'distantOrUnknown':sum(not(point and facts[v.id].coordinates and distance_m(point,facts[v.id].coordinates)<=heuristic) for v in p)} for a,p in zip(request.activities,pools)}
        first_routes=[context['routes'].get((request.startingLocation.point.id,v.id)) for v in pools[0]]
        diagnostics['firstStopVerification']={'verified':sum(bool(leg and leg.status in ('ok','same_location')) for leg in first_routes),
            'overMaximum':sum(bool(leg and exceeds(leg,request.firstTravel)) for leg in first_routes) if request.firstTravel else 0,
            'awaitingEvidence':sum(not leg or leg.status not in ('ok','same_location') for leg in first_routes)}
    diagnostics['discoveryTargets']={a.value:{'uniqueRelevant':len({v.id for p in pools for v in p if v.activity==a}),'target':100} for a in set(request.activities)}
    if any(not pool for pool in pools):
        from backend.option_sessions import option_sessions
        if "token" not in context:
            context["token"] = option_sessions.create(context)
        diagnostics.update(outing.usage(), discoveredCounts=[len(p) for p in pools])
        if discovery.excluded_count and not discovery.venues and any(
                reason in discovery.diagnostics for reason in ('area_unverified','outside_destination_area')):
            error=DiscoveryError('destination_unresolved' if not request.geography.strictDestination else 'geographic_verification',
                ("We couldn't confidently locate that area. Your confirmed starting point is kept. "
                 "You can explicitly use it as a nearby search reference or correct the destination."
                 if not request.geography.strictDestination and request.planningMode!='surprise' else
                 "The requested destination boundary could not be verified. Clarify the destination; no boundary was broadened and Surprise Me will not invent an origin."))
            error.diagnostics={**diagnostics,'failureBoundary':'geography'}
            raise error
        missing=[diagnostics['venuePipeline'].get(a.value,{}) for a,pool in zip(request.activities,pools) if not pool]
        geographic_block=any(row.get('geographyRejected',0) for row in missing)
        diagnostics['failureBoundary']='geographic_filtering' if geographic_block else 'discovery_coverage'
        message=("No complete outing in the checked results. Geographic checks rejected candidates for a missing activity; the area is not proven exhausted. Explore farther or refine your destination."
            if geographic_block else "Too few matching real venues in the checked search. Search for more venues if available, or choose a different area/activity; no fictional stops were added.")
        if any(not pool and any(a==activity.value for a,_ in hours_closed) for activity,pool in zip(request.activities,pools)):message="Matching venues were reported closed throughout the requested date or time window. Change the date/time or search more places; unknown hours were not treated as closed."
        result = empty(public,message,diagnostics)
        if not geographic_block:
            result.errors=[PlanningError(code="no_relevant_venues",message=message)]
        if not discovery.venues and not anchored and not near and not discovery.excluded_count:
            result.message="No venues were returned in the checked search, and the destination could not be verified. Correct the area or explicitly use your confirmed start as a nearby search reference. Search coverage may also be limited."
            result.errors=[PlanningError(code="destination_verification_unavailable",message=result.message),PlanningError(code="no_relevant_venues",message=message)]
            result.diagnostics['failureBoundary']='destination_verification_unavailable'
        result.optionsToken = context["token"]
        result.canDiscover = can_discover(context)
        from backend.continuation_status import continuation_status
        result.continuationStatus=ContinuationStatus(**continuation_status(discovery=result.canDiscover,constrained=geographic_block))
        context["lastContinuation"]=result
        result.notes += coverage_notes(diagnostics["venuePipeline"])
        return result
    from backend.routing_shortlist import shortlist
    all_pools = pools
    diversity_evidence_needed = context.get('continuationAction',False) and any(
        any(v.id not in context.get('venueDisplayCounts',{}).get(activity.value,{}) for v in pool)
        and context.get('unseenCheckedByActivity',{}).get(activity.value,0)==0
        for activity,pool in zip(request.activities,all_pools))
    if surprise:
        from backend.surprise import venue_order
        if 'surpriseOrder' not in context:
            context['surpriseOrder']=[v.id for v in venue_order(pools[0],context['usedPrimary']|context['recent'],facts)]
        priority={identity:i for i,identity in enumerate(context['surpriseOrder'])}
        pools[0]=sorted(pools[0],key=lambda v:priority.get(v.id,len(priority)))
    frontier = all_pools
    if outing.settings.exploration or context.get("locationFirst"):
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
                if not frontiers and request.startingLocation and not surprise:
                    from backend.venue_geography import distance_m
                    point=request.startingLocation.reference_coordinates or request.startingLocation.point.coordinates
                    if point:
                        chosen=sorted(pool,key=lambda v:(
                            sum(v.id==a or (a==request.startingLocation.point.id and v.id==b) for a,b in known),
                            distance_m(point,facts[v.id].coordinates) if facts[v.id].coordinates else float('inf'),v.id))[:width]
                chosen=chosen[:width]
                if context.get('locationFirst') and frontiers:
                    from backend.routing_shortlist import balanced_following
                    previous_pool=[v for v in all_pools[len(frontiers)-1] if v.id in frontiers[-1]]
                    chosen=balanced_following(pool,previous_pool,facts,width,context.get("venueDisplayCounts",{}).get(request.activities[len(frontiers)].value,{}))
                frontiers.append({v.id for v in chosen})
            context["actionFrontier"] = frontiers
        frontier = [[v for v in pool if v.id in ids] for pool, ids in zip(pools, context["actionFrontier"])]
    if diversity_evidence_needed:
        context['width']=expansion_width(session.settings,len(request.activities))
    pools = shortlist(frontier, facts, context["width"], request.startingLocation)
    if surprise:pools[0]=frontier[0][:context['width']]
    if surprise or context.get('locationFirst'):
        from backend.routing_shortlist import balanced_following
        for i in range(1,len(pools)):pools[i]=balanced_following(frontier[i],pools[i-1],facts,context['width'],context.get('venueDisplayCounts',{}).get(request.activities[i].value,{}))
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
    from backend.routes import current_evidence
    context["routes"] = {k:v for k,v in context["routes"].items() if current_evidence(v, mode)}
    missing = [key for key in required if key not in context["routes"]]
    # Reuse evaluated alternatives. A bounded stage fills a checked pool with
    # fewer than three options; initial infeasibility may expand once below.
    primary_evidence_needed = context.get('eligiblePrimary', 3) < min(3, len(all_pools[0]))
    # Cached combinations must not indefinitely starve undisplayed venues at
    # another stop. Admit only another finite route stage, never a search.
    if missing and (context.get("unseenEligible", 0) < 3 or primary_evidence_needed or diversity_evidence_needed) and not context.get("routedThisAction") and not context.get("stopped") and (not (outing.settings.exploration or context.get("locationFirst")) or context.get("actionRouteStages", 0) < 2):
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
    if request.startingLocation:
        from backend.location_policy import exceeds
        checked_first=[context['routes'].get((request.startingLocation.point.id,v.id)) for v in all_pools[0]]
        diagnostics['firstStopVerification']={'verified':sum(bool(leg and leg.status in ('ok','same_location')) for leg in checked_first),
            'overMaximum':sum(bool(leg and exceeds(leg,request.firstTravel)) for leg in checked_first) if request.firstTravel else 0,
            'awaitingEvidence':sum(not leg or leg.status not in ('ok','same_location') for leg in checked_first)}
    capacity = outing.routing_capacity()
    pending = sum(key not in context["routes"] for key in required)
    diagnostics.update(unroutedPairs=pending, routingCapacity=capacity)
    coverage_pending = pending or any(len(p) > len(q) for p, q in zip(all_pools, pools))
    route_notice = ("The remaining route budget limits checked coverage. Other suitable venues may exist." if coverage_pending and (not capacity['elements'] or not capacity['attempts']) else
                    "We've reached a temporary routing limit. You can still browse your saved plans and try exploring again shortly." if pending and not capacity['minuteElements'] else
                    "We found more places, but we couldn't verify enough travel routes to build another complete plan yet." if pending else "")
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
        candidates=beam_candidates(request.model_copy(update={'allowRevisits':False}),pools,routes,context['seen'],audit=context.setdefault('beamAudit',{}))
    evaluated, alternatives, rejections, rejection_codes = [], [], {}, {}
    checked = 0
    travel_sets = {state: {} for state in ('compatible', 'violated', 'unverified')}
    for candidate in candidates:
        from backend.retail import intent as retail_intent
        tenant_indices=[i for i,a in enumerate(request.activities) if (retail_intent(a.value) and retail_intent(a.value).same_mall)]
        if len(tenant_indices)>1 and not set.intersection(*[{p.id for p in (facts[candidate.venues[i].id].containingPlaces or []) if p.isMall} for i in tenant_indices]):
            continue # Shared-mall requirement is hard; never infer from proximity.
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
        if anchored:
            plan.issues.append(ConstraintIssue(code="approximate_destination",field="location",status="unknown",
                message="Search prioritizes the requested area near your confirmed reference. Exact neighborhood membership is not verified; check the actual venue addresses."))
        if request.dinner or request.dinnerStops:
            plan.issues.append(ConstraintIssue(code="unverified_dinner", field="availability", status="unknown",
                message="Dinner service is not verified for these restaurants. Check the displayed hours and confirm dinner availability."))
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
                if exceeds(routes[a.id,b.id],request.betweenTravel,original=True) and not exceeds(routes[a.id,b.id],request.betweenTravel):
                    plan.issues.append(ConstraintIssue(code='extra_between_travel',field='travel',status='unknown',
                        message=f'Journey {i+1} between activities exceeds your original preference, within the doubled flexible maximum.'))
        plan.feasibility="violated" if any(i.status=="violation" for i in plan.issues) else "provisional"
        if request.startingLocation:
            first = routes[request.startingLocation.point.id, candidate.venues[0].id]
            plan.firstLeg = {"source":request.startingLocation.source,"originLabel":request.startingLocation.label,"mode":mode,
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
        from backend.travel_classification import classify
        plan.travelClassification,plan.travelDeviations=classify(request,plan,routes,request.startingLocation)
        if plan.feasibility == "violated":
            if all(i.field=="travel" for i in plan.issues if i.status=="violation"):
                alternatives.append(plan)
            for issue in plan.issues:
                if issue.status == "violation":
                    rejection_codes[issue.code] = rejection_codes.get(issue.code, 0) + 1
                    rejections[issue.message] = rejections.get(issue.message, 0) + 1
        else:
            (evaluated if plan.travelClassification=="matching" else alternatives).append(plan)
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
    # Score alternatives using the same evidence; retain the original violation
    # issues/state on the returned plan rather than pretending they passed.
    scored_alternatives=[]
    for plan in alternatives:
        if plan.candidate.id in context['seen'] or surprise and not quality_qualified(plan):continue
        safe=plan.model_copy(deep=True,update={'feasibility':'provisional','issues':[i for i in plan.issues if i.status!='violation']})
        scored=score_candidates(public,[safe])[0]
        from backend.travel_classification import deviation_penalty
        plan.score=max(0,scored.score-deviation_penalty(request,plan,routes,request.startingLocation))
        plan.components=scored.components
        plan.explanations=[e for e in scored.explanations if e.code not in ("feasibility",)]
        scored_alternatives.append(plan)
    scored_alternatives.sort(key=lambda p:({'outside_preference':0,'unverified':1,'beyond_limit':2}[p.travelClassification],-p.score,p.candidate.id))
    # Never mix requirements-matching and beyond-requirements cards on a page.
    available=[p for p in scored_alternatives if p.travelClassification!='beyond_limit' or context.get('showBeyond',False)]
    if not ranked and available:
        category=available[0].travelClassification
        ranked=[p for p in available if p.travelClassification==category]

    if request.betweenTravel and request.betweenTravel.mode=='flexible':
        for plan in ranked:
            if not any(i.code=='extra_between_travel' for i in plan.issues):plan.score=min(1,plan.score+.05)
        ranked.sort(key=lambda p:-p.score)
    # Modest preference bonus: quality can still outweigh extra first-leg travel.
    if request.firstTravel and request.firstTravel.mode=='flexible':
        for plan in ranked:
            if not plan.firstLeg['exceedsPreference']:plan.score+=.05
        ranked.sort(key=lambda plan:(-plan.score,plan.candidate.id))
    from backend.retail import intent as retail_intent
    import re
    for plan in ranked:
        preferred=sum(bool((retail_intent(v.activity.value) and retail_intent(v.activity.value).outlet) and re.search(r'\boutlet\b|\bfactory\b',v.name,re.I)) for v in plan.candidate.venues)
        if preferred:
            plan.score=min(1,plan.score+.015*preferred/len(plan.candidate.venues))
            plan.components['retailFormatPreference']=.015*preferred/len(plan.candidate.venues)
    ranked.sort(key=lambda plan:(-plan.score,(plan.totalTravel+((plan.firstLeg or {}).get('minutes') or 0)) if plan.totalTravel is not None and (not plan.firstLeg or plan.firstLeg.get('minutes') is not None) else float('inf'),plan.candidate.id))
    for plan in ranked:
        ids=[v.id for v in plan.candidate.venues]
        pairs=list(zip(ids,ids[1:]))
        if request.startingLocation:pairs.insert(0,(request.startingLocation.point.id,ids[0]))
        legs=[routes.get(pair) for pair in pairs]
        plan.components['verifiedTravelSeconds']=sum(l.duration_seconds for l in legs) if all(l and l.status in ('ok','same_location') for l in legs) else 1e12
    ranked.sort(key=lambda p:(p.travelClassification!='matching',p.components['verifiedTravelSeconds'],-p.score,p.candidate.id))
    diagnostics["unseenEligibleCombinations"] = len(ranked)
    beyond_available=any(p.travelClassification=='beyond_limit' for p in scored_alternatives)
    from backend.travel_classification import limit_notice
    compliance_notice=limit_notice(request) if not ranked and beyond_available else None
    diagnostics['beyondLimitOptIn']=bool(context.get('showBeyond',False))
    diagnostics['withheldBeyondLimitCombinations']=sum(p.travelClassification=='beyond_limit' for p in scored_alternatives) if not context.get('showBeyond') else 0
    # Retain useful shared stops when only one activity has alternatives.
    if surprise:
        from backend.surprise import select
        diverse=select(ranked,3,context,facts)
    else:
        from backend.travel_classification import select_diverse
        diverse = select_diverse(ranked,3,context)
    previous_known=context.get('rankingKnownIds',set())
    current_known={v.id for pool in all_pools for v in pool}
    newly_discovered=current_known-previous_known if previous_known else set()
    previous_eligible=context.get('rankingEligibleIds',set())
    def journey_minutes(p):
        first=p.firstLeg.get('minutes') if p.firstLeg else 0
        return p.totalTravel+first if p.totalTravel is not None and first is not None else None
    diagnostics['rankingAudit']={'knownVenues':len(current_known),'newVenuesSincePreviousResponse':len(newly_discovered),
        'eligibleVerified':len([p for p in ranked if p.travelClassification=='matching']),
        'deferredEligible':max(0,len(ranked)-len(diverse)),
        'lateArrivalReason':'new_discovery' if newly_discovered else 'remaining_known_combinations' if previous_known else 'initial_staged_coverage',
        'selected':[{'score':p.score,'components':p.components,'interStopMinutes':p.totalTravel,
            'firstStopMinutes':p.firstLeg.get('minutes') if p.firstLeg else None,
            'newVenue':any(v.id in newly_discovered for v in p.candidate.venues),
            'lateReason':'new_discovery' if any(v.id in newly_discovered for v in p.candidate.venues) else 'remaining_ranked_combination' if p.candidate.id in previous_eligible else 'newly_verified_known_venues' if previous_known else 'initial_staged_coverage',
            'shorterThanPreviouslyShown':bool(journey_minutes(p) is not None and context.get('shortestShownJourney') is not None and journey_minutes(p)<context['shortestShownJourney'])} for p in diverse]}
    context['rankingEligibleIds']=previous_eligible|{p.candidate.id for p in ranked}
    known_journeys=[journey_minutes(p) for p in diverse if journey_minutes(p) is not None]
    if context.get('shortestShownJourney') is not None:known_journeys.append(context['shortestShownJourney'])
    if known_journeys:context['shortestShownJourney']=min(known_journeys)
    context['rankingKnownIds']=current_known
    diagnostics["selectedPrimaryCandidates"] = len({p.candidate.venues[0].id for p in diverse})
    context['eligiblePrimary'] = diagnostics['eligiblePrimaryCandidates']
    primary_shortage = context['eligiblePrimary'] < min(3, len(all_pools[0]))
    if (len(diverse) < 3 or primary_shortage) and not context["expanded"] and not context.get("stopped") and any(len(p) > len(q) for p, q in zip(all_pools, pools)):
        context["expanded"] = True
        context["primaryCoverageExpanded"] = primary_shortage
        context["routedThisAction"] = False
        context["width"] = expansion_width(session.settings, len(request.activities))
        return real_plans(request, session, context=context)
    if (context.get('locationFirst') and not context.get('continuationAction')
            and not context.get('adaptiveDiscoveryDone') and not context.get('stopped')
            and capacity['minuteElements']>0 and capacity['attempts']>0
            and len({p.candidate.venues[0].id for p in diverse})<3 and can_discover(context)):
        context['adaptiveDiscoveryDone']=True
        try:
            expand_venue_discovery(context)
            context['routedThisAction']=False
            return real_plans(request,session,context=context)
        except (DiscoveryError,ProviderLimitError,RouteError) as error:
            # A later quality-improvement failure must not erase useful plans.
            context['stopped']=True;outing.stop_reason=str(error)
            route_notice=str(error)
    batches, shown = [], {p.candidate.id for p in diverse}
    from backend.venue_details import details_sessions
    from backend.option_sessions import option_sessions
    context["usedPrimary"].update(p.candidate.venues[0].id for p in ranked if p.candidate.id in shown)
    context["seen"].update(shown)
    for plan in diverse:
        for venue in plan.candidate.venues:
            counts=context.setdefault('venueDisplayCounts',{}).setdefault(venue.activity.value,{})
            counts[venue.id]=counts.get(venue.id,0)+1
    diagnostics['displayedVenuesByActivity']={a:len(counts) for a,counts in context.get('venueDisplayCounts',{}).items()}
    diagnostics['travelClassifications']={category:sum(p.travelClassification==category for p in evaluated+alternatives) for category in ('matching','outside_preference','beyond_limit','unverified')}
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
    continuable=qualified+[p for p in scored_alternatives if p.travelClassification!='beyond_limit' or context.get('showBeyond',False)]
    context["unseenEligible"] = sum(p.candidate.id not in context["seen"] for p in continuable)
    context["routedThisAction"] = False
    context['unseenCheckedByActivity']={a.value:len({v.id for p in continuable
        if p.candidate.id not in context['seen'] for v in p.candidate.venues
        if v.activity==a and v.id not in context.get('venueDisplayCounts',{}).get(a.value,{})}) for a in set(request.activities)}
    diagnostics.update(outing.usage())
    diagnostics['venuePipeline'] = planning_coverage(discovery, all_pools, pools, request.activities,
        routes, travel_sets, [p for p in evaluated+alternatives if p.feasibility!="violated"], ranked, diverse, [p for p in ranked if p.candidate.id in shown], context)
    from backend.planning_diagnostics import bottlenecks
    diagnostics['discoveryBottlenecks']=bottlenecks(context,all_pools,pools,routes,ranked,diverse,pending)
    diagnostics['primaryCoverageExpansion'] = context.get('primaryCoverageExpanded', False)
    if context.get('referenceScoring'):diagnostics['referenceScoring']=context['referenceScoring']
    # Retained inventory alone is not useful work once the bounded frontier and
    # its routes are checked. Missing directed pairs remain explicit work.
    from backend.continuation_status import known_route_work
    known_pending=known_route_work(context,request,all_pools,facts,routes,mode)
    can_expand = not context.get("stopped") and (context["unseenEligible"] > 0 or (
        capacity['elements'] > 0 and capacity['attempts'] > 0 and (pending > 0 or
        known_pending or (not context["expanded"] and any(len(p) > len(q) for p, q in zip(all_pools, pools))))))
    classified_error = None
    if not diverse and route_notice:
        from backend.failures import MESSAGES
        codes={leg.error_code for leg in context['routes'].values()}
        category=('provider_quota_rejected' if 'quota' in codes else
                  'provider_service_error' if codes & {'provider','authentication','permission','timeout','invalid_response'} else 'insufficient_routing')
        # Preserve the more specific local minute/budget recovery instructions.
        if category!='insufficient_routing': route_notice=MESSAGES[category]
        classified_error=PlanningError(code=category,message=route_notice)
    from backend.continuation_status import continuation_status
    continuation=continuation_status(combinations=context['unseenEligible']>0,discovery=can_discover(context),
        pending=can_expand and context['unseenEligible']==0,constrained=bool(compliance_notice or rejections) and not diverse,
        limited=bool(context.get('stopped')) or bool(coverage_pending and (not capacity['elements'] or not capacity['attempts'] or not capacity['minuteElements'])))
    result = RankingResult(request=distinct_request, dataMode="real", continuationStatus=continuation, provisionalPlans=[p for p in diverse if p.feasibility=="provisional"], explorationPlans=[p for p in diverse if p.feasibility=="violated"], detailsToken=details_token,
        alternativeBatches=batches, optionsToken=context["token"], canExpand=can_expand, canDiscover=can_discover(context), canShowBeyond=beyond_available,
        diagnostics=diagnostics, message=(route_notice or compliance_notice or continuation["message"]) if not diverse else f"{len(diverse)} provisional real-venue options. Prices, hours and availability need confirmation.",
        errors=[] if diverse else [classified_error] if classified_error else [PlanningError(code="insufficient_data",message=compliance_notice)] if compliance_notice and not route_notice else [PlanningError(code="infeasible", message=m) for m in rejections] or [PlanningError(code="insufficient_data" if pending else "no_availability", message=route_notice if pending else continuation["message"])],
        notes=['Development local discovery/routing coverage: '+json.dumps({'localCoverage':diagnostics.get('localCoverage'),'firstStopVerification':diagnostics.get('firstStopVerification')},sort_keys=True),'Development location context: '+json.dumps(diagnostics['locationContext'],sort_keys=True)]+['Development per-activity discovery targets: '+json.dumps(diagnostics['discoveryTargets'],sort_keys=True), 'Development travel classifications: '+json.dumps(diagnostics['travelClassifications'],sort_keys=True),'Development displayed activity coverage: '+json.dumps(diagnostics['displayedVenuesByActivity'],sort_keys=True),'Development discovery bottlenecks: '+json.dumps(diagnostics['discoveryBottlenecks'],sort_keys=True)]+(["Surprise Me begins at the first activity; no journey from your location is planned. Quality-qualified weighted sampling favors unseen first venues. Repeated first venues may be needed when the checked pool is exhausted; further suitable venues may exist.",
                "Development Surprise coverage: "+json.dumps(diagnostics['surprise'],sort_keys=True)+f"; quality-excluded complete paths {diagnostics['surpriseQualityExcluded']}."] if surprise else []) + (["Development starting-area comparison: "+json.dumps(context['referenceScoring'],sort_keys=True)] if context.get('referenceScoring') else []) + (["Location-first discovery: multiple earlier-stop anchors and bounded route-evidence beam. Flexible first-stop maximum is twice the entered preference. Search coverage is not city-wide exhaustion.",
                   "Destination is a preference with a bounded nearby search unless Only within or explicit regional exclusions were requested."] if context.get('locationFirst') else []) + (["Development exploration active: finite discovery/route batches, persistent estimated usage accounting; daily warning is nonblocking. Cloud quota remaining is unknown.",
            f"Development usage — Text Searches {outing._dispatched['search']} dispatched ({outing._pagination} pagination reservations), Details {outing._dispatched['details']}, Matrix requests {outing._dispatched['matrix']}, elements {outing._dispatched['matrixElements']}. "
            f"Conservative reserved work: {outing._searches} searches, {outing._details} Details, {outing._matrix_requests} matrices / {outing._elements} elements. "
            f"Estimated gross: outing ${outing._gross/1000000:.3f}, local day ${diagnostics['estimatedDayGrossUsd']:.3f}; warning threshold ${diagnostics['warningThresholdUsd']:.2f} (nonblocking; {'reached' if diagnostics['estimatedUsageWarning'] else 'not reached'}). "
            "Estimates include failed/unsent batch reservations, exclude allowances/credits and unrelated usage; not verified Cloud billing."] if outing.settings.exploration else [f"Current application ceilings: {outing.settings.candidates_per_activity} retained venues per activity; {outing.settings.searches_per_outing} searches and {outing.settings.matrix_elements_per_outing} route elements per outing."]) + coverage_notes(diagnostics["venuePipeline"]) + ([route_notice] if route_notice else []) + ["Matching venue coverage: " + "; ".join(f"{activity.value}: {len(pool)}" for activity, pool in zip(request.activities, all_pools)) + ". This is limited search coverage, not a city-wide venue count.",
               "Real venues from Google Maps; activity categories reflect search context and need confirmation.",
               "Real prices, activity durations, hours, showtimes and reservations are unknown. No budget is confirmed.",
               "Driving uses current Google traffic estimates; actual times may change. Walking routes are beta and may omit sidewalks or pedestrian paths.",
               "Inter-stop travel excludes the first trip and return home. An explicitly shared start is shown separately.",
               ("Exploration retains eligible candidates across finite actions; searched coverage is not city-wide exhaustion." if outing.settings.exploration else f"Up to {session.settings.candidates_per_activity} relevant candidates per activity can be retained through explicit search expansion. These results do not cover every venue in the city.")])

    context["lastContinuation"]=result
    return result


def empty(request, message, diagnostics=None):
    return RankingResult(request=request, dataMode="real", message=message,
                         errors=[PlanningError(code="insufficient_data", message=message)], diagnostics=diagnostics or {},
                         notes=["Search coverage is limited; these results do not cover every venue in the city."] if diagnostics and diagnostics.get("placesSearchRequests") else [])


def more_real_plans(token, *, expand_discovery=False, show_beyond=False):
    from backend.option_sessions import option_sessions
    context, lock = option_sessions.get(token)
    if context.get('mockSurprise'):raise DiscoveryError('mode_changed','This outing uses mock data. Generate again in the current data mode.')
    context["session"].settings.require_live_provider()
    if context["request"].startingLocation is None and context["request"].planningMode!='surprise':
        raise DiscoveryError("origin_required","This older outing needs a confirmed starting point. Choose where your outing starts and generate again.")
    if not lock.acquire(blocking=False):
        raise DiscoveryError("busy", "Another options request is running. Wait for it to finish.")
    try:
        from backend.location_context import outing_problem
        problem=outing_problem(context['request'])
        if problem:raise DiscoveryError(problem[0],problem[1])
        previous=context.get('lastContinuation')
        if previous and not show_beyond and not (previous.canDiscover if expand_discovery else previous.canExpand):
            return previous.model_copy(update={'plans':[],'provisionalPlans':[],'explorationPlans':[],'alternativeBatches':[],
                'message':previous.continuationStatus.message if previous.continuationStatus else previous.message,'errors':[]})
        if context.get("stopped"):
            raise DiscoveryError("stopped", "Search expansion stopped after an earlier provider or budget failure. No automatic retry is available.")
        context["routedThisAction"] = False
        context["actionRouteStages"] = 0
        context["actionDiscoveryCalls"] = 0
        context["continuationAction"] = True
        context["showBeyond"] = show_beyond
        if context["request"].planningMode=='surprise':
            context.pop('surpriseOrder',None);context.pop('actionFrontier',None);context['expanded']=False
        if context['outing'].settings.exploration or context.get('locationFirst'):
            if expand_discovery or context.get('unseenEligible', 0) < 3:
                context.pop('actionFrontier', None)
            context['expanded'] = False
        if expand_discovery:
            expand_venue_discovery(context)
        result = real_plans(context["request"], context["session"], context=context)
        if not (result.provisionalPlans or result.explorationPlans) and not context["expanded"]:
            context["expanded"] = True
            # Larger inventory is staged, never sent as an all-pairs matrix.
            context["width"] = expansion_width(context["session"].settings, len(context["request"].activities))
            result = real_plans(context["request"], context["session"], context=context)
        return result
    except (DiscoveryError, ProviderLimitError, RouteError) as error:
        temporary= (isinstance(error,ProviderLimitError) or getattr(error,'code',None)=='application_limit') and ('minute' in str(error).lower() or 'cancelled' in str(error).lower())
        context["stopped"] = not temporary
        context['outing'].stop_reason = str(error)
        from backend.continuation_status import continuation_status
        previous=context.get('lastContinuation')
        error.continuation={'canExpand':bool(previous and previous.canExpand and temporary),
            'canDiscover':bool(previous and previous.canDiscover and temporary),
            'status':continuation_status(limited=True)}
        from backend.provider_errors import attach_accounting
        raise attach_accounting(error,context['outing'])
    finally:
        lock.release()


def discovery_activities(context):
    settings = context['session'].settings
    return [a for a in dict.fromkeys(context['request'].activities)
            if sum(a in v.activities for v in context['discovery'].venues) < min(100,settings.ceiling('candidates_per_activity'))
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
        accepted = [a for a in venue.activities if a in used and used[a] < min(100,outing.settings.ceiling('candidates_per_activity'))]
        if accepted:
            retained.append(venue.model_copy(update={'activities': accepted}))
            for a in accepted:
                used[a] += 1
    from backend.places import DiscoveryResult
    context['discovery'] = DiscoveryResult(candidates=[], venues=retained, observed={a:old.observed.get(a,set())|found.observed.get(a,set()) for a in old.observed.keys()|found.observed.keys()}, audit=merge_discovery_audits(old, found, retained), paging={**old.paging, **found.paging},
        excluded_count=old.excluded_count + found.excluded_count,
        diagnostics={key: old.diagnostics.get(key, 0) + found.diagnostics.get(key, 0) for key in old.diagnostics.keys() | found.diagnostics.keys()},
        stages={**({} if outing.settings.exploration else {'initial': old.stages}), 'expansion': found.stages,
                'retainedCounts': {a.value: n for a, n in used.items()},
                'newAssociations': sum(used[a] - counts[a] for a in counts),
                'candidateCapExcludedAssociations': sum(len(v.activities) for v in merged.venues) - sum(used.values())})
    context['unseenEligible'] = 0
    context['expanded'] = False
    context['width'] = 6 if len(request.activities) <= 2 else 4
