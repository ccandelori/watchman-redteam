from __future__ import annotations

from pathlib import Path

from aegis_redteam.models import Scenario
from aegis_redteam.yaml_utils import load_yaml_model


def load_scenario(path: Path | str) -> Scenario:
    """Load a single scenario from YAML."""
    return load_yaml_model(path, Scenario, "scenario")


def load_scenarios(directory: Path | str) -> list[Scenario]:
    """Load all .yaml/.yml files from a directory."""
    directory = Path(directory)
    scenarios: list[Scenario] = []
    seen_names: set[str] = set()
    for file in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml")):
        scenario = load_scenario(file)
        if scenario.name in seen_names:
            raise ValueError(f"duplicate scenario name: {scenario.name}")
        seen_names.add(scenario.name)
        scenarios.append(scenario)
    return scenarios
