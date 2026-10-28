"""Aggregate-only coverage accounting; never return identities or private input."""
from copy import deepcopy


def _ids(venues, activity):
    return {v.facts.id for v in venues if activity in v.activities}


def merge_discovery_audits(old, found, retained):
    result = deepcopy(old.audit)
    for activity, addition in found.audit.items():
        row = result.setdefault(activity, {})
        known = _ids(old.venues, activity)
        incoming = _ids(found.venues, activity)
        kept = _ids(retained, activity)
        overlap = known & incoming
        for key in ('googleResultsReceived', 'geographyRejected', 'normalizationRejected', 'mealRejected',
                    'duplicatesRemoved', 'relevanceRejected', 'normalizationPassed', 'relevancePassed', 'searchRequests', 'pagesFollowed'):
            row[key] = row.get(key, 0) + addition.get(key, 0)
        row['duplicatesRemoved'] += len(overlap)
        row['uniqueGoogleVenues']=len(old.observed.get(activity,set())|found.observed.get(activity,set()))
        row['newGoogleVenues']=len(found.observed.get(activity,set())-old.observed.get(activity,set()))
        row['knownGoogleVenues']=len(found.observed.get(activity,set())&old.observed.get(activity,set()))
        for key in ('geographyReasons', 'relevanceRejectedByReason', 'searchStrategies'):
            counts = row.setdefault(key, {})
            for reason, count in addition.get(key, {}).items():
                counts[reason] = counts.get(reason, 0) + count
        row['candidateCapExcluded'] = row.get('candidateCapExcluded', 0) + len((known | incoming) - kept)
        row.update(requestedPageSize=addition['requestedPageSize'], geographyPolicy=addition['geographyPolicy'],
                   eligibleRetained=len(kept), latestSearch={'newEligibleMatches': len(incoming - known),
                   'previouslyKnownMatches': len(overlap), 'newlyRetained': len(kept - known)})
    return result


def empty_coverage(discovery, pools):
    result = deepcopy(discovery.audit)
    for activity, pool in pools.items():
        result.setdefault(activity, {}).update(eligibleRetained=len(pool), shortlistedForRouting=0,
            selectedForRouting=0, selectedForRoutingCumulative=0, notInCheckedCompletePath=0, routeCompatibleVenues=0, routeUnverifiedVenues=0,
            excludedByCheckedRouteFeasibility=0, rankedVenues=0, unusedRankedVenues=0, withinBestScoreWindow=0,
            selectedVenues=0, offeredThisResponse=0, offeredInSession=0)
    return result


def planning_coverage(discovery, all_pools, pools, activities, routes, travel_sets, evaluated, ranked, selected, offered, context):
    retained = {a.value: {v.id for p in all_pools for v in p if v.activity == a} for a in activities}
    result = empty_coverage(discovery, retained)
    routed = {identity for pair in routes for identity in pair}
    best = ranked[0].score if ranked else 0
    for activity, ids in retained.items():
        def represented(plans):
            return {v.id for p in plans for v in p.candidate.venues if v.activity == activity}
        passed = travel_sets['compatible'].get(activity, set())
        failed = travel_sets['violated'].get(activity, set())
        unknown = travel_sets['unverified'].get(activity, set())
        session_offered = context.setdefault('offeredByActivity', {}).setdefault(activity, set())
        current_offered = represented(offered)
        session_offered.update(current_offered)
        shortlisted = {v.id for p in pools for v in p if v.activity == activity}
        result[activity].update(
            shortlistedForRouting=len(shortlisted),
            selectedForRouting=len(shortlisted & routed), selectedForRoutingCumulative=len(ids & routed),
            notInCheckedCompletePath=len(shortlisted - passed - failed - unknown), routeCompatibleVenues=len(passed),
            routeUnverifiedVenues=len(unknown - passed), excludedByCheckedRouteFeasibility=len(failed - passed - unknown),
            rankedVenues=len(represented(evaluated)), unusedRankedVenues=len(represented(ranked)), withinBestScoreWindow=len(represented([p for p in ranked if p.score >= best - .15])),
            selectedVenues=len(represented(selected)), offeredThisResponse=len(current_offered), offeredInSession=len(session_offered))
    return result


