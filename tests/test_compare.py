from __future__ import annotations

from aegis_redteam.compare import compare_results
from aegis_redteam.models import RedteamResult


def make_result(scenario_name: str, passed: bool) -> RedteamResult:
    return RedteamResult(
        run_id=f"run-{scenario_name}",
        scenario_name=scenario_name,
        target_url="http://localhost:8000",
        started_at="2026-06-23T00:00:00Z",
        finished_at="2026-06-23T00:00:01Z",
        passed=passed,
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
