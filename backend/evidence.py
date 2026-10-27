"""Task 45 transient evidence/display contracts. No I/O or feasibility decisions.

Adapters leave existing value models intact. Paths refer to those values, never
copy precise coordinates, raw payloads or internal diagnostics into messages.
"""
from datetime import date
from typing import Literal
from urllib.parse import urlencode

from pydantic import AwareDatetime, Field

from backend.feasibility import FeasibilityResult, State
from backend.models import ContractModel, DataStatus, Nonblank, Venue
from backend.routes import RouteLeg
from backend.venue_models import Attribution, VenueFacts, WebUrl
from backend.venue_quality import DistinctVenue

Certainty = Literal["reported", "estimated", "provisional", "unknown", "requires_confirmation", "fictional", "unverified"]
Basis = Literal["supplied", "computed", "not_retrieved", "not_checked", "fixture"]


class Source(ContractModel):
    kind: Literal["provider", "local", "user", "fixture", "unknown"]
    provider: Nonblank | None = None
    place_id: Nonblank | None = None
    reference: Nonblank | None = None
    url: WebUrl | None = None
    link_origin: Literal["provider", "documented_maps_url"] | None = None


class Claim(ContractModel):
    source: Source
    contributing_sources: list[Source] = Field(default_factory=list)
    certainty: Certainty
    basis: Basis
    message: Nonblank
    observed_at: AwareDatetime | None = None  # Receipt only; never a freshness guarantee.
    explicit_dates: list[date] = Field(default_factory=list)  # Supplied endpoint/special dates only.


class DisplayAttribution(ContractModel):
    google_maps_required: bool = False
    brand: Literal["Google Maps"] | None = None
    logo_preferred: bool = False
    text_only_when_space_limited: bool = False
    third_party: list[Attribution] = Field(default_factory=list)
    policy_url: WebUrl | None = None
    notices: list[str] = Field(default_factory=list)


class EvidenceLabels(ContractModel):
    claims: dict[str, Claim]
    attribution: DisplayAttribution = Field(default_factory=DisplayAttribution)


def google_attribution(product, credits=()):
    path = "places/web-service" if product == "places" else "routes"
    return DisplayAttribution(
        google_maps_required=True, brand="Google Maps", logo_preferred=True,
        text_only_when_space_limited=True, third_party=list(credits),
        policy_url=f"https://developers.google.com/maps/documentation/{path}/policies")


def venue_source(venue: VenueFacts) -> Source:
    url, origin = venue.mapsUrl, "provider" if venue.mapsUrl else None
    if url is None and venue.provider == "google_places" and venue.evidence == "provider_supplied":
        # Official Maps URL syntax. No API call/key; preserve ID and encode all text.
        link = "https://www.google.com/maps/search/?" + urlencode(
            {"api": "1", "query": venue.name, "query_place_id": venue.id})
        if len(link) <= 2048:
            url, origin = link, "documented_maps_url"
    return Source(kind="fixture" if venue.evidence == "fictional" else "provider",
                  provider=venue.provider, place_id=venue.id, url=url, link_origin=origin)


VENUE_FIELDS = {
    "id": "Venue identity", "resourceName": "Provider resource", "name": "Venue name",
    "address": "Address", "coordinates": "Coordinates", "providerTypes": "Venue types",
    "primaryType": "Primary venue type", "rating": "Rating", "ratingCount": "Rating count",
    "websiteUrl": "Website", "mapsUrl": "Google Maps link", "priceLevel": "Price category",
    "priceRange": "Price range", "timeZone": "Time zone", "utcOffsetMinutes": "UTC offset",
    "regularOpeningHours": "Regular opening hours", "currentOpeningHours": "Date-specific opening hours",
    "attributions": "Provider credits",
}


def _leaves(value, path):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _leaves(child, (*path, key))
    else:
        yield path, value  # Lists (including empty periods) are whole snapshots.


