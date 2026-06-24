from __future__ import annotations

import asyncio
from pathlib import Path
from typing import cast

import pytest
from textual.widgets import DataTable, Static

from aegis_redteam.models import DetectorResult, PolicyDecision, RedteamResult, Turn, TurnResult
from aegis_redteam.results import write_results_jsonl
from aegis_redteam.tui.app import RedteamTUI, load_results


def make_tui_result(
    scenario_name: str,
    passed: bool,
    policy_action: str,
    detector_name: str,
    failures: list[str],
) -> RedteamResult:
    return RedteamResult(
        run_id=f"run-{scenario_name}",
        scenario_name=scenario_name,
        target_url="http://localhost:8000",
        started_at="2026-06-23T00:00:00Z",
        finished_at="2026-06-23T00:00:01Z",
        passed=passed,
        failures=failures,
        turn_results=[
            TurnResult(
                turn_index=1,
                request=Turn(role="user", content="hello"),
                response_status=200,
                assistant_content="assistant response",
                detector_results=[DetectorResult(name=detector_name, evidence={"score": 0.91})],
                policy_decision=PolicyDecision(final_action=policy_action, reason="policy reason"),
            )
        ],
    )


def widget_text(widget: Static) -> str:
    return str(widget.render())


def test_redteam_tui_runs_headless_without_external_css_file() -> None:
    async def run_app() -> None:
        async with RedteamTUI([], source_path=None).run_test():
            return

    asyncio.run(run_app())


def test_tui_load_results_uses_shared_path_line_validation(tmp_path: Path) -> None:
    results_path = tmp_path / "bad.jsonl"
    results_path.write_text("not json\n", encoding="utf-8")

    with pytest.raises(ValueError, match="bad.jsonl:1: invalid JSON"):
        load_results(results_path)


def test_redteam_tui_renders_summary_table_and_initial_details() -> None:
    failed = make_tui_result("blocked-exfil", False, "block", "nimbus", ["expected detector did not fire"])
    passed = make_tui_result("benign-control", True, "allow", "none", [])

    async def run_app() -> None:
        async with RedteamTUI([failed, passed], source_path=Path("results/latest.jsonl")).run_test() as pilot:
            summary = pilot.app.query_one("#summary", Static)
            details = pilot.app.query_one("#details", Static)
            table = pilot.app.query_one("#results", DataTable)

            assert table.row_count == 2
            assert "1/2 scenarios passed" in widget_text(summary)
            assert "results/latest.jsonl" in widget_text(summary)
            assert "blocked-exfil" in widget_text(details)
            assert "FAIL" in widget_text(details)
            assert "block" in widget_text(details)
            assert "nimbus" in widget_text(details)
            assert "expected detector did not fire" in widget_text(details)

    asyncio.run(run_app())


def test_redteam_tui_updates_details_for_selected_result() -> None:
    failed = make_tui_result("blocked-exfil", False, "block", "nimbus", ["expected detector did not fire"])
    passed = make_tui_result("benign-control", True, "allow", "none", [])

    async def run_app() -> None:
        async with RedteamTUI([failed, passed], source_path=None).run_test() as pilot:
            app = cast(RedteamTUI, pilot.app)
            app.show_result_details(1)
            await pilot.pause()
            details = pilot.app.query_one("#details", Static)

            assert "benign-control" in widget_text(details)
            assert "PASS" in widget_text(details)
            assert "allow" in widget_text(details)
            assert "expected detector did not fire" not in widget_text(details)

    asyncio.run(run_app())


def test_tui_loads_results_written_by_shared_jsonl_writer(tmp_path: Path) -> None:
    results_path = tmp_path / "results.jsonl"
    result = make_tui_result("blocked-exfil", False, "block", "nimbus", ["unsafe egress"])
    write_results_jsonl([result], results_path)

    loaded = load_results(results_path)

    assert [record.scenario_name for record in loaded] == ["blocked-exfil"]
