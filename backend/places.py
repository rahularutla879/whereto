"""Bounded Text Search discovery for isolated diagnostics and local real planning."""

from datetime import datetime,timezone
from hashlib import sha256
import json
import os
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError, field_validator, model_validator

from backend.models import ActivityType
from backend.provider_budget import OutingBudget
from backend.venue_models import Coordinates
from backend.venue_geography import distance_m, geographic_reason
from backend.venue_normalization import normalize_discovery_candidates
from backend.venue_quality import DistinctVenue, assess_candidates

PROJECT = "where-to-512422"
SERVICE_ACCOUNT = f"whereto-local-maps@{PROJECT}.iam.gserviceaccount.com"
ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
# ID/attributions: IDs Only. Other fields: Text Search Pro (not Details tiers).
FIELD_MASK = "places.id,places.displayName,places.formattedAddress,places.location,places.addressComponents,places.attributions,places.types,places.primaryType,nextPageToken"
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]


class DiscoveryError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


class DiscoveryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SearchArea(DiscoveryModel):
    anchor_verified: bool = False
    enforce_name: bool = True
    include_name: bool = False
    restrict_to_area: bool = False
    boundary_coordinates: Coordinates | None = Field(default=None, repr=False)
    boundary_radius_m: Annotated[Number, Field(gt=0, le=2000000)] | None = None
    excluded_regions: list[Literal["VA", "MD", "DC"]] = Field(default_factory=list, max_length=3)
    name: Text | None = None
    coordinates: Coordinates | None = Field(default=None, repr=False)
    radius_m: Annotated[Number, Field(gt=0, le=2000000)] | None = None

    @model_validator(mode="after")
    def valid_area(self):
        if self.radius_m is not None and self.radius_m>50000 and not self.restrict_to_area:
            raise ValueError("Google circle bias supports at most 50 km; larger spatial searches require a rectangle.")
        if self.restrict_to_area and (self.coordinates is None or self.radius_m is None):
            raise ValueError("A provider search restriction requires a center and radius.")
        if (self.boundary_coordinates is None) != (self.boundary_radius_m is None):
            raise ValueError("A fixed search boundary requires both center and radius.")
        if not self.name and self.coordinates is None:
            raise ValueError("Specify a destination or coordinates.")
        if self.radius_m is not None and self.coordinates is None:
            raise ValueError("A radius requires an explicitly supplied coordinate center.")
        return self


class StartingLocation(DiscoveryModel):
    address: Text | None = None
    coordinates: Coordinates | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def valid_start(self):
        if self.address is None and self.coordinates is None:
            raise ValueError("Supply a starting address or coordinates, or omit starting_location.")
        return self


class TravelConstraints(DiscoveryModel):
    # Interface only; these limits are NOT evaluated by venue discovery.
    max_first_leg_minutes: Annotated[int, Field(strict=True, ge=0, le=1440)] | None = None
    max_between_activities_minutes: Annotated[int, Field(strict=True, ge=0, le=1440)] | None = None
    preference: Text | None = None


class DiscoveryRequest(DiscoveryModel):
    activity: ActivityType
    meal: Literal["dinner"] | None = None
    search_variant: Literal["initial", "alternative", "mixed"] = "initial"
    page_token: str | None = Field(default=None, min_length=1, max_length=4096, repr=False)
    destination: SearchArea | None = None
    current_location: SearchArea | None = Field(default=None, repr=False)
    starting_location: StartingLocation | None = Field(default=None, repr=False)
    travel_constraints: TravelConstraints | None = None

    @model_validator(mode="after")
    def location_required(self):
        if self.meal is not None and self.activity != ActivityType.food:
            raise ValueError("Meal context requires a food activity.")
        if self.destination is None and self.current_location is None:
            raise ValueError("Specify a destination or optionally share current-location coordinates.")
        if self.current_location is not None and (
                self.current_location.coordinates is None or self.current_location.name is not None):
            raise ValueError("Current location must contain coordinates, not an inferred city.")
        return self

    @property
    def area(self) -> SearchArea:
        # An outing destination always overrides the user's present location.
        return self.destination if self.destination is not None else self.current_location


