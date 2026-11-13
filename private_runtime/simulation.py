"""Explicit non-network synthetic provider, not model qualification or live fallback."""
import json
ADDITIONAL={}
from experiments.shared_state.contracts import Denied

def respond(payload):
    body=json.loads(payload)
    if 'model' in body:
        if body['input'] in ADDITIONAL:
            return dict(output=json.loads(json.dumps(ADDITIONAL[body['input']])),usage=dict(provider=body['provider'],model=body['model'],input_tokens=len(payload),output_tokens=2,cached_tokens=0,reasoning_tokens=0,tool_calls=0))
        if body['input'] not in ('Coffee and museum in Baltimore','Coffee and museum'):
            raise Denied('unsupported_synthetic_source')
        data=dict(activities=['coffee','museum'],location='Baltimore' if body['input'].endswith('Baltimore') else None,date=None,budget_per_person=None,preferences=[])
        return dict(output=data,usage=dict(provider=body['provider'],model=body['model'],input_tokens=len(payload),output_tokens=2,cached_tokens=0,reasoning_tokens=0,tool_calls=0))
    if body['operation']=='search':
        p=body['body'];q=p['textQuery'].casefold()
        circle=p.get('locationBias',{}).get('circle',{});center=circle.get('center',{})
        approved_bias=center in ({'latitude':39.29,'longitude':-76.61},{'latitude':39.28,'longitude':-76.60}) and type(circle.get('radius')) in (int,float) and 0<=circle['radius']<=50000
        if ('baltimore' not in q and not approved_bias) or not 1<=p['pageSize']<=10 or p.get('pageToken'):raise Denied('unsupported_synthetic_search')
        if q=='baltimore':
            return {'places':[dict(id='Fixture_Baltimore_area',displayName={'text':'Baltimore'},formattedAddress='Baltimore, MD',location={'latitude':39.28,'longitude':-76.60},types=['locality','political'],addressComponents=[{'longText':'Baltimore','types':['locality']},{'longText':'Maryland','shortText':'MD','types':['administrative_area_level_1']}],attributions=[{'provider':'Synthetic credit','providerUri':'https://example.com/credits'}])]}
        activity='coffee' if ('coffee' in q or q=='cafes' or q.startswith('cafes in ')) else 'museum' if 'museum' in q else None
        if activity is None:raise Denied('unsupported_synthetic_search')
        return {'places':[dict(id=f'Fixture_{activity}_{i}',displayName={'text':f'Fixture {activity} venue {i}'},formattedAddress='1 Synthetic Street, Baltimore, MD',location={'latitude':39.28+i*.001,'longitude':-76.60},types=['cafe' if activity=='coffee' else 'museum'],addressComponents=[{'longText':'Baltimore','types':['locality']},{'longText':'Maryland','shortText':'MD','types':['administrative_area_level_1']}],attributions=[{'provider':'Synthetic credit','providerUri':'https://example.com/credits'}]) for i in range(p['pageSize'])]}
    if body['operation']=='matrix':
        p=body['body'];n=len(p['origins'])*len(p['destinations'])
        if not 1<=n<=300:raise Denied('synthetic_matrix_bound')
        return [dict(originIndex=i,destinationIndex=j,status={},condition='ROUTE_EXISTS',duration='120s' if p['travelMode']=='DRIVE' else '600s',distanceMeters=600) for i in range(len(p['origins'])) for j in range(len(p['destinations']))]
    raise Denied('unsupported_synthetic_operation')
