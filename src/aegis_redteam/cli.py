from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import typer
from rich.console import Console
from rich.table import Table

from aegis_redteam.scenarios.loader import load_scenarios, load_scenario
from aegis_redteam.runner import run_scenarios
from aegis_redteam.report import generate_markdown_report
from aegis_redteam.compare import compare_results
from aegis_redteam.models import RedteamResult
from aegis_redteam.redact import redact_secrets

app = typer.Typer(help="Aegis Redteam Runner")
console = Console()


def write_results_jsonl(results: Sequence[RedteamResult], output_path: Path) -> None:
    """Write redteam results as JSONL after redacting credential-like strings."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as output_file:
        for result in results:
            redacted_result = redact_secrets(result.model_dump())
            output_file.write(RedteamResult.model_validate(redacted_result).model_dump_json() + "\n")


@app.command()
def run(
    scenarios_dir: Path = typer.Argument(..., help="Directory containing scenario YAML files"),
    target_url: str = typer.Option("http://localhost:8000", "--target", "-t"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write results to JSONL"),
) -> None:
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
        status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"

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
        write_results_jsonl(results, output)
        console.print(f"\nResults written to {output}")

    if any(not result.passed for result in results):
        raise typer.Exit(1)


@app.command()
def run_one(
    scenario_path: Path,
    target_url: str = typer.Option("http://localhost:8000", "--target", "-t"),
) -> None:
    """Run a single scenario with detailed output."""
    scenario = load_scenario(scenario_path)
    results = run_scenarios([scenario], target_url)
    result = results[0]

    console.print(f"[bold cyan]{result.scenario_name}[/bold cyan]")
    console.print(f"Passed: {'PASS' if result.passed else 'FAIL'}")
    console.print(f"Turns: {len(result.turn_results)}")

    for tr in result.turn_results:
        console.print(f"\n[bold]Turn {tr.turn_index}[/bold]")
        console.print(f"  Policy: {tr.policy_decision.final_action if tr.policy_decision else '-'}")
        console.print(f"  Detectors: {[d.name for d in tr.detector_results]}")

    if not result.passed:
        raise typer.Exit(1)


@app.command()
def view(results_file: Path) -> None:
    """View previously saved JSONL results."""
    if not results_file.exists():
        console.print(f"[red]File not found: {results_file}[/red]")
        raise typer.Exit(1)

    table = Table(title=f"Results from {results_file.name}")
    table.add_column("Scenario")
    table.add_column("Passed")
    table.add_column("Policy")

    import json
    with results_file.open() as f:
        for line in f:
            data = json.loads(line)
            status = "PASS" if data.get("passed") else "FAIL"
            policy = "-"
            if data.get("turn_results"):
                last = data["turn_results"][-1]
                if last.get("policy_decision"):
                    policy = last["policy_decision"].get("final_action", "-")

            table.add_row(data["scenario_name"], status, policy)

    console.print(table)


@app.command()
def report(results_file: Path, output: Path = typer.Argument(..., help="Output Markdown file")) -> None:
    """Generate a Markdown report from a JSONL results file."""
    import json

    results = []
    with results_file.open() as f:
        for line in f:
            data = json.loads(line)
            results.append(RedteamResult.model_validate(data))

    generate_markdown_report(results, output)
    console.print(f"Report written to {output}")


@app.command()
def compare(
    current_file: Path,
    baseline_file: Path,
) -> None:
    """Compare current results against a baseline. Exits with code 1 on regressions."""
    import json
    import sys

    current = []
    with current_file.open() as f:
        for line in f:
            data = json.loads(line)
            current.append(RedteamResult.model_validate(data))

    baseline = []
    with baseline_file.open() as f:
        for line in f:
            data = json.loads(line)
            baseline.append(RedteamResult.model_validate(data))

    regressions, _improvements, _new = compare_results(current, baseline)

    if regressions > 0:
        console.print(f"\n[red]Exiting with code 1 due to {regressions} regression(s).[/red]")
        sys.exit(1)
    else:
        sys.exit(0)


def main() -> None:
    """Console script entry point."""
    app()


if __name__ == "__main__":
    main()