QUERIES = {
    "food": "restaurants", "drinks": "bars", "movie": "movie theaters",
    "coffee": "cafes", "bowling": "bowling alleys", "arcade": "video arcades",
    "museum": "museums", "art": "art galleries", "outdoors": "parks",
    "karaoke": "karaoke venues", "escape": "escape rooms", "miniGolf": "miniature golf",
    "shopping": "shopping malls", "zoo": "zoos", "hiking": "hiking trails",
    "picnic": "picnic parks", "skating": "skating rinks",
    "baseball": "baseball stadiums", "basketball": "basketball arenas",
    "football": "football stadiums", "soccer": "soccer stadiums", "hockey": "ice hockey arenas",
    "sports": "sports stadiums", "concert": "concert venues", "theater": "performing arts theaters",
    "musical": "musical theater venues", "ballet": "ballet theaters",
    "opera": "opera houses", "comedy": "comedy clubs",
}


def search_body(request: DiscoveryRequest, limit: int) -> dict:
    area = request.area
    query = "dinner restaurants" if request.meal == "dinner" else QUERIES.get(request.activity.value, request.activity.value.removeprefix("custom:"))
    from backend.retail import query as retail_query
    retail=retail_query(request.activity.value,request.search_variant)
    if retail:query=retail
    if request.search_variant == "mixed":
        query = "entertainment centers with bowling" if request.activity == ActivityType.bowling else query + " places"
    if request.search_variant == "alternative":
        query = "bowling centers" if request.activity == ActivityType.bowling else "restaurants serving dinner" if request.meal == "dinner" else query + " venues"
    body = {"textQuery": f"{query} in {area.name}" if area.name and (area.coordinates is None or area.enforce_name or area.include_name) else query,
            "pageSize": limit, "languageCode": "en"}
    if request.activity == ActivityType.bowling and request.search_variant == "initial":
        # Text alone can return other entertainment businesses. Bowling has a
        # specific supported type; do not treat a broad arcade as a bowling stop.
        body.update(includedType="bowling_alley", strictTypeFiltering=True)
    if area.coordinates is not None:
        # Zero is Google's point-bias mode, NOT an invented user search radius.
        body["locationBias"] = {"circle": {"center": area.coordinates.model_dump(),
                                            "radius": area.radius_m if area.radius_m is not None else 0.0}}
    else:
        # Explicit nonlocal bias prevents Google's default server-IP bias. Google
        # ignores this bias when textQuery names a destination. Its method
        # reference limits rectangles to 180 degrees, even though the generic
        # viewport guide describes whole-world boxes. This is NOT a restriction
        # or the user's location; returned address components verify the area.
        body["locationBias"] = {"rectangle": {
            "low": {"latitude": -90.0, "longitude": -90.0},
            "high": {"latitude": 90.0, "longitude": 90.0}}}
    if area.restrict_to_area:
        from math import asin, cos, degrees, radians, sin
        angle=area.radius_m/6371008.8
        latitude=radians(area.coordinates.latitude)
        low=max(-90,area.coordinates.latitude-degrees(angle));high=min(90,area.coordinates.latitude+degrees(angle))
        if low==-90 or high==90:
            west,east=-180,180
        else:
            delta=degrees(asin(min(1,sin(angle)/cos(latitude))))
            west=(area.coordinates.longitude-delta+180)%360-180
            east=(area.coordinates.longitude+delta+180)%360-180
        body.pop('locationBias',None)
        body['locationRestriction']={'rectangle':{'low':{'latitude':low,'longitude':west},'high':{'latitude':high,'longitude':east}}}
    return body


class DiscoveryCandidate(DiscoveryModel):
    provider: Literal["google_places"] = "google_places"
    provider_id: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    display_name: Text
    address: Annotated[str, StringConstraints(min_length=1, max_length=1000)]
    coordinates: Coordinates
    attributions: list[dict] = Field(default_factory=list)
    types: list[str] | None = None
    currentOpeningHours: dict | None = None
    regularOpeningHours: dict | None = None
    timeZone: dict | None = None
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    containingPlaces: list[dict] | None = None
    primaryType: str | None = None
    rating: float | None = Field(default=None, ge=1, le=5, strict=True, allow_inf_nan=False)
    userRatingCount: int | None = Field(default=None, ge=0, strict=True)

    @field_validator("provider_id")
    @classmethod
    def original_identity(cls, value):
        if value.strip() != value:
            raise ValueError("Invalid original provider identity")
        return value


class DiscoveryResult(DiscoveryModel):
    provider: Literal["google_places"] = "google_places"
    candidates: list[DiscoveryCandidate]
    excluded_count: int = 0
    venues: list[DistinctVenue] = Field(default_factory=list, exclude=True, repr=False)
    diagnostics: dict[str, int] = Field(default_factory=dict, exclude=True, repr=False)
    stages: dict = Field(default_factory=dict, exclude=True, repr=False)
    audit: dict = Field(default_factory=dict, exclude=True, repr=False)
    observed: dict[str,set[str]] = Field(default_factory=dict, exclude=True, repr=False)
    paging: dict = Field(default_factory=dict, exclude=True, repr=False)
    notice: str = ("Discovery candidates only. Hours, prices, availability and travel are unknown. "
                   "Area names are checked conservatively against provider address components; "
                   "unverifiable matches are excluded. Without a radius, coordinates are a bias only. "
                   "Clear activity mismatches are excluded; uncertain matches remain candidates, "
                   "not confirmed activities or scheduled events.")


