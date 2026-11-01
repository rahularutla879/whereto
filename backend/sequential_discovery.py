"""Finite multi-path spatial discovery; existing planner verifies/ranks full paths."""
from hashlib import sha256
import json
from backend.places import DiscoveryRequest, DiscoveryResult, PlacesDiscovery, SearchArea, search_body
from backend.discovery_inventory import merge_inventory
from backend.location_policy import effective_max, radius
from backend.venue_geography import distance_m


def mode(request):return 'walk' if request.transport=='walking' else 'drive'


def search_area(request,center=None,first=False,band=None):
    preference=request.firstTravel if first else None
    onward=request.betweenTravel
    reach=radius(preference,band,mode(request)) if first else radius(onward,effective_max(onward),mode(request)) if onward else (min(50000,max(250,(request.maxLegTravel if request.maxLegTravel is not None else 10)*(80 if mode(request)=='walk' else 600))))
    # Preference-derived geometry is a search heuristic, never a retention filter.
    # An explicit first-leg range should not inherit a 12-km city default.
    # Broad inventory is retained; further cells remain explicit, finite actions.
    reach=max(reach,250 if first and preference else radius(None,None,mode(request)) if first else (1200 if mode(request)=="walk" else 6000))
    if first and preference and preference.mode=="strict":reach=max(250,reach*.5)
    from backend.location_context import anchor_compatible
    origin=request.startingLocation
    anchored=bool(center and origin and (request.useOriginAsSearchAnchor or anchor_compatible(
        request.location, origin.geographicDescription or origin.label)))
    return SearchArea(anchor_verified=anchored,name=request.location if request.location.casefold() not in ('near me','nearby','current location') else None,
        coordinates=center,radius_m=reach if center else None,enforce_name=request.geography.strictDestination,include_name=first and not anchored,restrict_to_area=center is not None,
        excluded_regions=request.geography.excludedRegions,
        boundary_coordinates=request.currentArea.coordinates if request.searchRadius is not None and request.currentArea else None,
        boundary_radius_m=request.searchRadius)


def key(query):return sha256(json.dumps(search_body(query,10),sort_keys=True).encode()).hexdigest()


def add_job(context,position,center=None,anchor=None,first=False,area=None):
    r=context['request'];area=area or search_area(r,center,first,effective_max(r.firstTravel))
    query=DiscoveryRequest(activity=r.activities[position],destination=area,
        meal='dinner' if r.activities[position]=='food' and (r.dinner or position in (r.dinnerStops or [])) else None)
    identity=key(query)
    if identity in context['jobKeys']:
        job=next(j for j in context['jobs'] if j['key']==identity)
        job['targets'].add((position,anchor))
        retain_job_results(context,job)
    else:
        context['jobKeys'].add(identity)
        context['jobs'].append({'key':identity,'targets':{(position,anchor)},'ids':set(),
            'request':query,'position':position,'anchor':anchor,'next':None,'searched':False,'done':False})


def retain_job_results(context,job):
    retained={v.facts.id for v in context['discovery'].venues}
    ids=job['ids'] & retained
    for position,anchor in job['targets']:
        context['positionIds'][position].update(ids)
        if anchor:
            context['spatialEdges'].update((position-1,anchor,identity) for identity in ids if identity!=anchor)


def run_job(context,job):
    context['actionDiscoveryCalls']=context.get('actionDiscoveryCalls',0)+1
    query=job['request']
    geometry=search_body(query,10)
    area_key=sha256(json.dumps({k:geometry[k] for k in ('locationRestriction','locationBias') if k in geometry} or {'name':query.area.name},sort_keys=True).encode()).hexdigest()
    found=PlacesDiscovery(context['outing']).discover(query)
    context.setdefault('searchedAreas',set()).add(area_key)
    context['discovery']=merge_inventory(context['discovery'],found,context['outing'])
    ids={v.facts.id for v in found.venues if query.activity in v.activities}
    job['ids'].update(ids)
    retain_job_results(context,job)
    retained={v.facts.id for v in context['discovery'].venues}
    for position_ids in context['positionIds']:position_ids.intersection_update(retained)
    job['searched']=True
    cursor=found.paging.get(query.activity,{})
    query=query.model_copy(update={'search_variant':cursor.get('variant',query.search_variant)})
    job['next']=cursor.get('next')
    if job['next']:
        job['request']=query.model_copy(update={'page_token':job['next']})
    else:
        variants=['initial','alternative','mixed'] if context['outing'].settings.exploration else ['initial','alternative']
        i=variants.index(query.search_variant)
        if i+1<len(variants):job['request']=query.model_copy(update={'search_variant':variants[i+1],'page_token':None})
        else:job['done']=True
    return found


