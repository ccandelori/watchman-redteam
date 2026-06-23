from __future__ import annotations

from rich.console import Console
from rich.table import Table

from aegis_redteam.models import RedteamResult


def print_summary(results: list[RedteamResult]) -> None:
    """Print a clean summary table."""
    console = Console()
    table = Table(title="Redteam Summary")
    table.add_column("Scenario")
    table.add_column("Passed")
    table.add_column("Detectors")
    table.add_column("Policy")

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        detectors = (
            ", ".join(
                detector.name for turn in result.turn_results for detector in turn.detector_results
            )
            or "-"
        )
        policy = "-"
        if result.turn_results and result.turn_results[-1].policy_decision:
            policy = result.turn_results[-1].policy_decision.final_action

        table.add_row(result.scenario_name, status, detectors, policy)

    console.print(table)
    passed = sum(1 for result in results if result.passed)
    console.print(f"\n[bold]{passed}/{len(results)} passed[/bold]")
