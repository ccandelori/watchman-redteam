from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from aegis_redteam.scenarios.loader import load_scenario, load_scenarios


def test_load_scenario_rejects_unknown_top_level_field(tmp_path: Path) -> None:
    scenario_path = tmp_path / "scenario.yaml"
    scenario_path.write_text(
        "\n".join(
            [
                "name: unknown-top-level",
                "target_control:",
                "  mock_response_mode: default",
                "turns:",
                "  - role: user",
                "    content: hello",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="extra_forbidden"):
        load_scenario(scenario_path)


def test_load_scenario_rejects_misspelled_seed_canary_field(tmp_path: Path) -> None:
    scenario_path = tmp_path / "scenario.yaml"
    scenario_path.write_text(
        "\n".join(
            [
                "name: misspelled-seed",
                "target_controls:",
                "  seed_canarry:",
                "    slot_name: api_key",
                "    credential_type: openai_key",
                "    turn_index: 0",
                "turns:",
                "  - role: user",
                "    content: hello",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="extra_forbidden"):
        load_scenario(scenario_path)


def test_load_scenario_rejects_empty_turns(tmp_path: Path) -> None:
    scenario_path = tmp_path / "scenario.yaml"
    scenario_path.write_text(
        "\n".join(
            [
                "name: empty-turns",
                "turns: []",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="too_short"):
        load_scenario(scenario_path)


def test_load_scenarios_rejects_duplicate_scenario_names(tmp_path: Path) -> None:
    first_path = tmp_path / "a.yaml"
    second_path = tmp_path / "b.yaml"
    scenario_body = "\n".join(
        [
            "name: duplicate-scenario",
            "turns:",
            "  - role: user",
            "    content: hello",
        ]
    )
    first_path.write_text(scenario_body, encoding="utf-8")
    second_path.write_text(scenario_body, encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate scenario name: duplicate-scenario"):
        load_scenarios(tmp_path)
