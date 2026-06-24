from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static

from aegis_redteam.models import RedteamResult, TurnResult
from aegis_redteam.redact import redact_text
from aegis_redteam.results import load_results_jsonl


def load_results(path: Path) -> list[RedteamResult]:
    """Load RedteamResult objects from a JSONL file."""
    return load_results_jsonl(path)


def format_summary(results: list[RedteamResult], source_path: Path | None) -> str:
    passed_count = sum(1 for result in results if result.passed)
    failed_count = len(results) - passed_count
    source = redact_text(str(source_path)) if source_path is not None else "in-memory results"
    return f"{passed_count}/{len(results)} scenarios passed | {failed_count} failed | Source: {source}"


def safe_text(value: str) -> str:
    return redact_text(value)


def detector_names(result: RedteamResult) -> list[str]:
    names: list[str] = []
    for turn_result in result.turn_results:
        for detector in turn_result.detector_results:
            name = safe_text(detector.name)
            if name not in names:
                names.append(name)
    return names


def final_policy(result: RedteamResult) -> str:
    for turn_result in reversed(result.turn_results):
        if turn_result.policy_decision is not None:
            return safe_text(turn_result.policy_decision.final_action)
    return "-"


def failure_count_label(result: RedteamResult) -> str:
    if len(result.failures) == 0:
        return "-"
    return str(len(result.failures))


def format_turn_detail(turn_result: TurnResult) -> str:
    policy = "-"
    policy_reason = "-"
    if turn_result.policy_decision is not None:
        policy = turn_result.policy_decision.final_action
        policy_reason = turn_result.policy_decision.reason or "-"
    detectors = ", ".join(safe_text(detector.name) for detector in turn_result.detector_results) or "-"
    assistant_content = safe_text(turn_result.assistant_content or "-")
    return (
        f"- Turn {turn_result.turn_index}: status={turn_result.response_status}; "
        f"policy={safe_text(policy)}; reason={safe_text(policy_reason)}; "
        f"detectors={detectors}; assistant={assistant_content}"
    )


def format_result_detail(result: RedteamResult) -> str:
    status = "PASS" if result.passed else "FAIL"
    detectors = ", ".join(detector_names(result)) or "-"
    lines = [
        f"Scenario: {safe_text(result.scenario_name)}",
        f"Status: {status}",
        f"Target: {safe_text(result.target_url)}",
        f"Run: {safe_text(result.run_id)}",
        f"Started: {safe_text(result.started_at)}",
        f"Finished: {safe_text(result.finished_at)}",
        f"Final policy: {final_policy(result)}",
        f"Detectors: {detectors}",
        "",
        "Failures:",
    ]
    if len(result.failures) == 0:
        lines.append("- none")
    else:
        lines.extend(f"- {safe_text(failure)}" for failure in result.failures)
    lines.extend(["", "Turns:"])
    if len(result.turn_results) == 0:
        lines.append("- none")
    else:
        lines.extend(format_turn_detail(turn_result) for turn_result in result.turn_results)
    return "\n".join(lines)


class RedteamTUI(App[None]):
    """TUI for viewing redteam results."""

    BINDINGS = [("q", "quit", "Quit"), ("escape", "quit", "Quit")]
    CSS = """
    #title {
        text-style: bold;
        height: 1;
    }

    #summary {
        height: 1;
    }

    #results {
        height: 1fr;
    }

    #details {
        height: 14;
        border: round $accent;
        padding: 1;
    }
    """

    def __init__(self, results: list[RedteamResult], source_path: Path | None) -> None:
        super().__init__()
        self.results = results
        self.source_path = source_path

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Aegis Redteam Results", id="title")
        yield Static("", id="summary")
        yield DataTable(id="results")
        yield Static("", id="details")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Aegis Redteam Results"
        table = self.query_one("#results", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns("Scenario", "Status", "Policy", "Detectors", "Failures")

        for index, result in enumerate(self.results):
            status = "PASS" if result.passed else "FAIL"
            table.add_row(
                result.scenario_name,
                status,
                final_policy(result),
                ", ".join(detector_names(result)) or "-",
                failure_count_label(result),
                key=str(index),
            )

        summary = self.query_one("#summary", Static)
        summary.update(format_summary(self.results, self.source_path))
        self.show_result_details(0)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self.show_result_details(event.cursor_row)

    def show_result_details(self, result_index: int) -> None:
        details = self.query_one("#details", Static)
        if len(self.results) == 0:
            details.update("No results loaded.")
            return
        if result_index < 0 or result_index >= len(self.results):
            return
        details.update(format_result_detail(self.results[result_index]))


def launch_tui(results_file: Path) -> None:
    results = load_results(results_file)
    app = RedteamTUI(results, source_path=results_file)
    app.run()


def main() -> None:
    import sys

    if len(sys.argv) > 1:
        launch_tui(Path(sys.argv[1]))
        return
    RedteamTUI([], source_path=None).run()


if __name__ == "__main__":
    main()
