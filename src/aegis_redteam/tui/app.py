from __future__ import annotations

from pathlib import Path
from typing import List

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static
from textual.containers import Vertical

from aegis_redteam.models import RedteamResult


class RedteamTUI(App):
    """TUI for viewing redteam results."""

    CSS_PATH = "app.css"
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, results: List[RedteamResult] | None = None):
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
            status = "✅" if result.passed else "❌"
            detectors = ", ".join(
                d.name for tr in result.turn_results for d in tr.detector_results
            ) or "-"
            policy = "-"
            if result.turn_results and result.turn_results[-1].policy_decision:
                policy = result.turn_results[-1].policy_decision.final_action

            table.add_row(result.scenario_name, status, policy, detectors)


def load_results(path: Path) -> List[RedteamResult]:
    """Load RedteamResult objects from a JSONL file."""
    import json
    results = []
    with path.open() as f:
        for line in f:
            data = json.loads(line)
            results.append(RedteamResult.model_validate(data))
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        results = load_results(Path(sys.argv[1]))
        app = RedteamTUI(results)
    else:
        app = RedteamTUI()
    app.run()