def coverage_notes(coverage):
    labels = {
        'arcade_without_bowling_evidence': 'arcades without bowling evidence',
        'activity_evidence_required': 'no supporting activity evidence',
        'unrelated_business_type': 'unrelated business types',
        'conflicting_business_name': 'conflicting business descriptions',
        'incompatible_venue_type': 'incompatible venue types',
        'incompatible_venue_name': 'incompatible venue names',
        'dinner_cafe_without_restaurant_evidence': 'cafes without restaurant evidence',
        'different_named_area_or_region': 'named area or region not matched',
        'missing_local_area_evidence': 'missing local-area evidence',
        'outside_radius': 'outside the authorized radius',
    }
    def reasons(row):
        return '; '.join(f"{count} {labels.get(reason, 'other evidence conflicts')}"
                         for key in ('geographyReasons', 'relevanceRejectedByReason')
                         for reason, count in row.get(key, {}).items()) or 'none'
    return [f"Latest backend coverage — {a}: {r.get('googleResultsReceived', 0)} Google results received; "
            f"{r.get('geographyRejected', 0)} rejected by area; {r.get('duplicatesRemoved', 0)} duplicates removed; "
            f"{r.get('normalizationRejected', 0)} invalid normalized records; "
            f"{r.get('relevanceRejected', 0)} activity mismatches; {r['eligibleRetained']} venues retained; "
            f"{r['shortlistedForRouting']} shortlisted; {r['selectedForRouting']} selected for travel checks; "
            f"{r['excludedByCheckedRouteFeasibility']} excluded from checked paths by travel; "
            f"{r['routeUnverifiedVenues']} with unverified travel; {r['rankedVenues']} represented in ranking; "
            f"{r['unusedRankedVenues']} in unused ranked options "
            f"({r['withinBestScoreWindow']} near the best score). Latest search: "
            f"{r.get('latestSearch', {}).get('newEligibleMatches', 0)} new eligible matches, "
            f"{r.get('latestSearch', {}).get('previouslyKnownMatches', 0)} already known. "
            f"Exclusion reasons: {reasons(r)}. "
            "Counts describe checked coverage, including queued options, not every venue in the area."
            for a, r in coverage.items()]



def bottlenecks(context,all_pools,pools,routes,ranked,selected,pending):
    from backend.location_policy import exceeds,FirstTravel
    request=context['request'];start=request.startingLocation
    first=[v.id for v in all_pools[0]]
    compliant=violated=unknown=0
    for identity in first:
        if not start:continue
        leg=routes.get((start.point.id,identity))
        if not leg or leg.status not in ('ok','same_location'):
            unknown+=1;continue
        limits=[p for p in (request.firstTravel,
            FirstTravel(value=float(request.maxFirstLegTravel),exclusive=request.maxFirstLegTravelExclusive) if request.maxFirstLegTravel is not None else None) if p]
        if any(exceeds(leg,p) for p in limits):violated+=1
        else:compliant+=1
    reasons=[]
    ranked_first=len({p.candidate.venues[0].id for p in ranked})
    displayed=len({p.candidate.venues[0].id for p in selected})
    if len(first)<3:reasons.append('limited_discovered_primary_supply')
    if any(r.get('geographyRejected',0) for r in context['discovery'].audit.values()):reasons.append('geographic_filtering')
    if any(r.get('relevanceRejected',0) for r in context['discovery'].audit.values()):reasons.append('activity_filtering')
    if violated:reasons.append('verified_first_limit_violation')
    if unknown:reasons.append('first_route_unverified')
    if pending or len(first)>len(pools[0]):reasons.append('routing_work_pending')
    if ranked_first>displayed:reasons.append('ranking_or_three_card_selection')
    if context.get('stopped'):reasons.append('provider_or_admission_failure')
    if context.get('beamAudit',{}).get('prunedPaths',0):reasons.append('beam_computation_bound')
    stage=('none_three_distinct_options' if displayed>=3 else
           'selection' if ranked_first>=3 else
           'route_or_work_coverage' if unknown or pending else
           'verified_first_limit' if violated else 'discovered_eligible_supply')
    return {'shortageStage':stage,'discoveredFirstVenues':len(first),'firstVenuesInRouteShortlist':len(pools[0]),
        'firstVenuesOutsideRouteShortlist':len(first)-len(pools[0]),
        'firstRouteCompliant':compliant,'firstRouteNoncompliant':violated,'firstRouteUnknown':unknown,
        'originJourneyApplicable':bool(start),'rankedFirstVenues':ranked_first,'displayedFirstVenues':displayed,
        'routePairsAwaitingEvaluation':pending,'searchedRegions':len(context.get('searchedAreas',())),
        'pendingSearchStrategies':sum(not j['done'] for j in context.get('jobs',[])),
        'completeSignaturesPreviouslyShown':len(context['seen']),
        'beam':context.get('beamAudit',{}),'latestExploration':context.get('latestExploration',{}),'reasonCodes':reasons}
