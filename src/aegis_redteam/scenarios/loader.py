from __future__ import annotations

from pathlib import Path
from typing import List

import yaml

from aegis_redteam.models import Scenario


def load_scenario(path: Path | str) -> Scenario:
    """Load a single scenario from YAML."""
    path = Path(path)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Scenario.model_validate(data)


def load_scenarios(directory: Path | str) -> List[Scenario]:
    """Load all .yaml/.yml files from a directory."""
    directory = Path(directory)
    scenarios: List[Scenario] = []
    for file in sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml")):
        scenarios.append(load_scenario(file))
    return scenarios
