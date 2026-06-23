from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aegis_redteam.compare import compare_results
from aegis_redteam.results import load_results_jsonl


@dataclass(frozen=True)
class CampaignComparison:
    regressions: int
    improvements: int
    new_scenarios: int


def compare_campaign_results(current_path: Path, baseline_path: Path) -> CampaignComparison:
    current = load_results_jsonl(current_path)
    baseline = load_results_jsonl(baseline_path)
    regressions, improvements, new_scenarios = compare_results(current, baseline)
    return CampaignComparison(
        regressions=regressions,
        improvements=improvements,
        new_scenarios=new_scenarios,
    )
