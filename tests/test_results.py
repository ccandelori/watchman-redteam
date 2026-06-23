from __future__ import annotations

from pathlib import Path

import pytest

from aegis_redteam.models import RedteamResult
from aegis_redteam.results import load_results_jsonl


def make_result(scenario_name: str, passed: bool) -> RedteamResult:
    return RedteamResult(
        run_id=f"run-{scenario_name}",
        scenario_name=scenario_name,
        target_url="http://localhost:8000",
        started_at="2026-06-23T00:00:00Z",
        finished_at="2026-06-23T00:00:01Z",
        passed=passed,
    )


def test_load_results_jsonl_returns_typed_results_in_file_order(tmp_path: Path) -> None:
    path = tmp_path / "results.jsonl"
    records = [make_result("first", True), make_result("second", False)]
    path.write_text("".join(f"{record.model_dump_json()}\n" for record in records), encoding="utf-8")

    loaded = load_results_jsonl(path)

    assert [result.scenario_name for result in loaded] == ["first", "second"]
    assert [result.passed for result in loaded] == [True, False]


def test_load_results_jsonl_includes_path_and_line_for_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "results.jsonl"
    valid_record = make_result("valid", True)
    path.write_text(f"{valid_record.model_dump_json()}\nnot json\n", encoding="utf-8")

    with pytest.raises(ValueError, match="results.jsonl:2"):
        load_results_jsonl(path)
