"""Local-only Task 50E orchestration. Provider evidence never comes from a client."""
from collections import OrderedDict
from datetime import datetime, timezone
import re
from hashlib import sha256
import os
import secrets
from threading import Lock
from time import monotonic, perf_counter
from typing import Literal
from pydantic import Field, model_validator

from backend.models import ContractModel, OutingDate
from backend.interpretation import InterpretationContext, activity_category
from backend.journey import Duration, Journey
from backend.location_policy import FirstTravel
from backend.places import DiscoveryError, SearchArea
from backend.provider_budget import local_real_enabled
from backend.routes import AuthorizedStart
from backend.stop_resolution import StopResolver
from backend.advanced_routing import AdvancedRouter
from backend.advanced_timing import evaluate_advanced_timing
from backend.saved_plans import Token
from backend.saved_advanced import redact_source
from backend.failures import MESSAGES, provider_code


def enabled():
    return local_real_enabled() and os.environ.get('WHERETO_ADVANCED_DEV') == '1' and os.environ.get('WHERETO_STOP_RESOLUTION_DEV') == '1'


class Choice(ContractModel):
    occurrence: int = Field(strict=True, ge=0, le=4)
    placeId: str = Field(min_length=1, max_length=200)


class DwellAnswer(ContractModel):
    occurrence: int = Field(strict=True, ge=0, lt=4)
    minutes: int = Field(strict=True, ge=0, le=10080)
    relation: Literal['exact', 'minimum', 'maximum', 'under', 'approximate'] = 'approximate'

    @model_validator(mode='after')
    def nonempty(self):
        if self.relation=='under' and self.minutes==0:raise ValueError('A visit cannot take strictly less than zero minutes.')
        return self