def anchors(context,position):
    wanted=context['positionIds'][position]
    facts=[v.facts for v in context['discovery'].venues if v.facts.id in wanted and v.facts.coordinates]
    # Keep multiple strong spatial alternatives, not only the nearest business.
    origin=context['request'].startingLocation
    point=(origin.reference_coordinates or origin.point.coordinates) if position==0 and origin else None
    facts.sort(key=lambda v:(distance_m(point,v.coordinates) if point else 0,-(v.ratingCount or 0),-(v.rating or 0),v.id))
    if position==0 and context['request'].planningMode=='surprise':
        from backend.surprise import venue_order,region
        ordered=venue_order(facts,context.get('usedPrimary',set())|set(context['request'].recentSurpriseIds))
        count=3 if context['outing'].settings.exploration else 2
        selected=[];cells=set()
        for venue in ordered:
            cell=region(venue.coordinates)
            if cell not in cells:selected.append(venue);cells.add(cell)
            if len(selected)>=count:break
        selected+=( [v for v in ordered if v not in selected][:count-len(selected)] )
        context['surpriseOrder']=[v.id for v in selected]+[v.id for v in ordered if v not in selected]
        return selected
    selected=[]
    while facts and len(selected)<2:
        # Co-located businesses should share one query, not consume both paths.
        if selected:
            facts=[v for v in facts if all(distance_m(v.coordinates,s.coordinates)>=1 for s in selected)]
            if not facts:break
        if not selected:chosen=facts.pop(0)
        else:
            chosen=(facts[0] if position==0 and point else
                    max(facts,key=lambda v:(min(distance_m(v.coordinates,s.coordinates) for s in selected),v.id)))
            facts.remove(chosen)
        selected.append(chosen)
    return selected


def initialize(request,outing,seed=None,seed_routes=None):
    context={'request':request,'outing':outing,'discovery':seed or DiscoveryResult(candidates=[]), 'jobs':[], 'jobKeys':set(),
             'positionIds':[set() for _ in request.activities],'spatialEdges':set(),
             'locationFirst':True,'actionDiscoveryCalls':0}
    near=request.location.casefold() in ('near me','nearby','current location')
    center=request.currentArea.coordinates if near and request.currentArea else (
        (request.startingLocation.reference_coordinates or request.startingLocation.point.coordinates) if request.startingLocation else None)
    if seed:
        reach=radius(request.firstTravel,effective_max(request.firstTravel),mode(request))
        context['positionIds'][0].update(v.facts.id for v in seed.venues if request.activities[0] in v.activities
            and (not center or v.facts.coordinates and distance_m(center,v.facts.coordinates)<=reach))
    add_job(context,0,center,first=True)
    if len(context['positionIds'][0])<3:run_job(context,context['jobs'][-1])
    # Initial finite beam: at most two search anchors per transition, up to
    # seven venue requests for four stops. No route/venue Cartesian search.
    for i in range(1,len(request.activities)):
        # Seed onward venues only with already checked directed connections.
        # Do not discard useful preflight evidence merely because the next
        # spatial query uses another anchor.
        if seed and seed_routes:
            for venue in seed.venues:
                if request.activities[i] not in venue.activities:continue
                for prior in context['positionIds'][i-1]:
                    route=seed_routes.get((prior,venue.facts.id))
                    if route and route.status in ('ok','same_location'):
                        context['positionIds'][i].add(venue.facts.id)
                        context['spatialEdges'].add((i-1,prior,venue.facts.id))
        for previous in anchors(context,i-1):
            remaining_stops=len(request.activities)-i-1
            if outing.usage()['placesSearchRequests']>=outing.settings.ceiling('searches_per_outing')-remaining_stops:break
            count=len(context['jobs']);add_job(context,i,previous.coordinates,previous.id)
            if len(context['jobs'])>count:run_job(context,context['jobs'][-1])
    return context


def can_expand(context):
    counts={a:sum(a in v.activities for v in context['discovery'].venues) for a in set(context['request'].activities)}
    cap=min(100,context['outing'].settings.ceiling('candidates_per_activity'))
    if all(n>=cap for n in counts.values()):return False
    if any(not j['done'] and counts[context['request'].activities[j['position']]]<cap for j in context['jobs']):return True
    if any(counts[a]<cap and next_region(context,commit=False,position=context['request'].activities.index(a)) is not None for a in counts):return True
    return any(context['positionIds'][i-1] - {anchor for j in context['jobs'] for position,anchor in j['targets'] if position==i}
               for i in range(1,len(context['request'].activities)) if counts[context['request'].activities[i]]<cap)


