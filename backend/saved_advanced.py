"""Version 2 app-owned requirements. No Google content or private locations."""
import re
from typing import Annotated, Literal
from pydantic import Field, model_validator
from backend.models import ContractModel, OutingRequest
from backend.journey import Journey


def redact_source(value, context):
    """Safe app-owned display/storage text, independent of provider facts."""
    value=re.sub(r'\b(?:start(?:ing)?|leave|depart)\s+from\b[^;!?]*','Start from [private location omitted]',value,flags=re.I)
    for private in (context.originText,context.endpointAnswer):
        if private and len(private)>=3 and private.casefold()!='return to my starting point':
            value=re.sub(re.escape(private),'[private location omitted]',value,flags=re.I)
    return value


class AdvancedSaved(ContractModel):
    sourceText: str = Field(min_length=1,max_length=4000)
    journey: Journey
    originalJourney: Journey | None = None
    budgetScope: Literal['outing','travel'] = 'outing'
    durationOverrides: list[Annotated[int, Field(strict=True,ge=0,lt=4)]] = Field(default_factory=list,max_length=4)
    departureOverride: bool = Field(default=False,strict=True)
    occurrenceOrder: list[int] = Field(min_length=1,max_length=4)
    omittedOccurrences: list[int] = Field(max_length=4)
    ending: Literal['last_activity','origin','named_destination']
    endpointId: str | None = Field(default=None,pattern=r'^[A-Za-z0-9_-]{1,200}$')
    travelException: bool = Field(default=False,strict=True)
    routingPolicy: Literal['traffic_aware_current','walking'] | None = None
    departureNow: bool = Field(default=False,strict=True)
    historicalTiming: Literal['feasible','unverified']
    timingProvenance: Literal['route_estimates_and_user_constraints_not_retained'] = 'route_estimates_and_user_constraints_not_retained'
    departureMinute: int | None = Field(default=None,strict=True,ge=0,lt=1440)

    @model_validator(mode='after')
    def coverage(self):
        if self.budgetScope=='travel' and self.journey.total_duration is None:raise ValueError('Travel-only override needs its original source budget.')
        if any(type(n) is not int or not 0<=n<len(self.journey.stops) for n in self.durationOverrides) or len(set(self.durationOverrides))!=len(self.durationOverrides):raise ValueError('Invalid duration override occurrences.')
        if self.originalJourney:
            original=self.originalJourney.model_dump()
            effective=self.journey.model_dump()
            if len(original['stops'])!=len(effective['stops']):raise ValueError('Original stop provenance changed.')
            for n,(before,after) in enumerate(zip(original['stops'],effective['stops'])):
                if n in self.durationOverrides:after['duration']=before['duration']
            if original!=effective:raise ValueError('An override changed unrelated original requirements.')
        indexes=self.occurrenceOrder+self.omittedOccurrences
        if sorted(indexes)!=list(range(len(self.journey.stops))) or self.journey.order_conflict:
            raise ValueError('Incomplete advanced requirements')
        if any(self.journey.stops[i].requirement!='optional' for i in self.omittedOccurrences):
            raise ValueError('Required occurrence omitted')
        from backend.advanced_routing import _ancestors
        positions={n:i for i,n in enumerate(self.occurrenceOrder)}
        if any(positions[a]>=positions[b] for b,parents in _ancestors(self.journey).items() for a in parents if a in positions and b in positions):
            raise ValueError('Saved precedence violation')
        if self.journey.ordering=='unspecified' and self.occurrenceOrder!=sorted(self.occurrenceOrder):
            raise ValueError('Source order changed')
        if (self.endpointId is not None)!=(self.ending=='named_destination'):
            raise ValueError('Endpoint reference missing')
        if bool(self.journey.endpoint)!=(self.ending!='last_activity'):
            raise ValueError('Endpoint requirement changed')
        if self.journey.endpoint and self.journey.endpoint.kind=='origin' and self.ending!='origin':
            raise ValueError('Return requirement changed')
        return self


def issue_advanced(session,candidates,options):
    from backend.interpretation import activity_category
    from backend.saved_plans import SavedStop, SavedOption, receipts
    from backend.saved_plans import digest
    import secrets
    from time import monotonic
    # Preserve user wording, redacting any explicit private origin and supplied home.
    source=session.text
    def redact(value):
        if isinstance(value,str):return redact_source(value,session.context)
        if isinstance(value,list):return [redact(v) for v in value]
        if isinstance(value,dict):return {k:redact(v) for k,v in value.items()}
        return value
    source=redact(source)
    context=session.context
    activities=[activity_category(s.source) or 'custom:requested destination' for s in session.journey.stops]
    constraints=OutingRequest(activities=activities,location=context.destination or 'Named destinations',date=context.date,
        calendarTimezone=context.timezone,transport=context.transport or 'driving',startTime=context.departureMinute or 0,
        explicitStart=context.departureMinute is not None,firstTravel=context.firstTravel.model_copy(update={'originText':None}) if context.firstTravel else None,
        betweenTravel=context.betweenTravel.model_copy(update={'originText':None}) if context.betweenTravel else None,
        geography=context.geography or {},travel=context.travel,travelExclusive=context.travelExclusive,
        maxLegTravel=context.maxLegTravel,maxLegTravelExclusive=context.maxLegTravelExclusive)
    saved=[]
    for candidate,option in zip(candidates,options):
        route=candidate.route
        advanced=AdvancedSaved(sourceText=source,originalJourney=Journey.model_validate(redact(session.journey.model_dump())),budgetScope=session.budget_scope,durationOverrides=sorted(session.durations),departureOverride='departure' in session.explicit_overrides,journey=Journey.model_validate(redact(route.journey.model_dump())),occurrenceOrder=[v.occurrence for v in route.visits],
            omittedOccurrences=[o.occurrence for o in route.omitted],ending=route.ending,endpointId=route.endpoint.place_id if route.endpoint else None,
            routingPolicy='walking' if context.transport and context.transport.value=='walking' else 'traffic_aware_current',departureNow=context.departureNow and session.departure is None,historicalTiming=option.state,travelException=option.travelException,departureMinute=session.departure if session.departure is not None else context.departureMinute)
        saved.append(SavedOption(candidateId=option.id,advanced=advanced,stops=[SavedStop(position=i,activity=activities[v.occurrence],
            provider='google_places',reference=v.selected.place_id,timingBasis='unknown',start=None,end=None,duration=None) for i,v in enumerate(route.visits)]))
    token,access=secrets.token_urlsafe(32),secrets.token_urlsafe(32)
    safe={'version':2,'dataMode':'real','constraints':constraints.model_dump(mode='json'),'options':saved,'bound':digest(access)}
    with receipts.lock:
        receipts.items[token]=(monotonic()+600,safe)
        while len(receipts.items)>100: receipts.items.popitem(last=False)
    return token,access
