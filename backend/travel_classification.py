"""Classify supplied evidence without changing the owner's original requirements."""
from decimal import Decimal
from backend.location_policy import FirstTravel, effective_max, first_measure, exceeds

def number(value):
    text=format(value,'f')
    return text.rstrip('0').rstrip('.') if '.' in text else text

def display_measure(value,unit):
    if unit=='minutes':
        seconds=(value*60).quantize(Decimal('.000000001'))
        minutes=int(seconds//60)
        remainder=seconds-minutes*60
        return ' '.join(part for part in (
            f'{minutes} min' if minutes else '',
            f'{number(remainder)} sec' if remainder or not minutes else '') if part)
    rounded=value.quantize(Decimal('.000001'))
    if value>0 and not rounded:return 'less than 0.000001 road miles'
    return f'approximately {number(rounded)} road miles'

def classify(request, plan, routes, origin=None):
    deviations=[]
    unknown=False
    beyond=False
    preferred=False
    pairs=[(a.id,b.id) for a,b in zip(plan.candidate.venues,plan.candidate.venues[1:])]
    def check(pair, preference, label):
        nonlocal unknown,beyond,preferred
        leg=routes.get(pair)
        if not leg or leg.status not in ('ok','same_location'):
            unknown=True
            return
        actual=first_measure(leg,preference)
        if actual is None:
            unknown=True
            return
        maximum=Decimal(str(effective_max(preference)))
        violation=bool(exceeds(leg,preference))
        soft=preference.mode=='flexible' and actual>Decimal(str(preference.value))
        if violation or soft:
            beyond |= violation
            preferred |= soft
            limit=maximum if violation else Decimal(str(preference.value))
            units='minutes' if preference.unit=='minutes' else 'road miles'
            qualifier='strict maximum' if preference.mode=='strict' else 'Flexible maximum' if violation else 'preferred range'
            amount=display_measure(actual,preference.unit)
            delta=display_measure(max(Decimal(0),actual-limit),preference.unit)
            requirement=f'your {qualifier} was {number(limit)} {units}'
            if violation and preference.mode=='flexible':
                requirement=f'your original preference was {number(Decimal(str(preference.value)))} {units} (Flexible maximum {number(maximum)} {units})'
            deviations.append(f'{label}: {requirement}; the Google route estimate is {amount}, {delta} over' + (' (the exact boundary is excluded).' if violation and preference.exclusive and actual==limit else '.'))
    first=request.firstTravel or (FirstTravel(value=float(request.maxFirstLegTravel),exclusive=request.maxFirstLegTravelExclusive) if request.maxFirstLegTravel is not None else None)
    between=request.betweenTravel or (FirstTravel(value=float(request.maxLegTravel),exclusive=request.maxLegTravelExclusive) if request.maxLegTravel is not None else None)
    if origin:
        pair=(origin.point.id,plan.candidate.venues[0].id)
        if first:check(pair,first,'Journey to the first stop')
        elif pair not in routes or routes[pair].status not in ('ok','same_location'):unknown=True
    for i,pair in enumerate(pairs):
        if between:check(pair,between,f'Journey {i+1} between activities')
        elif pair not in routes or routes[pair].status not in ('ok','same_location'):unknown=True
    if request.travel is not None:
        legs=[routes.get(pair) for pair in pairs]
        if any(not leg or leg.status not in ('ok','same_location') for leg in legs):unknown=True
        else:
            seconds=sum((Decimal(leg.duration_nanoseconds)/10**9 if leg.duration_nanoseconds is not None else Decimal(str(leg.duration_seconds))) for leg in legs)
            minutes=seconds/60
            if minutes>request.travel or request.travelExclusive and minutes==request.travel:
                beyond=True
                deviations.append(f'Total between-activity travel: your maximum was {request.travel} minutes; the Google route estimates total {display_measure(minutes,"minutes")} ({display_measure(max(Decimal(0),minutes-request.travel),"minutes")} over).')
    if unknown:deviations.append('Necessary travel evidence is unavailable. Travel compliance cannot be verified.')
    category='beyond_limit' if beyond else 'unverified' if unknown else 'outside_preference' if preferred else 'matching'
    if request.requireWheelchairAccess:
        support=[v.wheelchairAccessible for v in plan.candidate.venues]
        if any(value is False for value in support):
            raise ValueError('Known inaccessible venue cannot be recommended as usable.')
        if any(value is None for value in support):
            if category=='matching':category='unverified'
            deviations.append('Required wheelchair access is unverified. Confirm suitability with every venue before choosing this outing.')
    # A hard budget without supplied costs has never passed verification.
    if category=='matching' and (request.budget is not None or request.groupBudget is not None):
        category='unverified'
        deviations.append('Your financial budget cannot be verified because activity prices are unavailable.')
    return category,deviations

def select_diverse(ranked,count,context):
    """All-stop novelty within a modest evidence-quality band, no random filler."""
    chosen=[];remaining=list(ranked)
    usage=context.get('venueDisplayCounts',{})
    while remaining and len(chosen)<count:
        best=max(p.score for p in remaining)
        near=[p for p in remaining if p.score>=best-.15]
        def key(p):
            batch=sum(any(v.id==q.candidate.venues[i].id for q in chosen) for i,v in enumerate(p.candidate.venues))
            repeats=sum(usage.get(v.activity.value,{}).get(v.id,0) for v in p.candidate.venues)
            return batch,repeats,-p.score,tuple(v.id for v in p.candidate.venues)
        pick=min(near,key=key);chosen.append(pick);remaining.remove(pick)
    return chosen

def deviation_penalty(request,plan,routes,origin=None):
    """Small normalized deviation penalty; never changes compliance or facts."""
    pairs=[(a.id,b.id) for a,b in zip(plan.candidate.venues,plan.candidate.venues[1:])]
    checks=[]
    first=request.firstTravel or (FirstTravel(value=float(request.maxFirstLegTravel)) if request.maxFirstLegTravel is not None else None)
    between=request.betweenTravel or (FirstTravel(value=float(request.maxLegTravel)) if request.maxLegTravel is not None else None)
    if origin and first:checks.append(((origin.point.id,plan.candidate.venues[0].id),first))
    if between:checks.extend((pair,between) for pair in pairs)
    deviation=Decimal(0)
    for pair,preference in checks:
        leg=routes.get(pair)
        if not leg:continue
        actual=first_measure(leg,preference)
        if actual is None:continue
        limit=Decimal(str(preference.value))
        deviation+=max(Decimal(0),actual-limit)/max(Decimal(1),limit)
    return .03*min(5,float(deviation))


def limit_notice(request):
    preference=request.firstTravel or request.betweenTravel
    if preference:
        value=number(Decimal(str(effective_max(preference))))
        unit='minute' if preference.unit=='minutes' else 'road-mile'
        label=f'{value}-{unit}'
    else:
        limit=request.maxFirstLegTravel if request.maxFirstLegTravel is not None else request.maxLegTravel if request.maxLegTravel is not None else request.travel
        label=f'{limit}-minute' if limit is not None else 'stated'
    return f"We haven't verified an outing within your {label} travel limit yet. You can search more nearby places or choose to see options farther away."
