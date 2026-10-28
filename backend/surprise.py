"""Transient novelty-aware weighted sampling. No provider I/O or durable history."""
from math import log
from random import SystemRandom
from backend.venue_geography import distance_m

def weighted(items,weight,rng=None):
    rng=rng or SystemRandom()
    return sorted(items,key=lambda p:-log(max(rng.random(),1e-15))/max(.001,weight(p)))

def quality(venue):
    # Missing ratings are neutral, not proof of poor quality.
    rating=getattr(venue,'rating',None)
    count=getattr(venue,'ratingCount',None) or 0
    strength=getattr(venue,'relevanceStrength',None)
    return (1 if strength in (None,'strong') else .4)*(1+(rating or 3)/5*min(count/100,1))

def quality_qualified(plan):
    return all(v.rating is None or (v.ratingCount or 0)<10 or v.rating>=3 for v in plan.candidate.venues)

def venue_order(venues,used=(),facts=None,rng=None):
    remaining=list(venues);ordered=[];used=set(used)
    # Spatial sampling is bounded to the existing computational frontier;
    # remaining retained venues get a linear weighted order, not a new cap.
    while remaining and len(ordered)<20:
        unseen=[v for v in remaining if v.id not in used]
        pool=unseen or remaining
        def weight(v):
            spatial=1
            point=getattr((facts or {}).get(v.id,v),'coordinates',None)
            previous=[getattr((facts or {}).get(p.id,p),'coordinates',None) for p in ordered[:3]]
            if point and any(previous):
                spatial=1+min(3,min(distance_m(point,p) for p in previous if p)/2000)
            return quality(v)*spatial
        pick=weighted(pool,weight,rng)[0];ordered.append(pick);remaining.remove(pick)
    return ordered+weighted([v for v in remaining if v.id not in used],quality,rng)+weighted([v for v in remaining if v.id in used],quality,rng)

def select(ranked,count,context,facts=None,rng=None):
    """Feasible, evidence-qualified plans; sample near the best remaining score."""
    # Unknown/low-count ratings cannot prove poor quality. This threshold uses
    # only actual supplied ratings, never extra paid enrichment.
    remaining=[p for p in ranked if quality_qualified(p)]
    chosen=[];used=set(context.get('usedPrimary',()))|set(context.get('recent',()))
    while remaining and len(chosen)<count:
        best=max(p.score for p in remaining)
        near=[p for p in remaining if p.score>=best-.15]
        unseen=[p for p in near if p.candidate.venues[0].id not in used]
        batch_first={p.candidate.venues[0].id for p in chosen}
        different=[p for p in near if p.candidate.venues[0].id not in batch_first]
        pool=unseen or different or near
        activity_usage=context.get('usedActivities',{})
        def novelty(p):
            return sum(v.id not in activity_usage.get(v.activity,set()) and
                       all(v.id!=q.candidate.venues[i].id for q in chosen)
                       for i,v in enumerate(p.candidate.venues))
        most=max(map(novelty,pool))
        pool=[p for p in pool if novelty(p)==most]
        vertices=list({p.candidate.venues[0].id:p.candidate.venues[0] for p in pool}.values())
        def first_weight(v):
            novelty=1
            point=(facts or {}).get(v.id)
            if point and point.coordinates and region(point.coordinates) not in context.get('usedRegions',set()):novelty+=1
            prior=[(facts or {}).get(p.candidate.venues[0].id) for p in chosen]
            if point and point.coordinates and any(p and p.coordinates for p in prior):
                novelty+=min(3,min(distance_m(point.coordinates,p.coordinates) for p in prior if p and p.coordinates)/2000)
            return quality(v)*novelty
        first=weighted(vertices,first_weight,rng)[0].id
        alternatives=[p for p in pool if p.candidate.venues[0].id==first]
        used_activities=context.get('usedActivities',{})
        pick=weighted(alternatives,lambda p:1+sum(v.id not in used_activities.get(v.activity,set()) for v in p.candidate.venues[1:])+p.score,rng)[0]
        pick.surpriseRepeated=first in used
        chosen.append(pick);used.add(first)
        remaining=[p for p in remaining if p.candidate.id!=pick.candidate.id]
    return chosen

def region(point):
    return (round(point.latitude*50),round(point.longitude*50))

def record(context,plans,facts=None):
    for p in plans:
        for v in p.candidate.venues:context.setdefault('usedActivities',{}).setdefault(v.activity,set()).add(v.id)
        context.setdefault('usedPrimary',set()).add(p.candidate.venues[0].id)
        context.setdefault('seen',set()).add(p.candidate.id)
        first=(facts or {}).get(p.candidate.venues[0].id)
        if first and first.coordinates:context.setdefault('usedRegions',set()).add(region(first.coordinates))

def validate_beginning(request):
    from backend.places import DiscoveryError
    if request.planningMode=='surprise':
        if any(getattr(request,key,None) is not None for key in ('startingLocation','currentArea','searchRadius','manualStartingPlace','referenceToken','firstTravel','maxFirstLegTravel')):
            raise DiscoveryError('origin_conflict','Surprise Me begins at the first activity. Switch to a location-based mode, or explicitly remove the origin and first-stop constraint.')
        if request.location.casefold().strip() in ('near me','nearby','current location'):
            raise DiscoveryError('destination_required','Enter a destination city for Surprise Me; no device location is requested.')
    elif request.startingLocation is None:
        raise DiscoveryError('origin_required','Choose and confirm where your outing starts, or select Surprise Me.')
