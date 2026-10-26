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
                    'duplicatesRemoved', 'relevanceRejected', 'searchRequests', 'pagesFollowed'):
            row[key] = row.get(key, 0) + addition.get(key, 0)
        row['duplicatesRemoved'] += len(overlap)
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
