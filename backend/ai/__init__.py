"""Standalone AI boundary for Task 30; not used by the planning API yet."""

import os
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from backend.models import GroupSize, Money, Nonblank, OutingDate


class Interpretation(BaseModel):
    """Partial extraction, never a resolved planning request or verified facts.

    Activity phrases remain unnormalized. Task 31 must handle supported-category
    mapping, ambiguity, defaults, overrides and semantic checks before planning.
    Required nullable fields distinguish missing information from model defaults.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    activities: list[Nonblank]
    people: GroupSize | None
    budget_per_person: Money | None
    date: OutingDate | None
    location: Nonblank | None
    preferences: list[Nonblank]


class AIError(RuntimeError):
    """Safe, actionable error from the AI boundary."""


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
