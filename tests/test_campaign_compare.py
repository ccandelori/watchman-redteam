from __future__ import annotations

from pathlib import Path

from aegis_redteam.campaigns.compare import compare_campaign_results
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


def write_results(path: Path, results: list[RedteamResult]) -> None:
    path.write_text("".join(f"{result.model_dump_json()}\n" for result in results), encoding="utf-8")


def test_compare_campaign_results_returns_existing_compare_counts(tmp_path: Path) -> None:
    current_path = tmp_path / "current.jsonl"
    baseline_path = tmp_path / "baseline.jsonl"
    write_results(
        current_path,
        [
            make_result("credential_exfil_v1__regressed", False),
            make_result("credential_exfil_v1__improved", True),
            make_result("credential_exfil_v1__new", True),
        ],
    )
    write_results(
        baseline_path,
        [
            make_result("credential_exfil_v1__regressed", True),
            make_result("credential_exfil_v1__improved", False),
        ],
    )

    comparison = compare_campaign_results(current_path, baseline_path)

    assert comparison.regressions == 1
    assert comparison.improvements == 1
    assert comparison.new_scenarios == 1
