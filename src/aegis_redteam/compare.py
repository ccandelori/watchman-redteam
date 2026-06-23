from __future__ import annotations

from typing import List
from rich.console import Console
from rich.table import Table

from aegis_redteam.models import RedteamResult


def compare_results(current: List[RedteamResult], baseline: List[RedteamResult]) -> None:
    """Compare current results against a baseline and print differences."""
    console = Console()
    table = Table(title="Regression Comparison")
    table.add_column("Scenario")
    table.add_column("Current")
    table.add_column("Baseline")
    table.add_column("Change")

    baseline_map = {r.scenario_name: r.passed for r in baseline}

    regressions = 0
    improvements = 0

    for result in current:
        base_passed = baseline_map.get(result.scenario_name)
        if base_passed is None:
            change = "new"
        elif result.passed and not base_passed:
            change = "[green]improved[/green]"
            improvements += 1
        elif not result.passed and base_passed:
            change = "[red]regressed[/red]"
            regressions += 1
        else:
            change = "same"

        current_status = "✅" if result.passed else "❌"
        base_status = "✅" if base_passed else "❌" if base_passed is not None else "-"

        table.add_row(result.scenario_name, current_status, base_status, change)

    console.print(table)
    console.print(f"\nRegressions: {regressions} | Improvements: {improvements}")
