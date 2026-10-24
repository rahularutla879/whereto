"""Bounded route calculation contracts and pure adjacent-group matrix planning.

No planner connection, geocoding, feasibility filtering, persistence or logging.
"""
from collections import defaultdict
from decimal import Decimal
from hashlib import sha256
import json
import os
import re
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator

from backend.provider_budget import OutingBudget, ProviderLimitError
from backend.venue_models import Coordinates, VenueFacts

Mode = Literal["drive", "walk"]
Identity = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=200, pattern=r"^\S+$")]
PlaceID = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=200, pattern=r"^[A-Za-z0-9_-]+$")]
FIELD_MASK = "originIndex,destinationIndex,status,condition,distanceMeters,duration"
ENDPOINT = "https://routes.googleapis.com/distanceMatrix/v2:computeRouteMatrix"


class RouteError(RuntimeError):
    """Fixed safe error codes/messages; never attach raw provider input."""
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


class RouteModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RoutePoint(RouteModel):
    id: Identity
    coordinates: Coordinates | None = Field(default=None, repr=False)
    place_id: PlaceID | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def located(self):
        if (self.coordinates is None) == (self.place_id is None):
            raise ValueError("Provide exactly one validated coordinate point or Google Place ID.")
        return self

    @classmethod
    def from_venue(cls, venue: VenueFacts) -> "RoutePoint":
        venue = VenueFacts.model_validate(venue.model_dump())
        if venue.provider != "google_places" or venue.evidence != "provider_supplied":
            raise RouteError("invalid_venue", "Routing requires provider-supplied Google venue facts.")
        # Keep the original stable provider ID, with no discovery/detail request.
        return cls(id=venue.id, place_id=venue.id)


class AuthorizedStart(RouteModel):
    point: RoutePoint = Field(repr=False)
    explicitly_authorized: Literal[True]

    @field_validator("explicitly_authorized", mode="before")
    @classmethod
    def explicit_boolean(cls, value):
        if value is not True:
            raise ValueError("Starting-location authorization must be explicitly true.")
        return value


class RouteRequest(RouteModel):
    activity_groups: Annotated[list[Annotated[list[RoutePoint], Field(min_length=1, max_length=3)]], Field(min_length=1, max_length=4)] = Field(repr=False)
    mode: Mode
    starting_location: AuthorizedStart | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def consistent_identities(self):
        points = [p for group in self.activity_groups for p in group]
        if self.starting_location:
            points.append(self.starting_location.point)
        seen = {}
        for point in points:
            if point.id in seen and seen[point.id] != point:
                raise ValueError("A stable routing identifier must identify one location.")
            seen[point.id] = point
        return self


class RouteLeg(RouteModel):
    origin_id: str
    destination_id: str
    mode: Mode
    duration_seconds: Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)] | None = None
    # Exact protobuf duration retained for hard constraints (up to nine decimals).
    duration_nanoseconds: Annotated[int, Field(strict=True, ge=0)] | None = None
    duration_minutes: Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)] | None = None
    distance_meters: Annotated[int, Field(strict=True, ge=0)] | None = None
    status: Literal["ok", "same_location", "unreachable", "error", "unknown"]
    provider: Literal["google_routes", "local_identity"] = "google_routes"
    estimate_type: Literal["traffic_unaware", "walking", "same_location"]
    error_code: str | None = None
    provider_status_code: int | None = None

    @model_validator(mode="after")
    def consistent_metrics(self):
        metrics = (self.duration_seconds, self.duration_minutes, self.distance_meters)
        if self.status in ("ok", "same_location"):
            if any(v is None for v in metrics) or self.duration_minutes != self.duration_seconds / 60:
                raise ValueError("Successful routes require consistent distance and duration.")
        elif any(v is not None for v in metrics):
            raise ValueError("Failed or unknown routes must not supply travel metrics.")
        if self.duration_nanoseconds is not None and (
                self.duration_seconds is None or float(Decimal(self.duration_nanoseconds) / 10**9) != self.duration_seconds):
            raise ValueError("Exact duration must agree with seconds.")
        return self


