"""Bounded, verified public references. Tokens/Google content expire in memory."""
from collections import OrderedDict
from hashlib import sha256
import json
from secrets import token_urlsafe
from threading import Lock
from time import monotonic
import os
from pydantic import BaseModel, ConfigDict, Field, field_validator
from backend.models import ActivityType
from backend.location_policy import FirstTravel, Geography, exceeds
from backend.places import (DiscoveryError, DiscoveryRequest, PlacesDiscovery, SearchArea,
                            FIELD_MASK, parse_response)
from backend.routes import RoutePoint, RouteRequest, GoogleRouteCalculator, AuthorizedStart
from backend.venue_geography import distance_m

PUBLIC_TYPES={'train_station','subway_station','transit_station','light_rail_station','bus_station','park','plaza','town_square','neighborhood'}


class StartingAreaQuery(BaseModel):
    model_config=ConfigDict(extra='forbid')
    destination: str = Field(min_length=2,max_length=80)
    activities: list[ActivityType] = Field(min_length=1,max_length=4)
    transport: str = Field(default='driving',pattern='^(driving|walking)$')
    firstTravel: FirstTravel | None = None
    geography: Geography = Field(default_factory=Geography)

    @field_validator('destination')
    @classmethod
    def destination_text(cls,value):
        value=value.strip()
        if len(value)<2 or any(ord(c)<32 for c in value):raise ValueError('Enter a destination city without control characters.')
        return value


class References:
    def __init__(self):self.entries=OrderedDict();self.lock=Lock()
    def create(self,data):
        with self.lock:
            now=monotonic()
            self.entries=OrderedDict((k,v) for k,v in self.entries.items() if now-v[0]<600)
            while len(self.entries)>=20:self.entries.popitem(last=False)
            token=token_urlsafe(32);self.entries[token]=(now,data,False)
            return token
    def confirm(self,token,identity,session):
        with self.lock:
            entry=self.entries.get(token)
            if not entry or monotonic()-entry[0]>=600 or entry[1]['session'] is not session:
                raise DiscoveryError('expired','This starting-area suggestion expired or was already used. Choose a new starting area.')
            data={**entry[1], **({'outing':session.outing()} if entry[2] else {})}
            match=next((p for p in data['matches'] if p['placeId']==identity),None)
            if not match:raise DiscoveryError('invalid_origin','Confirm one of the suggested starting areas.')
            self.entries[token]=(entry[0],data,True)
            point=RoutePoint(id='reference_'+identity,place_id=identity)
            origin=AuthorizedStart(point=point,reference_coordinates=match['coordinates'],source='suggested',label=match['name'],precision=match['precision'],explicitly_authorized=True)
            return data,origin


references=References()


def suggest_starting_areas(query,session):
    session.settings.require_live_provider()
    if os.environ.get('WHERETO_START_LOOKUP_DEV')!='1':
        raise DiscoveryError('disabled','Starting-area suggestions are disabled. Enable the local starting-location lookup switch, enter a place, or plan without an origin.')
    if query.destination.strip().casefold() in ('near me','nearby','current location'):
        raise DiscoveryError('location_required','Enter a destination city for a suggested starting area, or explicitly share your current location.')
    outing=session.outing()
    body={'textQuery':f'public transit stations and public squares in {query.destination}', 'pageSize':3,'languageCode':'en'}
    with outing.reserve('lookup',sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()):
        from backend.places_transport import text_search
        raw=text_search(body,field_mask=FIELD_MASK)
    found=parse_response(raw,SearchArea(name=query.destination,excluded_regions=query.geography.excludedRegions),3)
    candidates=[p for p in found.candidates if set(p.types or []) & PUBLIC_TYPES]
    if not candidates:return {'matches':[], 'message':'No trustworthy public reference was found in this search. Enter and confirm a manual starting place instead.', 'diagnostics':outing.usage()}
    area=SearchArea(name=query.destination,coordinates=candidates[0].coordinates,radius_m=30000,
                    enforce_name=query.geography.strictDestination,excluded_regions=query.geography.excludedRegions)
    activities=list(dict.fromkeys(query.activities))[:2]
    inventory=PlacesDiscovery(outing).discover_many([DiscoveryRequest(activity=a,destination=area) for a in activities])
    first=[v.facts for v in inventory.venues if query.activities[0] in v.activities][:3]
    mode='walk' if query.transport=='walking' else 'drive'
    routes={}; matrix_requests=0
    if first:
        result=GoogleRouteCalculator(outing).calculate(RouteRequest(activity_groups=[
            [RoutePoint(id='reference_'+p.provider_id,place_id=p.provider_id) for p in candidates],
            [RoutePoint.from_venue(p) for p in first]],mode=mode))
        matrix_requests=result.matrix_requests
        routes={(r.origin_id,r.destination_id):r for r in result.legs}
        if any(r.status=='error' for r in result.legs):
            raise DiscoveryError('reference_routes','Starting-area route comparison was unavailable. No automatic retry was made; choose a manual place or try a new authorized search later.')
    second=[v.facts for v in inventory.venues if len(query.activities)>1 and query.activities[1] in v.activities]
    matches=[]
    for p in candidates:
        near=[v for v in first if v.coordinates and distance_m(p.coordinates,v.coordinates)<=15000]
        checked=[routes.get(('reference_'+p.provider_id,v.id)) for v in near]
        usable=[r for r in checked if r and r.status in ('ok','same_location') and (not query.firstTravel or not exceeds(r,query.firstTravel))]
        second_coverage=sum(any(distance_m(v.coordinates,n.coordinates)<=8000 for n in second if n.coordinates) for v in near)
        score=len(usable)*100+len(near)*20+second_coverage*10-(sum(r.duration_seconds for r in usable)/max(1,len(usable)))/60
        if not first:score=0  # No invented coverage/accessibility evidence.
        precision='neighborhood' if 'neighborhood' in (p.types or []) else 'address_or_place'
        matches.append({'placeId':p.provider_id,'name':p.display_name,'address':p.address,
            'coordinates':p.coordinates.model_dump(),'precision':precision,'attributions':[{'provider':a.get('provider'),'uri':a.get('providerUri')} for a in p.attributions],
            'score':round(score,3),'reason':f'Public planning reference; {len(usable)} checked first-stop routes, {second_coverage} nearby second-activity connections by proximity. Access and operating hours are not verified.'})
    matches.sort(key=lambda p:(-p['score'],p['placeId']))
    token=references.create({'session':session,'outing':outing,'inventory':inventory,'routes':routes,'matches':matches,'query':query,'matrixRequests':matrix_requests})
    return {'matches':matches,'referenceToken':token,'diagnostics':outing.usage(),
            'message':'Choose a planning reference. This is a suggested meeting area, not your actual position.'}
