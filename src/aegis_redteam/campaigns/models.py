from __future__ import annotations

from typing import Self

from pydantic import BaseModel, Field, model_validator


class CampaignVariant(BaseModel):
    name: str
    prompt: str
    mock_response_mode: str
    detector: str
    min_final_action: str


class Campaign(BaseModel):
    name: str
    credential: str
    reset_before_run: bool
    variants: list[CampaignVariant] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_variant_names(self) -> Self:
        names = [variant.name for variant in self.variants]
        duplicate_names = sorted({name for name in names if names.count(name) > 1})
        if len(duplicate_names) > 0:
            raise ValueError(f"duplicate campaign variant name: {duplicate_names[0]}")
        return self