class AdvancedInput(ContractModel):
    token: Token = Field(repr=False)
    startingLocation: AuthorizedStart | None = Field(default=None, repr=False)
    firstTravel: FirstTravel | None = None
    betweenTravel: FirstTravel | None = None
    choice: Choice | None = None
    dwell: DwellAnswer | None = None
    departure: str | None = Field(default=None, pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    date: str | None = Field(default=None,min_length=1,max_length=100)
    action: Literal['different','discover','beyond'] | None = None
    searchNearOrigin: bool = Field(default=False,strict=True)
    includeBeyond: bool = Field(default=False,strict=True)
    destination: str | None = Field(default=None, min_length=2, max_length=200)


class PublicStop(ContractModel):
    occurrence: int
    activity: str | None = None
    requested: str
    requirement: Literal['required', 'optional']
    placeId: str
    name: str
    address: str | None
    mapsUrl: str
    duration: Duration | None
    arrival: str | None
    departure: str | None
    hoursState: str
    hours: dict
    rating: float | None
    ratingCount: int | None
    credits: list[dict]


class PublicLeg(ContractModel):
    role: str
    fromOccurrence: int | None
    toOccurrence: int | None
    seconds: float | None
    meters: int | None
    status: str
    mode: str
    mapsUrl: str | None = None


class PublicOption(ContractModel):
    id: str
    travelException: bool = False
    travelDeviations: list[str] = Field(default_factory=list)
    state: Literal['feasible', 'unverified']
    routeState: str
    stops: list[PublicStop]
    ending: str
    endpoint: dict | None
    legs: list[PublicLeg]
    knownTravelSeconds: float
    elapsedLowerSeconds: float
    elapsedUpperSeconds: float | None
    upperExclusive: bool
    totalConstraint: Duration | None
    deadlineSource: str | None
    durationState: str
    deadlineState: str
    reasons: list[str]
    omitted: list[dict]


class AdvancedResult(ContractModel):
    kind: Literal['advanced'] = 'advanced'
    token: Token = Field(repr=False)
    status: Literal['clarification', 'results', 'no_results', 'unsupported', 'provider_failure']
    message: str
    date: str | None
    destination: str | None
    transport: str
    questions: list[dict] = Field(default_factory=list)
    options: list[PublicOption] = Field(default_factory=list, max_length=3)
    saveReceipt: str | None = Field(default=None, repr=False)
    saveAccessToken: str | None = Field(default=None, repr=False)
    code: str | None = None
    bounded: Literal[True] = True
    canExpand: bool = False
    canDiscover: bool = False
    canShowBeyond: bool = False


def directions_link(origin, destination, mode):
    if not origin or not destination: return None
    from urllib.parse import urlencode
    return 'https://www.google.com/maps/dir/?'+urlencode({'api':'1','origin':'Place','origin_place_id':origin,'destination':'Place','destination_place_id':destination,'travelmode':'walking' if mode=='walk' else 'driving'})


def maps_link(identity):
    from urllib.parse import urlencode
    return 'https://www.google.com/maps/search/?' + urlencode({'api':'1','query':'Place','query_place_id':identity})


class Session:
    def __init__(self, text, journey, context, budget, *, limitation=None):
        self.text, self.journey = text, journey.model_copy(deep=True)
        self.context = context.model_copy(deep=True)
        import re
        self.requires_date_confirmation = context.timezoneBasis=='unknown' and bool(re.search(r'\b(?:today|tomorrow|tonight|this|next|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b',text,re.I))
        self.outing = budget.outing()
        self.token = secrets.token_urlsafe(32)
        self.expires = monotonic() + 600
        self.lock = Lock()
        self.resolver = self.router = None
        self.origin = None
        self.configuration = None
        self.durations = {}
        self.departure = None
        self.limitation = limitation
        self.latencies = {}
        self.receipt_key = None
        self.receipt = None
        self.last = None
        self.resolution_attempted = False
        self.route_attempted = False
        self.date_answer = False
        self.search_area = None
        self.candidates = {}
        self.seen = set()
        self.current_ids = set()
        self.actions = 0
        self.beyond = False
        self.offerable = {False:set(),True:set()}

    def base(self, **kwargs):
        return AdvancedResult(token=self.token, date=str(self.context.date) if self.context.date else None,
            destination=self.context.destination, transport=self.context.transport.value if self.context.transport else 'driving', **kwargs)

    def run(self, value):
        if value.action and self.router is None:raise ValueError('Generate an initial page before continuing.')
        if value.startingLocation and (value.startingLocation.source=='mock' or value.startingLocation.point.place_id):
            raise ValueError('Confirm real starting coordinates through the existing location control.')
        if self.limitation:
            return self.base(status='unsupported', message=self.limitation)
        from backend.date_resolution import resolve_datetime
        def calendar_for(location,zone=None,answer=None):
            calendar=resolve_datetime(answer or self.text,[],[],location,
                manual_date=answer if answer and re.fullmatch(r'\d{4}-\d{2}-\d{2}',answer) else '',
                calendar_timezone=zone,now=datetime.now(timezone.utc))
            return calendar
        def apply_calendar(calendar):
            self.context.issues=[issue for issue in self.context.issues if issue not in self.context.dateIssues]
            self.context.dateIssues=[p.message for p in calendar.problems if p.field=='date']
            self.context.issues+=self.context.dateIssues
            if not self.date_answer and calendar.date:self.context.date=calendar.date
        if value.date is not None:
            calendar=calendar_for(self.context.destination,self.context.timezone if self.context.timezoneBasis=='destination_calendar' else None,value.date)
            if calendar.date is None or any(p.reason!='past_date' or self.context.timezoneBasis=='destination_calendar' for p in calendar.problems):
                return self.base(status='clarification',message=' '.join(calendar.issues) or 'Choose a valid date.',questions=[{'field':'date','question':'What date is this outing?'}])
            if self.resolver and not getattr(self.resolver,'_named_only',False) and calendar.date!=self.context.date:raise ValueError('Regenerate to change the date after discovery.')
            self.context.date=calendar.date
            self.context.issues=[issue for issue in self.context.issues if issue not in self.context.dateIssues]
            self.context.dateIssues=[]
            self.requires_date_confirmation=False
            self.date_answer=True
        if value.destination is not None:
            if self.resolver and not getattr(self.resolver,'_named_only',False) and value.destination!=self.context.destination:raise ValueError('Regenerate to change the search area.')
            self.context.destination=value.destination
            self.search_area=None
            calendar=calendar_for(value.destination,answer=str(self.context.date) if self.date_answer and self.context.date else None)
            self.context.timezone=calendar.timezone
            self.context.timezoneBasis='destination_calendar' if calendar.timezone!='UTC' else 'unknown'
            apply_calendar(calendar)
            if calendar.timezone!='UTC':self.requires_date_confirmation=False
        if value.searchNearOrigin:
            if self.context.destination or self.resolver:raise ValueError('Change the destination through explicit regeneration.')
            if not value.startingLocation or not value.startingLocation.point.coordinates:raise ValueError('Confirm starting coordinates first.')
            # Explicit geographic consent only. Coordinates are not a timezone.
            self.search_area=SearchArea(coordinates=value.startingLocation.point.coordinates)
            self.context.destination="Near confirmed starting point"
            from backend.starting_places import verified_start_calendar
            verified=verified_start_calendar(value.startingLocation)
            if verified:
                city,zone=verified
                self.context.timezone=zone;self.context.timezoneBasis='destination_calendar'
                calendar=calendar_for(city,zone,str(self.context.date) if self.date_answer and self.context.date else None)
                apply_calendar(calendar)
                self.requires_date_confirmation=False
        # A mandatory establishment can establish its calendar from verified public
        # identity/address evidence. Resolve it once before requesting redundant dates.
        if not self.context.destination and self.search_area is None and any(s.kind=='named_place' for s in self.journey.stops):
            if self.resolver is None:
                self.resolver=StopResolver(self.outing)
                self.resolver.resolve(self.journey,None,context=self.context,named_only=True)
            choices=self.resolver.choices()['questions']
            if value.choice:self.resolver.choose(self.resolver.choices()['context'],value.choice.occurrence,value.choice.placeId)
            choices=self.resolver.choices()['questions']
            if choices:return self.base(status='clarification',message='Choose the intended destination.',questions=[dict(q,field='place') for q in choices])
            snap=self.resolver.routing_snapshot()
            failed=next((s for s in snap.stops if s.requested.kind=='named_place' and s.requested.requirement=='required' and not s.candidates),None)
            if failed:
                if failed.status=='provider_failure':
                    code='provider_local_admission' if failed.error_code=='application_limit' else provider_code(DiscoveryError(failed.error_code or 'provider','Place discovery unavailable.'))
                    return self.base(status='provider_failure',code=code,message=MESSAGES.get(code,'Place discovery could not finish.')+' Your requested destination is kept.')
                return self.base(status='no_results',message='The required destination could not be verified: '+redact_source(failed.requested.source,self.context)+'. Add its city or branch to the original request and regenerate.')
            fixed=next((s.candidates[0].facts for s in snap.stops if s.requested.kind=='named_place' and s.status=='resolved'),None)
            if fixed:
                from backend.location_context import timezone_for
                zone=fixed.timeZone.id if fixed.timeZone else timezone_for(fixed.address)
                self.search_area=SearchArea(coordinates=fixed.coordinates)
                # Public provider address, never a remote origin/browser timezone.
                if zone!='UTC':
                    self.context.destination=next((p.strip() for p in fixed.address.split(',')[1:] if timezone_for(p)==zone),fixed.address)
                    self.context.timezone=zone;self.context.timezoneBasis='destination_calendar'
                    calendar=calendar_for(self.context.destination,zone,str(self.context.date) if self.date_answer and self.context.date else None)
                    apply_calendar(calendar)
                    self.requires_date_confirmation=False
        if self.requires_date_confirmation and self.search_area is not None and self.context.timezoneBasis!='destination_calendar':
            return self.base(status='clarification',message='The nearby search area is kept. Choose an exact date because its timezone is not verified.',questions=[{'field':'date','question':'What exact date is this outing?'}])
        if self.requires_date_confirmation and self.context.timezoneBasis!='destination_calendar':
            return self.base(status='clarification',message='Choose the search area so tomorrow can use its local calendar.',questions=[{'field':'destination','question':'Which city or neighborhood should we search?'}])
        if self.context.date is None:
            return self.base(status='clarification',message=' '.join(self.context.dateIssues) or 'Choose the outing date.',questions=[{'field':'date','question':'What date is this outing?'}])
        # UTC midnight cannot prove a confirmed local date has expired when the
        # destination timezone is unknown. Ask for that missing evidence first.
        from zoneinfo import ZoneInfo
        if self.context.timezoneBasis!='destination_calendar' and self.context.date<=datetime.now(timezone.utc).date():
            if self.resolver:
                return self.base(status='unsupported',message='Confirm the destination timezone by editing the location and regenerating. Your original date and stops are kept.')
            return self.base(status='clarification',message='A destination timezone is needed to check this date without treating UTC as your local calendar.',questions=[{'field':'destination','question':'Which city or neighborhood should we search?'}])
        today = datetime.now(ZoneInfo(self.context.timezone or 'UTC')).date()
        if self.context.date < today:
            if not self.resolver or getattr(self.resolver,'_named_only',False):
                return self.base(status='clarification',message='This outing date has passed. Choose today or a future date.',questions=[{'field':'date','question':'What future date should we use?'}])
            return self.base(status='unsupported',message='This outing date has passed. Edit the date and regenerate.')
        if self.context.issues:
            return self.base(status='unsupported',message=' '.join(self.context.issues))
        returning = bool(self.journey.endpoint and (self.journey.endpoint.kind == 'origin' or self.journey.endpoint.kind == 'home' and self.context.endpointStatus == 'origin_confirmed'))
        if self.journey.endpoint and self.journey.endpoint.kind == 'home' and not returning:
            return self.base(status='unsupported',message='A separate home address is not verified by this flow. Choose Return to my starting point and confirm that origin, or request a named final establishment.')
        if not self.context.destination and self.search_area is None and (any(s.kind != 'named_place' for s in self.journey.stops) or self.journey.deadline):
            return self.base(status='clarification',message='Choose a search area without changing your stops.',questions=[{'field':'destination','question':'Which city or neighborhood should we search?'}])
        minute=self.context.departureMinute
        if minute is None:
            minute=int(value.departure[:2])*60+int(value.departure[3:]) if value.departure else self.departure
        if minute is not None and self.context.timezoneBasis=='destination_calendar':
            from backend.feasibility import _local_instant
            zone=ZoneInfo(self.context.timezone)
            instant=_local_instant(self.context.date,minute//60,minute%60,zone)
            invalid_clock=instant is None or instant<datetime.now(zone)
            if invalid_clock:
                message='That departure is past or ambiguous at a clock change. Choose a future, unambiguous destination-local departure, or edit the outing date.'
                if self.context.departureMinute is not None:
                    return self.base(status='unsupported',message=message+' Edit the original request to replace its stated departure.')
                return self.base(status='clarification',message=message,questions=[{'field':'departure','question':'What time will you depart, in the destination timezone?'}])
        config = (value.startingLocation.model_dump_json() if value.startingLocation else None,
                  value.firstTravel.model_dump_json() if value.firstTravel else None,
                  value.betweenTravel.model_dump_json() if value.betweenTravel else None)
        if self.configuration is not None and config != self.configuration:
            raise ValueError('Routing preferences changed. Regenerate from the original request.')
        if self.configuration is None:
            if 'firstTravel' in value.model_fields_set: self.context.firstTravel=value.firstTravel
            if 'betweenTravel' in value.model_fields_set:
                self.context.betweenTravel=value.betweenTravel
                self.context.maxLegTravel=None
            if not value.startingLocation and (returning or self.context.firstTravel or self.context.originText):
                return self.base(status='clarification',message='Confirm your starting point using Starting location, then continue.',questions=[{'field':'origin','question':'Confirm a starting point, then continue.'}])
            if value.startingLocation and value.startingLocation.source == 'mock':
                raise ValueError('Real journeys need a confirmed real starting point.')
            # Origins are user-authorized points, never client-supplied establishment evidence.
            if value.startingLocation and value.startingLocation.point.place_id:
                raise ValueError('Confirm starting coordinates through the existing location control.')
            self.origin = value.startingLocation
            self.configuration = config
        if self.resolution_attempted and self.resolver._result is None:
            return self.base(status='provider_failure',code='provider_service_error',message='Discovery was interrupted. Your text is kept; regenerate explicitly to start a new search.')
        if self.resolver is None:
            self.resolution_attempted = True
            self.resolver = StopResolver(self.outing)
            started=perf_counter()
            self.resolver.resolve(self.journey, self.search_area or (SearchArea(name=self.context.destination) if self.context.destination else None), context=self.context)
            self.latencies['resolutionMs']=(perf_counter()-started)*1000
        if getattr(self.resolver,'_named_only',False):
            self.resolver.complete(self.search_area or SearchArea(name=self.context.destination),self.context)
        if value.choice:
            snapshot=self.resolver.routing_snapshot()
            groups=snapshot.stops+([snapshot.endpoint] if snapshot.endpoint else [])
            group=next((s for s in groups if s.occurrence==value.choice.occurrence),None)
            if not (group and group.status=='resolved' and len(group.candidates)==1 and group.candidates[0].place_id==value.choice.placeId):
                self.resolver.choose(self.resolver.choices()['context'],value.choice.occurrence,value.choice.placeId)
        choices=self.resolver.choices()['questions']
        if choices:
            return self.base(status='clarification',message='Choose the intended destination.',questions=[dict(q,field='place') for q in choices])
        snapshot=self.resolver.routing_snapshot()
        failed=next((s for s in snapshot.stops+([snapshot.endpoint] if snapshot.endpoint else []) if s.status=='provider_failure'),None)
        if failed:
            code='provider_local_admission' if failed.error_code=='application_limit' else provider_code(DiscoveryError(failed.error_code or 'provider','Place discovery unavailable.'))
            return self.base(status='provider_failure',code=code,message=MESSAGES.get(code,'Place discovery could not finish.')+' Your original request and successful evidence are kept.')
        if self.route_attempted and self.router._result is None:
            return self.base(status='provider_failure',code='provider_service_error',message='Routing was interrupted. Your text and resolved destinations are kept; regenerate explicitly to start a new computation.')
        missing=next((s for s in snapshot.stops+([snapshot.endpoint] if snapshot.endpoint else []) if s.requested.requirement=='required' and not s.candidates),None)
        if missing:
            return self.base(status='no_results',code='no_relevant_venues',message=f'No eligible place could be verified for requested stop {missing.occurrence+1}: {redact_source(missing.requested.source,self.context)}. Required stops have been kept. Edit the request to try again.')
        if self.router is None:
            self.route_attempted = True
            self.router=AdvancedRouter(self.resolver)
            started=perf_counter()
            self.router.plan(origin=self.origin,allow_beyond_limit=True)
            self.candidates.update((self.route_id(c),c) for c in self.router.all_candidates)
            self.latencies['routingMs']=(perf_counter()-started)*1000
        if value.dwell:
            n=value.dwell.occurrence
            if n>=len(self.journey.stops): raise ValueError('Unknown stop occurrence.')
            if self.journey.stops[n].duration is not None: raise ValueError('Edit the request to replace an original duration.')
            self.durations[n]=Duration(minutes=value.dwell.minutes,relation=value.dwell.relation,
                source=f'User clarification: {value.dwell.relation} {value.dwell.minutes} minutes at stop {n+1}')
        if value.departure:
            if self.context.departureMinute is not None: raise ValueError('Edit the request to replace an original departure.')
            self.departure=int(value.departure[:2])*60+int(value.departure[3:])
        if value.action:
            if self.actions>=32 or len(self.router.checked)>=256:raise ValueError('This bounded session has ended. Viewed pages remain available.')
            self.actions+=1
            self.current_ids=set()
            self.beyond=value.action=='beyond' or value.includeBeyond
            if value.action=='discover':self.resolver.expand()
            unoffered=[c for key,c in self.candidates.items() if key not in self.seen and key in self.offerable[self.beyond]]
            if value.action=='discover' or len(unoffered)<3:
                self.router.advance(origin=self.origin,allow_beyond_limit=True)
                self.candidates.update((self.route_id(c),c) for c in self.router.all_candidates)
        self.router.use_candidates(list(self.candidates.values())[:256])
        started=perf_counter()
        timing=evaluate_advanced_timing(self.router,evaluated_at=datetime.now(timezone.utc),dwell_answers=self.durations,departure_minute=self.departure)
        self.latencies['timingMs']=(perf_counter()-started)*1000
        route_errors=[l.evidence.error_code for c in timing.candidates for l in c.route.legs if l.evidence.error_code]
        def permitted(c,beyond=False):
            if any(l.evidence.error_code=='application_limit' for l in c.route.legs):return False
            # Explicit exceptions waive only scoped travel limits. All original
            # deadline/duration/hours/reachability checks still apply.
            if c.route.route_status=='beyond_limit':
                return beyond and c.routing_state=='feasible' and all(x!='infeasible' for x in (c.duration_state,c.deadline_state,c.hours_state)) and not (c.route.between_total_check and c.route.between_total_check.state=='beyond_limit')
            return c.state!='infeasible'
        self.offerable={b:{self.route_id(c.route) for c in timing.candidates if permitted(c,b) and (not b or c.route.route_status=='beyond_limit')} for b in (False,True)}
        available=[c for c in timing.candidates if permitted(c,self.beyond) and (not self.beyond or c.route.route_status=='beyond_limit')]
        eligible=sorted((c for c in available if self.route_id(c.route) in self.current_ids or self.route_id(c.route) not in self.seen),key=lambda c:(c.state!='feasible',c.route.route_status=='beyond_limit'))[:3]
        self.current_ids={self.route_id(c.route) for c in eligible}
        self.seen.update(self.current_ids)
        options=[]
        questions=[]
        for c in eligible:
            route=c.route
            stops=[]
            for v,t in zip(route.visits,c.visits):
                facts=v.selected.facts
                from backend.planning_hours import venue_hours
                stops.append(PublicStop(occurrence=v.occurrence,activity=activity_category(redact_source(v.requested.source,self.context)),requested=redact_source(v.requested.source,self.context),requirement=v.requested.requirement,
                    placeId=facts.id,name=facts.name,address=facts.address,mapsUrl=maps_link(facts.id),duration=v.requested.duration.model_copy(update={'source':redact_source(v.requested.duration.source,self.context)}) if v.requested.duration else None,
                    arrival=t.arrival.earliest.isoformat() if t.arrival.earliest and t.arrival.offsets.exact else None,
                    departure=t.departure.earliest.isoformat() if t.departure.earliest and t.departure.offsets.exact else None,
                    hoursState=t.hours_state,hours=venue_hours(facts,self.context.date,calendar_timezone=self.context.timezone),
                    rating=facts.rating,ratingCount=facts.ratingCount,credits=[a.model_dump(mode='json') for a in facts.attributions or []]))
            identity=sha256(repr(([(v.occurrence,v.selected.place_id) for v in route.visits],route.ending,route.endpoint.place_id if route.endpoint else None)).encode()).hexdigest()[:32]
            options.append(PublicOption(id='advanced_'+identity,state='unverified' if route.route_status=='beyond_limit' else c.state,travelException=route.route_status=='beyond_limit',travelDeviations=[f"{'First stop' if route.legs[t.leg_index].role=='origin_to_first' else 'Between stops'}: {t.actual:g} {t.preference.unit}; preferred {t.preferred:g}; original maximum {t.maximum:g}." for t in route.checks if t.state in ('outside_preference','beyond_limit')],routeState=route.route_status,stops=stops,ending=route.ending,
                endpoint={'placeId':route.endpoint.place_id,'name':route.endpoint.facts.name,'mapsUrl':maps_link(route.endpoint.place_id),
                    'credits':[a.model_dump(mode='json') for a in route.endpoint.facts.attributions or []]} if route.endpoint else None,
                legs=[PublicLeg(role=l.role,fromOccurrence=l.from_occurrence,toOccurrence=l.to_occurrence,seconds=l.evidence.duration_seconds,
                    meters=l.evidence.distance_meters,status=l.evidence.status,mode=l.evidence.mode,mapsUrl=directions_link(l.evidence.origin_id if l.role in ('inter_activity','final_destination') else None,l.evidence.destination_id,l.evidence.mode)) for l in route.legs],
                knownTravelSeconds=float(c.known_travel_seconds),elapsedLowerSeconds=float(c.elapsed.lower),
                elapsedUpperSeconds=float(c.elapsed.upper) if c.elapsed.upper is not None else None,upperExclusive=c.elapsed.upper_exclusive,
                totalConstraint=route.journey.total_duration.model_copy(update={'source':redact_source(route.journey.total_duration.source,self.context)}) if route.journey.total_duration else None,deadlineSource=redact_source(route.journey.deadline.source,self.context) if route.journey.deadline else None,durationState=c.duration_state,deadlineState=c.deadline_state,reasons=list(dict.fromkeys(r.message for r in c.reasons if r.state!='feasible')),
                omitted=[{'occurrence':o.occurrence,'requested':redact_source(o.requested.source,self.context),'reason':o.reason} for o in route.omitted]))
            if route.journey.total_duration or route.journey.deadline:
                for v in route.visits:
                    if v.requested.duration is None:
                        q={'field':'dwell','occurrence':v.occurrence,'question':f'How long will you spend on {redact_source(v.requested.source,self.context)}?'}
                        if q not in questions: questions.append(q)
            if route.journey.deadline and c.start is None and self.context.departureMinute is None and self.departure is None:
                q={'field':'departure','question':'What time will you depart, in the destination timezone?'}
                if q not in questions: questions.append(q)
        message='Here are the options checked for your outing. Add any missing visit times to check the whole trip.' if options else ' '.join(timing.routing_reasons) or 'All checked options are infeasible: '+' '.join(dict.fromkeys(r.message for c in timing.candidates for r in c.reasons if r.state=='infeasible'))
        if not options and timing.candidates:
            evidence=[]
            for c in timing.candidates:
                if c.duration_state=='infeasible' and c.route.journey.total_duration:
                    d=c.route.journey.total_duration
                    lower=float(c.elapsed.lower)/60
                    upper=float(c.elapsed.upper)/60 if c.elapsed.upper is not None else None
                    span=f'{lower:g} minutes or more' if upper is None else f'{lower:g} to {upper:g} minutes'
                    evidence.append(f'Whole-trip requirement: {d.relation} {d.minutes} minutes. Supported journey duration: {span}.')
            if evidence:message='No checked option meets your requirements. '+' '.join(dict.fromkeys(evidence))+' Edit your request or preferences to try a different requirement.'
        route_error_code='provider_quota_rejected' if 'quota' in route_errors else 'provider_local_admission' if 'application_limit' in route_errors else 'provider_service_error'
        if route_errors:
            message=MESSAGES[route_error_code]+' Available evidence and your original constraints are kept; incomplete timing remains unverified.'
        result=self.base(status='results' if options else 'no_results',message=message,options=options,questions=questions,
            code=route_error_code if route_errors else None if options else 'insufficient_routing')
        if options:
            from backend.saved_advanced import issue_advanced
            key=repr(([(p.id,p.state,p.model_dump()['stops']) for p in options],self.durations,self.departure))
            if key!=self.receipt_key:
                self.receipt=issue_advanced(self,eligible,options)
                self.receipt_key=key
            result.saveReceipt,result.saveAccessToken=self.receipt
        result.canExpand=self.actions<32 and len(self.router.checked)<256 and (any(self.route_id(c.route) not in self.seen and permitted(c,self.beyond) and (not self.beyond or c.route.route_status=='beyond_limit') for c in timing.candidates) or self.router.pending_paths)
        result.canDiscover=self.actions<32 and len(self.router.checked)<256 and self.resolver.can_expand()
        result.canShowBeyond=self.actions<32 and len(self.router.checked)<256 and any(self.route_id(c.route) not in self.seen and c.route.route_status=='beyond_limit' and permitted(c,True) for c in timing.candidates)
        if not options and result.canShowBeyond:result.message='No checked option fits your travel maximum. Search more or explicitly view options beyond that travel limit.'
        if not options and value.action and not result.canShowBeyond and not route_errors:result.message='No further eligible options in this checked batch. Earlier pages are kept. Other venues may exist.'
        if 'quota' in route_errors:result.canExpand=result.canDiscover=result.canShowBeyond=False
        self.last=result
        return result


    @staticmethod
    def route_id(route):
        return tuple((v.occurrence,v.selected.place_id) for v in route.visits)


class Sessions:
    def __init__(self): self.items=OrderedDict();self.lock=Lock()

    def diagnostics(self):
        with self.lock:
            latest=next(reversed(self.items.values()),None) if self.items else None
            return {'activeSessions':len(self.items),'lastStageMs':dict(latest.latencies) if latest else {}}

    def create(self,text,result,budget,preferences):
        if not enabled() or result.executionStatus!='advanced_unavailable' or result.context is None or not result.interpretation.journey:
            return None
        ai=result.interpretation
        # Unsupported independent hard requirements must not vanish at the advanced branch.
        import re
        limitation=None
        if preferences.budget.strip() or ai.budget_per_person is not None or ai.budget_group is not None or re.search(r'[$€£¥₹]|\b(?:budget|wheelchair|accessible|tickets?|reservations?|vegan|halal|kosher|private room)\b',text,re.I):
            limitation='This advanced flow cannot verify spending, accessibility, tickets or reservations. Edit those requirements explicitly before continuing.'
        if len(ai.journey.stops)>4: limitation='Advanced routing supports up to four stops. Edit the request to choose fewer stops.'
        session=Session(text,ai.journey,result.context,budget,limitation=limitation)
        if preferences.date.strip():session.requires_date_confirmation=False;session.date_answer=True
        with self.lock:
            now=monotonic()
            self.items=OrderedDict((k,s) for k,s in self.items.items() if s.expires>now)
            self.items[session.token]=session
            while len(self.items)>50:self.items.popitem(last=False)
        return session.token

    def run(self,value):
        if not enabled(): raise DiscoveryError('disabled','Advanced planning is enabled only in approved local development.')
        with self.lock:session=self.items.get(value.token)
        if not session or session.expires<=monotonic(): raise ValueError('Advanced session expired. Your text is kept; regenerate to continue.')
        if not session.lock.acquire(blocking=False): raise DiscoveryError('application_limit','This outing is already being processed.')
        try:return session.run(value)
        finally:session.lock.release()


sessions=Sessions()
