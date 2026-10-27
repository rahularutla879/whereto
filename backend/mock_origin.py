"""Explicit mock first-leg evidence, never a real geocoder or route fallback."""
from backend.location_policy import exceeds
from types import SimpleNamespace

def apply_mock_origin(result,request):
    origin=request.startingLocation
    if origin.source!='mock':
        # Real coordinates cannot establish travel to fictional businesses.
        for plan in result.plans+result.provisionalPlans:
            plan.firstLeg={'source':origin.source,'originLabel':origin.label,'minutes':None,'miles':None,'approximate':True}
        return result
    groups=[]
    for plans in (result.plans,result.provisionalPlans):
        kept=[]
        for plan in plans:
            leg=SimpleNamespace(duration_seconds=300.0,duration_nanoseconds=300000000000,distance_meters=1609,status='ok')
            if request.firstTravel and exceeds(leg,request.firstTravel):continue
            if request.maxFirstLegTravel is not None and (5>request.maxFirstLegTravel or request.maxFirstLegTravelExclusive and 5==request.maxFirstLegTravel):continue
            plan.firstLeg={'source':'mock','originLabel':origin.label,'minutes':5,'miles':round(1609/1609.344,2),'approximate':True,'fictional':True}
            kept.append(plan)
        groups.append(kept)
    result.plans,result.provisionalPlans=groups
    if not any(groups):result.message='No fictional first-leg estimate meets this starting preference. Mock travel is not real routing.'
    return result
