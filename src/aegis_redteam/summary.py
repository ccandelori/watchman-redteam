from __future__ import annotations

from typing import List
from rich.table import Table
from rich.console import Console

from aegis_redteam.models import RedteamResult


def print_summary(results: List[RedteamResult]) -> None:
    """Print a clean summary table."""
    console = Console()
    table = Table(title="Redteam Summary")
    table.add_column("Scenario")
    table.add_column("Passed")
    table.add_column("Detectors")
    table.add_column("Policy")

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        detectors = ", ".join(
            d.name for tr in r.turn_results for d in tr.detector_results
        ) or "-"
        policy = "-"
        if r.turn_results and r.turn_results[-1].policy_decision:
            policy = r.turn_results[-1].policy_decision.final_action

        table.add_row(r.scenario_name, status, detectors, policy)

    console.print(table)
    passed = sum(1 for r in results if r.passed)
    console.print(f"\n[bold]{passed}/{len(results)} passed[/bold]")