def next_region(context,*,commit,position=0):
    """Finite provider-backed search grid, never a claimed user position.

    Tiles guide discovery only. Exact first-leg routes and hard geography still
    decide eligibility. No-limit range grows only on explicit exploration.
    """
    from math import sin,cos,radians
    from backend.venue_models import Coordinates
    r=context['request'];origin=r.startingLocation
    first=[v.facts for v in context['discovery'].venues if v.facts.id in context['positionIds'][0] and v.facts.coordinates]
    # Provider-backed venue can guide search when a legacy Place-ID origin has
    # no coordinates. This never changes the route origin or claims user position.
    center=((origin.reference_coordinates or origin.point.coordinates) if origin else None) or (first[0].coordinates if first else None)
    if not center:return None
    steps=context.setdefault('regionSteps',{})
    activity=r.activities[position]
    step=steps.get(activity,0)
    if step>=32:return None  # Finite regional strategy, not city-wide exhaustion.
    ring=step//8+1;angle=radians((step%8)*45)
    reach=radius(r.firstTravel,effective_max(r.firstTravel),mode(r))
    local_reach=reach*.5 if r.firstTravel and r.firstTravel.mode=='strict' else reach
    offset=local_reach*ring*.65
    tile=min(50000,local_reach*(1+ring*.25))
    latitude=center.latitude+sin(angle)*offset/111320
    longitude=center.longitude+cos(angle)*offset/(111320*max(.05,cos(radians(center.latitude))))
    if abs(latitude)>90:return None
    longitude=(longitude+180)%360-180
    area=search_area(r,Coordinates(latitude=latitude,longitude=longitude),True,effective_max(r.firstTravel))
    area=area.model_copy(update={'radius_m':float(min(50000,tile))})
    if commit:steps[activity]=step+1
    return area


def expand(context):
    # Two explicit discovery steps: advance primary coverage first; then seed
    # a later activity near a new promising path, not another old restaurant page.
    before=set(context['positionIds'][0]);before_regions=len(context.get('searchedAreas',()));start_calls=context.get('actionDiscoveryCalls',0)
    # Two finite requests, rotating the least-covered distinct activities.
    # Pagination is consumed before a new anchor/region/strategy.
    counts={a:sum(a in v.activities for v in context['discovery'].venues) for a in set(context['request'].activities)}
    positions=list(dict.fromkeys(context['request'].activities))
    actions=context.setdefault('activitySearchActions',{})
    selected=sorted(positions,key=lambda a:(counts[a]>=100,actions.get(a,0),counts[a],positions.index(a)))[:2]
    for activity in selected:
        if counts[activity]>=100:continue
        i=context['request'].activities.index(activity)
        job=next((j for j in context['jobs'] if context['request'].activities[j['position']]==activity and not j['done']),None)
        if job is None and i==0:
            area=next_region(context,commit=True)
            if area:
                count=len(context['jobs']);add_job(context,0,first=True,area=area)
                if len(context['jobs'])>count:job=context['jobs'][-1]
        elif job is None:
            inspected={anchor for j in context['jobs'] for position,anchor in j['targets'] if position==i}
            source=[v.facts for v in context['discovery'].venues if v.facts.id in context['positionIds'][i-1] and v.facts.coordinates and v.facts.id not in inspected]
            if source:
                source.sort(key=lambda v:v.id)
                v=source[0];count=len(context['jobs']);add_job(context,i,v.coordinates,v.id)
                if len(context['jobs'])>count:job=context['jobs'][-1]
        if job is None and i>0:
            area=next_region(context,commit=True,position=i)
            if area:
                count=len(context['jobs']);add_job(context,i,area=area)
                if len(context['jobs'])>count:job=context['jobs'][-1]
        if job:
            run_job(context,job)
            actions[activity]=actions.get(activity,0)+1
    context['latestExploration']={'newFirstVenues':len(context['positionIds'][0]-before),
        'newSearchRegions':len(context.get('searchedAreas',()))-before_regions,'searchRequests':context.get('actionDiscoveryCalls',0)-start_calls}
    context.pop('actionFrontier',None)
    context['unseenEligible']=0;context['expanded']=False
    context['width']=6 if len(context['request'].activities)<=2 else 4
