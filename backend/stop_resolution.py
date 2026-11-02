"""Task 50B: transient identity/discovery evidence, never routing or persistence.

Only callable deliberately by backend development/test consumers. No public route,
Qwen call, Details fan-out, provider cache on disk, or automatic planner integration.
"""
import os
import re
import secrets
from time import monotonic
from typing import Literal
from pydantic import Field, field_validator
from backend.journey import Journey, JourneyModel, RequestedStop
from backend.interpretation import InterpretationContext
from backend.models import ActivityType
from backend.places import DiscoveryError, DiscoveryRequest, PlacesDiscovery, SearchArea
from backend.provider_budget import ProviderLimitError
from backend.venue_models import VenueFacts
from backend.venue_geography import normalized
from backend.retail import MALL_TYPES, RETAIL_TYPES, intent, matches_brand, verdict


class ResolvedCandidate(JourneyModel):
    provider: Literal['google_places'] = 'google_places'
    place_id: str = Field(min_length=1, max_length=200)
    eligibility: Literal['identity_verified', 'activity_candidate']
    reason: str = Field(max_length=200)
    # Internal canonical facts; deliberately excluded from the safe choice DTO.
    facts: VenueFacts

    @field_validator('place_id')
    @classmethod
    def valid_id(cls, value):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', value):
            raise ValueError('Unsupported Google Place ID')
        return value

    @field_validator('facts')
    @classmethod
    def provider_facts(cls, facts, info):
        if (facts.provider != 'google_places' or facts.evidence != 'provider_supplied'
                or facts.id != info.data.get('place_id') or not facts.address or not facts.coordinates
                or not facts.providerTypes):
            raise ValueError('Incomplete provider identity evidence')
        return facts


class ResolvedStop(JourneyModel):
    occurrence: int = Field(strict=True, ge=0, le=32)
    requested: RequestedStop
    status: Literal['resolved', 'candidates', 'ambiguous', 'unresolved', 'provider_failure']
    candidates: list[ResolvedCandidate] = Field(default_factory=list, max_length=10)
    explanation: str = Field(default='', max_length=500)
    error_code: str | None = Field(default=None, max_length=80)


class ResolvedJourney(JourneyModel):
    journey: Journey
    area: SearchArea | None = None
    context: InterpretationContext | None = None
    stops: list[ResolvedStop] = Field(max_length=32)
    endpoint: ResolvedStop | None = None
    unresolved_constraints: list[str] = Field(default_factory=list, max_length=40)
    execution: Literal['unavailable'] = 'unavailable'
    diagnostics: dict[str, int] = Field(default_factory=dict)


def _label(text):
    text = re.sub(r'^(?:go to|visit|stop at|find|finish at|end at|return to)\s+(?:the\s+)?', '', text, flags=re.I)
    return text.strip()


def _words(text):
    # Address spelling variants only; no geographic or establishment aliases.
    text = normalized(text)
    return re.sub(r'\b(?:st|rd|ave|rte)\b', lambda m: {'st':'street','rd':'road','ave':'avenue','rte':'route'}[m[0]], text)


def _identity(source, venue, parents):
    phrase = _label(source)
    parts = re.split(r'\s+(?:at|inside|on|in)\s+', phrase, maxsplit=1, flags=re.I)
    base, qualifier = parts[0], parts[1] if len(parts)>1 else ''
    name = normalized(venue.name)
    types = set(venue.providerTypes or []) | ({venue.primaryType} if venue.primaryType else set())
    area_types = {'establishment', 'point_of_interest', 'street_address', 'premise', 'subpremise',
                  'locality', 'postal_code', 'neighborhood', 'route', 'country', 'sublocality'}
    if not {t for t in types - area_types if not t.startswith(('administrative_area_', 'sublocality_level_'))}:
        return False
    retail = intent(base)
    brand = retail.brands[0] if retail and len(retail.brands)==1 else base
    exact = name == normalized(base) or bool(types & RETAIL_TYPES and matches_brand(venue.name, brand))
    # Branch labels may be in the establishment name itself, e.g. Apple WTC.
    if qualifier:
        exact |= name in {normalized(base+' '+qualifier), normalized(re.sub(r'\bStore\b','',base,flags=re.I)+' '+qualifier)}
    if not exact:
        return False
    if re.search(r'\b(?:college|university)\b', base, re.I) and not types & {'university', 'school'}:
        return False
    if retail:
        accepted, _ = verdict(venue, retail)
        # For qualified branch labels check format/type against the base name.
        if not accepted:
            copy = venue.model_copy(update={'name': base})
            if not verdict(copy, retail)[0]: return False
    elif types & MALL_TYPES and not re.search(r'\b(?:mall|cent(?:er|re)|plaza)\b', base, re.I):
        return False
    if qualifier:
        parent = parents.get(normalized(qualifier))
        if parent is not None:
            # Independently verified parent + directed provider relation; never proximity.
            if not any(p.id == parent.id for p in venue.containingPlaces or []): return False
        else:
            qualifier_words = set(_words(qualifier).split())
            name_words = set(_words(venue.name).split())
            location_words = set(_words(venue.name+' '+venue.address).split())
            retail_parent = bool(re.search(r'\s+(?:at|inside)\s+',phrase,re.I) and types & RETAIL_TYPES)
            if not qualifier_words <= location_words or retail_parent and not qualifier_words <= name_words:
                return False
    return True


