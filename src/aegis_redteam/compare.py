from __future__ import annotations

from rich.console import Console
from rich.table import Table

from aegis_redteam.models import PolicyDecision, RedteamResult, TurnResult

PolicySignature = tuple[str, tuple[str, ...]] | None
TurnSignature = tuple[int, int, tuple[str, ...], PolicySignature]
ResultSignature = tuple[bool, tuple[str, ...], tuple[TurnSignature, ...]]


def count_missing_baseline_scenarios(
    current: list[RedteamResult], baseline: list[RedteamResult]
) -> int:
    current_names = {result.scenario_name for result in current}
    return sum(1 for result in baseline if result.scenario_name not in current_names)


def count_changed_baseline_scenarios(
    current: list[RedteamResult], baseline: list[RedteamResult]
) -> int:
    baseline_by_name = {result.scenario_name: result for result in baseline}
    changed_scenarios = 0
    for result in current:
        baseline_result = baseline_by_name.get(result.scenario_name)
        if baseline_result is None:
            continue
        if result.passed != baseline_result.passed:
            continue
        if _result_signature(result) != _result_signature(baseline_result):
            changed_scenarios += 1
    return changed_scenarios


def _result_signature(result: RedteamResult) -> ResultSignature:
    return (
        result.passed,
        tuple(result.failures),
        tuple(_turn_signature(turn_result) for turn_result in result.turn_results),
    )


def _turn_signature(turn_result: TurnResult) -> TurnSignature:
    return (
        turn_result.turn_index,
        turn_result.response_status,
        tuple(detector_result.name for detector_result in turn_result.detector_results),
        _policy_signature(turn_result.policy_decision),
    )


def _policy_signature(policy_decision: PolicyDecision | None) -> PolicySignature:
    if policy_decision is None:
        return None
    return (policy_decision.final_action, tuple(policy_decision.triggered_detectors))


def compare_results(
    current: list[RedteamResult], baseline: list[RedteamResult]
) -> tuple[int, int, int]:
    """
    Compare current results against a baseline.
    Returns (regressions, improvements, new).
    """
    console = Console()
    table = Table(title="Regression Comparison")
    table.add_column("Scenario")
    table.add_column("Current")
    table.add_column("Baseline")
    table.add_column("Change")

    baseline_map = {r.scenario_name: r.passed for r in baseline}
    current_names = {r.scenario_name for r in current}

    regressions = 0
    improvements = 0
    new_scenarios = 0

    for result in current:
        base_passed = baseline_map.get(result.scenario_name)
        if base_passed is None:
            change = "[yellow]new[/yellow]"
            new_scenarios += 1
        elif result.passed and not base_passed:
            change = "[green]improved[/green]"
            improvements += 1
        elif not result.passed and base_passed:
            change = "[red]regressed[/red]"
            regressions += 1
        else:
            change = "same"

        current_status = "PASS" if result.passed else "FAIL"
        base_status = "PASS" if base_passed else "FAIL" if base_passed is not None else "-"

        table.add_row(result.scenario_name, current_status, base_status, change)

    for result in baseline:
        if result.scenario_name in current_names:
            continue
        if result.passed:
            regressions += 1
            table.add_row(result.scenario_name, "MISSING", "PASS", "[red]missing[/red]")

    console.print(table)
    console.print(
        f"\nRegressions: {regressions} | Improvements: {improvements} | New: {new_scenarios}"
    )
    return regressions, improvements, new_scenarios
