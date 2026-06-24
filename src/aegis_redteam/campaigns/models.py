from __future__ import annotations

import re
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from aegis_redteam.models import CanarySeed, Expected

_SAFE_SLUG_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")


_SUPPORTED_MOCK_RESPONSE_MODES = {
    "default",
    "base64_first_honeytoken",
    "partial_first_honeytoken",
    "leak_first_honeytoken",
}


class CampaignDetectorExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    should_trigger: bool


class CampaignVariant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    prompt: str
    mock_response_mode: str
    detectors: list[CampaignDetectorExpectation] = Field(min_length=1)
    min_final_action: str
    seed_canary: CanarySeed | None = None
    expected: Expected | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if _SAFE_SLUG_PATTERN.fullmatch(value) is None:
            raise ValueError("campaign variant name must be a filesystem-safe slug")
        return value

    @field_validator("mock_response_mode")
    @classmethod
    def validate_mock_response_mode(cls, value: str) -> str:
        if value not in _SUPPORTED_MOCK_RESPONSE_MODES:
            raise ValueError(f"unsupported mock_response_mode: {value}")
        return value


class Campaign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    credential: str
    reset_before_run: bool
    variants: list[CampaignVariant] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if _SAFE_SLUG_PATTERN.fullmatch(value) is None:
            raise ValueError("campaign name must be a filesystem-safe slug")
        return value

    @model_validator(mode="after")
    def validate_unique_variant_names(self) -> Self:
        names = [variant.name for variant in self.variants]
        duplicate_names = sorted({name for name in names if names.count(name) > 1})
        if len(duplicate_names) > 0:
            raise ValueError(f"duplicate campaign variant name: {duplicate_names[0]}")
        return self
