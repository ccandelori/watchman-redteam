from __future__ import annotations

from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class DetectorExpectation(BaseModel):
    name: str
    should_trigger: bool


class PolicyExpectation(BaseModel):
    min_final_action: str


class Expected(BaseModel):
    detectors: List[DetectorExpectation] = Field(default_factory=list)
    policy: Optional[PolicyExpectation] = None


class TargetControls(BaseModel):
    mock_response_mode: Optional[str] = None
    reset_before_run: bool = False
    session_id: Optional[str] = None


class Scenario(BaseModel):
    name: str
    description: Optional[str] = None
    target_controls: TargetControls = Field(default_factory=TargetControls)
    turns: List[Turn]
    expected: Optional[Expected] = None


class DetectorResult(BaseModel):
    name: str
    evidence: Dict[str, Any] = Field(default_factory=dict)


class PolicyDecision(BaseModel):
    final_action: str
    reason: Optional[str] = None
    triggered_detectors: List[str] = Field(default_factory=list)


class TurnResult(BaseModel):
    turn_index: int
    request: Turn
    response_status: int
    assistant_content: Optional[str] = None
    aegis_metadata: Dict[str, Any] = Field(default_factory=dict)
    detector_results: List[DetectorResult] = Field(default_factory=list)
    policy_decision: Optional[PolicyDecision] = None
    latency_ms: Optional[int] = None


class RedteamResult(BaseModel):
    run_id: str
    scenario_name: str
    target_url: str
    started_at: str
    finished_at: str
    passed: bool
    turn_results: List[TurnResult] = Field(default_factory=list)
    failures: List[str] = Field(default_factory=list)
    raw_responses: List[Dict[str, Any]] = Field(default_factory=list)
