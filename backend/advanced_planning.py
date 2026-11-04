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
from backend.advanced_routing import AdvancedRouter, MAX_ELEMENTS
from backend.advanced_timing import evaluate_advanced_timing
from backend.saved_plans import Token
from backend.display_duration import seconds_text
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
    proceedClosed: Token | None = Field(default=None,repr=False)
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
    closedVisitException: bool = False
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
    closureOffers: list[dict] = Field(default_factory=list,repr=False)
    questions: list[dict] = Field(default_factory=list)
    options: list[PublicOption] = Field(default_factory=list, max_length=3)
    saveReceipt: str | None = Field(default=None, repr=False)
    saveAccessToken: str | None = Field(default=None, repr=False)
    code: str | None = None
    preferences: dict = Field(default_factory=dict)
    detailsToken: str | None = Field(default=None,repr=False)
    bounded: Literal[True] = True
    exploration: dict = Field(default_factory=dict)
    canExpand: bool = False
    canDiscover: bool = False
    canShowBeyond: bool = False


def directions_link(origin, destination, mode):
    if not origin and not destination: return None
    from urllib.parse import urlencode
    return 'https://www.google.com/maps/dir/?'+urlencode({'api':'1',**({'origin':'Place','origin_place_id':origin} if origin else {}),**({'destination':'Place','destination_place_id':destination} if destination else {}),'travelmode':'walking' if mode=='walk' else 'driving'})


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
        self.closure_offers = {}
        self.closure_overrides = {}
        self.selection_counts = {}
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
        self.initial_fill_done = False
        self.initial_fill_elements = 0
        self.date_answer = context.dateOverride
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
        return {'closedVisits':[{'occurrence':n,'requested':redact_source(self.journey.stops[n].source,self.context)} for n in self.closure_overrides], 'stops':stops,'budget':{**self.journey.total_duration.model_dump(mode='json'),'source':redact_source(self.journey.total_duration.source,self.context)} if self.journey.total_duration else None,
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
        if any(n>=len(self.journey.stops) for n in edits.removeClosure):raise AdvancedAnswerError('advanced_answer_invalid','Choose an existing visit permission to remove.')
        for n in edits.removeClosure:self.closure_overrides.pop(n,None)
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
                    return self.base(status='unsupported',code='advanced_evidence_expired',message='These travel estimates have expired. Regenerate plans to check current routes with your saved preferences.',exploration={'combination':'evidence_expired','discovery':'regenerate_required','message':'Travel estimates expired. Viewed pages are kept; regenerate to check current routes.'})
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
            if calendar.date!=self.context.date:
                self.closure_overrides.clear();self.closure_offers.clear()
                self.seen.clear();self.current_ids.clear()
                if self.resolver and self.resolver._result:self.resolver._result.context.date=calendar.date
                if self.router:
                    self.reusable_routes=dict(self.router._evidence)
                    self.router=None;self.route_attempted=False;self.candidates={}
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
        from backend.journey import ambiguous_return, unresolved_return_clause
        if unresolved_return_clause(self.text) and ambiguous_return(self.journey.endpoint) and self.context.endpointStatus != 'origin_confirmed':
            return self.base(status='unsupported',message='Confirm where you want to return before generating this outing.')
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
            if value.action=='discover':self.resolver.expand(prefer_optional=any(s.requirement=='optional' for s in self.journey.stops))
            unoffered=[c for key,c in self.candidates.items() if key not in self.seen and key in self.offerable[self.beyond]]
            optional_opportunity=any(s.requirement=='optional' for s in self.journey.stops) and not any(any(v.requested.requirement=='optional' for v in c.visits) for c in unoffered)
            if value.action=='discover' or len(unoffered)<3 or optional_opportunity:
                self.router.advance(origin=self.origin,allow_beyond_limit=True)
                self.candidates.update((self.route_id(c),c) for c in self.router.all_candidates)
        self.router.use_candidates(list(self.candidates.values())[:256])
        zero=next((n for n,stop in enumerate(self.journey.stops) if (d:=self.durations.get(n,stop.duration)) is not None and d.minutes==0 and (self.budget_scope!='travel' or n not in self.explicit_overrides or self.journey.deadline is not None)),None)
        if zero is not None:
            return self.base(status='clarification',message='Zero is not a realistic visit duration. Supply positive visit time, or explicitly confirm zero counted time under a travel-only budget.',questions=[{'field':'dwell','occurrence':zero,'question':'How should time at this stop be counted?'}])
        if not self.initial_fill_done:
            self.initial_fill_done=True
            # One local probe, at most one additional selective stage; no search,
            # retries, extra initial element ceiling or recursive exploration.
            initial_started=perf_counter()
            probe=evaluate_advanced_timing(self.router,evaluated_at=datetime.now(timezone.utc),dwell_answers=self.durations,departure_minute=self.departure,budget_scope=self.budget_scope,allow_overrides=True)
            supported=[c for c in probe.candidates if c.state!='infeasible' and c.route.route_status!='beyond_limit']
            remaining=MAX_ELEMENTS-self.router._result.matrix_elements
            errors=any(l.evidence.error_code for c in probe.candidates for l in c.route.legs)
            if 0<len(supported)<3 and self.router.pending_paths and remaining>0 and not errors:
                extra=self.router.advance(origin=self.origin,allow_beyond_limit=True,element_allowance=remaining)
                self.initial_fill_elements=extra.matrix_elements
                self.candidates.update((self.route_id(c),c) for c in self.router.all_candidates)
                self.router.use_candidates(list(self.candidates.values())[:256])
            self.latencies['initialFillMs']=(perf_counter()-initial_started)*1000
        started=perf_counter()
        timing=evaluate_advanced_timing(self.router,evaluated_at=datetime.now(timezone.utc),dwell_answers=self.durations,departure_minute=self.departure,budget_scope=self.budget_scope,allow_overrides=True)
        # Offer authority is opaque, server-owned and bound to the exact verified
        # occurrence, identity, schedule, hours observation and routing assumptions.
        previous_offers=self.closure_offers
        self.closure_offers={}
        matches=set()
        def closure_key(c,v):
            facts=next(x.selected.facts for x in c.route.visits if x.occurrence==v.occurrence)
            return sha256(repr((str(self.context.date),self.context.timezone,self.departure,
                self.context.departureMinute,self.context.departureNow,self.configuration,
                self.context.transport,v.dwell_constraint,v.arrival.offsets,v.departure.offsets,
                facts.currentOpeningHours,facts.observedAt.get('currentOpeningHours.periods'))).encode()).hexdigest()
        for c in timing.candidates:
            for v,visit in zip(c.visits,c.route.visits):
                if v.hours_state!='infeasible' or visit.requested.kind!='named_place' or visit.requested.requirement!='required':continue
                binding=(v.occurrence,v.place_id,closure_key(c,v))
                if self.closure_overrides.get(v.occurrence)==binding:
                    matches.add((c.candidate_index,v.occurrence,v.place_id))
                else:
                    token=next((k for k,b in previous_offers.items() if b==binding),None) or secrets.token_urlsafe(32)
                    self.closure_offers[token]=binding
        if value.proceedClosed:
            binding=previous_offers.get(value.proceedClosed)
            if binding is None or binding not in self.closure_offers.values():
                raise AdvancedAnswerError('advanced_answer_invalid','This closed-visit choice has expired or changed. Review the current visit before proceeding.')
            self.closure_overrides[binding[0]]=binding
            return self.run(value.model_copy(update={'proceedClosed':None,'edits':None,'dwell':None,'departure':None,'action':None}))
        active={n for _,n,_ in matches}
        self.closure_overrides={n:b for n,b in self.closure_overrides.items() if n in active}
        if matches:
            timing=evaluate_advanced_timing(self.router,evaluated_at=datetime.now(timezone.utc),dwell_answers=self.durations,departure_minute=self.departure,budget_scope=self.budget_scope,allow_overrides=True,hours_exceptions=matches)
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
        pool=sorted((c for c in available if self.route_id(c.route) in self.current_ids or self.route_id(c.route) not in self.seen),key=lambda c:(c.state!='feasible',c.route.route_status=='beyond_limit',sum(t.state=='outside_preference' for t in c.route.checks),-sum(v.requested.requirement=='optional' for v in c.route.visits),c.route.known_travel_seconds))
        eligible=[]
        while pool and len(eligible)<3:
            best=pool[0]
            def category(c):return (c.state,c.route.route_status,sum(t.state=='outside_preference' for t in c.route.checks),sum(v.requested.requirement=='optional' for v in c.route.visits))
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
        def omission_explanation(omission):
            checked=[c for c in timing.candidates if any(v.occurrence==omission.occurrence for v in c.route.visits)]
            if any(permitted(c,self.beyond) for c in checked):
                return 'Other checked alternatives include this optional stop; it is left out of this option.'
            if checked and all(c.duration_state=='infeasible' for c in checked):
                limit=self.journey.total_duration
                unavoidable=sum(d.minutes for n,s in enumerate(self.journey.stops)
                    if (s.requirement=='required' or n==omission.occurrence)
                    and (d:=self.durations.get(n,s.duration)) is not None and d.relation in ('exact','minimum'))
                if self.budget_scope=='outing' and limit and (unavoidable>limit.minutes and limit.relation in ('maximum','under','exact') or unavoidable==limit.minutes and limit.relation=='under'):
                    return 'The supplied visit times alone exceed the original time budget for the whole outing.'
                return 'Including this stop exceeds the original time budget in the routes checked so far. Other combinations or nearby places may still fit.'
            if checked and all(c.deadline_state=='infeasible' for c in checked):
                return 'Including this stop misses the finish deadline in the routes checked so far. Coverage is limited.'
            if omission.reason=='known_closed':return 'The checked venues are closed on the requested date.'
            return 'No eligible route including this stop is established in the checked pool. Other venues may exist.'
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
                    closedVisitException=t.hours_exception,hoursState=t.hours_state,hours=venue_hours(facts,self.context.date,calendar_timezone=self.context.timezone),
                    rating=facts.rating,ratingCount=facts.ratingCount,credits=[a.model_dump(mode='json') for a in facts.attributions or []]))
            identity=sha256(repr(([(v.occurrence,v.selected.place_id) for v in route.visits],route.ending,route.endpoint.place_id if route.endpoint else None)).encode()).hexdigest()[:32]
            options.append(PublicOption(id='advanced_'+identity,originApproximate=bool(self.origin and (self.origin.source=='suggested' or self.origin.accuracy_m and self.origin.accuracy_m>100 or self.origin.precision not in ('device','address_or_place'))),state='unverified' if route.route_status=='beyond_limit' else c.state,travelException=route.route_status=='beyond_limit',travelDeviations=[f"{'First stop' if route.legs[t.leg_index].role=='origin_to_first' else 'Between stops'}: {seconds_text(t.actual*60) if t.preference.unit=='minutes' else f'{t.actual:g} miles'}; preferred {t.preferred:g}; original maximum {t.maximum:g}." for t in route.checks if t.state in ('outside_preference','beyond_limit')],routeState=route.route_status,stops=stops,ending=route.ending,
                endpoint={'placeId':route.endpoint.place_id,'name':route.endpoint.facts.name,'mapsUrl':maps_link(route.endpoint.place_id),
                    'credits':[a.model_dump(mode='json') for a in route.endpoint.facts.attributions or []]} if route.endpoint else None,
                legs=[PublicLeg(role=l.role,fromOccurrence=l.from_occurrence,toOccurrence=l.to_occurrence,seconds=l.evidence.duration_seconds,
                    meters=l.evidence.distance_meters,status=l.evidence.status,mode=l.evidence.mode,mapsUrl=directions_link(l.evidence.origin_id if l.role!='origin_to_first' else None,l.evidence.destination_id if l.role!='return_to_origin' else None,l.evidence.mode) if l.evidence.status!='same_location' else None) for l in route.legs],
                knownTravelSeconds=float(c.known_travel_seconds),elapsedLowerSeconds=float(c.elapsed.lower),
                elapsedUpperSeconds=float(c.elapsed.upper) if c.elapsed.upper is not None else None,upperExclusive=c.elapsed.upper_exclusive,
                budgetScope=self.budget_scope,totalConstraint=route.journey.total_duration.model_copy(update={'source':redact_source(route.journey.total_duration.source,self.context)}) if route.journey.total_duration else None,deadlineSource=redact_source(route.journey.deadline.source,self.context) if route.journey.deadline else None,durationState=c.duration_state,deadlineState=c.deadline_state,reasons=list(dict.fromkeys(r.message for r in c.reasons if r.state!='feasible')),
                omitted=[{'occurrence':o.occurrence,'requested':redact_source(o.requested.source,self.context),'reason':o.reason,'explanation':omission_explanation(o)} for o in route.omitted]))
            if route.journey.total_duration and self.budget_scope=='outing' or route.journey.deadline or self.context.departureNow and c.hours_state=='unverified' and any(v.selected.facts.currentOpeningHours is not None for v in route.visits):
                for v in route.visits:
                    if v.requested.duration is None:
                        q={'field':'dwell','occurrence':v.occurrence,'question':f'How long will you spend on {redact_source(v.requested.source,self.context)}?'}
                        if q not in questions: questions.append(q)
            if route.journey.deadline and c.start is None and self.context.departureMinute is None and self.departure is None:
                q={'field':'departure','question':'What time will you depart, in the destination timezone?'}
                if q not in questions: questions.append(q)
        for c in available:
            if (c.route.journey.total_duration and self.budget_scope=='outing') or c.route.journey.deadline:
                for v in c.route.visits:
                    if v.requested.requirement=='optional' and v.requested.duration is None:
                        q={'field':'dwell','occurrence':v.occurrence,'question':f'How long will you spend on optional {redact_source(v.requested.source,self.context)}? This is needed to check whether it fits; it has not been assumed to take zero time.'}
                        if q not in questions and not any(x.get('field')=='dwell' and x.get('occurrence')==v.occurrence for x in questions):questions.append(q)
        self.selection_counts={'initialFillElements':self.initial_fill_elements,'checked':len(timing.candidates),'eligible':len(available),
            'optionalInclusive':sum(any(v.requested.requirement=='optional' for v in c.route.visits) for c in timing.candidates),
            'selectedOptionalInclusive':sum(any(v.requested.requirement=='optional' for v in c.route.visits) for c in eligible),
            'exclusions':{code:sum(any(r.code==code and r.state=='infeasible' for r in c.reasons) for c in timing.candidates) for code in {r.code for c in timing.candidates for r in c.reasons if r.state=='infeasible'}}}
        message='Here are the options checked for your outing. Add any missing visit times to check the whole trip.' if options else ' '.join(timing.routing_reasons) or 'All checked options are infeasible: '+' '.join(dict.fromkeys(r.message for c in timing.candidates for r in c.reasons if r.state=='infeasible'))
        if not options and timing.candidates:
            evidence=[]
            for c in timing.candidates:
                if c.duration_state=='infeasible' and c.route.journey.total_duration:
                    d=c.route.journey.total_duration
                    measured=c.travel if self.budget_scope=='travel' else c.elapsed
                    lower=seconds_text(measured.lower,'lower')
                    upper=seconds_text(measured.upper,'upper') if measured.upper is not None else None
                    span=f'{lower} or more' if upper is None else f'{lower} to {upper}'
                    evidence.append(f"{'Travel-only' if self.budget_scope=='travel' else 'Whole-trip'} requirement: {d.relation} {d.minutes} minutes. Supported journey duration: {span}.")
            if evidence:message='No checked option meets your requirements. '+' '.join(dict.fromkeys(evidence))+' Edit your request or preferences to try a different requirement.'
        closure_offers=[]
        for token,(n,place_id,_) in self.closure_offers.items():
            visit=next(v for c in timing.candidates for v in c.route.visits if v.occurrence==n and v.selected.place_id==place_id)
            if not any(o['occurrence']==n for o in closure_offers):
                closure_offers.append({'token':token,'occurrence':n,'name':visit.selected.facts.name,
                    'message':f'{visit.selected.facts.name} is expected to be closed at the planned visit time. You may keep this destination for an outside visit; access and services are not confirmed.'})
        if not options and closure_offers:message=' '.join(o['message'] for o in closure_offers)
        route_error_code='provider_quota_rejected' if 'quota' in route_errors else 'provider_local_admission' if 'application_limit' in route_errors else 'provider_service_error'
        if route_errors:
            message=MESSAGES[route_error_code]+' Available evidence and your original constraints are kept; incomplete timing remains unverified.'
        result=self.base(status='results' if options else 'no_results',message=message,options=options,questions=questions,
            closureOffers=closure_offers,code=route_error_code if route_errors else None if options else 'insufficient_routing')
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
        optional=[]
        for n,stop in enumerate(self.journey.stops):
            if stop.requirement!='optional':continue
            checked=[c for c in timing.candidates if any(v.occurrence==n for v in c.route.visits)]
            valid=[c for c in checked if permitted(c,self.beyond)]
            group=snapshot.stops[n]
            closed={x.candidate.place_id for x in self.router._result.hours_exclusions if x.occurrence==n}
            state=('known_closed' if group.candidates and {x.place_id for x in group.candidates}<=closed else 'not_discovered' if not group.candidates else 'not_routed' if not checked else
                   'needs_duration' if valid and any(v.occurrence==n and v.requested.duration is None for c in valid for v in c.route.visits) and self.budget_scope=='outing' and self.journey.total_duration else
                   'offered' if any(any(v.occurrence==n for v in c.route.visits) for c in eligible) else
                   'eligible_not_shown' if valid else 'checked_infeasible' if all(c.state=='infeasible' for c in checked) else 'unverified')
            optional.append({'occurrence':n,'state':state,'timing':'unverified' if any(c.state=='unverified' for c in valid) else 'feasible' if valid else 'infeasible' if checked and all(c.state=='infeasible' for c in checked) else 'unknown','reasons':sorted({r.code for c in checked for r in c.reasons if r.state!='feasible'})})
        combination=('provider_quota' if 'quota' in route_errors else 'local_admission' if 'application_limit' in route_errors else
                     'session_bound' if self.actions>=32 or len(self.router.checked)>=256 else
                     'eligible_not_shown' if any(self.route_id(c.route) not in self.seen for c in available) else
                     'provider_service' if route_errors else 'unchecked_combinations' if self.router.pending_paths else 'checked_pool_exhausted')
        discovery='available' if result.canDiscover else 'provider_quota' if 'quota' in route_errors else 'session_bound' if self.actions>=32 or len(self.router.checked)>=256 else self.resolver.discovery_state()
        note=('Only the checked routes have been evaluated. Further combinations and nearby searches keep your original limits.' if any(o['state'] in ('checked_infeasible','not_routed','not_discovered') for o in optional) and (result.canExpand or result.canDiscover) else
              'No further eligible options in this finite session. Viewed pages remain available; other venues may exist.' if not result.canExpand and not result.canDiscover else '')
        result.exploration={'combination':combination,'discovery':discovery,'optional':optional,'message':note}
        self.selection_counts.update(unseenEligible=sum(self.route_id(c.route) not in self.seen for c in available),offered=len(self.seen),continuation=combination,discovery=discovery)
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
                'selection':dict(latest.selection_counts) if latest else {},
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
