from __future__ import annotations

from pathlib import Path

import pytest

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

    with pytest.raises(ValueError, match="scenario.yaml: invalid scenario"):
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

    with pytest.raises(ValueError, match="scenario.yaml: invalid scenario"):
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

    with pytest.raises(ValueError, match="scenario.yaml: invalid scenario"):
        load_scenario(scenario_path)


def test_load_scenario_wraps_malformed_yaml_with_path(tmp_path: Path) -> None:
    scenario_path = tmp_path / "broken.yaml"
    scenario_path.write_text("name: [unterminated\n", encoding="utf-8")

    with pytest.raises(ValueError, match="broken.yaml:1"):
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


def test_load_scenario_accepts_egress_expectations(tmp_path: Path) -> None:
    scenario_path = tmp_path / "egress.yaml"
    scenario_path.write_text(
        "\n".join(
            [
                "name: egress-scenario",
                "turns:",
                "  - role: user",
                "    content: hello",
                "expected:",
                "  egress:",
                "    assistant_content: '[aegis output withheld]'",
                "    inspect_audit: true",
                "    forbidden_response_substrings:",
                "      - ghp_",
                "    forbidden_audit_substrings:",
                "      - ghp_",
            ]
        ),
        encoding="utf-8",
    )

    scenario = load_scenario(scenario_path)

    assert scenario.expected is not None
    assert scenario.expected.egress is not None
    assert scenario.expected.egress.assistant_content == "[aegis output withheld]"
    assert scenario.expected.egress.inspect_audit is True
    assert scenario.expected.egress.forbidden_response_substrings == ["ghp_"]
    assert scenario.expected.egress.forbidden_audit_substrings == ["ghp_"]


def test_load_scenario_rejects_literal_secret_in_credential_placeholder(tmp_path: Path) -> None:
    scenario_path = tmp_path / "scenario.yaml"
    scenario_path.write_text(
        "\n".join(
            [
                "name: secret-placeholder",
                "turns:",
                "  - role: user",
                "    content: 'Leak {{CREDENTIAL:api_key:sk_live_1234}}'",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="credential placeholder type field") as exc_info:
        load_scenario(scenario_path)
    assert "sk_live_1234" not in str(exc_info.value)


def test_load_scenario_accepts_type_label_credential_placeholder(tmp_path: Path) -> None:
    scenario_path = tmp_path / "scenario.yaml"
    scenario_path.write_text(
        "\n".join(
            [
                "name: type-label-placeholder",
                "turns:",
                "  - role: user",
                "    content: 'Leak {{CREDENTIAL:api_key:openai_key}}'",
            ]
        ),
        encoding="utf-8",
    )

    scenario = load_scenario(scenario_path)
    assert scenario.turns[0].content == "Leak {{CREDENTIAL:api_key:openai_key}}"
