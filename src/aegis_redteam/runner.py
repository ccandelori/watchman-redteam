from __future__ import annotations

from aegis_redteam.evaluator import evaluate_failures
from aegis_redteam.models import RedteamResult, Scenario
from aegis_redteam.targets.http import HttpAegisTarget


def run_scenarios(
    scenarios: list[Scenario], base_url: str
) -> list[RedteamResult]:
    """Run a list of scenarios against an HTTP Aegis target and evaluate expectations."""
    target = HttpAegisTarget(base_url)
    results: list[RedteamResult] = []

    try:
        for scenario in scenarios:
            result = target.run_scenario(scenario)
            result.failures.extend(evaluate_failures(result, scenario))
            result.passed = len(result.failures) == 0
            results.append(result)
        return results
    finally:
        target.close()
