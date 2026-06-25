from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from rich.console import Console
from rich.table import Table

from aegis_redteam.models import RedteamResult


class FailureCategory(str, Enum):
    TARGET_CONTRACT = "target_contract"
    DETECTOR_EXPECTATION = "detector_expectation"
    POLICY_EXPECTATION = "policy_expectation"
    EGRESS_RESPONSE = "egress_response"
    EGRESS_AUDIT = "egress_audit"
    SCENARIO_VALIDATION = "scenario_validation"
    OTHER = "other"


_CATEGORY_DISPLAY_ORDER: tuple[FailureCategory, ...] = (
    FailureCategory.TARGET_CONTRACT,
    FailureCategory.DETECTOR_EXPECTATION,
    FailureCategory.POLICY_EXPECTATION,
    FailureCategory.EGRESS_RESPONSE,
    FailureCategory.EGRESS_AUDIT,
    FailureCategory.SCENARIO_VALIDATION,
    FailureCategory.OTHER,
)


def categorize_failure(failure: str) -> FailureCategory:
    """Map a failure string to a root-cause category.

    Categories are derived from failure-string shape rather than a typed field,
    keeping the RedteamResult JSONL schema stable. Order matters: egress-audit is
    checked before egress-response, and validation before generic target checks.
    """
    if failure.startswith("Detector expectation failed"):
        return FailureCategory.DETECTOR_EXPECTATION
    if failure.startswith("Policy expectation failed"):
        return FailureCategory.POLICY_EXPECTATION
    if _is_egress_audit_failure(failure):
        return FailureCategory.EGRESS_AUDIT
    if _is_egress_response_failure(failure):
        return FailureCategory.EGRESS_RESPONSE
    if _is_scenario_validation_failure(failure):
        return FailureCategory.SCENARIO_VALIDATION
    if _is_target_contract_failure(failure):
        return FailureCategory.TARGET_CONTRACT
    return FailureCategory.OTHER


def _is_egress_audit_failure(failure: str) -> bool:
    if "forbidden audit substring" in failure:
        return True
    return failure.startswith("Audit inspection returned HTTP") or failure.startswith(
        "Failed to inspect audit"
    )


def _is_egress_response_failure(failure: str) -> bool:
    if "forbidden response substring" in failure:
        return True
    return "expected assistant content" in failure


def _is_scenario_validation_failure(failure: str) -> bool:
    return ": invalid scenario:" in failure or ": invalid campaign:" in failure or (
        ": invalid YAML:" in failure
    )


_TARGET_CONTRACT_PREFIXES: tuple[str, ...] = (
    "Turn ",
    "Reset returned HTTP",
    "Failed to reset",
    "Seed canary returned HTTP",
    "Failed to seed canary",
    "Could not connect to",
    "Malformed target response",
)


def _is_target_contract_failure(failure: str) -> bool:
    return any(failure.startswith(prefix) for prefix in _TARGET_CONTRACT_PREFIXES)


@dataclass(frozen=True)
class FailedScenario:
    scenario_name: str
    categories: list[FailureCategory]
    failures: list[str]


@dataclass(frozen=True)
class RunSummary:
    total: int
    passed: int
    failed: int
    category_counts: dict[FailureCategory, int]
    failed_scenarios: list[FailedScenario]

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "category_counts": {
                category.value: self.category_counts.get(category, 0)
                for category in _CATEGORY_DISPLAY_ORDER
                if self.category_counts.get(category, 0) > 0
            },
            "failed_scenarios": [
                {
                    "scenario_name": failed.scenario_name,
                    "categories": [category.value for category in failed.categories],
                    "failures": failed.failures,
                }
                for failed in self.failed_scenarios
            ],
        }


def summarize_results(results: list[RedteamResult]) -> RunSummary:
    category_counts: dict[FailureCategory, int] = {}
    failed_scenarios: list[FailedScenario] = []

    for result in results:
        if result.passed and len(result.failures) == 0:
            continue
        categories: list[FailureCategory] = []
        for failure in result.failures:
            category = categorize_failure(failure)
            category_counts[category] = category_counts.get(category, 0) + 1
            if category not in categories:
                categories.append(category)
        failed_scenarios.append(
            FailedScenario(
                scenario_name=result.scenario_name,
                categories=categories,
                failures=list(result.failures),
            )
        )

    passed = sum(1 for result in results if result.passed)
    return RunSummary(
        total=len(results),
        passed=passed,
        failed=len(results) - passed,
        category_counts=category_counts,
        failed_scenarios=failed_scenarios,
    )


def print_summary(results: list[RedteamResult]) -> None:
    """Print a human-readable categorized failure summary."""
    console = Console()
    summary = summarize_results(results)

    console.print(
        f"[bold]{summary.passed}/{summary.total} passed[/bold] "
        f"({summary.failed} failed)"
    )

    if summary.failed == 0:
        return

    category_table = Table(title="Failures by category")
    category_table.add_column("Category")
    category_table.add_column("Count", justify="right")
    for category in _CATEGORY_DISPLAY_ORDER:
        count = summary.category_counts.get(category, 0)
        if count > 0:
            category_table.add_row(category.value, str(count))
    console.print(category_table)

    scenario_table = Table(title="Failed scenarios")
    scenario_table.add_column("Scenario")
    scenario_table.add_column("Categories")
    for failed in summary.failed_scenarios:
        scenario_table.add_row(
            failed.scenario_name,
            ", ".join(category.value for category in failed.categories),
        )
    console.print(scenario_table)