def parse_response(data: dict, area: SearchArea, limit: int) -> DiscoveryResult:
    if not isinstance(data, dict) or not isinstance(data.get("places", []), list):
        raise DiscoveryError("invalid_response", "Google returned an invalid discovery response.")
    token = data.get("nextPageToken")
    if token is not None and (not isinstance(token, str) or not token.strip() or len(token) > 4096):
        raise DiscoveryError("invalid_response", "Google returned invalid search pagination data.")
    places = data.get("places", [])
    if len(places) > limit:
        raise DiscoveryError("invalid_response", "Google exceeded the requested candidate limit.")
    if area.name and not area.enforce_name and area.coordinates is None:
        # Multiple distant matches do not establish one city/region.
        references=[]
        for place in places:
            try:
                point=Coordinates.model_validate(place['location'])
                if not geographic_reason(area.model_copy(update={'enforce_name':True,'excluded_regions':[]}),point,place.get('addressComponents',[])):
                    references.append(point)
            except (KeyError,ValueError,TypeError,AttributeError):continue
        if references and any(distance_m(references[0],point)>60000 for point in references[1:]):
            raise DiscoveryError('destination_ambiguous',
                'Several distant areas match that destination. Add the city/state or confirm a nearby starting place. No area was chosen automatically.')
        for place in places:
            try:
                point = Coordinates.model_validate(place['location'])
                if not geographic_reason(area.model_copy(update={'enforce_name':True, 'excluded_regions':[]}), point, place.get('addressComponents',[])):
                    area=area.model_copy(update={'coordinates':point,'radius_m':30000})
                    break
            except (KeyError, ValueError, TypeError, AttributeError):
                continue
    if area.name and not area.enforce_name and area.coordinates is None:
        # Without a provider-backed destination reference, nearby coverage
        # cannot be established. Do not treat a query string as location proof.
        area=area.model_copy(update={'enforce_name':True})
    city_reference=None
    if area.name and area.include_name and not area.enforce_name and not area.anchor_verified:
        for p in places:
            try:
                point=Coordinates.model_validate(p['location'])
                if not geographic_reason(SearchArea(name=area.name),point,p.get('addressComponents',[])):
                    city_reference=point;break
            except (KeyError,ValueError,TypeError,AttributeError):continue
        if city_reference is None:area=area.model_copy(update={'enforce_name':True})
    candidates, excluded = [], 0
    diagnostics, geography_reasons = {}, {}
    for place in places:
        try:
            candidate = DiscoveryCandidate(
                provider_id=place["id"], display_name=place["displayName"]["text"],
                address=place["formattedAddress"], coordinates=place["location"],
                attributions=place.get("attributions", []), types=place.get("types"),
                currentOpeningHours=place.get("currentOpeningHours"),regularOpeningHours=place.get("regularOpeningHours"),timeZone=place.get("timeZone"),containingPlaces=place.get("containingPlaces"),primaryType=place.get("primaryType"), rating=place.get("rating"), userRatingCount=place.get("userRatingCount"))
            reason = geographic_reason(area, candidate.coordinates, place.get("addressComponents", []))
            if not reason and city_reference and distance_m(city_reference,candidate.coordinates)>30000:
                reason='outside_destination_area'
            if reason:
                excluded += 1
                diagnostics[reason] = diagnostics.get(reason, 0) + 1
                from backend.venue_geography import geographic_detail
                detail = reason if reason=='outside_destination_area' else geographic_detail(area, candidate.coordinates, place.get("addressComponents", []))
                geography_reasons[detail] = geography_reasons.get(detail, 0) + 1
                continue
            candidates.append(candidate)
        except (KeyError, TypeError, AttributeError, ValidationError):
            raise DiscoveryError("invalid_response", "Google returned incomplete or invalid venue data.") from None
    return DiscoveryResult(candidates=candidates, observed={'all':{p['id'] for p in places}}, excluded_count=excluded, diagnostics=diagnostics, stages={"returned": len(places), "afterGeography": len(candidates), "geographyRejectedByReason": geography_reasons}, paging={"next": token})


