"""Deterministic reference coverage and diversity from measured directed routes."""
from backend.location_policy import exceeds
from backend.venue_geography import distance_m


def regions(points,count):
    remaining=sorted(points,key=lambda p:p.id if hasattr(p,'id') else p.provider_id)
    selected=[]
    while remaining and len(selected)<count:
        pick=remaining[0] if not selected else max(remaining,key=lambda p:min(distance_m(p.coordinates,q.coordinates) for q in selected))
        selected.append(pick);remaining.remove(pick)
    return selected


def compare(candidates,first,second,routes,preference,max_leg=None,exclusive=False,total=None,total_exclusive=False):
    from decimal import Decimal
    def onward_ok(r):
        if not r or r.status not in ("ok","same_location"):return False
        seconds=Decimal(r.duration_nanoseconds)/10**9 if r.duration_nanoseconds is not None else Decimal(str(r.duration_seconds))
        return all(limit is None or seconds<Decimal(limit)*60 or seconds==Decimal(limit)*60 and not exclude for limit,exclude in ((max_leg,exclusive),(total,total_exclusive)))
    rows=[]
    for p in candidates:
        legs={v.id:routes.get(('reference_'+p.provider_id,v.id)) for v in first}
        valid={k:r for k,r in legs.items() if r and r.status in ('ok','same_location') and (not preference or not exceeds(r,preference))}
        if not valid:continue
        preferred={k:r for k,r in valid.items() if not preference or not exceeds(r,preference,original=True)}
        onward={a for a in valid if any(onward_ok(routes.get((a,b.id))) for b in second)}
        mean=sum(r.duration_seconds for r in valid.values())/len(valid)
        score=len(valid)*100+len(preferred)*25+len(onward)*20-mean/60
        rows.append({'place':p,'valid':valid,'preferred':preferred,'onward':onward,'score':score})
    rows.sort(key=lambda r:(-r['score'],r['place'].provider_id))
    selected=[];evidence=[]
    for row in rows:
        new=set(row['valid'])-set().union(*(set(r['valid']) for r in selected)) if selected else set(row['valid'])
        overlap=max((len(set(row['valid'])&set(r['valid']))/len(set(row['valid'])|set(r['valid'])) for r in selected),default=0)
        shorter=sum(any(identity in old['valid'] and leg.duration_seconds+300<=old['valid'][identity].duration_seconds for old in selected) for identity,leg in row['valid'].items())
        if selected and overlap>=.8 and not new and not shorter:continue
        row['label']='Different activity choices' if selected and new else 'Shorter first journeys' if selected and shorter else 'Activity coverage'
        selected.append(row)
        evidence.append({'checkedFirstVenues':len(row['valid']),'withinOriginalPreference':len(row['preferred']),'onwardConnectedFirstVenues':len(row['onward']),'newFirstVenues':len(new),'maximumCoverageOverlap':round(overlap,3),'shorterFirstJourneys':shorter,'score':round(row['score'],3)})
        if len(selected)==3:break
    return selected,{'comparedReferences':len(rows),'selectedReferences':len(selected),'selection':evidence}
