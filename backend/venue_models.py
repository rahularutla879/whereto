"""Canonical physical-place facts. No scheduling, provider I/O or persistence."""
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AfterValidator, AwareDatetime, ConfigDict, Field, HttpUrl, StringConstraints, field_validator, model_validator

from backend.models import ContractModel, Nonblank, OutingDate, VenueIdentity

Number = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Integer = Annotated[int, Field(strict=True)]


def public_url(value):
    if value.username is not None or value.password is not None:
        raise ValueError("URLs must not contain credentials")
    return value


WebUrl = Annotated[HttpUrl, AfterValidator(public_url)]


class Coordinates(ContractModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, frozen=True)
    latitude: Annotated[Number, Field(ge=-90, le=90)]
    longitude: Annotated[Number, Field(ge=-180, le=180)]


class Attribution(ContractModel):
    provider: Nonblank | None = None
    uri: WebUrl | None = None

    @model_validator(mode="after")
    def useful(self):
        if self.provider is None and self.uri is None:
            raise ValueError("Attribution needs a provider or URI")
        return self


class HoursPoint(ContractModel):
    day: Annotated[Integer, Field(ge=0, le=6)]
    hour: Annotated[Integer, Field(ge=0, le=23)]
    minute: Annotated[Integer, Field(ge=0, le=59)]
    date: OutingDate | None = None
    truncated: bool | None = Field(default=None, strict=True)

    @model_validator(mode="after")
    def matching_weekday(self):
        if self.date is not None and (self.date.weekday() + 1) % 7 != self.day:
            raise ValueError("Hours date and weekday disagree")
        return self


class HoursPeriod(ContractModel):
    open: HoursPoint
    close: HoursPoint | None = None  # Preserve open-ended/24-hour provider periods.

    @model_validator(mode="after")
    def chronological_dates(self):
        if self.close is not None and self.open.date is not None and self.close.date is not None:
            start = (self.open.date, self.open.hour, self.open.minute)
            end = (self.close.date, self.close.hour, self.close.minute)
            if end <= start:
                raise ValueError("Dated period must close after opening")
        return self


class OpeningHours(ContractModel):
    # None: absent; []: explicitly supplied no periods. Never infer availability.
    periods: list[HoursPeriod] | None = None
    weekdayDescriptions: list[Nonblank] | None = None
    specialDays: list[OutingDate] | None = None
    openNow: bool | None = Field(default=None, strict=True)
    nextOpenTime: AwareDatetime | None = None
    nextCloseTime: AwareDatetime | None = None

    @field_validator("nextOpenTime", "nextCloseTime", mode="before")
    @classmethod
    def timestamp_format(cls, value):
        if value is not None and not isinstance(value, datetime) and not (
                isinstance(value, str) and "T" in value):
            raise ValueError("Use a timezone-aware RFC 3339 timestamp")
        return value


class PlaceTimeZone(ContractModel):
    id: Nonblank
    version: Nonblank | None = None

    @field_validator("id")
    @classmethod
    def known_zone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Unknown IANA timezone") from None
        return value


class PriceAmount(ContractModel):
    currency: Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
    amount: Annotated[Decimal, Field(ge=0, allow_inf_nan=False)]


class PriceRange(ContractModel):
    start: PriceAmount | None = None
    end: PriceAmount | None = None

    @model_validator(mode="after")
    def consistent(self):
        if self.start is not None and self.end is not None:
            if self.start.currency != self.end.currency or self.start.amount > self.end.amount:
                raise ValueError("Price range must use one currency and ordered bounds")
        return self


class VenueFacts(VenueIdentity):
    """Physical venue, including event buildings; never an event occurrence.

    id is the original provider ID, scoped by provider. Category is caller-supplied
    discovery context, not provider-confirmed relevance. All detail facts are nullable.
    """
    provider: Nonblank
    evidence: Literal["provider_supplied", "fictional", "estimated", "unknown"]
    resourceName: Nonblank | None = None
    address: Nonblank | None = None
    coordinates: Coordinates | None = None
    providerTypes: list[Nonblank] | None = None
    rating: Annotated[Number, Field(ge=1, le=5)] | None = None
    ratingCount: Annotated[Integer, Field(ge=0)] | None = None
    regularOpeningHours: OpeningHours | None = None
    currentOpeningHours: OpeningHours | None = None
    websiteUrl: WebUrl | None = None
    mapsUrl: WebUrl | None = None
    priceLevel: Literal["free", "inexpensive", "moderate", "expensive", "very_expensive"] | None = None
    priceRange: PriceRange | None = None  # Provider indicator; NOT USD/person or a ticket quote.
    timeZone: PlaceTimeZone | None = None
    utcOffsetMinutes: Annotated[Integer, Field(ge=-840, le=840)] | None = None
    attributions: list[Attribution] | None = None
    # Local receipt times by scalar/list path, not provider verification/freshness guarantees.
    observedAt: dict[str, AwareDatetime] = Field(default_factory=dict)
