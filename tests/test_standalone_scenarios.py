from __future__ import annotations

from pathlib import Path

import yaml

from aegis_redteam.scenarios.loader import load_scenario


def test_detector_positive_standalone_scenarios_without_placeholders_seed_canary() -> None:
    scenario_dir = Path("scenarios")
    missing_seed: list[str] = []

    for scenario_path in sorted(scenario_dir.glob("*.yaml")):
        raw_scenario = yaml.safe_load(scenario_path.read_text(encoding="utf-8"))
        detectors = raw_scenario.get("expected", {}).get("detectors", [])
        expects_detector = any(detector.get("should_trigger") is True for detector in detectors)
        turn_content = "\n".join(turn.get("content", "") for turn in raw_scenario.get("turns", []))
        if not expects_detector or "{{CREDENTIAL:" in turn_content:
            continue

        scenario = load_scenario(scenario_path)
        if scenario.target_controls.seed_canary is None:
            missing_seed.append(scenario_path.name)

    assert missing_seed == []
