from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aegis_redteam.models import DetectorResult, PolicyDecision, RedteamResult, TurnResult
from aegis_redteam.results import load_results_jsonl, write_results_jsonl

BASELINE_TARGET_URL = "baseline://campaign-regression"
BASELINE_TIMESTAMP = "1970-01-01T00:00:00Z"


@dataclass(frozen=True)
class CampaignBaselinePromotion:
    source_path: Path
    baseline_path: Path
    result_count: int
    overwritten: bool


def canonicalize_campaign_baseline_result(result: RedteamResult) -> RedteamResult:
    return result.model_copy(
        update={
            "run_id": f"baseline:{result.scenario_name}",
            "target_url": BASELINE_TARGET_URL,
            "started_at": BASELINE_TIMESTAMP,
            "finished_at": BASELINE_TIMESTAMP,
            "turn_results": [_canonicalize_turn_result(turn_result) for turn_result in result.turn_results],
            "failures": _canonicalize_failures(result.failures, result.target_url),
            "raw_responses": [],
        }
    )


def _canonicalize_turn_result(turn_result: TurnResult) -> TurnResult:
    policy_decision = turn_result.policy_decision
    canonical_policy_decision = (
        None if policy_decision is None else _canonicalize_policy_decision(policy_decision)
    )
    return turn_result.model_copy(
        update={
            "assistant_content": None,
            "aegis_metadata": {},
            "detector_results": [
                DetectorResult(name=detector_result.name, evidence={})
                for detector_result in turn_result.detector_results
            ],
            "policy_decision": canonical_policy_decision,
            "latency_ms": None,
        }
    )


def _canonicalize_policy_decision(policy_decision: PolicyDecision) -> PolicyDecision:
    return PolicyDecision(
        final_action=policy_decision.final_action,
        reason=None,
        triggered_detectors=list(policy_decision.triggered_detectors),
    )


def _canonicalize_failures(failures: list[str], source_target_url: str) -> list[str]:
    return [failure.replace(source_target_url, BASELINE_TARGET_URL) for failure in failures]


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

    baseline_results = [canonicalize_campaign_baseline_result(result) for result in results]
    write_results_jsonl(baseline_results, baseline_path)
    return CampaignBaselinePromotion(
        source_path=source_path,
        baseline_path=baseline_path,
        result_count=len(results),
        overwritten=baseline_exists,
    )
