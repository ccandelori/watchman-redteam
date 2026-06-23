from __future__ import annotations

from aegis_redteam.evaluator import evaluate_result
from aegis_redteam.models import RedteamResult, Scenario
from aegis_redteam.targets.http import HttpAegisTarget


def run_scenarios(scenarios: list[Scenario], base_url: str) -> list[RedteamResult]:
    """Run scenarios against an HTTP Aegis target and evaluate expectations."""
    target = HttpAegisTarget(base_url)
    results: list[RedteamResult] = []

    try:
        for scenario in scenarios:
            result = target.run_scenario(scenario)
            result.passed = evaluate_result(result, scenario)
            results.append(result)
    finally:
        target.close()
    return results
