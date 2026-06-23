from __future__ import annotations

from pathlib import Path

import pytest

from aegis_redteam.campaigns.baseline import promote_campaign_baseline
from aegis_redteam.models import RedteamResult
from aegis_redteam.results import load_results_jsonl, write_results_jsonl


def make_result(scenario_name: str, passed: bool) -> RedteamResult:
    return RedteamResult(
        run_id=f"run-{scenario_name}",
        scenario_name=scenario_name,
        target_url="http://localhost:8000",
        started_at="2026-06-23T00:00:00Z",
        finished_at="2026-06-23T00:00:01Z",
        passed=passed,
    )


def test_promote_campaign_baseline_canonicalizes_volatile_run_fields(tmp_path: Path) -> None:
    source_path = tmp_path / "results" / "campaign.jsonl"
    baseline_path = tmp_path / "baselines" / "credential_exfil.jsonl"
    source_result = RedteamResult(
        run_id="runtime-uuid",
        scenario_name="credential_exfil_v1__direct_base64",
        target_url="http://127.0.0.1:9812",
        started_at="2026-06-23T22:38:28Z",
        finished_at="2026-06-23T22:38:29Z",
        passed=True,
        failures=[],
    )
    write_results_jsonl([source_result], source_path)

    promote_campaign_baseline(source_path, baseline_path, force=False)

    promoted = load_results_jsonl(baseline_path)[0]
    assert promoted.run_id == "baseline:credential_exfil_v1__direct_base64"
    assert promoted.target_url == "baseline://campaign-regression"
    assert promoted.started_at == "1970-01-01T00:00:00Z"
    assert promoted.finished_at == "1970-01-01T00:00:00Z"
    assert promoted.scenario_name == "credential_exfil_v1__direct_base64"
    assert promoted.passed is True


def test_promote_campaign_baseline_writes_validated_results(tmp_path: Path) -> None:
    source_path = tmp_path / "results" / "campaign.jsonl"
    baseline_path = tmp_path / "baselines" / "credential_exfil.jsonl"
    source_results = [
        make_result("credential_exfil_v1__direct_base64", True),
        make_result("credential_exfil_v1__semantic_text_leak", True),
    ]
    write_results_jsonl(source_results, source_path)

    promotion = promote_campaign_baseline(source_path, baseline_path, force=False)

    loaded = load_results_jsonl(baseline_path)
    assert promotion.source_path == source_path
    assert promotion.baseline_path == baseline_path
    assert promotion.result_count == 2
    assert promotion.overwritten is False
    assert [result.scenario_name for result in loaded] == [
        "credential_exfil_v1__direct_base64",
        "credential_exfil_v1__semantic_text_leak",
    ]


def test_promote_campaign_baseline_rejects_existing_baseline_without_force(tmp_path: Path) -> None:
    source_path = tmp_path / "campaign.jsonl"
    baseline_path = tmp_path / "baseline.jsonl"
    write_results_jsonl([make_result("new", True)], source_path)
    baseline_path.write_text("existing baseline\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="already exists"):
        promote_campaign_baseline(source_path, baseline_path, force=False)

    assert baseline_path.read_text(encoding="utf-8") == "existing baseline\n"


def test_promote_campaign_baseline_overwrites_existing_baseline_with_force(tmp_path: Path) -> None:
    source_path = tmp_path / "campaign.jsonl"
    baseline_path = tmp_path / "baseline.jsonl"
    write_results_jsonl([make_result("forced", True)], source_path)
    baseline_path.write_text("stale baseline\n", encoding="utf-8")

    promotion = promote_campaign_baseline(source_path, baseline_path, force=True)

    assert promotion.overwritten is True
    assert [result.scenario_name for result in load_results_jsonl(baseline_path)] == ["forced"]


def test_promote_campaign_baseline_rejects_empty_source(tmp_path: Path) -> None:
    source_path = tmp_path / "empty.jsonl"
    baseline_path = tmp_path / "baseline.jsonl"
    source_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="contains no results"):
        promote_campaign_baseline(source_path, baseline_path, force=False)

    assert not baseline_path.exists()
