"""Public continuation state, independent of ranking and diagnostic internals."""

def continuation_status(*, combinations=False, discovery=False, pending=False, constrained=False, limited=False):
    if limited:
        return {'kind':'provider_limited','message':'Further search or route checks are limited right now. Your existing pages and original preferences are kept. Review the provider limit before trying again.'}
    if combinations:
        return {'kind':'available','message':'More combinations from the places already checked are available.'}
    if pending:
        return {'kind':'pending_routes','message':'More places are known, but their routes still need checking. Show different options can check the next bounded batch.'}
    if constrained:
        return {'kind':'constraints','message':'No more checked options fit your original requirements. Your limits are unchanged; adjust them explicitly or explore another area.'}
    if discovery:
        return {'kind':'discovery_remaining','message':"We've shown the available combinations from the places checked so far. Explore farther to discover more."}
    return {'kind':'search_exhausted','message':"We can't find any more options for this outing right now. Try a different area or change your preferences."}


def known_route_work(context,request,pools,facts,routes,mode):
    """Only missing pairs the current bounded planner would consider useful."""
    from backend.location_policy import radius,effective_max
    from backend.venue_geography import distance_m
    threshold=radius(request.betweenTravel,effective_max(request.betweenTravel),mode) if request.betweenTravel else max(250,(request.maxLegTravel if request.maxLegTravel is not None else 10)*(80 if mode=='walk' else 600))
    for i,(left,right) in enumerate(zip(pools,pools[1:])):
        for a in left:
            for b in right:
                if a.id==b.id or (a.id,b.id) in routes:continue
                x,y=facts[a.id].coordinates,facts[b.id].coordinates
                if not context.get('locationFirst') or (x and y and distance_m(x,y)<=threshold) or (i,a.id,b.id) in context.get('spatialEdges',set()):
                    return True
    return bool(request.startingLocation and any((request.startingLocation.point.id,v.id) not in routes for v in pools[0]))
