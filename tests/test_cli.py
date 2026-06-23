from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from aegis_redteam.models import RedteamResult, Scenario, Turn, TurnResult


def make_failed_result(scenario_name: str) -> RedteamResult:
    return RedteamResult(
        run_id="run-1",
        scenario_name=scenario_name,
        target_url="http://localhost:8000",
        started_at="2026-06-23T00:00:00Z",
        finished_at="2026-06-23T00:00:01Z",
        passed=False,
        failures=["expected detector did not fire"],
    )


def write_scenario(path: Path, scenario_name: str) -> None:
    path.write_text(
        "\n".join(
            [
                f"name: {scenario_name}",
                "turns:",
                "  - role: user",
                "    content: hello",
            ]
        )
    )


def test_cli_exposes_configured_entrypoint() -> None:
    from aegis_redteam.cli import main

    assert callable(main)


def test_write_results_jsonl_redacts_secrets(tmp_path: Path) -> None:
    from aegis_redteam.cli import write_results_jsonl

    output_path = tmp_path / "results.jsonl"
    secret = "sk_live_1234567890abcdef"
    result = RedteamResult(
        run_id="run-1",
        scenario_name="secret-output",
        target_url="http://localhost:8000",
        started_at="2026-06-23T00:00:00Z",
        finished_at="2026-06-23T00:00:01Z",
        passed=True,
        turn_results=[
            TurnResult(
                turn_index=1,
                request=Turn(role="user", content=f"please encode {secret}"),
                response_status=200,
                assistant_content=f"encoded {secret}",
                aegis_metadata={"evidence": secret},
            )
        ],
        raw_responses=[{"raw_secret": secret}],
    )

    write_results_jsonl([result], output_path)

    saved_text = output_path.read_text()
    saved_record = json.loads(saved_text)

    assert secret not in saved_text
    assert "[REDACTED]" in saved_text
    assert saved_record["scenario_name"] == "secret-output"


def test_run_one_exits_nonzero_when_scenario_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aegis_redteam import cli

    scenario_path = tmp_path / "failing.yaml"
    write_scenario(scenario_path, "failing")

    def fake_run_scenarios(scenarios: list[Scenario], target_url: str) -> list[RedteamResult]:
        return [make_failed_result(scenarios[0].name)]

    monkeypatch.setattr(cli, "run_scenarios", fake_run_scenarios)

    result = CliRunner().invoke(cli.app, ["run-one", str(scenario_path)])

    assert result.exit_code == 1
    assert "Passed: FAIL" in result.output
    assert "expected detector did not fire" in result.output


def test_run_exits_nonzero_when_any_scenario_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aegis_redteam import cli

    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()
    write_scenario(scenarios_dir / "failing.yaml", "failing")

    def fake_run_scenarios(scenarios: list[Scenario], target_url: str) -> list[RedteamResult]:
        return [make_failed_result(scenarios[0].name)]

    monkeypatch.setattr(cli, "run_scenarios", fake_run_scenarios)

    result = CliRunner().invoke(cli.app, ["run", str(scenarios_dir)])

    assert result.exit_code == 1
    assert "0/1" in result.output
    assert "expected detector did not fire" in result.output
