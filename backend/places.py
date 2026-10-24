"""Development-only Text Search discovery. No planner connection or persistence."""

from hashlib import sha256
import json
from math import asin, cos, radians, sin, sqrt
import os
import re
from typing import Annotated, Literal
import unicodedata

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError, model_validator

from backend.models import ActivityType
from backend.provider_budget import OutingBudget
from backend.venue_models import Coordinates

PROJECT = "where-to-512422"
SERVICE_ACCOUNT = f"whereto-local-maps@{PROJECT}.iam.gserviceaccount.com"
ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
# ID/attributions: IDs Only. Other fields: Text Search Pro (not Details tiers).
FIELD_MASK = "places.id,places.displayName,places.formattedAddress,places.location,places.addressComponents,places.attributions"
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
    destination: SearchArea | None = None
    current_location: SearchArea | None = Field(default=None, repr=False)
    starting_location: StartingLocation | None = Field(default=None, repr=False)
    travel_constraints: TravelConstraints | None = None

    @model_validator(mode="after")
    def location_required(self):
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
    query = QUERIES[request.activity.value]
    body = {"textQuery": f"{query} in {area.name}" if area.name else query,
            "pageSize": limit, "languageCode": "en"}
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


def _normalized(value: str) -> str:
    return re.sub(r"[^\w]", "", unicodedata.normalize("NFKD", value).casefold())


def distance_m(a: Coordinates, b: Coordinates) -> float:
    lat1, lat2 = radians(a.latitude), radians(b.latitude)
    h = sin((lat2-lat1)/2)**2 + cos(lat1)*cos(lat2)*sin(radians(b.longitude-a.longitude)/2)**2
    return 6371008.8 * 2 * asin(sqrt(min(1.0, h)))


class DiscoveryCandidate(DiscoveryModel):
    provider: Literal["google_places"] = "google_places"
    provider_id: Text
    display_name: Text
    address: Annotated[str, StringConstraints(min_length=1, max_length=1000)]
    coordinates: Coordinates
    attributions: list[dict] = Field(default_factory=list)


class DiscoveryResult(DiscoveryModel):
    provider: Literal["google_places"] = "google_places"
    candidates: list[DiscoveryCandidate]
    excluded_count: int = 0
    notice: str = ("Discovery candidates only. Hours, prices, availability and travel are unknown. "
                   "Area names are checked conservatively against provider address components; "
                   "unverifiable matches are excluded. Without a radius, coordinates are a bias only.")


def parse_response(data: dict, area: SearchArea, limit: int) -> DiscoveryResult:
    if not isinstance(data, dict) or not isinstance(data.get("places", []), list):
        raise DiscoveryError("invalid_response", "Google returned an invalid discovery response.")
    places = data.get("places", [])
    if len(places) > limit:
        raise DiscoveryError("invalid_response", "Google exceeded the requested candidate limit.")
    candidates, excluded = [], 0
    for place in places:
        try:
            candidate = DiscoveryCandidate(
                provider_id=place["id"], display_name=place["displayName"]["text"],
                address=place["formattedAddress"], coordinates=place["location"],
                attributions=place.get("attributions", []))
            # Only geographic components count; never a venue/street name match.
            geographic_types = {"locality", "postal_town", "neighborhood", "country",
                                "sublocality", "administrative_area_level_1",
                                "administrative_area_level_2",
                                *(f"sublocality_level_{i}" for i in range(1, 6))}
            names = {_normalized(c[k]) for c in place.get("addressComponents", [])
                     if geographic_types.intersection(c.get("types", []))
                     for k in ("longText", "shortText") if isinstance(c.get(k), str)}
            if area.name and not all(_normalized(part) in names for part in area.name.split(",")):
                excluded += 1
                continue
            if area.radius_m is not None and distance_m(area.coordinates, candidate.coordinates) > area.radius_m:
                excluded += 1
                continue
            candidates.append(candidate)
        except (KeyError, TypeError, AttributeError, ValidationError):
            raise DiscoveryError("invalid_response", "Google returned incomplete or invalid venue data.") from None
    return DiscoveryResult(candidates=candidates, excluded_count=excluded)


def require_development_discovery() -> None:
    if os.environ.get("WHERETO_PLACES_DEV") != "1":
        raise DiscoveryError("disabled", "Real discovery is disabled. Enable only for an authorized local development test.")


class PlacesDiscovery:
    """One shared OutingBudget per outing; reuse it across requested activities."""

    def __init__(self, outing: OutingBudget):
        self.outing = outing

    def discover(self, request: DiscoveryRequest) -> DiscoveryResult:
        require_development_discovery()
        # Revalidate mutable nested inputs before any authentication or network.
        request = DiscoveryRequest.model_validate(request.model_dump())
        limit = self.outing.settings.candidates_per_activity
        body = search_body(request, limit)
        identity = sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
        with self.outing.reserve("search", identity):
            from backend.places_transport import text_search
            data = text_search(body)
        result = parse_response(data, request.area, limit)
        self.outing.check_candidates(len(result.candidates))
        return result
