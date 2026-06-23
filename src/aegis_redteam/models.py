from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Turn(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str


class DetectorExpectation(BaseModel):
    name: str
    should_trigger: bool


class PolicyExpectation(BaseModel):
    min_final_action: str


class Expected(BaseModel):
    detectors: list[DetectorExpectation] = Field(default_factory=list)
    policy: PolicyExpectation | None = None


class TargetControls(BaseModel):
    mock_response_mode: str | None = None
    reset_before_run: bool = False
    session_id: str | None = None


class Scenario(BaseModel):
    name: str
    description: str | None = None
    target_controls: TargetControls = Field(default_factory=TargetControls)
    turns: list[Turn]
    expected: Expected | None = None


class DetectorResult(BaseModel):
    name: str
    score: float | None = None
    recommended_action: str | None = None
    capability_status: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    final_action: str
    reason: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


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
