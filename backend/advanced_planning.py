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
from pydantic import Field

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


class AdvancedAnswerError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


from backend.advanced_preferences import Choice, DwellAnswer, AdvancedEdits


class AdvancedInput(ContractModel):
    token: Token = Field(repr=False)
    startingLocation: AuthorizedStart | None = Field(default=None, repr=False)
    firstTravel: FirstTravel | None = None
    betweenTravel: FirstTravel | None = None
    edits: AdvancedEdits | None = None
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
    originApproximate: bool = False
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
    budgetScope: Literal['outing','travel'] = 'outing'
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
    preferences: dict = Field(default_factory=dict)
    detailsToken: str | None = Field(default=None,repr=False)
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
        self.budget_scope = 'outing'
        self.explicit_overrides = set()
        self.details_token = None
        self.departure = None
        self.limitation = limitation
        self.latencies = {}
        self.timing_counts = {}
        self.receipt_key = None
        self.receipt = None
        self.last = None
        self.resolution_attempted = False
        self.route_attempted = False
        self.date_answer = False
        self.search_area = None
        self.near_origin = None
        self.candidates = {}
        self.seen = set()
        self.current_ids = set()
        self.actions = 0
        self.beyond = False
        self.offerable = {False:set(),True:set()}

    def base(self, **kwargs):
        return AdvancedResult(token=self.token, date=str(self.context.date) if self.context.date else None,
            preferences=self.preferences(), destination=self.context.destination, transport=self.context.transport.value if self.context.transport else 'driving', **kwargs)

    def preferences(self):
        stops=[]
        choices=self.resolver.preference_choices() if self.resolver and self.resolver._result else []
        for choice in choices:choice['label']=redact_source(choice['label'],self.context)
        for n,stop in enumerate(self.journey.stops):
            effective=self.durations.get(n,stop.duration)
            stops.append({'occurrence':n,'requested':redact_source(stop.source,self.context),
                'duration':{**effective.model_dump(mode='json'),'source':redact_source(effective.source,self.context)} if effective else None,
                'originalDuration':{**stop.duration.model_dump(mode='json'),'source':redact_source(stop.duration.source,self.context)} if stop.duration else None,
                'override':n in self.explicit_overrides})
        departure=self.departure if self.departure is not None else self.context.departureMinute
        return {'stops':stops,'budget':{**self.journey.total_duration.model_dump(mode='json'),'source':redact_source(self.journey.total_duration.source,self.context)} if self.journey.total_duration else None,
            'budgetScope':self.budget_scope,'scopeOverride':self.budget_scope!='outing',
            'departure':f'{departure//60:02d}:{departure%60:02d}' if departure is not None else None,
            'departureNow':self.context.departureNow and self.departure is None,'departureOverride':'departure' in self.explicit_overrides,'deadlineSource':redact_source(self.journey.deadline.source,self.context) if self.journey.deadline else None,
            'returnToOrigin':bool(self.journey.endpoint and (self.journey.endpoint.kind=='origin' or self.journey.endpoint.kind=='home' and self.context.endpointStatus=='origin_confirmed')),
            'endpoint':redact_source(self.journey.endpoint.source,self.context) if self.journey.endpoint else None,
            'choices':choices}

    def apply_edits(self, edits):
        scope=edits.budgetScope or self.budget_scope
        if edits.budgetScope and self.journey.total_duration is None:
            raise AdvancedAnswerError('advanced_answer_invalid','There is no whole-trip duration to change. Keep the original request or edit its wording.')
        if any(n>=len(self.journey.stops) for n in edits.resetDwell):raise AdvancedAnswerError('advanced_answer_invalid','Choose an existing visit to reset.')
        for d in edits.dwell:
            if d.occurrence>=len(self.journey.stops):raise AdvancedAnswerError('advanced_answer_invalid','Choose an existing visit.')
            if d.minutes==0 and not (scope=='travel' and d.zeroCountedTime and self.journey.deadline is None):
                raise AdvancedAnswerError('advanced_answer_invalid','Zero counted visit time needs an explicit travel-only choice and confirmation. Include positive visit time for an entire-outing budget or a finish deadline.')
        retained={n:d for n,d in self.durations.items() if n not in edits.resetDwell}
        retained.update({d.occurrence:d for d in edits.dwell})
        if any(d.minutes==0 for d in retained.values()) and (scope!='travel' or self.journey.deadline is not None):
            raise AdvancedAnswerError('advanced_answer_invalid','Set a positive visit duration before including visits in the time budget or checking a finish deadline.')
        if edits.choices:
            if not self.resolver:raise AdvancedAnswerError('advanced_answer_invalid','Resolve the destination choices first.')
            allowed={q['occurrence']:{c['placeId'] for c in q['choices']} for q in self.resolver.preference_choices()}
            if any(c.placeId not in allowed.get(c.occurrence,set()) for c in edits.choices):raise AdvancedAnswerError('advanced_answer_invalid','Choose one of the verified destinations.')
            from backend.location_context import timezone_for
            for choice in edits.choices:
                candidate=next(c for c in self.resolver._alternatives[choice.occurrence] if c.place_id==choice.placeId)
                zone=candidate.facts.timeZone.id if candidate.facts.timeZone else timezone_for(candidate.facts.address)
                if self.router and self.context.timezoneBasis=='destination_calendar' and zone!=self.context.timezone:
                    raise AdvancedAnswerError('advanced_answer_invalid','This destination uses another local calendar. Edit Location and regenerate to revalidate the area and date.')
        self.budget_scope=scope
        for n in edits.resetDwell:self.durations.pop(n,None);self.explicit_overrides.discard(n)
        if edits.resetDeparture:self.departure=None;self.explicit_overrides.discard('departure')
        for d in edits.dwell:
            self.durations[d.occurrence]=Duration(minutes=d.minutes,relation=d.relation,
                source=f'Explicit user override: {d.relation} {d.minutes} counted minutes at stop {d.occurrence+1}')
            self.explicit_overrides.add(d.occurrence)
        if edits.departure is not None:
            self.departure=int(edits.departure[:2])*60+int(edits.departure[3:]);self.explicit_overrides.add('departure')
        changed=False
        for choice in edits.choices:
            changed|=self.resolver.change_choice(choice.occurrence,choice.placeId)
        if changed:
            old=self.router
            self.router=None;self.route_attempted=False
            self.candidates={}
            self.reusable_routes=dict(old._evidence) if old else {}
        # A changed verdict invalidates old pages/receipts, not compatible routes.
        self.seen.clear();self.current_ids.clear();self.offerable={False:set(),True:set()}
        self.receipt=self.receipt_key=None

    def run(self, value):
        if value.action and self.router is None:raise ValueError('Generate an initial page before continuing.')
        if value.startingLocation and (value.startingLocation.source=='mock' or value.startingLocation.point.place_id):
            raise ValueError('Confirm real starting coordinates through the existing location control.')
        if self.near_origin is not None and value.startingLocation != self.near_origin:
            raise AdvancedAnswerError('advanced_origin_changed','Your starting point changed. Regenerate to use the new origin.')
        if value.edits and value.action:raise AdvancedAnswerError('advanced_answer_invalid','Apply preferences before exploring more options.')
        if self.router:
            from backend.routes import current_evidence
            mode='walk' if self.context.transport and self.context.transport.value=='walking' else 'drive'
            stale=any(not current_evidence(l.evidence,mode) for c in self.candidates.values() for l in c.legs)
            if stale:
                if value.action:
                    return self.base(status='unsupported',message='These travel estimates have expired. Regenerate plans to check current routes with your saved preferences.')
                self.router=None;self.route_attempted=False;self.candidates={};self.reusable_routes={}
                self.seen.clear();self.current_ids.clear();self.offerable={False:set(),True:set()}
                self.receipt=self.receipt_key=None
        if value.edits:
            supplied=(value.startingLocation.model_dump_json() if value.startingLocation else None,value.firstTravel.model_dump_json() if value.firstTravel else None,value.betweenTravel.model_dump_json() if value.betweenTravel else None)
            if self.configuration is not None and supplied!=self.configuration:raise AdvancedAnswerError('advanced_origin_changed','Routing preferences changed. Regenerate to use the new origin or travel limits.')
            self.apply_edits(value.edits)
        if self.limitation:
            return self.base(status='unsupported', message=self.limitation)
        from zoneinfo import ZoneInfo
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
            if self.near_origin is not None and value.destination!=self.context.destination:
                raise AdvancedAnswerError('advanced_answer_invalid','Regenerate to change the accepted nearby search area.')
            self.context.destination=value.destination
            if self.near_origin is None:self.search_area=None
            calendar=calendar_for(value.destination,answer=str(self.context.date) if self.date_answer and self.context.date else None)
            self.context.timezone=calendar.timezone
            self.context.timezoneBasis='destination_calendar' if calendar.timezone!='UTC' else 'unknown'
            apply_calendar(calendar)
            if calendar.timezone!='UTC':self.requires_date_confirmation=False
        if value.searchNearOrigin:
            if not value.startingLocation or not value.startingLocation.point.coordinates:
                raise AdvancedAnswerError('advanced_answer_invalid','Confirm a starting point first, then choose nearby search.')
            if self.near_origin is None:
                if self.context.destination or self.resolver or self.context.geography and self.context.geography.strictDestination:
                    raise AdvancedAnswerError('advanced_answer_invalid','Keep the requested destination, or edit Location and regenerate to change it.')
                # Explicit geography consent never changes the exact route origin.
                self.near_origin=value.startingLocation
                self.search_area=SearchArea(coordinates=value.startingLocation.point.coordinates,
                    excluded_regions=self.context.geography.excludedRegions if self.context.geography else [])
                self.context.destination='Near confirmed starting point'
            from backend.starting_places import verified_start_calendar
            verified=verified_start_calendar(value.startingLocation)
            if verified:
                city,zone=verified
                self.context.timezone=zone;self.context.timezoneBasis='destination_calendar'
                apply_calendar(calendar_for(city,zone,str(self.context.date) if self.date_answer and self.context.date else None))
                self.requires_date_confirmation=False
            elif self.resolver is None:
                # GPS is a search bias, never a city/timezone assertion. Existing
                # discovery supplies public place evidence without another lookup.
                self.resolver=StopResolver(self.outing)
                started=perf_counter()
                self.resolver.resolve(self.journey,self.search_area,context=self.context)
                self.latencies['resolutionMs']=(perf_counter()-started)*1000
                from backend.location_context import timezone_for
                facts=[c.facts for group in self.resolver.routing_snapshot().stops for c in group.candidates]
                zones={v.timeZone.id if v.timeZone else timezone_for(v.address) for v in facts}
                if len(zones)==1 and 'UTC' not in zones:
                    zone=next(iter(zones))
                    self.context.timezone=zone;self.context.timezoneBasis='destination_calendar'
                    apply_calendar(calendar_for(None,zone,str(self.context.date) if self.date_answer and self.context.date else None))
                    self.requires_date_confirmation=False
        # A mandatory establishment can establish its calendar from verified public
        # identity/address evidence. Resolve it once before requesting redundant dates.
        if not self.context.destination and self.search_area is None and any(s.kind=='named_place' for s in self.journey.stops):
            if self.resolver is None:
                self.resolver=StopResolver(self.outing)
                started=perf_counter()
                self.resolver.resolve(self.journey,None,context=self.context,named_only=True)
                self.latencies['namedResolutionMs']=(perf_counter()-started)*1000
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
        if self.context.departureNow and self.departure is None and not value.departure and not self.date_answer and self.context.timezoneBasis=='destination_calendar':
            self.context.date=datetime.now(ZoneInfo(self.context.timezone)).date()
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
        from backend.journey import ambiguous_return
        if ambiguous_return(self.journey.endpoint) and self.context.endpointStatus != 'origin_confirmed':
            return self.base(status='unsupported',message='Confirm where you mean by be back before generating this outing.')
        returning = bool(self.journey.endpoint and (self.journey.endpoint.kind == 'origin' or self.journey.endpoint.kind == 'home' and self.context.endpointStatus == 'origin_confirmed'))
        if self.journey.endpoint and self.journey.endpoint.kind == 'home' and not returning:
            return self.base(status='unsupported',message='A separate home address is not verified by this flow. Choose Return to my starting point and confirm that origin, or request a named final establishment.')
        if not self.context.destination and self.search_area is None and (any(s.kind != 'named_place' for s in self.journey.stops) or self.journey.deadline):
            return self.base(status='clarification',message='Choose a search area without changing your stops.',questions=[{'field':'destination','question':'Which city or neighborhood should we search?'}])
        if self.context.departureNow and self.departure is None and not value.departure:
            instant=datetime.now(timezone.utc)
            if self.context.date != instant.astimezone(ZoneInfo(self.context.timezone)).date():
                return self.base(status='clarification',message='Now means today at the destination. Choose an explicit departure for this date.',questions=[{'field':'departure','question':'What time will you depart?'}])
            self.context.departureInstant=instant
        minute=self.departure if self.departure is not None else self.context.departureMinute
        if minute is None:
            minute=int(value.departure[:2])*60+int(value.departure[3:]) if value.departure else self.departure
        if minute is not None and self.context.timezoneBasis=='destination_calendar':
            from backend.feasibility import _local_instant
            zone=ZoneInfo(self.context.timezone)
            instant=_local_instant(self.context.date,minute//60,minute%60,zone)
            invalid_clock=instant is None or instant<datetime.now(zone)
            if invalid_clock:
                message='That departure is past or ambiguous at a clock change. Choose a future, unambiguous destination-local departure, or edit the outing date.'
                if self.context.departureMinute is not None and self.departure is None:
                    return self.base(status='unsupported',message=message+' Change Departure time in Set preferences to explicitly override the original departure.')
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
            if not value.startingLocation and (returning or self.context.departureNow or self.context.firstTravel or self.context.originText):
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
        if self.resolver and self.resolver._result:
            # Clocks are action-scoped even when venue and directional evidence
            # remain compatible. Never reuse an earlier now verdict.
            self.resolver._result.context=self.context.model_copy(deep=True)
        if getattr(self.resolver,'_named_only',False):
            started=perf_counter()
            self.resolver.complete(self.search_area or SearchArea(name=self.context.destination),self.context)
            self.latencies['activityDiscoveryMs']=(perf_counter()-started)*1000
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
            self.router._evidence.update(getattr(self,'reusable_routes',{}))
            started=perf_counter()
            self.router.plan(origin=self.origin,allow_beyond_limit=True)
            self.candidates.update((self.route_id(c),c) for c in self.router.all_candidates)
            self.latencies['routingMs']=(perf_counter()-started)*1000
        if value.dwell:
            n=value.dwell.occurrence
            if n>=len(self.journey.stops): raise ValueError('Unknown stop occurrence.')
            if self.journey.stops[n].duration is not None: raise ValueError('Edit the request to replace an original duration.')
            if value.dwell.minutes==0:raise AdvancedAnswerError('advanced_answer_invalid','Use the time-budget preferences to explicitly choose travel-only and confirm zero counted visit time.')
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
        zero=next((n for n,stop in enumerate(self.journey.stops) if (d:=self.durations.get(n,stop.duration)) is not None and d.minutes==0 and (self.budget_scope!='travel' or n not in self.explicit_overrides or self.journey.deadline is not None)),None)
        if zero is not None:
            return self.base(status='clarification',message='Zero is not a realistic visit duration. Supply positive visit time, or explicitly confirm zero counted time under a travel-only budget.',questions=[{'field':'dwell','occurrence':zero,'question':'How should time at this stop be counted?'}])
        started=perf_counter()
        timing=evaluate_advanced_timing(self.router,evaluated_at=datetime.now(timezone.utc),dwell_answers=self.durations,departure_minute=self.departure,budget_scope=self.budget_scope,allow_overrides=True)
        self.latencies['timingMs']=(perf_counter()-started)*1000
        self.timing_counts={state:sum(c.state==state for c in timing.candidates) for state in ('feasible','infeasible','unverified')}
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
        pool=sorted((c for c in available if self.route_id(c.route) in self.current_ids or self.route_id(c.route) not in self.seen),key=lambda c:(c.state!='feasible',c.route.route_status=='beyond_limit',sum(t.state=='outside_preference' for t in c.route.checks),c.route.known_travel_seconds))
        eligible=[]
        while pool and len(eligible)<3:
            best=pool[0]
            def category(c):return (c.state,c.route.route_status,sum(t.state=='outside_preference' for t in c.route.checks))
            near=[c for c in pool if category(c)==category(best)
                  and c.route.known_travel_seconds<=best.route.known_travel_seconds+60]
            def overlap(candidate):
                signature=self.route_id(candidate.route)
                # Keep a viewed page stable across field-only answers. Otherwise
                # diversify every occurrence among comparable verified options.
                history=[self.route_id(c.route) for c in eligible]
                return (signature not in self.current_ids,
                        sum(key in previous for key in signature for previous in history),
                        sum(key in previous for key in signature for previous in self.seen),
                        candidate.route.known_travel_seconds)
            chosen=min(near,key=overlap)
            eligible.append(chosen);pool.remove(chosen)
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
            options.append(PublicOption(id='advanced_'+identity,originApproximate=bool(self.origin and (self.origin.source=='suggested' or self.origin.accuracy_m and self.origin.accuracy_m>100 or self.origin.precision not in ('device','address_or_place'))),state='unverified' if route.route_status=='beyond_limit' else c.state,travelException=route.route_status=='beyond_limit',travelDeviations=[f"{'First stop' if route.legs[t.leg_index].role=='origin_to_first' else 'Between stops'}: {t.actual:g} {t.preference.unit}; preferred {t.preferred:g}; original maximum {t.maximum:g}." for t in route.checks if t.state in ('outside_preference','beyond_limit')],routeState=route.route_status,stops=stops,ending=route.ending,
                endpoint={'placeId':route.endpoint.place_id,'name':route.endpoint.facts.name,'mapsUrl':maps_link(route.endpoint.place_id),
                    'credits':[a.model_dump(mode='json') for a in route.endpoint.facts.attributions or []]} if route.endpoint else None,
                legs=[PublicLeg(role=l.role,fromOccurrence=l.from_occurrence,toOccurrence=l.to_occurrence,seconds=l.evidence.duration_seconds,
                    meters=l.evidence.distance_meters,status=l.evidence.status,mode=l.evidence.mode,mapsUrl=directions_link(l.evidence.origin_id if l.role in ('inter_activity','final_destination') else None,l.evidence.destination_id,l.evidence.mode)) for l in route.legs],
                knownTravelSeconds=float(c.known_travel_seconds),elapsedLowerSeconds=float(c.elapsed.lower),
                elapsedUpperSeconds=float(c.elapsed.upper) if c.elapsed.upper is not None else None,upperExclusive=c.elapsed.upper_exclusive,
                budgetScope=self.budget_scope,totalConstraint=route.journey.total_duration.model_copy(update={'source':redact_source(route.journey.total_duration.source,self.context)}) if route.journey.total_duration else None,deadlineSource=redact_source(route.journey.deadline.source,self.context) if route.journey.deadline else None,durationState=c.duration_state,deadlineState=c.deadline_state,reasons=list(dict.fromkeys(r.message for r in c.reasons if r.state!='feasible')),
                omitted=[{'occurrence':o.occurrence,'requested':redact_source(o.requested.source,self.context),'reason':o.reason} for o in route.omitted]))
            if route.journey.total_duration and self.budget_scope=='outing' or route.journey.deadline or self.context.departureNow and c.hours_state=='unverified' and any(v.selected.facts.currentOpeningHours is not None for v in route.visits):
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
                    measured=c.travel if self.budget_scope=='travel' else c.elapsed
                    lower=float(measured.lower)/60
                    upper=float(measured.upper)/60 if measured.upper is not None else None
                    span=f'{lower:g} minutes or more' if upper is None else f'{lower:g} to {upper:g} minutes'
                    evidence.append(f"{'Travel-only' if self.budget_scope=='travel' else 'Whole-trip'} requirement: {d.relation} {d.minutes} minutes. Supported journey duration: {span}.")
            if evidence:message='No checked option meets your requirements. '+' '.join(dict.fromkeys(evidence))+' Edit your request or preferences to try a different requirement.'
        route_error_code='provider_quota_rejected' if 'quota' in route_errors else 'provider_local_admission' if 'application_limit' in route_errors else 'provider_service_error'
        if route_errors:
            message=MESSAGES[route_error_code]+' Available evidence and your original constraints are kept; incomplete timing remains unverified.'
        result=self.base(status='results' if options else 'no_results',message=message,options=options,questions=questions,
            code=route_error_code if route_errors else None if options else 'insufficient_routing')
        if options:
            from backend.venue_details import details_sessions
            ids=[v.placeId for option in options for v in option.stops]
            if self.details_token:details_sessions.extend(self.details_token,ids)
            else:self.details_token=details_sessions.create(ids,self.outing)
            result.detailsToken=self.details_token
            from backend.saved_advanced import issue_advanced
            key=repr(([(p.id,p.state,p.model_dump()['stops']) for p in options],self.durations,self.departure,self.budget_scope))
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
            return {'activeSessions':len(self.items),'lastStageMs':dict(latest.latencies) if latest else {},
                'timingVerdicts':dict(latest.timing_counts) if latest else {},
                'coverage':latest.resolver.coverage(latest.router,latest.seen) if latest and latest.resolver else {},
                'routeAssumptions':{'provider':'google_routes','drivingPolicy':'TRAFFIC_AWARE','departureTimeSent':False,
                    'originSource':latest.origin.source if latest and latest.origin else 'none',
                    'originPrecision':latest.origin.precision if latest and latest.origin else 'none',
                    'originAccuracyMeters':latest.origin.accuracy_m if latest and latest.origin else None,
                    'originAssociation':'confirmed_point','privateOriginLogged':False}}

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
        if not session or session.expires<=monotonic(): raise AdvancedAnswerError('advanced_session_expired','This outing session expired. Your text is kept; regenerate plans to continue.')
        if not session.lock.acquire(blocking=False): raise DiscoveryError('application_limit','This outing is already being processed.')
        try:return session.run(value)
        finally:session.lock.release()


sessions=Sessions()
