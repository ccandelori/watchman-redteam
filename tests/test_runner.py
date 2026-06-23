from __future__ import annotations

import pytest

from aegis_redteam.models import Expected, PolicyDecision, PolicyExpectation, RedteamResult, Scenario, Turn, TurnResult


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
