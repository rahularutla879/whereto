"""Pure Google-to-canonical conversion. Never imports transport/auth/budgets.

Only explicitly supported facts survive. Invalid known fields reject the record;
unknown provider extensions are ignored. No raw response or actual live fixture is saved.
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import AwareDatetime, TypeAdapter, ValidationError

from backend.models import ActivityType
from backend.venue_models import VenueFacts


class NormalizationError(ValueError):
    """Safe error with no raw provider content or validation input values."""


def _object(value: Any) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Expected object")
    return value


def _date(value):
    obj = _object(value)
    parts = [obj[k] for k in ("year", "month", "day")]
    if any(type(part) is not int for part in parts):
        raise ValueError("Invalid date")
    return date(*parts)


def _hours(value):
    obj = _object(value)
    result = {k: obj[k] for k in ("weekdayDescriptions", "openNow", "nextOpenTime", "nextCloseTime") if k in obj}
    if obj.get("periods") is not None:
        if not isinstance(obj["periods"], list):
            raise ValueError("Invalid periods")
        periods = []
        for period in obj["periods"]:
            period = _object(period)
            converted = {}
            for endpoint in ("open", "close"):
                if period.get(endpoint) is not None:
                    point = _object(period[endpoint])
                    converted[endpoint] = {k: point[k] for k in ("day", "hour", "minute", "truncated") if k in point}
                    if point.get("date") is not None:
                        converted[endpoint]["date"] = _date(point["date"])
            periods.append(converted)
        result["periods"] = periods
    if obj.get("specialDays") is not None:
        if not isinstance(obj["specialDays"], list):
            raise ValueError("Invalid special days")
        result["specialDays"] = [_date(_object(day)["date"]) for day in obj["specialDays"]]
    return result or None


def _money(value):
    obj = _object(value)
    units, nanos = obj.get("units"), obj.get("nanos")
    if units is None and nanos is None:
        raise ValueError("Missing monetary amount")
    # Google Money units are int64 JSON strings. Absent components have protobuf zero semantics.
    if units is not None and (not isinstance(units, str) or not units.isascii() or not units.isdecimal()):
        raise ValueError("Invalid money units")
    if nanos is not None and (type(nanos) is not int or not 0 <= nanos <= 999999999):
        raise ValueError("Invalid money nanos")
    whole = int(units) if units is not None else 0
    if whole > 9223372036854775807:
        raise ValueError("Invalid int64 money")
    return {"currency": obj["currencyCode"], "amount": Decimal(whole) + Decimal(nanos or 0) / Decimal(1000000000)}


def _price_range(value):
    obj = _object(value)
    return {target: _money(obj[key]) for key, target in (("startPrice", "start"), ("endPrice", "end"))
            if obj.get(key) is not None} or None


def _attributions(value):
    if not isinstance(value, list):
        raise ValueError("Invalid attributions")
    return [{"provider": _object(item).get("provider"), "uri": item.get("providerUri")} for item in value]


DIRECT_FIELDS = {
    "name": "resourceName", "formattedAddress": "address", "location": "coordinates",
    "types": "providerTypes", "primaryType": "primaryType", "rating": "rating", "userRatingCount": "ratingCount",
    "websiteUri": "websiteUrl", "googleMapsUri": "mapsUrl", "utcOffsetMinutes": "utcOffsetMinutes",
}
PRICE_LEVELS = {"PRICE_LEVEL_" + name.upper(): name for name in
                ("free", "inexpensive", "moderate", "expensive", "very_expensive")}


def _supplied(values, prefix=()):
    """Atomic observations: scalars/lists; nested missing/null leaves do not erase."""
    for key, value in values.items():
        path = (*prefix, key)
        if isinstance(value, dict) and key in {"coordinates", "regularOpeningHours", "currentOpeningHours",
                                               "timeZone", "priceRange", "start", "end"}:
            yield from _supplied(value, path)
        elif value is not None:
            yield path, value


def _assign(payload, path, value):
    for key in path[:-1]:
        if payload.get(key) is None:
            payload[key] = {}
        payload = payload[key]
    payload[path[-1]] = value


def normalize_google_place(raw: dict, activity: ActivityType | str, *,
                           observed_at: datetime | None = None,
                           existing: VenueFacts | None = None) -> VenueFacts:
    """Normalize a Place, or apply a partial Place update to the same Google ID.

    existing is optional, in-memory only. A new record needs id + displayName.text;
    an update needs id. Missing/null leaves never erase previous facts. Lists
    (including hours periods) replace whole snapshots; receipt times stay separate.
    """
    try:
        obj = _object(raw)
        identity = obj["id"]
        if not isinstance(identity, str) or not identity or identity.strip() != identity:
            raise ValueError("Invalid ID")
        if observed_at is not None and not isinstance(observed_at, datetime):
            raise ValueError("Receipt time must be a timezone-aware datetime")
        when = TypeAdapter(AwareDatetime).validate_python(
            observed_at if observed_at is not None else datetime.now(timezone.utc))
        values = {target: obj[key] for key, target in DIRECT_FIELDS.items() if obj.get(key) is not None}
        if obj.get("name") is not None and obj["name"] != "places/" + identity:
            raise ValueError("Resource name and ID disagree")
        if obj.get("displayName") is not None:
            values["name"] = _object(obj["displayName"])["text"]
        for key, parser in (("regularOpeningHours", _hours), ("currentOpeningHours", _hours),
                            ("priceRange", _price_range), ("attributions", _attributions)):
            if obj.get(key) is not None:
                values[key] = parser(obj[key])
        if obj.get("timeZone") is not None:
            zone = _object(obj["timeZone"])
            values["timeZone"] = {k: zone[k] for k in ("id", "version") if k in zone}
        if obj.get("containingPlaces") is not None:
            values["containingPlaces"]=[{"id":p["id"],"displayName":p.get("displayName",{}).get("text"),"isMall":p.get("isMall",False)} for p in obj["containingPlaces"]]
        level = obj.get("priceLevel")
        if level is not None:
            values["priceLevel"] = None if level == "PRICE_LEVEL_UNSPECIFIED" else PRICE_LEVELS[level]
        values = {key: value for key, value in values.items() if value is not None}
        if existing is None:
            payload = {"id": identity, "activity": activity, "provider": "google_places",
                       "evidence": "provider_supplied", **values,
                       "observedAt": {".".join(path): when for path, _ in _supplied(values)}}
        else:
            # Revalidation prevents mutated model instances bypassing the contract.
            existing = VenueFacts.model_validate(existing.model_dump())
            if (existing.provider, existing.id, existing.activity, existing.evidence) != (
                    "google_places", identity, ActivityType(activity), "provider_supplied"):
                raise ValueError("Update identity/context mismatch")
            # Validate even older updates, without erasing nested missing fields.
            combined = existing.model_dump()
            incoming = list(_supplied(values))
            for path, value in incoming:
                _assign(combined, path, value)
            validated = VenueFacts.model_validate(combined).model_dump()
            payload = existing.model_dump()
            for path, _ in incoming:
                key = ".".join(path)
                value = validated
                for part in path:
                    value = value[part]
                previous_time = existing.observedAt.get(key)
                if previous_time is None or when >= previous_time:
                    if key == "attributions":
                        # Required credits survive partial enrichment; do not drop old credits.
                        previous = payload.get(key) or []
                        value = previous + [item for item in value if item not in previous]
                    _assign(payload, path, value)
                    payload["observedAt"][key] = when
        return VenueFacts.model_validate(payload)
    except (KeyError, TypeError, ValueError, OverflowError, ValidationError):
        raise NormalizationError("Google venue data is incomplete or invalid.") from None


def normalize_google_places(records: list[dict], activity: ActivityType | str, *,
                            observed_at: datetime | None = None) -> tuple[list[VenueFacts], int]:
    """Convert an already bounded collection, isolating invalid records, in order.

    No deduplication, ranking, refill requests or error payload logging.
    """
    if not isinstance(records, list):
        raise NormalizationError("Expected a venue collection.")
    activity = ActivityType(activity)
    when = observed_at if observed_at is not None else datetime.now(timezone.utc)
    venues, rejected = [], 0
    for record in records:
        try:
            venues.append(normalize_google_place(record, activity, observed_at=when))
        except NormalizationError:
            rejected += 1
    return venues, rejected


def normalize_discovery_candidates(result, activity: ActivityType | str, *, observed_at=None):
    """Offline bridge from Task 40's minimal transport DTO; no new API request.

    Use raw Place input above for richer authorized future responses; Task 40's
    DTO deliberately retains only its six-field discovery contract.
    """
    records = [{"id": candidate.provider_id, "displayName": {"text": candidate.display_name},
                "formattedAddress": candidate.address, "location": candidate.coordinates.model_dump(),
                "attributions": candidate.attributions, "types": candidate.types, "containingPlaces": candidate.containingPlaces, "primaryType": candidate.primaryType,
                "rating": candidate.rating, "userRatingCount": candidate.userRatingCount} for candidate in result.candidates]
    return normalize_google_places(records, activity, observed_at=observed_at)
