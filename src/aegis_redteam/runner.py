from __future__ import annotations

from typing import List

from aegis_redteam.models import Scenario, RedteamResult
from aegis_redteam.targets.http import HttpAegisTarget


def run_scenarios(
    scenarios: List[Scenario], base_url: str
) -> List[RedteamResult]:
    """Run a list of scenarios against an HTTP Aegis target."""
    target = HttpAegisTarget(base_url)
    results: List[RedteamResult] = []

    for scenario in scenarios:
        result = target.run_scenario(scenario)
        results.append(result)

    target.close()
    return results
