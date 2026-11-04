"""Provider-independent partial AI extraction for the interpretation service."""

import json
import os
from typing import Annotated, Protocol

from pydantic import BaseModel, ConfigDict, Field

from backend.models import (ActivityType, CostPreference, EndMinute, GroupSize, Money,
                            Nonblank, OutingDate, StartMinute, TransportationMode, TravelMinutes)
from backend.journey import Journey


class Interpretation(BaseModel):
    """Partial extraction, never a resolved planning request or verified facts.

    Activity phrases remain unnormalized. The interpretation service handles
    supported-category mapping, ambiguity, overrides and semantic guards.
    Required nullable fields distinguish missing information from model defaults.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, revalidate_instances="always")
    activities: Annotated[list[Annotated[Nonblank, Field(max_length=500)]], Field(strict=True, max_length=32)]
    people: GroupSize | None = None
    budget_per_person: Money | None
    date: OutingDate | None
    location: Annotated[Nonblank, Field(max_length=200)] | None
    preferences: Annotated[list[Annotated[Nonblank, Field(max_length=1000)]], Field(strict=True, max_length=32)]
    # Additive fields preserve the Task 30 provider method and original fields.
    suggested_activities: list[ActivityType] = Field(default_factory=list, strict=True, max_length=32)
    budget_group: Money | None = None
    currency: Annotated[Nonblank, Field(max_length=30)] | None = None
    travel_total_minutes: TravelMinutes | None = None
    travel_leg_minutes: TravelMinutes | None = None
    transport: TransportationMode | None = None
    cost: CostPreference | None = None
    date_expressions: Annotated[list[Annotated[Nonblank, Field(max_length=1000)]], Field(strict=True, max_length=32)] = Field(default_factory=list)
    time_expressions: Annotated[list[Annotated[Nonblank, Field(max_length=1000)]], Field(strict=True, max_length=32)] = Field(default_factory=list)
    start_time: StartMinute | None = None
    end_time: EndMinute | None = None
    uncertainties: Annotated[list[Annotated[Nonblank, Field(max_length=1000)]], Field(strict=True, max_length=32)] = Field(default_factory=list)
    journey: Journey | None = None


def parse_interpretation(content: str) -> Interpretation:
    """One JSON object; repeated keys are ambiguous even if the last value is valid."""
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Repeated JSON field")
            result[key] = value
        return result

    return Interpretation.model_validate(json.loads(content, object_pairs_hook=unique_object))


class AIError(RuntimeError):
    """Private diagnostic detail and a stable public category; never log content."""
    def __init__(self,message,code='llm_unavailable'):
        self.code=code
        super().__init__(message)


class AIProvider(Protocol):
    def interpret(self, text: str) -> Interpretation:
        """Extract stated information, leaving unknown quantities null."""
        ...


class AISettings(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    provider: Nonblank = "ollama"
    model: Nonblank = "qwen3:4b"
    base_url: Nonblank = "http://127.0.0.1:11434"
    timeout_seconds: float = Field(default=60, gt=0)

    @classmethod
    def from_env(cls) -> "AISettings":
        # Deliberately no dotenv dependency or automatic reading of local files.
        return cls(**{field: os.environ[name] for field, name in {
            "provider": "AI_PROVIDER", "model": "AI_MODEL",
            "base_url": "AI_BASE_URL", "timeout_seconds": "AI_TIMEOUT_SECONDS",
        }.items() if name in os.environ})


def create_provider(settings: AISettings | None = None) -> AIProvider:
    settings = settings if settings is not None else AISettings.from_env()
    if settings.provider != "ollama":
        raise AIError("Unsupported AI_PROVIDER; Task 30 supports only 'ollama'.")
    from backend.ai.ollama import OllamaProvider
    return OllamaProvider(settings)
