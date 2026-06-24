from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aegis_redteam.compare import compare_results, count_missing_baseline_scenarios
from aegis_redteam.results import load_results_jsonl
from aegis_redteam.campaigns.validation import validate_unique_scenario_names


@dataclass(frozen=True)
class CampaignComparison:
    regressions: int
    improvements: int
    new_scenarios: int
    missing_scenarios: int


def compare_campaign_results(current_path: Path, baseline_path: Path) -> CampaignComparison:
    current = load_results_jsonl(current_path)
    baseline = load_results_jsonl(baseline_path)
    validate_unique_scenario_names(current, current_path)
    validate_unique_scenario_names(baseline, baseline_path)
    missing_scenarios = count_missing_baseline_scenarios(current, baseline)
    regressions, improvements, new_scenarios = compare_results(current, baseline)
    return CampaignComparison(
        regressions=regressions,
        improvements=improvements,
        new_scenarios=new_scenarios,
        missing_scenarios=missing_scenarios,
    )