class RouteResult(RouteModel):
    legs: list[RouteLeg]
    matrix_elements: int  # Conservatively reserved, not a billing receipt.
    matrix_requests: int
    notice: str = "Routing estimates are not live traffic predictions or guaranteed travel times. Walking routes are beta and may omit sidewalks or pedestrian paths."


class RouteCalculator(Protocol):
    def calculate(self, request: RouteRequest) -> RouteResult: ...


def require_development_routes():
    if os.environ.get("WHERETO_ROUTES_DEV") != "1":
        raise RouteError("disabled", "Real routing is disabled. Separate owner authorization is required for a local live test.")


def waypoint(point: RoutePoint) -> dict:
    return {"waypoint": ({"placeId": point.place_id} if point.place_id else
                         {"location": {"latLng": point.coordinates.model_dump()}})}


def matrix_body(origins: list[RoutePoint], destinations: list[RoutePoint], mode: Mode) -> dict:
    if not origins or not destinations:
        raise RouteError("invalid_request", "A matrix needs origins and destinations.")
    if mode not in ("drive", "walk"):
        raise RouteError("unsupported_mode", "Only driving and walking are supported.")
    if len(origins) * len(destinations) > 625 or sum(p.place_id is not None for p in origins + destinations) > 50:
        raise RouteError("matrix_limit", "The matrix exceeds Google's request limits.")
    body = {"origins": [waypoint(p) for p in origins],
            "destinations": [waypoint(p) for p in destinations],
            "travelMode": "DRIVE" if mode == "drive" else "WALK"}
    if mode == "drive":
        body["routingPreference"] = "TRAFFIC_UNAWARE"
    return body


def same_location(a: RoutePoint, b: RoutePoint) -> bool:
    # Equal coordinates alone cannot prove identical venues/entrances.
    return a.id == b.id or (a.place_id is not None and a.place_id == b.place_id)


def location_key(point: RoutePoint) -> tuple:
    """Identical provider waypoints can reuse metrics across caller aliases."""
    return (("place", point.place_id) if point.place_id else
            ("coordinates", point.coordinates.latitude, point.coordinates.longitude))


def plan_matrices(request: RouteRequest):
    """Exact directed pair union; rectangular batches contain no unneeded pairs."""
    request = RouteRequest.model_validate(request.model_dump())
    groups = request.activity_groups
    transitions = list(zip(groups, groups[1:]))
    if request.starting_location:
        transitions.insert(0, ([request.starting_location.point], groups[0]))
    pairs = {}
    for origins, destinations in transitions:
        for a in origins:
            for b in destinations:
                pairs.setdefault((a.id, b.id), (a, b))
    pending = defaultdict(dict)
    points = {}
    for key, (a, b) in pairs.items():
        if not same_location(a, b):
            origin, destination = location_key(a), location_key(b)
            points.setdefault(origin, a)
            points.setdefault(destination, b)
            pending[origin][destination] = b
    rectangles = {}
    for origin, destinations in pending.items():
        signature = tuple(sorted(destinations))
        rectangles.setdefault(signature, []).append(points[origin])
    matrices = [(origins, [points[d] for d in signature]) for signature, origins in rectangles.items()]
    return pairs, matrices


def _leg(a, b, mode, status="unknown", **kwargs):
    return RouteLeg(origin_id=a.id, destination_id=b.id, mode=mode, status=status,
                    estimate_type="traffic_unaware" if mode == "drive" else "walking", **kwargs)


