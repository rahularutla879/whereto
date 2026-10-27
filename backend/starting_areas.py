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
from backend.location_policy import FirstTravel, Geography
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
    maxLegTravel: int | None = Field(default=None,ge=0,le=1440,strict=True)
    maxLegTravelExclusive: bool = Field(default=False,strict=True)
    travel: int | None = Field(default=None,ge=0,le=1440,strict=True)
    travelExclusive: bool = Field(default=False,strict=True)
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
    from backend.provider_budget import ProviderLimitError
    from backend.routes import RouteError
    from backend.provider_errors import attach_accounting
    outing=session.outing()
    try:return _suggest_starting_areas(query,session,outing)
    except (ProviderLimitError,DiscoveryError,RouteError) as error:raise attach_accounting(error,outing)


def _suggest_starting_areas(query,session,outing):
    session.settings.require_live_provider()
    if os.environ.get('WHERETO_START_LOOKUP_DEV')!='1':
        raise DiscoveryError('disabled','Starting-area suggestions are disabled. Enable the local starting-location lookup switch, enter a place, or use current location.')
    if query.destination.strip().casefold() in ('near me','nearby','current location'):
        raise DiscoveryError('location_required','Enter a destination city for a suggested starting area, or explicitly share your current location.')
    from backend.starting_scoring import regions,compare
    from backend.places import search_body
    activities=list(dict.fromkeys(query.activities))[:2]
    area=SearchArea(name=query.destination,enforce_name=query.geography.strictDestination,include_name=True,excluded_regions=query.geography.excludedRegions)
    inventory=PlacesDiscovery(outing).discover_many([DiscoveryRequest(activity=a,destination=area) for a in activities])
    first_all=[v.facts for v in inventory.venues if query.activities[0] in v.activities and v.facts.coordinates]
    first=regions(first_all,6 if session.settings.exploration else 4)
    second=[v.facts for v in inventory.venues if len(query.activities)>1 and query.activities[1] in v.activities and v.facts.coordinates]
    if not first:return {'matches':[],'message':'No verified first-activity region was found. Enter and confirm a manual starting place.','diagnostics':outing.usage()}
    candidates=[];known=set()
    # At most three finite region jobs, not a fixed central-landmark list.
    for anchor in regions(first,3):
        search_area=SearchArea(name=query.destination,coordinates=anchor.coordinates,radius_m=5000,restrict_to_area=True,
            enforce_name=query.geography.strictDestination,excluded_regions=query.geography.excludedRegions)
        body=search_body(DiscoveryRequest(activity=query.activities[0],destination=search_area),3)
        body.pop('includedType',None);body.pop('strictTypeFiltering',None)
        body['textQuery']=f'public transit stations and public squares in {query.destination}'
        with outing.reserve('lookup',sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()):
            from backend.places_transport import text_search
            raw=text_search(body,field_mask=FIELD_MASK)
        found=parse_response(raw,search_area,3)
        for p in found.candidates:
            if p.provider_id not in known and set(p.types or []) & PUBLIC_TYPES:
                candidates.append(p);known.add(p.provider_id)
    if not candidates:return {'matches':[],'message':'No trustworthy public reference was found near the checked activity regions. Enter and confirm a manual starting place.','diagnostics':outing.usage()}
    mode='walk' if query.transport=='walking' else 'drive'
    result=GoogleRouteCalculator(outing).calculate(RouteRequest(activity_groups=[
        [RoutePoint(id='reference_'+p.provider_id,place_id=p.provider_id) for p in candidates],
        [RoutePoint.from_venue(p) for p in first]],mode=mode))
    routes={(r.origin_id,r.destination_id):r for r in result.legs};matrix_requests=result.matrix_requests
    if any(r.status=='error' for r in result.legs):
        failure=next(r for r in result.legs if r.status=='error')
        error=DiscoveryError(failure.error_code or 'reference_routes',failure.error_message or 'Starting-area route comparison was unavailable. No automatic retry was made.');error.diagnostics=failure.error_context or {};raise error
    if second:
        chosen=set()
        for a in first:
            for b in sorted(second,key=lambda b:distance_m(a.coordinates,b.coordinates))[:2]:chosen.add((a.id,b.id))
        onward=GoogleRouteCalculator(outing).calculate(RouteRequest(activity_groups=[[RoutePoint.from_venue(p) for p in first],[RoutePoint.from_venue(p) for p in second]],mode=mode,required_pairs=list(chosen)))
        routes.update({(r.origin_id,r.destination_id):r for r in onward.legs});matrix_requests+=onward.matrix_requests
        failure=next((r for r in onward.legs if r.error_message),None)
        if failure:
            error=DiscoveryError(failure.error_code,failure.error_message);error.diagnostics=failure.error_context or {};raise error
    selected,scoring=compare(candidates,first,second,routes,query.firstTravel,query.maxLegTravel,query.maxLegTravelExclusive,query.travel,query.travelExclusive)
    matches=[]
    for row in selected:
        p=row['place'];precision='neighborhood' if 'neighborhood' in (p.types or []) else 'address_or_place'
        preferred=f"{len(row['preferred'])} within the original preference." if query.firstTravel else 'No first-stop maximum supplied.'
        reason=f"{row['label']} — {len(row['valid'])} checked {query.activities[0].value} options; {preferred} {len(row['onward'])} have checked onward connections. Public access and hours need confirmation."
        matches.append({'placeId':p.provider_id,'name':p.display_name,'address':p.address,'coordinates':p.coordinates.model_dump(),
            'precision':precision,'attributions':[{'provider':a.get('provider'),'uri':a.get('providerUri')} for a in p.attributions],
            'score':round(row['score'],3),'reason':reason})
    if not matches:return {'matches':[],'message':'No public starting reference has checked first-stop routes within this maximum. Confirm a manual place or change the preference.','diagnostics':{**outing.usage(),'referenceScoring':scoring}}
    token=references.create({'session':session,'outing':outing,'inventory':inventory,'routes':routes,'matches':matches,'query':query,'matrixRequests':matrix_requests,'referenceScoring':scoring})
    return {'matches':matches,'referenceToken':token,'diagnostics':{**outing.usage(),'referenceScoring':scoring},
            'message':'Choose a planning reference. This is a suggested meeting area, not your actual position.'}
