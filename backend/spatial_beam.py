"""Bounded route-evidence beam, retaining several primary venues at each depth."""
from backend.planner import _walk


def candidates(request,pools,routes,seen,width=96):
    beam=[()]
    for index,pool in enumerate(pools):
        next_paths=[]
        for path in beam:
            for venue in pool:
                if any(v.id==venue.id for v in path):continue
                if path:
                    route=routes.get((path[-1].id,venue.id))
                    if not route or route.status not in ('ok','same_location'):continue
                extended=path+(venue,)
                if index==len(pools)-1 and next(_walk(request,[[v] for v in extended])).id in seen:continue
                next_paths.append(extended)
        def score(path):
            travel=sum(routes[a.id,b.id].duration_seconds for a,b in zip(path,path[1:]))
            quality=sum(v.rating or 0 for v in path)
            return travel-quality*15,tuple(v.id for v in path)
        next_paths.sort(key=score)
        groups={}
        for path in next_paths:groups.setdefault(path[0].id,[]).append(path)
        beam=[]
        for row in range(width):
            for group in groups.values():
                if row<len(group):beam.append(group[row])
                if len(beam)>=width:break
            if len(beam)>=width:break
        if not beam:break
    result=[]
    for path in beam:
        if len(path)!=len(pools):continue
        candidate=next(_walk(request,[[v] for v in path]))
        if candidate.id not in seen:result.append(candidate)
    return result
