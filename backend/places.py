"""Bounded Text Search discovery for isolated diagnostics and local real planning."""

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
FIELD_MASK = "places.id,places.displayName,places.formattedAddress,places.location,places.addressComponents,places.attributions,places.types,places.primaryType"
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]


class DiscoveryError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


class DiscoveryModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SearchArea(DiscoveryModel):
    name: Text | None = None
    coordinates: Coordinates | None = Field(default=None, repr=False)
    radius_m: Annotated[Number, Field(gt=0, le=50000)] | None = None

    @model_validator(mode="after")
    def valid_area(self):
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
    query = "dinner restaurants" if request.meal == "dinner" else QUERIES[request.activity.value]
    body = {"textQuery": f"{query} in {area.name}" if area.name else query,
            "pageSize": limit, "languageCode": "en"}
    if request.activity == ActivityType.bowling:
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
    return body


class DiscoveryCandidate(DiscoveryModel):
    provider: Literal["google_places"] = "google_places"
    provider_id: Annotated[str, StringConstraints(min_length=1, max_length=200)]
    display_name: Text
    address: Annotated[str, StringConstraints(min_length=1, max_length=1000)]
    coordinates: Coordinates
    attributions: list[dict] = Field(default_factory=list)
    types: list[str] | None = None
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
    notice: str = ("Discovery candidates only. Hours, prices, availability and travel are unknown. "
                   "Area names are checked conservatively against provider address components; "
                   "unverifiable matches are excluded. Without a radius, coordinates are a bias only. "
                   "Clear activity mismatches are excluded; uncertain matches remain candidates, "
                   "not confirmed activities or scheduled events.")


def parse_response(data: dict, area: SearchArea, limit: int) -> DiscoveryResult:
    if not isinstance(data, dict) or not isinstance(data.get("places", []), list):
        raise DiscoveryError("invalid_response", "Google returned an invalid discovery response.")
    places = data.get("places", [])
    if len(places) > limit:
        raise DiscoveryError("invalid_response", "Google exceeded the requested candidate limit.")
    candidates, excluded = [], 0
    diagnostics = {}
    for place in places:
        try:
            candidate = DiscoveryCandidate(
                provider_id=place["id"], display_name=place["displayName"]["text"],
                address=place["formattedAddress"], coordinates=place["location"],
                attributions=place.get("attributions", []), types=place.get("types"),
                primaryType=place.get("primaryType"), rating=place.get("rating"), userRatingCount=place.get("userRatingCount"))
            reason = geographic_reason(area, candidate.coordinates, place.get("addressComponents", []))
            if reason:
                excluded += 1
                diagnostics[reason] = diagnostics.get(reason, 0) + 1
                continue
            candidates.append(candidate)
        except (KeyError, TypeError, AttributeError, ValidationError):
            raise DiscoveryError("invalid_response", "Google returned incomplete or invalid venue data.") from None
    return DiscoveryResult(candidates=candidates, excluded_count=excluded, diagnostics=diagnostics)


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
        if len(requests) > self.outing.settings.searches_per_outing:
            from backend.provider_budget import ProviderLimitError
            raise ProviderLimitError("This outing's venue search limit was reached. Narrow the activities or search area.")
        if requests and any(r.area != requests[0].area for r in requests):
            raise DiscoveryError("mixed_areas", "Use one explicit discovery area per outing.")
        records, diagnostics, geographic_exclusions = [], {}, 0
        for request in requests:
            result = self._search(request)
            geographic_exclusions += result.excluded_count
            for reason, count in result.diagnostics.items():
                diagnostics[reason] = diagnostics.get(reason, 0) + count
            normalized, rejected = normalize_discovery_candidates(result, request.activity)
            if rejected:
                diagnostics['invalid_normalized_venue'] = diagnostics.get('invalid_normalized_venue', 0) + rejected
                geographic_exclusions += rejected
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
            records.extend(normalized)
        quality = assess_candidates(records)
        for reason, count in quality.diagnostics.items():
            diagnostics[reason] = diagnostics.get(reason, 0) + count
        candidates = [DiscoveryCandidate(provider_id=v.facts.id, display_name=v.facts.name,
                      address=v.facts.address, coordinates=v.facts.coordinates,
                      attributions=[{'provider': a.provider, 'providerUri': str(a.uri) if a.uri else None}
                                    for a in (v.facts.attributions or [])]) for v in quality.venues]
        # Multiple categories can share one physical venue. Each category still
        # obeys the original ceiling; no ranking or refill occurs.
        for activity in {r.activity for r in requests}:
            self.outing.check_candidates(sum(activity in v.activities for v in quality.venues))
        return DiscoveryResult(candidates=candidates, venues=quality.venues,
                               excluded_count=geographic_exclusions + quality.excluded_count,
                               diagnostics=dict(sorted(diagnostics.items())))

    def _search(self, request: DiscoveryRequest) -> DiscoveryResult:
        limit = self.outing.settings.candidates_per_activity
        body = search_body(request, limit)
        identity = sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        with self.outing.reserve("search", identity):
            from backend.places_transport import text_search
            data = text_search(body)
        result = parse_response(data, request.area, limit)
        self.outing.check_candidates(len(result.candidates))
        return result
