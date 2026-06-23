from __future__ import annotations

from aegis_redteam.evaluator import evaluate_result
from aegis_redteam.models import (
    DetectorResult,
    PolicyDecision,
    RedteamResult,
    Scenario,
    Turn,
    TurnResult,
)


def test_detector_expectation_passes_when_matching_detector_triggers() -> None:
    scenario = Scenario(
        name="encoded",
        turns=[Turn(role="user", content="leak")],
        expected={"detectors": [{"name": "encoded_canary", "should_trigger": True}]},
    )
    result = _result(
        detector_results=[
            DetectorResult(name="encoded_canary", score=1.0, recommended_action="block")
        ],
        policy_action="block",
    )

    assert evaluate_result(result, scenario) is True


def test_detector_expectation_does_not_treat_allow_result_as_triggered() -> None:
    scenario = Scenario(
        name="safe",
        turns=[Turn(role="user", content="safe")],
        expected={"detectors": [{"name": "encoded_canary", "should_trigger": False}]},
    )
    result = _result(
        detector_results=[
            DetectorResult(name="encoded_canary", score=0.0, recommended_action="allow")
        ],
        policy_action="allow",
    )

    assert evaluate_result(result, scenario) is True


def test_policy_expectation_uses_strongest_observed_action() -> None:
    scenario = Scenario(
        name="drip",
        turns=[
            Turn(role="user", content="one"),
            Turn(role="user", content="two"),
            Turn(role="user", content="three"),
        ],
        expected={"policy": {"min_final_action": "block"}},
    )
    result = RedteamResult(
        run_id="run-1",
        scenario_name="drip",
        target_url="http://localhost:8000",
        started_at="2026-06-23T00:00:00Z",
        finished_at="2026-06-23T00:00:01Z",
        passed=True,
        turn_results=[
            _turn_result(turn_index=1, policy_action="allow"),
            _turn_result(turn_index=2, policy_action="warn"),
            _turn_result(turn_index=3, policy_action="block"),
        ],
    )

    assert evaluate_result(result, scenario) is True


def test_policy_expectation_fails_unknown_action() -> None:
    scenario = Scenario(
        name="unknown",
        turns=[Turn(role="user", content="one")],
        expected={"policy": {"min_final_action": "block"}},
    )
    result = _result(detector_results=[], policy_action="mystery")

    assert evaluate_result(result, scenario) is False


def test_result_failures_fail_evaluation() -> None:
    scenario = Scenario(name="failure", turns=[Turn(role="user", content="one")])
    result = _result(detector_results=[], policy_action="allow")
    result.failures.append("network failed")

    assert evaluate_result(result, scenario) is False


def _result(detector_results: list[DetectorResult], policy_action: str) -> RedteamResult:
    return RedteamResult(
        run_id="run-1",
        scenario_name="scenario",
        target_url="http://localhost:8000",
        started_at="2026-06-23T00:00:00Z",
        finished_at="2026-06-23T00:00:01Z",
        passed=True,
        turn_results=[
            _turn_result(
                turn_index=1, detector_results=detector_results, policy_action=policy_action
            )
        ],
    )


def _turn_result(
    turn_index: int,
    policy_action: str,
    detector_results: list[DetectorResult] | None = None,
) -> TurnResult:
    return TurnResult(
        turn_index=turn_index,
        request=Turn(role="user", content="request"),
        response_status=200,
        detector_results=detector_results or [],
        policy_decision=PolicyDecision(final_action=policy_action),
    )
