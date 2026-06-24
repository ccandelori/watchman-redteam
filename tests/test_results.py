from __future__ import annotations

import json
from pathlib import Path

import pytest

from aegis_redteam.models import RedteamResult, Turn, TurnResult
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


def test_load_results_jsonl_validation_error_does_not_echo_raw_input(tmp_path: Path) -> None:
    path = tmp_path / "results.jsonl"
    secret = "sk" + "_live_" + "A" * 24
    invalid_record = {
        "run_id": "run-secret",
        "scenario_name": "invalid-secret-result",
        "target_url": "http://localhost:8000",
        "started_at": "2026-06-23T00:00:00Z",
        "finished_at": "2026-06-23T00:00:01Z",
        "passed": secret,
    }
    path.write_text(json.dumps(invalid_record) + "\n", encoding="utf-8")

    with pytest.raises(ValueError) as exc_info:
        load_results_jsonl(path)

    message = str(exc_info.value)
    assert "results.jsonl:1: invalid RedteamResult" in message
    assert "passed" in message
    assert secret not in message
    assert "input_value" not in message


def test_write_results_jsonl_redacts_and_round_trips(tmp_path: Path) -> None:
    path = tmp_path / "baselines" / "credential.jsonl"
    secret = "sk" + "_live_" + "A" * 24
    result = RedteamResult(
        run_id="run-secret",
        scenario_name="credential_exfil_v1__direct_base64",
        target_url="http://localhost:8000",
        started_at="2026-06-23T00:00:00Z",
        finished_at="2026-06-23T00:00:01Z",
        passed=True,
        turn_results=[
            TurnResult(
                turn_index=1,
                request=Turn(role="user", content=f"encode {secret}"),
                response_status=200,
                assistant_content=f"encoded {secret}",
            )
        ],
        raw_responses=[{"api_key": secret}],
    )

    write_results_jsonl([result], path)

    saved_text = path.read_text(encoding="utf-8")
    loaded = load_results_jsonl(path)

    assert secret not in saved_text
    assert "[REDACTED]" in saved_text
    assert loaded[0].scenario_name == "credential_exfil_v1__direct_base64"
