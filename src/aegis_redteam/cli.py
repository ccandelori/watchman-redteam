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
from aegis_redteam.doctor import DoctorReport, run_doctor
from aegis_redteam.campaigns.baseline import CampaignBaselinePromotion, promote_campaign_baseline
from aegis_redteam.campaigns.compare import CampaignComparison, compare_campaign_results
from aegis_redteam.campaigns.runner import CampaignRun, run_campaign
from aegis_redteam.results import load_results_jsonl, write_results_jsonl

app = typer.Typer(help="Aegis Redteam Runner")
campaign_app = typer.Typer(help="Campaign commands")
baseline_app = typer.Typer(help="Campaign baseline commands")
campaign_app.add_typer(baseline_app, name="baseline")
app.add_typer(campaign_app, name="campaign")
console = Console()



def print_failure_details(results: Sequence[RedteamResult]) -> None:
    failed_results = [result for result in results if len(result.failures) > 0]
    if len(failed_results) == 0:
        return

    console.print("\n[bold red]Failures[/bold red]")
    for result in failed_results:
        for failure in result.failures:
            console.print(f"- {result.scenario_name}: {failure}")


def print_doctor_report(report: DoctorReport) -> None:
    table = Table(title=f"Target Doctor: {report.target_url} ({report.target_kind})")
    table.add_column("Check", style="cyan")
    table.add_column("Required", justify="center")
    table.add_column("Status", justify="center")
    table.add_column("Detail")

    for check in report.checks:
        status = "[green]PASS[/green]" if check.passed else "[red]FAIL[/red]"
        table.add_row(check.name, "yes" if check.required else "no", status, check.detail)

    console.print(table)


@app.command()
def doctor(
    target_url: str = typer.Option("http://localhost:8000", "--target", "-t"),
    timeout: float = typer.Option(5.0, "--timeout", help="HTTP timeout in seconds"),
) -> None:
    """Probe target readiness for the Aegis HTTP contract."""
    report = run_doctor(target_url, timeout)
    print_doctor_report(report)
    if not report.passed:
        raise typer.Exit(1)


def print_campaign_run_summary(run: CampaignRun) -> None:
    passed_count = sum(1 for result in run.results if result.passed)
    console.print(
        f"\n[bold]{run.campaign.name}[/bold]: "
        f"[bold]{passed_count}/{len(run.results)}[/bold] campaign scenarios passed"
    )
    if len(run.generated_paths) > 0:
        console.print(f"Generated scenarios: {len(run.generated_paths)}")


@campaign_app.command("run")
def campaign_run(
    campaign_path: Path = typer.Argument(..., help="Campaign YAML file"),
    target_url: str = typer.Option("http://localhost:8000", "--target", "-t"),
    output: Path = typer.Option(..., "--output", "-o", help="Write results to JSONL"),
    generated_dir: Path = typer.Option(
        ...,
        "--generated-dir",
        help="Write generated scenario YAML files to this directory",
    ),
) -> None:
    """Generate and run deterministic campaign scenarios."""
    campaign_run_result = run_campaign(campaign_path, target_url, generated_dir)
    print_campaign_run_summary(campaign_run_result)

    if output is not None:
        write_results_jsonl(campaign_run_result.results, output)
        console.print(f"Results written to {output}")

    print_failure_details(campaign_run_result.results)
    if any(not result.passed for result in campaign_run_result.results):
        raise typer.Exit(1)


def print_campaign_comparison(comparison: CampaignComparison) -> None:
    console.print("\n[bold]Campaign comparison[/bold]")
    console.print(
        f"Regressions: {comparison.regressions} | "
        f"Improvements: {comparison.improvements} | "
        f"New: {comparison.new_scenarios}"
    )


def print_campaign_baseline_promotion(promotion: CampaignBaselinePromotion) -> None:
    console.print("\n[bold]Campaign baseline promoted[/bold]")
    console.print(f"Source: {promotion.source_path}")
    console.print(f"Baseline: {promotion.baseline_path}")
    console.print(f"Results: {promotion.result_count}")
    console.print(f"Overwritten: {'yes' if promotion.overwritten else 'no'}")


@baseline_app.command("promote")
def campaign_baseline_promote(
    source_file: Path = typer.Argument(..., help="Source campaign result JSONL"),
    baseline_file: Path = typer.Argument(..., help="Baseline JSONL destination"),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing baseline"),
) -> None:
    """Promote campaign result JSONL to a baseline file."""
    try:
        promotion = promote_campaign_baseline(source_file, baseline_file, force)
    except (FileExistsError, ValueError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc
    print_campaign_baseline_promotion(promotion)


@campaign_app.command("compare")
def campaign_compare(
    current_file: Path = typer.Argument(..., help="Current campaign result JSONL"),
    baseline_file: Path = typer.Argument(..., help="Baseline campaign result JSONL"),
) -> None:
    """Compare campaign result JSONL against a baseline."""
    comparison = compare_campaign_results(current_file, baseline_file)
    print_campaign_comparison(comparison)
    if comparison.regressions > 0:
        console.print(
            f"\n[red]Exiting with code 1 due to {comparison.regressions} regression(s).[/red]"
        )
        raise typer.Exit(1)


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

    print_failure_details(results)

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

    print_failure_details([result])

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
    import sys

    current = load_results_jsonl(current_file)
    baseline = load_results_jsonl(baseline_file)

    regressions, _improvements, _new = compare_results(current, baseline)

    if regressions > 0:
        console.print(f"\n[red]Exiting with code 1 due to {regressions} regression(s).[/red]")
        sys.exit(1)
    else:
        sys.exit(0)


@app.command()
def serve_fixture(
    host: str = typer.Option("127.0.0.1", "--host", help="Host interface to bind"),
    port: int = typer.Option(8000, "--port", help="TCP port to bind"),
) -> None:
    """Start a local deterministic Aegis-compatible fixture server."""
    from aegis_redteam.fixture_server import serve_fixture_server

    console.print(f"Serving Aegis fixture target at http://{host}:{port}")
    serve_fixture_server(host, port)


def main() -> None:
    """Console script entry point."""
    app()


if __name__ == "__main__":
    main()