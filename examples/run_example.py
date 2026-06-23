"""Example script showing how to run the redteam pipeline."""

from pathlib import Path

from aegis_redteam.scenarios.loader import load_scenarios
from aegis_redteam.runner import run_scenarios
from aegis_redteam.summary import print_summary

def main() -> None:
    scenarios_dir = Path(__file__).parent.parent / "scenarios"
    scenarios = load_scenarios(scenarios_dir)

    print(f"Loaded {len(scenarios)} scenarios")

    # Run against local Aegis proxy
    results = run_scenarios(scenarios, "http://localhost:8000")

    print_summary(results)


if __name__ == "__main__":
    main()
