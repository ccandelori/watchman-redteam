from __future__ import annotations

from pathlib import Path

import yaml

from aegis_redteam.campaigns.models import Campaign
from aegis_redteam.models import (
    DetectorExpectation,
    Expected,
    PolicyExpectation,
    Scenario,
    TargetControls,
    Turn,
)


def generate_campaign_scenarios(campaign: Campaign) -> list[Scenario]:
    scenarios: list[Scenario] = []
    for variant in campaign.variants:
        scenario_name = f"{campaign.name}__{variant.name}"
        scenarios.append(
            Scenario(
                name=scenario_name,
                description=f"Generated campaign variant {variant.name} from {campaign.name}",
                target_controls=TargetControls(
                    mock_response_mode=variant.mock_response_mode,
                    reset_before_run=campaign.reset_before_run,
                    session_id=scenario_name,
                ),
                turns=[
                    Turn(
                        role="user",
                        content=variant.prompt.replace("{{credential}}", campaign.credential),
                    )
                ],
                expected=Expected(
                    detectors=[
                        DetectorExpectation(name=detector.name, should_trigger=detector.should_trigger)
                        for detector in variant.detectors
                    ],
                    policy=PolicyExpectation(min_final_action=variant.min_final_action),
                ),
            )
        )
    return scenarios


def write_generated_scenarios(scenarios: list[Scenario], generated_dir: Path) -> list[Path]:
    generated_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for scenario in scenarios:
        output_path = generated_dir / f"{scenario.name}.yaml"
        output_path.write_text(
            yaml.safe_dump(scenario.model_dump(mode="json", exclude_none=True), sort_keys=False),
            encoding="utf-8",
        )
        paths.append(output_path)
    return paths