def parse_matrix(data, origins, destinations, mode) -> list[RouteLeg]:
    """Associate by indices, never response order; unknown/error never means zero."""
    if not isinstance(data, list) or len(data) > len(origins) * len(destinations):
        raise RouteError("invalid_response", "Google returned an invalid matrix response.")
    indexed, duplicates = {}, set()
    for item in data:
        if not isinstance(item, dict):
            raise RouteError("invalid_response", "Google returned an invalid matrix element.")
        # Google may omit default scalar values under proto3 JSON semantics.
        # Decode absent indices as zero, never infer them from response order.
        i, j = item.get("originIndex", 0), item.get("destinationIndex", 0)
        if type(i) is not int or type(j) is not int or not (0 <= i < len(origins) and 0 <= j < len(destinations)):
            raise RouteError("invalid_response", "Google returned missing or invalid matrix indices.")
        if (i, j) in indexed:
            duplicates.add((i, j))
        indexed[i, j] = item
    legs = []
    for i, a in enumerate(origins):
        for j, b in enumerate(destinations):
            item = indexed.get((i, j))
            if item is None or (i, j) in duplicates:
                legs.append(_leg(a, b, mode, error_code="duplicate_element" if (i, j) in duplicates else "missing_element"))
                continue
            status = item.get("status")
            code = status.get("code", 0) if isinstance(status, dict) else None
            if type(code) is not int or code < 0 or code > 16:
                legs.append(_leg(a, b, mode, error_code="invalid_status"))
                continue
            if code:
                legs.append(_leg(a, b, mode, "error", error_code="provider_element", provider_status_code=code))
                continue
            if item.get("condition") == "ROUTE_NOT_FOUND":
                legs.append(_leg(a, b, mode, "unreachable", error_code="route_not_found"))
                continue
            duration, distance = item.get("duration"), item.get("distanceMeters", 0)
            if (item.get("condition") != "ROUTE_EXISTS" or not isinstance(duration, str)
                    or not re.fullmatch(r"[0-9]{1,12}(?:\.[0-9]{1,9})?s", duration)
                    or type(distance) is not int or distance < 0):
                legs.append(_leg(a, b, mode, error_code="invalid_metrics"))
                continue
            seconds = float(duration[:-1])
            legs.append(_leg(a, b, mode, "ok", duration_seconds=seconds,
                             duration_nanoseconds=int(Decimal(duration[:-1]) * 10**9),
                             duration_minutes=seconds / 60, distance_meters=distance))
    return legs


class GoogleRouteCalculator:
    """One call per outing; retain results in memory for future candidate reuse."""
    def __init__(self, outing: OutingBudget):
        self.outing = outing

    def calculate(self, request: RouteRequest) -> RouteResult:
        require_development_routes()  # Before even authentication imports.
        request = RouteRequest.model_validate(request.model_dump())
        pairs, matrices = plan_matrices(request)
        try:
            for group in request.activity_groups:
                self.outing.check_candidates(len(group))
        except ProviderLimitError as error:
            raise RouteError("application_limit", str(error)) from None
        bodies = [matrix_body(a, b, request.mode) for a, b in matrices]
        reservations = [(sha256(json.dumps(body, sort_keys=True).encode()).hexdigest(), len(a), len(b))
                        for body, (a, b) in zip(bodies, matrices)]
        legs = {}
        for key, (a, b) in pairs.items():
            if same_location(a, b):
                legs[key] = RouteLeg(origin_id=a.id, destination_id=b.id, mode=request.mode,
                                     status="same_location", duration_seconds=0, duration_minutes=0,
                                     distance_meters=0, provider="local_identity", estimate_type="same_location")
        if reservations:
            try:
                with self.outing.reserve_matrices(reservations):
                    from backend.routes_transport import compute_matrix
                    computed = {}
                    routed_points = {p.id: p for origins, destinations in matrices for p in origins + destinations}
                    stopped = None
                    for body, (origins, destinations) in zip(bodies, matrices):
                        try:
                            if stopped:
                                raise RouteError("not_requested", "Routing stopped after a provider failure.")
                            parsed = parse_matrix(compute_matrix(body), origins, destinations, request.mode)
                        except RouteError as error:
                            stopped = error.code
                            parsed = [_leg(a, b, request.mode, "error", error_code=error.code)
                                      for a in origins for b in destinations]
                        for leg in parsed:
                            computed[location_key(routed_points[leg.origin_id]), location_key(routed_points[leg.destination_id])] = leg
                    for key, (a, b) in pairs.items():
                        if key not in legs:
                            legs[key] = computed[location_key(a), location_key(b)].model_copy(
                                update={"origin_id": a.id, "destination_id": b.id})
            except ProviderLimitError as error:
                raise RouteError("application_limit", str(error)) from None
        return RouteResult(legs=[legs[key] for key in pairs],
                           matrix_elements=sum(a * b for _, a, b in reservations),
                           matrix_requests=len(reservations))