def require_development_discovery() -> None:
    from backend.provider_budget import local_real_enabled
    if not local_real_enabled() and os.environ.get("WHERETO_PLACES_DEV") != "1":
        raise DiscoveryError("disabled", "Real discovery is disabled. Enable only for an authorized local development test.")


class PlacesDiscovery:
    """One shared OutingBudget per outing; reuse it across requested activities."""

    def __init__(self, outing: OutingBudget):
        self.outing = outing

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        return self.discover_many([request])

    def discover_many(self, requests: list[DiscoveryRequest]) -> DiscoveryResult:
        """One bounded outing/area, retaining cross-activity venue associations.

        No implicit extra queries. Callers supply every search and share this
        adapter's existing outing budget. No state/cache survives the call.
        """
        require_development_discovery()
        requests = [DiscoveryRequest.model_validate(r.model_dump()) for r in requests]
        if len(requests) > (4 if self.outing.settings.exploration else self.outing.settings.searches_per_outing):
            from backend.provider_budget import ProviderLimitError
            raise ProviderLimitError("This outing's venue search limit was reached. Narrow the activities or search area.")
        if requests and any(r.area != requests[0].area for r in requests):
            raise DiscoveryError("mixed_areas", "Use one explicit discovery area per outing.")
        records, diagnostics, geographic_exclusions, stages, paging, audit, observed = [], {}, 0, {}, {}, {}, {}
        for request in requests:
            result = self._search(request)
            paging[request.activity] = {"variant": request.search_variant, "next": result.paging.get("next")}
            stages[request.activity.value] = {**result.stages}
            observed[request.activity.value]=result.observed.get('all',set())
            audit[request.activity.value] = {
                'uniqueGoogleVenues':len(observed[request.activity.value]),
                'googleResultsReceived': result.stages['returned'],
                'geographyRejected': result.excluded_count,
                'geographyReasons': result.stages['geographyRejectedByReason'],
                'searchRequests': 1+result.stages.get('relationshipSearches',0), 'relationshipSearches':result.stages.get('relationshipSearches',0), 'pagesFollowed': int(request.page_token is not None),
                'searchStrategies': {('bowling_strict_type' if request.search_variant == 'initial' else 'bowling_text_evidence') if request.activity == 'bowling' else 'category_' + request.search_variant: 1},
                'requestedPageSize': min(10, self.outing.settings.ceiling("candidates_per_activity")),
                'geographyPolicy': 'verified_named_area' if request.area.name and request.area.enforce_name else 'bounded_destination_preference' if request.area.name else 'authorized_radius' if request.area.radius_m else 'coordinate_bias_only',
            }
            geographic_exclusions += result.excluded_count
            for reason, count in result.diagnostics.items():
                diagnostics[reason] = diagnostics.get(reason, 0) + count
            normalized, rejected = normalize_discovery_candidates(result, request.activity)
            if rejected:
                diagnostics['invalid_normalized_venue'] = diagnostics.get('invalid_normalized_venue', 0) + rejected
                geographic_exclusions += rejected
            audit[request.activity.value]["normalizationRejected"] = rejected
            audit[request.activity.value]["normalizationPassed"] = len(normalized)
            before_meal = len(normalized)
            stages[request.activity.value]["afterNormalization"] = len(normalized)
            if request.meal == "dinner":
                relevant = []
                for venue in normalized:
                    types = set(venue.providerTypes or []) | ({venue.primaryType} if venue.primaryType else set())
                    restaurant = bool(types & {"restaurant", "diner", "food_court", "bar_and_grill"}) or any(t.endswith("_restaurant") for t in types)
                    if types & {"cafe", "coffee_shop", "coffee_stand", "bakery"} and not restaurant:
                        diagnostics['dinner_cafe_without_restaurant_evidence'] = diagnostics.get('dinner_cafe_without_restaurant_evidence', 0) + 1
                        geographic_exclusions += 1
                    else:
                        relevant.append(venue)
                normalized = relevant
            stages[request.activity.value]["afterMealFilter"] = len(normalized)
            audit[request.activity.value]["mealRejected"] = before_meal - len(normalized)
            records.extend(normalized)
        # The unfiltered bowling refinement must bring affirmative type/name
        # evidence; a generic entertainment-center match alone is insufficient.
        quality = assess_candidates(records, require_support={r.activity for r in requests
            if r.activity == ActivityType.bowling and r.search_variant != 'initial'})
        for reason, count in quality.diagnostics.items():
            diagnostics[reason] = diagnostics.get(reason, 0) + count
        for activity in stages:
            stages[activity].update(quality.stages.get(activity, {}))
            stages[activity]["afterDeduplicationAndRelevance"] = sum(activity in v.activities for v in quality.venues)
            row = audit[activity]
            row.update(duplicatesRemoved=quality.stages.get(activity, {}).get('duplicatesRemoved', 0),
                       relevanceRejectedByReason={**quality.stages.get(activity, {}).get('relevanceRejectedByReason', {}),
                           **({'dinner_cafe_without_restaurant_evidence': row['mealRejected']} if row['mealRejected'] else {})},
                       eligibleRetained=stages[activity]['afterDeduplicationAndRelevance'], candidateCapExcluded=0)
            row['relevancePassed'] = row['eligibleRetained']
            row['latestSearch'] = {'newEligibleMatches': row['eligibleRetained'], 'previouslyKnownMatches': 0,
                                   'newlyRetained': row['eligibleRetained']}
            row['relevanceRejected'] = sum(row['relevanceRejectedByReason'].values())
        candidates = [DiscoveryCandidate(provider_id=v.facts.id, display_name=v.facts.name,
                      address=v.facts.address, coordinates=v.facts.coordinates,
                      attributions=[{'provider': a.provider, 'providerUri': str(a.uri) if a.uri else None}
                                    for a in (v.facts.attributions or [])]) for v in quality.venues]
        # Multiple categories can share one physical venue. Each category still
        # obeys the original ceiling; no ranking or refill occurs.
        for activity in {r.activity for r in requests}:
            self.outing.check_candidates(sum(activity in v.activities for v in quality.venues))
        if len(requests)==1 and not quality.venues:
            from backend.retail import intent as retail_intent
            r=requests[0];retail=retail_intent(r.activity.value)
            if retail and retail.brands and not retail.destination and not retail.hard_format and r.search_variant=='initial' and not r.page_token:
                fallback=self.discover(r.model_copy(update={'search_variant':'alternative'}))
                from backend.discovery_inventory import merge_inventory
                initial=DiscoveryResult(candidates=[],venues=[],observed=observed,audit=audit,paging=paging)
                return merge_inventory(initial,fallback,self.outing)
        return DiscoveryResult(candidates=candidates, venues=quality.venues, observed=observed,
                               excluded_count=geographic_exclusions + quality.excluded_count,
                               diagnostics=dict(sorted(diagnostics.items())), stages=stages, paging=paging, audit=audit)

    def _search(self, request: DiscoveryRequest) -> DiscoveryResult:
        limit = min(10, self.outing.settings.ceiling("candidates_per_activity"))
        body = search_body(request, limit)
        if request.page_token:
            body["pageToken"] = request.page_token
        identity = sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        with self.outing.reserve("search", identity):
            if request.page_token:
                self.outing.note_page()
            from backend.places_transport import text_search
            data = text_search(body)
        from backend.retail import intent as retail_intent
        relationship_start=self.outing.usage()["placesSearchRequests"]
        retail=retail_intent(request.activity.value)
        if retail and not retail.destination and (retail.parent or retail.same_mall):
            mall_activity=ActivityType('custom:'+retail.parent+' mall') if retail.parent else ActivityType.shopping
            malls=self.discover(request.model_copy(update={'activity':mall_activity,'page_token':None}))
            from backend.retail import MALL_TYPES
            known={v.facts.id:v.facts.name for v in malls.venues if set(v.facts.providerTypes or []) & MALL_TYPES}
            data={**data,'places':[{**p,'containingPlaces':[{**parent,**({'displayName':{'text':known[parent['id']]},'isMall':True} if parent.get('id') in known else {})} for parent in p.get('containingPlaces',[])]} for p in data.get('places',[])]}
        if retail and retail.destination and retail.brands:
            # A mall search cannot prove its tenants. Verify directed provider
            # containment from separate brand-store searches, never proximity.
            parent_sets=[]
            if len(retail.brands)>3:
                raise DiscoveryError('invalid_request','At most three tenant brands can be checked in one mall search.')
            for brand in retail.brands:
                tenant_request=request.model_copy(update={'activity':ActivityType('custom:'+brand+' store'),'page_token':None})
                tenant_result=self.discover(tenant_request)
                parent_sets.append({p.id for v in tenant_result.venues for p in (v.facts.containingPlaces or [])})
            supported=set.intersection(*parent_sets) if parent_sets else set()
            data={**data,'places':[p for p in data.get('places',[]) if p.get('id') in supported]}
        result = parse_response(data, request.area, limit)
        result.stages["relationshipSearches"]=self.outing.usage()["placesSearchRequests"]-relationship_start
        self.outing.check_candidates(len(result.candidates))
        return result