def venue_labels(value: VenueFacts) -> EvidenceLabels:
    venue = VenueFacts.model_validate(value.model_dump())
    source = venue_source(venue)
    claims = {}
    for field, title in VENUE_FIELDS.items():
        content = venue.model_dump()[field]
        # Atomic nested facts retain individual receipt times through partial updates.
        for path, supplied in _leaves(content, (field,)):
            key = ".".join(path)
            if supplied is None:
                claims[key] = Claim(source=source, certainty="unknown", basis="not_retrieved",
                                  message=f"{title} unavailable or not retrieved.")
                continue
            certainty: Certainty = {"provider_supplied": "reported", "fictional": "fictional",
                                     "estimated": "estimated", "unknown": "unverified"}[venue.evidence]
            message = f"{title} from Google Maps." if venue.provider == "google_places" else f"{title} from the provider."
            dates = []
            if field in {"regularOpeningHours", "currentOpeningHours", "rating", "ratingCount", "priceLevel", "priceRange", "utcOffsetMinutes"} and certainty == "reported":
                certainty = "provisional"
                message += " May change."
            if field == "regularOpeningHours":
                message = "Regular opening hours; holidays and exceptions may differ."
            elif field == "currentOpeningHours":
                message = "Date-specific opening hours; applicability requires a date check."
                if path[-1] == "periods":
                    dates = sorted({p.date for period in venue.currentOpeningHours.periods
                                    for p in (period.open, period.close) if p is not None and p.date is not None})
                elif path[-1] == "specialDays":
                    dates = venue.currentOpeningHours.specialDays or []
            elif field in {"priceLevel", "priceRange"}:
                message = "Provider price indicator; not a per-person or ticket quote."
            if certainty == "fictional":
                message = f"Fictional development data: {title.lower()}."
            elif certainty == "estimated":
                message = f"Estimated {title.lower()}; not verified."
            elif certainty == "unverified":
                message = f"{title} not verified."
            claims[key] = Claim(source=source, certainty=certainty,
                                basis="fixture" if certainty == "fictional" else "computed" if certainty == "estimated" else "supplied",
                                message=message, observed_at=venue.observedAt.get(key), explicit_dates=dates)
    # These are separate claims, never inferred from hours or broad price bands.
    for key, message, certainty in (
        ("price", "Price information unavailable.", "unknown"),
        ("businessStatus", "Business status not retrieved.", "unknown"),
        ("availability", "Availability requires confirmation.", "requires_confirmation"),
        ("reservation", "Reservation availability requires confirmation.", "requires_confirmation"),
        ("session", "Movie showtime not verified." if venue.activity == "movie" else "Activity session not verified.", "unverified"),
    ):
        claims[key] = Claim(source=Source(kind="unknown"), certainty=certainty, basis="not_checked", message=message)
    claims["activity"] = Claim(source=Source(kind="local"), certainty="unverified", basis="computed",
                                message="Activity category is search context; suitability needs checking.")
    attribution = (google_attribution("places", venue.attributions or [])
                   if venue.provider == "google_places" and venue.evidence == "provider_supplied" else DisplayAttribution())
    return EvidenceLabels(claims=claims, attribution=attribution)


def distinct_venue_labels(value: DistinctVenue) -> EvidenceLabels:
    """Label Task 42 merged facts without losing IDs of contributing observations."""
    distinct = DistinctVenue.model_validate(value.model_dump())
    labels = venue_labels(distinct.facts)
    for key, claim in labels.claims.items():
        if key.split(".")[0] not in VENUE_FIELDS or claim.certainty == "unknown":
            continue
        parts = tuple(key.split("."))
        merged = dict(_leaves(distinct.facts.model_dump(), ()))[parts]
        contributors = []
        observed_source = None
        for original in distinct.sources:
            supplied = dict(_leaves(original.model_dump(), ())).get(parts)
            matches = (any(item in merged for item in supplied) if isinstance(merged, list) and isinstance(supplied, list)
                       else supplied == merged and supplied is not None)
            if matches:
                source = venue_source(original)
                if source not in contributors:
                    contributors.append(source)
                if original.observedAt.get(key) == claim.observed_at:
                    observed_source = source
        if contributors:
            claim.source = observed_source or contributors[0]
            claim.contributing_sources = contributors
    return labels


def route_labels(value: RouteLeg) -> EvidenceLabels:
    leg = RouteLeg.model_validate(value.model_dump())
    source = Source(kind="provider" if leg.provider == "google_routes" else "local", provider=leg.provider)
    routed = (leg.provider == "google_routes" and leg.status == "ok"
              and leg.estimate_type == ("traffic_unaware" if leg.mode == "drive" else "walking"))
    local = (leg.provider == "local_identity" and leg.status == "same_location"
             and leg.estimate_type == "same_location" and leg.duration_seconds == 0 and leg.distance_meters == 0)
    claims = {}
    for key, title in (("duration_seconds", "Travel time"), ("distance_meters", "Travel distance")):
        message = f"{title} unavailable."
        if routed:
            message = (f"Estimated {'drive' if leg.mode == 'drive' else 'walk'}: {leg.duration_minutes:.1f} minutes."
                       if key == "duration_seconds" else "Estimated route distance from Google Maps.")
        elif local:
            message = "Same venue; no inter-venue travel calculated."
        claims[key] = Claim(source=source, certainty="estimated" if routed or local else "unknown",
                            basis="computed" if routed or local else "not_checked", message=message)
    claims["status"] = Claim(source=source, certainty="reported" if leg.status == "unreachable" and leg.provider == "google_routes" else "estimated" if routed or local else "unknown",
                             basis="supplied" if leg.provider == "google_routes" and (routed or leg.status == "unreachable") else "computed" if local else "not_checked",
                             message="No route found by Google Maps." if leg.status == "unreachable" and leg.provider == "google_routes" else "Route estimate available." if routed or local else "Route not verified.")
    attribution = google_attribution("routes") if leg.provider == "google_routes" else DisplayAttribution()
    attribution.notices = (["Driving estimates exclude live traffic; arrival times are not guaranteed."] if leg.mode == "drive" else
                           ["Walking routes are beta and may omit sidewalks or pedestrian paths; travel times are not guaranteed."])
    # Direction, mode, estimate_type and exact metrics stay on the paired RouteLeg.
    return EvidenceLabels(claims=claims, attribution=attribution)


