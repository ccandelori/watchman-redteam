from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static

from aegis_redteam.models import RedteamResult
from aegis_redteam.results import load_results_jsonl


class RedteamTUI(App[None]):
    """TUI for viewing redteam results."""

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, results: list[RedteamResult] | None = None) -> None:
        super().__init__()
        self.results = results or []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Aegis Redteam Results", id="title")
        yield DataTable(id="results")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Scenario", "Status", "Policy", "Detectors")

        for result in self.results:
            status = "PASS" if result.passed else "FAIL"
            detectors = ", ".join(
                d.name for tr in result.turn_results for d in tr.detector_results
            ) or "-"
            policy = "-"
            if result.turn_results and result.turn_results[-1].policy_decision:
                policy = result.turn_results[-1].policy_decision.final_action

            table.add_row(result.scenario_name, status, policy, detectors)


def load_results(path: Path) -> list[RedteamResult]:
    """Load RedteamResult objects from a JSONL file."""
    return load_results_jsonl(path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        results = load_results(Path(sys.argv[1]))
        app = RedteamTUI(results)
    else:
        app = RedteamTUI()
    app.run()