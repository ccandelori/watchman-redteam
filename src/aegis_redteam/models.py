from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class Turn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str


class DetectorExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    should_trigger: bool


class PolicyExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    min_final_action: str


class EgressExpectation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assistant_content: str | None = None
    forbidden_response_substrings: list[str] = Field(default_factory=list)
    inspect_audit: bool = False
    forbidden_audit_substrings: list[str] = Field(default_factory=list)


class Expected(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detectors: list[DetectorExpectation] = Field(default_factory=list)
    policy: PolicyExpectation | None = None
    egress: EgressExpectation | None = None


class CanarySeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot_name: str
    credential_type: str
    turn_index: int


class TargetControls(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mock_response_mode: str | None = None
    reset_before_run: bool = False
    session_id: str | None = None
    seed_canary: CanarySeed | None = None
    history_mode: Literal["latest_user", "full_history"] = "latest_user"


class Scenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    target_controls: TargetControls = Field(default_factory=TargetControls)
    turns: list[Turn] = Field(min_length=1)
    expected: Expected | None = None


class DetectorResult(BaseModel):
    name: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    final_action: str
    reason: str | None = None
    triggered_detectors: list[str] = Field(default_factory=list)


class TurnResult(BaseModel):
    turn_index: int
    request: Turn
    response_status: int
    assistant_content: str | None = None
    aegis_metadata: dict[str, Any] = Field(default_factory=dict)
    detector_results: list[DetectorResult] = Field(default_factory=list)
    policy_decision: PolicyDecision | None = None
    latency_ms: int | None = None


class RedteamResult(BaseModel):
    run_id: str
    scenario_name: str
    target_url: str
    started_at: str
    finished_at: str
    passed: bool
    turn_results: list[TurnResult] = Field(default_factory=list)
    failures: list[str] = Field(default_factory=list)
    raw_responses: list[dict[str, Any]] = Field(default_factory=list)
