from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from aegis_redteam.scenarios.loader import load_scenarios
from aegis_redteam.runner import run_scenarios

app = typer.Typer(help="Aegis Redteam Runner")


@app.command()
def run(
    scenarios_dir: Path = typer.Argument(..., help="Directory containing scenario YAML files"),
    target_url: str = typer.Option("http://localhost:8000", "--target", "-t"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write results to JSONL"),
):
    """Run all scenarios in a directory against Aegis."""
    scenarios = load_scenarios(scenarios_dir)
    results = run_scenarios(scenarios, target_url)

    for result in results:
        line = result.model_dump_json()
        typer.echo(line)
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("a") as f:
                f.write(line + "\n")

    passed = sum(1 for r in results if r.passed)
    typer.echo(f"\n{passed}/{len(results)} scenarios passed")


if __name__ == "__main__":
    app()