CHECK_MESSAGES = {
    "route_verified": "Travel constraints satisfied according to route estimates.",
    "hours_cover_activity": "Opening hours cover the planned visit according to available date-specific evidence.",
    "closed_during_activity": "Opening hours conflict with the planned visit.",
    "unreachable_route": "No route found by Google Maps.",
    "leg_limit_exceeded": "Estimated travel exceeds the per-leg limit.",
    "first_preference_exceeded": "First-stop route exceeds the strict or doubled flexible maximum; no travel requirement was relaxed.",
    "first_preference_verified": "First-stop preference checked using Google route duration or road distance.",
    "first_leg_limit_exceeded": "Estimated travel to the first stop exceeds its limit.",
    "total_travel_limit_exceeded": "Known estimated travel exceeds the total limit.",
    "insufficient_transfer_time": "The schedule leaves less time than the travel estimate.",
    "overlapping_stops": "Planned visits overlap.",
    "regular_hours_only": "Opening hours not verified for this date; only regular hours are available.",
    "session_not_verified": "Activity session or movie showtime not verified.",
}


class CheckLabel(ContractModel):
    kind: Literal["travel", "hours", "session"]
    state: State
    stop_index: int
    label: Claim


class FeasibilityLabels(ContractModel):
    state: State
    message: str
    scope: str = "Travel and opening-hour checks only; prices, reservations and availability are not verified."
    checks: list[CheckLabel]


def feasibility_labels(value: FeasibilityResult) -> FeasibilityLabels:
    result = FeasibilityResult.model_validate(value.model_dump())
    checks = []
    for check in result.checks:
        fallback = ("Opening hours not verified for this date." if check.kind == "hours" else
                    "Activity session not verified." if check.kind == "session" else "Travel constraint not fully verified.")
        checks.append(CheckLabel(kind=check.kind, state=check.state, stop_index=check.stop_index,
                                label=Claim(source=Source(kind="local", reference="Task 44 feasibility evaluation"),
                                            certainty="unverified" if check.state == "unverified" else "reported",
                                            basis="computed", message=CHECK_MESSAGES.get(check.code, fallback))))
    return FeasibilityLabels(state=result.state, checks=checks, message={
        "feasible": "Travel and opening-hour constraints satisfied according to available evidence.",
        "infeasible": "A checked hard constraint is violated; other details may remain unverified.",
        "unverified": "Some travel, opening-hour or session constraints remain unverified.",
    }[result.state])


def fictional_labels(value: Venue) -> EvidenceLabels:
    """Explicit adapter for existing fictional fixtures; missing fields stay unknown."""
    if value.dataQuality.identity != DataStatus.fictional:
        raise ValueError("Explicit fictional identity evidence is required.")
    source = Source(kind="fixture", reference=value.source)
    claims = {}
    fields = {"id": "identity", "name": "identity", "price": "price", "duration": "duration",
              "capacity": "capacity", "experience": "experience", "zone": "travel", "eventDate": "schedule",
              "start": "schedule", "openingWindows": "schedule", "availabilityWindows": "schedule"}
    for key, quality_field in fields.items():
        present = getattr(value, key, None) is not None
        fictional = present and getattr(value.dataQuality, quality_field) == DataStatus.fictional
        claims[key] = Claim(source=source, certainty="fictional" if fictional else "unverified" if present else "unknown",
                            basis="fixture" if fictional else "not_checked",
                            message="Fictional development data." if fictional else "Information not verified." if present else "Information unavailable.")
    return EvidenceLabels(claims=claims)


def user_detail_label() -> Claim:
    return Claim(source=Source(kind="user"), certainty="unverified", basis="supplied",
                 message="Provided by you; not independently verified.")
