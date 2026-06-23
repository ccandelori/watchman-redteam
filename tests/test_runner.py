from __future__ import annotations

import pytest

from aegis_redteam.models import (
    Expected,
    PolicyDecision,
    PolicyExpectation,
    RedteamResult,
    Scenario,
    Turn,
    TurnResult,
)


class FakeTarget:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    def run_scenario(self, scenario: Scenario) -> RedteamResult:
        return RedteamResult(
            run_id="run-1",
            scenario_name=scenario.name,
            target_url=self.base_url,
            started_at="2026-06-23T00:00:00Z",
            finished_at="2026-06-23T00:00:01Z",
            passed=True,
            turn_results=[
                TurnResult(
                    turn_index=1,
                    request=scenario.turns[0],
                    response_status=200,
                    policy_decision=PolicyDecision(final_action="allow"),
                )
            ],
        )

    def close(self) -> None:
        return


class CloseTrackingTarget(FakeTarget):
    closed: bool = False

    def close(self) -> None:
        type(self).closed = True


def test_run_scenarios_appends_evaluator_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    from aegis_redteam import runner

    scenario = Scenario(
        name="runner-policy-failure",
        turns=[Turn(role="user", content="leak credential")],
        expected=Expected(policy=PolicyExpectation(min_final_action="block")),
    )

    monkeypatch.setattr(runner, "HttpAegisTarget", FakeTarget)

    result = runner.run_scenarios([scenario], "http://fixture")[0]

    assert result.passed is False
    assert result.failures == [
        "Policy expectation failed for runner-policy-failure: expected minimum action block observed allow on turn 1"
    ]


def test_run_scenarios_closes_target_when_evaluation_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aegis_redteam import runner

    scenario = Scenario(
        name="invalid-policy-expectation",
        turns=[Turn(role="user", content="leak credential")],
        expected=Expected(policy=PolicyExpectation(min_final_action="quarantine")),
    )

    CloseTrackingTarget.closed = False
    monkeypatch.setattr(runner, "HttpAegisTarget", CloseTrackingTarget)

    with pytest.raises(ValueError, match="Unknown expected policy action"):
        runner.run_scenarios([scenario], "http://fixture")

    assert CloseTrackingTarget.closed is True
