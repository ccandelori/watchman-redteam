from __future__ import annotations

from aegis_redteam.compare import compare_results, count_changed_baseline_scenarios
from aegis_redteam.models import DetectorResult, PolicyDecision, RedteamResult, Turn, TurnResult


def make_result(scenario_name: str, passed: bool) -> RedteamResult:
    return RedteamResult(
        run_id=f"run-{scenario_name}",
        scenario_name=scenario_name,
        target_url="http://localhost:8000",
        started_at="2026-06-23T00:00:00Z",
        finished_at="2026-06-23T00:00:01Z",
        passed=passed,
    )


def make_observed_result(
    scenario_name: str,
    detector_name: str,
    final_action: str,
    triggered_detectors: list[str],
) -> RedteamResult:
    return RedteamResult(
        run_id=f"run-{scenario_name}",
        scenario_name=scenario_name,
        target_url="http://localhost:8000",
        started_at="2026-06-23T00:00:00Z",
        finished_at="2026-06-23T00:00:01Z",
        passed=True,
        turn_results=[
            TurnResult(
                turn_index=1,
                request=Turn(role="user", content="hello"),
                response_status=200,
                assistant_content="runtime text",
                aegis_metadata={"trace_id": "runtime"},
                detector_results=[DetectorResult(name=detector_name, evidence={"runtime": "evidence"})],
                policy_decision=PolicyDecision(
                    final_action=final_action,
                    reason="runtime reason",
                    triggered_detectors=triggered_detectors,
                ),
                latency_ms=17,
            )
        ],
        raw_responses=[{"id": "runtime"}],
    )


def test_compare_results_counts_status_changes_and_new_scenarios() -> None:
    current = [
        make_result("regressed", False),
        make_result("improved", True),
        make_result("new", True),
    ]
    baseline = [
        make_result("regressed", True),
        make_result("improved", False),
    ]

    assert compare_results(current, baseline) == (1, 1, 1)


def test_compare_results_counts_missing_baseline_pass_as_regression() -> None:
    current = [make_result("still-present", True)]
    baseline = [
        make_result("still-present", True),
        make_result("removed-critical-scenario", True),
    ]

    assert compare_results(current, baseline) == (1, 0, 0)


def test_count_changed_baseline_scenarios_detects_detector_results_drift() -> None:
    current = [make_observed_result("stable-pass", "text_canary", "block", ["text_canary"])]
    baseline = [make_observed_result("stable-pass", "encoded_canary", "block", ["encoded_canary"])]

    assert compare_results(current, baseline) == (0, 0, 0)
    assert count_changed_baseline_scenarios(current, baseline) == 1


def test_count_changed_baseline_scenarios_detects_policy_decision_drift() -> None:
    current = [make_observed_result("stable-pass", "encoded_canary", "warn", ["encoded_canary"])]
    baseline = [make_observed_result("stable-pass", "encoded_canary", "block", ["encoded_canary"])]

    assert compare_results(current, baseline) == (0, 0, 0)
    assert count_changed_baseline_scenarios(current, baseline) == 1


def test_count_changed_baseline_scenarios_ignores_volatile_runtime_fields() -> None:
    current = [
        make_observed_result("stable-pass", "encoded_canary", "block", ["encoded_canary"]).model_copy(
            update={
                "run_id": "runtime-run",
                "target_url": "http://127.0.0.1:9812",
                "started_at": "2026-06-23T22:38:28Z",
                "finished_at": "2026-06-23T22:38:29Z",
            }
        )
    ]
    baseline = [
        make_observed_result("stable-pass", "encoded_canary", "block", ["encoded_canary"]).model_copy(
            update={
                "run_id": "baseline:stable-pass",
                "target_url": "baseline://campaign-regression",
                "started_at": "1970-01-01T00:00:00Z",
                "finished_at": "1970-01-01T00:00:00Z",
            }
        )
    ]

    assert count_changed_baseline_scenarios(current, baseline) == 0
