from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from aegis_redteam.campaigns.generator import generate_campaign_scenarios, write_generated_scenarios
from aegis_redteam.campaigns.loader import load_campaign
from aegis_redteam.campaigns.models import Campaign
from aegis_redteam.models import RedteamResult
from aegis_redteam.runner import run_scenarios


@dataclass(frozen=True)
class CampaignRun:
    campaign: Campaign
    generated_paths: list[Path]
    results: list[RedteamResult]


def run_campaign(campaign_path: Path, target_url: str, generated_dir: Path) -> CampaignRun:
    campaign = load_campaign(campaign_path)
    scenarios = generate_campaign_scenarios(campaign)
    generated_paths = write_generated_scenarios(scenarios, generated_dir)
    results = run_scenarios(scenarios, target_url)
    return CampaignRun(campaign=campaign, generated_paths=generated_paths, results=results)
