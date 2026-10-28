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
            travel=sum((routes[a.id,b.id].duration_seconds or 0) for a,b in zip(path,path[1:]))
            quality=sum(v.rating or 0 for v in path)
            return travel-quality*15,tuple(v.id for v in path)
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
