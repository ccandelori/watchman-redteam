from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from aegis_redteam.scenarios.loader import load_scenarios
from aegis_redteam.runner import run_scenarios

app = typer.Typer(help="Aegis Redteam Runner")
console = Console()


@app.command()
def run(
    scenarios_dir: Path = typer.Argument(..., help="Directory containing scenario YAML files"),
    target_url: str = typer.Option("http://localhost:8000", "--target", "-t"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write results to JSONL"),
):
    """Run all scenarios in a directory against Aegis."""
    scenarios = load_scenarios(scenarios_dir)
    if not scenarios:
        console.print("[red]No scenarios found.[/red]")
        raise typer.Exit(1)

    results = run_scenarios(scenarios, target_url)

    table = Table(title="Redteam Results")
    table.add_column("Scenario", style="cyan")
    table.add_column("Passed", justify="center")
    table.add_column("Turns")
    table.add_column("Detectors Fired")
    table.add_column("Policy")

    for result in results:
        status = "[green]✅[/green]" if result.passed else "[red]❌[/red]"

        detectors_fired = []
        policy_action = "-"
        for turn in result.turn_results:
            for d in turn.detector_results:
                detectors_fired.append(d.name)
            if turn.policy_decision:
                policy_action = turn.policy_decision.final_action

        table.add_row(
            result.scenario_name,
            status,
            str(len(result.turn_results)),
            ", ".join(detectors_fired) if detectors_fired else "-",
            policy_action,
        )

    console.print(table)

    passed_count = sum(1 for r in results if r.passed)
    console.print(f"\n[bold]{passed_count}/{len(results)}[/bold] scenarios passed")

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w") as f:
            for result in results:
                f.write(result.model_dump_json() + "\n")
        console.print(f"\nResults written to {output}")


if __name__ == "__main__":
    app()
