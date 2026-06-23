from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aegis_redteam.results import load_results_jsonl, write_results_jsonl


@dataclass(frozen=True)
class CampaignBaselinePromotion:
    source_path: Path
    baseline_path: Path
    result_count: int
    overwritten: bool


def promote_campaign_baseline(
    source_path: Path,
    baseline_path: Path,
    force: bool,
) -> CampaignBaselinePromotion:
    baseline_exists = baseline_path.exists()
    if baseline_exists and not force:
        raise FileExistsError(f"Baseline already exists: {baseline_path}. Pass --force to overwrite.")

    results = load_results_jsonl(source_path)
    if len(results) == 0:
        raise ValueError(f"Campaign result source contains no results: {source_path}")

    write_results_jsonl(results, baseline_path)
    return CampaignBaselinePromotion(
        source_path=source_path,
        baseline_path=baseline_path,
        result_count=len(results),
        overwritten=baseline_exists,
    )
