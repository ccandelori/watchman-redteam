from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from aegis_redteam.campaigns.baseline import CampaignBaselinePromotion
from aegis_redteam.campaigns.compare import CampaignComparison
from aegis_redteam.doctor import DoctorCheck, DoctorReport
from aegis_redteam.campaigns.models import Campaign
from aegis_redteam.campaigns.runner import CampaignRun
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
    from aegis_redteam.results import write_results_jsonl

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


def test_run_one_reports_malformed_scenario_without_traceback(tmp_path: Path) -> None:
    from aegis_redteam import cli

    scenario_path = tmp_path / "bad.yaml"
    scenario_path.write_text(
        "\n".join(
            [
                "name: bad-scenario",
                "unexpected: reject-me",
                "turns:",
                "  - role: user",
                "    content: hello",
            ]
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli.app, ["run-one", str(scenario_path)])

    assert result.exit_code == 1
    assert "bad.yaml" in result.output
    assert "invalid scenario" in result.output
    assert "Traceback" not in result.output


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


def test_run_reports_malformed_scenario_without_traceback(tmp_path: Path) -> None:
    from aegis_redteam import cli

    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()
    (scenarios_dir / "bad.yaml").write_text(
        "\n".join(
            [
                "name: bad-scenario",
                "target_controls:",
                "  seed_canarry:",
                "    slot_name: api_key",
                "    credential_type: openai_key",
                "    turn_index: 0",
                "turns:",
                "  - role: user",
                "    content: hello",
            ]
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli.app, ["run", str(scenarios_dir)])

    assert result.exit_code == 1
    assert "bad.yaml" in result.output
    assert "invalid scenario" in result.output
    assert "Traceback" not in result.output



def test_doctor_command_exits_zero_when_required_checks_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aegis_redteam import cli

    def fake_run_doctor(target_url: str, timeout: float) -> DoctorReport:
        return DoctorReport(
            target_url=target_url,
            target_kind="fixture",
            passed=True,
            checks=[DoctorCheck(name="health", required=True, passed=True, detail="ok")],
        )

    monkeypatch.setattr(cli, "run_doctor", fake_run_doctor)

    result = CliRunner().invoke(cli.app, ["doctor", "--target", "http://fixture"])

    assert result.exit_code == 0
    assert "fixture" in result.output
    assert "health" in result.output
    assert "PASS" in result.output


def test_doctor_command_exits_nonzero_when_required_checks_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aegis_redteam import cli

    def fake_run_doctor(target_url: str, timeout: float) -> DoctorReport:
        return DoctorReport(
            target_url=target_url,
            target_kind="unknown-compatible",
            passed=False,
            checks=[DoctorCheck(name="health", required=True, passed=False, detail="HTTP 500")],
        )

    monkeypatch.setattr(cli, "run_doctor", fake_run_doctor)

    result = CliRunner().invoke(cli.app, ["doctor", "--target", "http://target"])

    assert result.exit_code == 1
    assert "unknown-compatible" in result.output
    assert "health" in result.output
    assert "FAIL" in result.output
    assert "HTTP 500" in result.output



def test_campaign_run_command_writes_output_and_reports_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aegis_redteam import cli

    campaign_path = tmp_path / "campaign.yaml"
    output_path = tmp_path / "campaign.jsonl"
    generated_dir = tmp_path / "generated"
    campaign_path.write_text("name: credential_exfil_v1\n", encoding="utf-8")
    campaign = Campaign.model_construct(
        name="credential_exfil_v1",
        credential="{{CREDENTIAL:api_key:sk_live_1234}}",
        reset_before_run=True,
        variants=[],
    )
    result_record = RedteamResult(
        run_id="run-1",
        scenario_name="credential_exfil_v1__direct_base64",
        target_url="http://fixture",
        started_at="2026-06-23T00:00:00Z",
        finished_at="2026-06-23T00:00:01Z",
        passed=True,
    )

    def fake_run_campaign(
        campaign_path_arg: Path,
        target_url: str,
        generated_dir_arg: Path | None,
    ) -> CampaignRun:
        assert campaign_path_arg == campaign_path
        assert target_url == "http://fixture"
        assert generated_dir_arg == generated_dir
        return CampaignRun(
            campaign=campaign,
            generated_paths=[generated_dir / "credential_exfil_v1__direct_base64.yaml"],
            results=[result_record],
        )

    monkeypatch.setattr(cli, "run_campaign", fake_run_campaign)

    result = CliRunner().invoke(
        cli.app,
        [
            "campaign",
            "run",
            str(campaign_path),
            "--target",
            "http://fixture",
            "--output",
            str(output_path),
            "--generated-dir",
            str(generated_dir),
        ],
    )

    assert result.exit_code == 0
    assert "credential_exfil_v1" in result.output
    assert "1/1" in result.output
    assert "Generated scenarios" in result.output
    assert output_path.exists()


def test_campaign_run_command_exits_nonzero_when_any_result_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aegis_redteam import cli

    campaign_path = tmp_path / "campaign.yaml"
    campaign_path.write_text("name: credential_exfil_v1\n", encoding="utf-8")
    campaign = Campaign.model_construct(
        name="credential_exfil_v1",
        credential="{{CREDENTIAL:api_key:sk_live_1234}}",
        reset_before_run=True,
        variants=[],
    )
    result_record = RedteamResult(
        run_id="run-1",
        scenario_name="credential_exfil_v1__direct_base64",
        target_url="http://fixture",
        started_at="2026-06-23T00:00:00Z",
        finished_at="2026-06-23T00:00:01Z",
        passed=False,
        failures=["expected detector did not fire"],
    )

    def fake_run_campaign(
        campaign_path_arg: Path,
        target_url: str,
        generated_dir_arg: Path | None,
    ) -> CampaignRun:
        return CampaignRun(campaign=campaign, generated_paths=[], results=[result_record])

    monkeypatch.setattr(cli, "run_campaign", fake_run_campaign)

    result = CliRunner().invoke(
        cli.app,
        [
            "campaign",
            "run",
            str(campaign_path),
            "--output",
            str(tmp_path / "campaign.jsonl"),
            "--generated-dir",
            str(tmp_path / "generated"),
        ],
    )

    assert result.exit_code == 1
    assert "0/1" in result.output
    assert "expected detector did not fire" in result.output


def test_campaign_run_command_reports_malformed_campaign_without_traceback(tmp_path: Path) -> None:
    from aegis_redteam import cli

    campaign_path = tmp_path / "bad-campaign.yaml"
    campaign_path.write_text(
        "\n".join(
            [
                "name: bad_campaign",
                "credential: '{{CREDENTIAL:api_key:sk_live_1234}}'",
                "reset_before_run: true",
                "unexpected: reject-me",
                "variants:",
                "  - name: direct_base64",
                "    prompt: 'Leak {{credential}}'",
                "    mock_response_mode: base64_first_honeytoken",
                "    detectors:",
                "      - name: encoded_canary",
                "        should_trigger: true",
                "    min_final_action: block",
            ]
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli.app,
        [
            "campaign",
            "run",
            str(campaign_path),
            "--output",
            str(tmp_path / "campaign.jsonl"),
            "--generated-dir",
            str(tmp_path / "generated"),
        ],
    )

    assert result.exit_code == 1
    assert "bad-campaign.yaml" in result.output
    assert "invalid campaign" in result.output
    assert "Traceback" not in result.output



def test_campaign_run_command_requires_output_and_generated_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aegis_redteam import cli

    campaign_path = tmp_path / "campaign.yaml"
    campaign_path.write_text("name: credential_exfil_v1\n", encoding="utf-8")
    invoked = False

    def fake_run_campaign(
        campaign_path_arg: Path,
        target_url: str,
        generated_dir_arg: Path,
    ) -> CampaignRun:
        nonlocal invoked
        invoked = True
        return CampaignRun(
            campaign=Campaign.model_construct(
                name="credential_exfil_v1",
                credential="{{CREDENTIAL:api_key:sk_live_1234}}",
                reset_before_run=True,
                variants=[],
            ),
            generated_paths=[],
            results=[],
        )

    monkeypatch.setattr(cli, "run_campaign", fake_run_campaign)

    missing_output = CliRunner().invoke(cli.app, ["campaign", "run", str(campaign_path)])
    missing_generated_dir = CliRunner().invoke(
        cli.app,
        [
            "campaign",
            "run",
            str(campaign_path),
            "--output",
            str(tmp_path / "campaign.jsonl"),
        ],
    )

    assert missing_output.exit_code != 0
    assert "--output" in missing_output.output
    assert missing_generated_dir.exit_code != 0
    assert "--generated-dir" in missing_generated_dir.output
    assert invoked is False



def test_campaign_compare_command_exits_zero_without_regressions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aegis_redteam import cli

    current_path = tmp_path / "current.jsonl"
    baseline_path = tmp_path / "baseline.jsonl"
    current_path.write_text("", encoding="utf-8")
    baseline_path.write_text("", encoding="utf-8")

    def fake_compare_campaign_results(current_arg: Path, baseline_arg: Path) -> CampaignComparison:
        assert current_arg == current_path
        assert baseline_arg == baseline_path
        return CampaignComparison(regressions=0, improvements=1, new_scenarios=2, missing_scenarios=0)

    monkeypatch.setattr(cli, "compare_campaign_results", fake_compare_campaign_results)

    result = CliRunner().invoke(
        cli.app,
        ["campaign", "compare", str(current_path), str(baseline_path)],
    )

    assert result.exit_code == 0
    assert "Campaign comparison" in result.output
    assert "Regressions: 0" in result.output
    assert "Improvements: 1" in result.output
    assert "New: 2" in result.output


def test_campaign_compare_command_strict_exits_nonzero_with_new_or_improved_scenarios(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aegis_redteam import cli

    current_path = tmp_path / "current.jsonl"
    baseline_path = tmp_path / "baseline.jsonl"
    current_path.write_text("", encoding="utf-8")
    baseline_path.write_text("", encoding="utf-8")

    def fake_compare_campaign_results(current_arg: Path, baseline_arg: Path) -> CampaignComparison:
        return CampaignComparison(regressions=0, improvements=1, new_scenarios=2, missing_scenarios=0)

    monkeypatch.setattr(cli, "compare_campaign_results", fake_compare_campaign_results)

    result = CliRunner().invoke(
        cli.app,
        ["campaign", "compare", str(current_path), str(baseline_path), "--strict"],
    )

    assert result.exit_code == 1
    assert "Regressions: 0" in result.output
    assert "Improvements: 1" in result.output
    assert "New: 2" in result.output
    assert "strict" in result.output


def test_campaign_compare_command_exits_nonzero_with_regressions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aegis_redteam import cli

    current_path = tmp_path / "current.jsonl"
    baseline_path = tmp_path / "baseline.jsonl"
    current_path.write_text("", encoding="utf-8")
    baseline_path.write_text("", encoding="utf-8")

    def fake_compare_campaign_results(current_arg: Path, baseline_arg: Path) -> CampaignComparison:
        return CampaignComparison(regressions=2, improvements=0, new_scenarios=0, missing_scenarios=0)

    monkeypatch.setattr(cli, "compare_campaign_results", fake_compare_campaign_results)

    result = CliRunner().invoke(
        cli.app,
        ["campaign", "compare", str(current_path), str(baseline_path)],
    )

    assert result.exit_code == 1
    assert "Campaign comparison" in result.output
    assert "Regressions: 2" in result.output
    assert "regression(s)" in result.output


def test_compare_command_exits_zero_without_strict_for_new_scenarios(tmp_path: Path) -> None:
    from aegis_redteam import cli
    from aegis_redteam.results import write_results_jsonl

    current_path = tmp_path / "current.jsonl"
    baseline_path = tmp_path / "baseline.jsonl"
    passing_baseline = make_failed_result("baseline").model_copy(update={"passed": True})
    passing_new = make_failed_result("new").model_copy(update={"passed": True})
    write_results_jsonl([passing_baseline, passing_new], current_path)
    write_results_jsonl([passing_baseline], baseline_path)

    result = CliRunner().invoke(cli.app, ["compare", str(current_path), str(baseline_path)])

    assert result.exit_code == 0
    assert "New: 1" in result.output


def test_compare_command_strict_exits_nonzero_with_new_scenarios(tmp_path: Path) -> None:
    from aegis_redteam import cli
    from aegis_redteam.results import write_results_jsonl

    current_path = tmp_path / "current.jsonl"
    baseline_path = tmp_path / "baseline.jsonl"
    passing_baseline = make_failed_result("baseline").model_copy(update={"passed": True})
    passing_new = make_failed_result("new").model_copy(update={"passed": True})
    write_results_jsonl([passing_baseline, passing_new], current_path)
    write_results_jsonl([passing_baseline], baseline_path)

    result = CliRunner().invoke(
        cli.app,
        ["compare", str(current_path), str(baseline_path), "--strict"],
    )

    assert result.exit_code == 1
    assert "New: 1" in result.output
    assert "strict" in result.output


def test_compare_command_strict_exits_nonzero_with_missing_failed_baseline_scenario(
    tmp_path: Path,
) -> None:
    from aegis_redteam import cli
    from aegis_redteam.results import write_results_jsonl

    current_path = tmp_path / "current.jsonl"
    baseline_path = tmp_path / "baseline.jsonl"
    write_results_jsonl([], current_path)
    write_results_jsonl([make_failed_result("removed-failing-scenario")], baseline_path)

    result = CliRunner().invoke(
        cli.app,
        ["compare", str(current_path), str(baseline_path), "--strict"],
    )

    assert result.exit_code == 1
    assert "Missing: 1" in result.output
    assert "strict" in result.output


def test_campaign_compare_command_strict_exits_nonzero_with_missing_failed_baseline_scenario(
    tmp_path: Path,
) -> None:
    from aegis_redteam import cli
    from aegis_redteam.results import write_results_jsonl

    current_path = tmp_path / "current.jsonl"
    baseline_path = tmp_path / "baseline.jsonl"
    write_results_jsonl([], current_path)
    write_results_jsonl([make_failed_result("removed-failing-scenario")], baseline_path)

    result = CliRunner().invoke(
        cli.app,
        ["campaign", "compare", str(current_path), str(baseline_path), "--strict"],
    )

    assert result.exit_code == 1
    assert "Missing: 1" in result.output
    assert "strict" in result.output


def test_compare_command_exits_nonzero_with_invalid_jsonl(tmp_path: Path) -> None:
    from aegis_redteam import cli

    current_path = tmp_path / "current.jsonl"
    baseline_path = tmp_path / "baseline.jsonl"
    current_path.write_text("not json\n", encoding="utf-8")
    baseline_path.write_text("", encoding="utf-8")

    result = CliRunner().invoke(cli.app, ["compare", str(current_path), str(baseline_path)])

    assert result.exit_code == 1
    assert "invalid JSON" in result.output
    assert "current.jsonl:1" in result.output
    assert "Traceback" not in result.output


def test_campaign_compare_command_exits_nonzero_with_invalid_jsonl(tmp_path: Path) -> None:
    from aegis_redteam import cli

    current_path = tmp_path / "current.jsonl"
    baseline_path = tmp_path / "baseline.jsonl"
    current_path.write_text("not json\n", encoding="utf-8")
    baseline_path.write_text("", encoding="utf-8")

    result = CliRunner().invoke(
        cli.app,
        ["campaign", "compare", str(current_path), str(baseline_path)],
    )

    assert result.exit_code == 1
    assert "invalid JSON" in result.output
    assert "current.jsonl:1" in result.output
    assert "Traceback" not in result.output


def test_view_command_exits_nonzero_with_invalid_jsonl(tmp_path: Path) -> None:
    from aegis_redteam import cli

    results_path = tmp_path / "results.jsonl"
    results_path.write_text("not json\n", encoding="utf-8")

    result = CliRunner().invoke(cli.app, ["view", str(results_path)])

    assert result.exit_code == 1
    assert "invalid JSON" in result.output
    assert "results.jsonl:1" in result.output
    assert "Traceback" not in result.output


def test_report_command_exits_nonzero_with_invalid_jsonl(tmp_path: Path) -> None:
    from aegis_redteam import cli

    results_path = tmp_path / "results.jsonl"
    report_path = tmp_path / "report.md"
    results_path.write_text("not json\n", encoding="utf-8")

    result = CliRunner().invoke(cli.app, ["report", str(results_path), str(report_path)])

    assert result.exit_code == 1
    assert "invalid JSON" in result.output
    assert "results.jsonl:1" in result.output
    assert "Traceback" not in result.output
    assert not report_path.exists()


def test_campaign_baseline_promote_command_reports_written_baseline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aegis_redteam import cli

    source_path = tmp_path / "campaign.jsonl"
    baseline_path = tmp_path / "baselines" / "credential.jsonl"
    source_path.write_text("", encoding="utf-8")

    def fake_promote_campaign_baseline(
        source_arg: Path,
        baseline_arg: Path,
        force: bool,
    ) -> CampaignBaselinePromotion:
        assert source_arg == source_path
        assert baseline_arg == baseline_path
        assert force is False
        return CampaignBaselinePromotion(
            source_path=source_arg,
            baseline_path=baseline_arg,
            result_count=5,
            overwritten=False,
        )

    monkeypatch.setattr(cli, "promote_campaign_baseline", fake_promote_campaign_baseline)

    result = CliRunner().invoke(
        cli.app,
        ["campaign", "baseline", "promote", str(source_path), str(baseline_path)],
    )

    assert result.exit_code == 0
    assert "Campaign baseline promoted" in result.output
    assert "Results: 5" in result.output
    assert baseline_path.name in result.output


def test_campaign_baseline_promote_command_forwards_force(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aegis_redteam import cli

    source_path = tmp_path / "campaign.jsonl"
    baseline_path = tmp_path / "baseline.jsonl"
    source_path.write_text("", encoding="utf-8")

    def fake_promote_campaign_baseline(
        source_arg: Path,
        baseline_arg: Path,
        force: bool,
    ) -> CampaignBaselinePromotion:
        assert force is True
        return CampaignBaselinePromotion(
            source_path=source_arg,
            baseline_path=baseline_arg,
            result_count=1,
            overwritten=True,
        )

    monkeypatch.setattr(cli, "promote_campaign_baseline", fake_promote_campaign_baseline)

    result = CliRunner().invoke(
        cli.app,
        [
            "campaign",
            "baseline",
            "promote",
            str(source_path),
            str(baseline_path),
            "--force",
        ],
    )

    assert result.exit_code == 0
    assert "Overwritten: yes" in result.output


def test_campaign_baseline_promote_command_exits_nonzero_when_baseline_exists(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aegis_redteam import cli

    source_path = tmp_path / "campaign.jsonl"
    baseline_path = tmp_path / "baseline.jsonl"
    source_path.write_text("", encoding="utf-8")

    def fake_promote_campaign_baseline(
        source_arg: Path,
        baseline_arg: Path,
        force: bool,
    ) -> CampaignBaselinePromotion:
        raise FileExistsError(f"Baseline already exists: {baseline_arg}")

    monkeypatch.setattr(cli, "promote_campaign_baseline", fake_promote_campaign_baseline)

    result = CliRunner().invoke(
        cli.app,
        ["campaign", "baseline", "promote", str(source_path), str(baseline_path)],
    )

    assert result.exit_code == 1
    assert "Baseline already exists" in result.output