class StopResolver:
    """One active backend-owned context. Choices expire and never authorize I/O.

    A future API must keep this object server-side and treat its opaque token as
    private. A client-supplied resolved object/Place ID is never an authority.
    """
    def __init__(self, outing):
        if os.environ.get('WHERETO_STOP_RESOLUTION_DEV') != '1':
            raise DiscoveryError('disabled', 'Advanced stop resolution is disabled.')
        self.discovery = PlacesDiscovery(outing)
        self.outing = outing
        self._cache = {}
        self._result = None
        self._started = False
        self._excluded_regions = []
        self._token = secrets.token_urlsafe(32)
        self._expires = monotonic()+600

    def _named(self, query, area):
        key = ('named', query, area.model_dump_json())
        if key not in self._cache:
            try:
                self._cache[key] = self.discovery.resolve_named(query, area)
            except (DiscoveryError, ProviderLimitError) as error:
                self._cache[key] = error
        value = self._cache[key]
        if isinstance(value, Exception): raise value
        return value

    def _resolve_stop(self, index, stop, area):
        candidates = []
        if area is None:
            # A named phrase can establish its own geography; do not invent an origin.
            area = SearchArea(name='Explicit named destination', enforce_name=False, excluded_regions=self._excluded_regions)
            if stop.kind != 'named_place':
                return ResolvedStop(occurrence=index, requested=stop, status='unresolved', explanation='A search area or verified stop is needed for discovery.')
        try:
            if stop.kind == 'named_place':
                phrase = _label(stop.source)
                parents = {}
                parts = re.split(r'\s+(?:at|inside)\s+', phrase, maxsplit=1, flags=re.I)
                if len(parts)>1:
                    matches = [v for v in self._named(parts[1], area)
                               if normalized(v.name)==normalized(parts[1]) and set(v.providerTypes or []) & MALL_TYPES]
                    if len({v.id for v in matches})==1: parents[normalized(parts[1])] = matches[0]
                    # A named mall must be verified, not inferred from an address.
                    if re.search(r'\bmall\b',parts[1],re.I) and not parents:
                        return ResolvedStop(occurrence=index,requested=stop,status='unresolved',explanation='The specified containing mall could not be verified.')
                venues = [v for v in self._named(phrase, area) if _identity(stop.source,v,parents)]
                eligibility, reason = 'identity_verified', 'Exact name, type and explicit qualifiers supported by provider evidence.'
            else:
                from backend.interpretation import activity_category
                source = re.sub(r'^(?:go to|find)\s+(?:the\s+)?(?:nearest\s+)?','',stop.source,flags=re.I)
                source = re.sub(r'^(?:the\s+)?nearest\s+','',source,flags=re.I)
                activity = activity_category(source + (' store' if stop.kind=='brand' and not intent(source) else ''))
                if activity is None: raise DiscoveryError('invalid_request','The activity needs clarification.')
                key = ('activity',activity,area.model_dump_json())
                if key not in self._cache:
                    self._cache[key] = self.discovery.discover(DiscoveryRequest(activity=activity,destination=area)).venues
                venues = [v.facts for v in self._cache[key]]
                eligibility, reason = 'activity_candidate', 'Existing discovery relevance and geography checks; availability and nearest route unverified.'
            seen = {}
            for venue in venues:
                try:
                    c = ResolvedCandidate(place_id=venue.id, eligibility=eligibility,reason=reason,facts=venue)
                    # Conflicting observations for one ID cannot establish identity.
                    if c.place_id in seen and seen[c.place_id].facts.model_dump(exclude={'observedAt'}) != venue.model_dump(exclude={'observedAt'}):
                        raise DiscoveryError('invalid_response','Conflicting venue identity evidence.')
                    seen[c.place_id] = c
                except ValueError:
                    continue
            candidates = list(seen.values())[:10]
            status = ('ambiguous' if len(candidates)>1 else 'resolved') if stop.kind=='named_place' and candidates else 'candidates' if candidates else 'unresolved'
            return ResolvedStop(occurrence=index, requested=stop,status=status,candidates=candidates,
                explanation='Which destination did you mean? Choose its name and location.' if status=='ambiguous' else '' if candidates else 'No eligible place identity could be verified. Your stop is kept.')
        except (DiscoveryError,ProviderLimitError) as error:
            from backend.provider_errors import attach_accounting
            attach_accounting(error,self.outing)
            return ResolvedStop(occurrence=index,requested=stop,status='provider_failure',explanation=str(error),error_code=getattr(error,'code','application_limit'))

    def resolve(self, journey, area=None, *, context=None):
        if self._started: raise ValueError('Use the active context; do not repeat resolution.')
        self._started = True
        journey = Journey.model_validate(journey.model_dump())
        area = SearchArea.model_validate(area.model_dump()) if area else None
        context = InterpretationContext.model_validate(context.model_dump()) if context else None
        if context and context.geography:
            policy=context.geography
            self._excluded_regions=policy.excludedRegions
            if policy.strictDestination and (area is None or not area.name):
                raise ValueError('A hard destination restriction needs an explicit named area.')
            if area:
                area=area.model_copy(update={'enforce_name':policy.strictDestination or area.enforce_name,
                    'excluded_regions':list(set(area.excluded_regions+policy.excludedRegions))})
        stops = []
        for i,stop in enumerate(journey.stops):
            discovery_area = area
            # With no explicit area, a uniquely verified mandatory place can bias
            # following discovery. This never establishes an origin or route.
            if discovery_area is None and stop.kind!='named_place':
                anchor=next((s.candidates[0].facts.coordinates for s in reversed(stops) if s.status=='resolved'),None)
                if anchor: discovery_area=SearchArea(coordinates=anchor,excluded_regions=self._excluded_regions)
            stops.append(self._resolve_stop(i,stop,discovery_area))
        endpoint = None
        if journey.endpoint and journey.endpoint.kind not in ('origin','home'):
            endpoint=self._resolve_stop(len(stops),RequestedStop(source=journey.endpoint.source,kind=journey.endpoint.kind),area)
        constraints = []
        if journey.endpoint and journey.endpoint.kind=='home':
            if context and context.endpointStatus=='origin_confirmed':
                constraints.append('Explicit return to the starting point requires Task 50C routing.')
            elif context and context.endpointStatus=='location_needs_verification':
                constraints.append('The supplied endpoint location still needs place verification.')
            else:
                constraints.append('Home endpoint needs an explicit location or return-to-start confirmation.')
        if journey.endpoint and journey.endpoint.kind=='origin': constraints.append('Return to the confirmed origin requires Task 50C routing.')
        if journey.shared_place:
            groups = [stops[i] for i in journey.shared_place.stops]
            from backend.retail import MALL_TYPES
            # Validate containment parents through existing mall discovery once.
            malls = self._resolve_stop(32,RequestedStop(source='shopping'),area)
            ids={c.place_id for c in malls.candidates if set(c.facts.providerTypes or []) & MALL_TYPES}
            for group in groups:
                group.candidates=[c for c in group.candidates if any(p.id in ids for p in c.facts.containingPlaces or [])]
                if not group.candidates: group.status='unresolved'
            shared = set.intersection(*[{p.id for c in g.candidates for p in c.facts.containingPlaces or [] if p.id in ids} for g in groups])
            if not shared: constraints.append('No shared mall containment could be verified for all requested stores.')
            else:
                for group in groups:
                    group.candidates=[c for c in group.candidates if any(p.id in shared for p in c.facts.containingPlaces or [])]
        self._result = ResolvedJourney(journey=journey,area=area,context=context,stops=stops,endpoint=endpoint,
            unresolved_constraints=constraints,diagnostics={k:self.outing.usage()[k] for k in ('placesSearchRequests','placesDetailsRequests','reservedMatrixElements','providerAttempts')})
        return self._result.model_copy(deep=True)

    def choices(self):
        if self._result is None or monotonic()>self._expires: raise ValueError('Resolution context expired.')
        return {'context':self._token,'questions':[{'occurrence':s.occurrence,'question':s.explanation,
            'choices':[{'placeId':c.place_id,'name':c.facts.name,'address':c.facts.address,
                        'attributions':[a.model_dump(mode='json') for a in c.facts.attributions or []]} for c in s.candidates]}
            for s in self._result.stops+([self._result.endpoint] if self._result.endpoint else []) if s.status=='ambiguous']}

    def choose(self, context, occurrence, place_id):
        if (not isinstance(context,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',context)
                or type(occurrence) is not int or not isinstance(place_id,str)
                or self._result is None or monotonic()>self._expires or not secrets.compare_digest(context,self._token)):
            raise ValueError('Resolution context expired or invalid.')
        groups=self._result.stops+([self._result.endpoint] if self._result.endpoint else [])
        stop=next((s for s in groups if s.occurrence==occurrence and s.status=='ambiguous'),None)
        candidate=next((c for c in stop.candidates if c.place_id==place_id),None) if stop else None
        if candidate is None: raise ValueError('Choose a candidate from this unresolved stop.')
        stop.candidates=[candidate];stop.status='resolved';stop.explanation='Explicitly selected from verified candidates.'
        return self._result.model_copy(deep=True)
