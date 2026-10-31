"""Bounded route-evidence beam, retaining several primary venues at each depth."""
from backend.planner import _walk


def candidates(request,pools,routes,seen,width=96,audit=None):
    if audit is not None:audit.update(expandedPaths=0,prunedPaths=0,previouslyShownRemoved=0)
    beam=[()]
    for index,pool in enumerate(pools):
        next_paths=[]
        for path in beam:
            for venue in pool:
                if any(v.id==venue.id for v in path):continue
                if path:
                    route=routes.get((path[-1].id,venue.id))
                    if not route or route.status=='unreachable':continue
                extended=path+(venue,)
                if index==len(pools)-1 and next(_walk(request,[[v] for v in extended])).id in seen:
                    if audit is not None:audit['previouslyShownRemoved']+=1
                    continue
                next_paths.append(extended)
        def score(path):
            legs=[routes.get((a.id,b.id)) for a,b in zip(path,path[1:])]
            origin=getattr(request,'startingLocation',None)
            if origin:legs.insert(0,routes.get((origin.point.id,path[0].id)))
            route_unknown=sum(not leg or leg.status not in ('ok','same_location') or leg.duration_seconds is None for leg in legs)
            travel=sum(leg.duration_seconds for leg in legs if leg and leg.duration_seconds is not None)
            quality=sum(v.rating or 0 for v in path)
            # Preserve compliant partial paths before high-rated distant ones.
            # Unknown evidence is not compliance; retain it only behind verified paths.
            from backend.location_policy import exceeds,FirstTravel
            checks=[]
            origin=getattr(request,'startingLocation',None)
            first=request.firstTravel or (FirstTravel(value=float(request.maxFirstLegTravel),exclusive=request.maxFirstLegTravelExclusive) if request.maxFirstLegTravel is not None else None)
            if origin and first:
                checks.append((routes.get((origin.point.id,path[0].id)),first))
            if request.betweenTravel:
                checks.extend((routes.get((a.id,b.id)),request.betweenTravel) for a,b in zip(path,path[1:]))
            violations=sum(bool(exceeds(leg,p)) for leg,p in checks if leg and leg.status in ('ok','same_location'))
            unknown=sum(not leg or leg.status not in ('ok','same_location') for leg,_ in checks)
            return violations,unknown+route_unknown,travel-quality*15,tuple(v.id for v in path)
        next_paths.sort(key=score)
        expanded_count=len(next_paths)
        beam=[]
        usage={}
        while next_paths and len(beam)<width:
            # A finite shortlist-quality band, then coverage across every depth.
            near=next_paths[:max(width,12)]
            chosen=min(near,key=lambda path:(sum(usage.get((i,v.id),0) for i,v in enumerate(path)),score(path)))
            beam.append(chosen);next_paths.remove(chosen)
            for i,v in enumerate(chosen):usage[i,v.id]=usage.get((i,v.id),0)+1
        if audit is not None:
            audit['expandedPaths']+=expanded_count
            audit['prunedPaths']+=max(0,expanded_count-len(beam))
        if not beam:break
    result=[]
    for path in beam:
        if len(path)!=len(pools):continue
        candidate=next(_walk(request,[[v] for v in path]))
        if candidate.id not in seen:result.append(candidate)
    return result
