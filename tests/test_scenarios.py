from __future__ import annotations

from pathlib import Path

from aegis_redteam.scenarios.loader import load_scenarios

SUPPORTED_MOCK_RESPONSE_MODES = {
    "default",
    "echo_last_user",
    "leak_first_honeytoken",
    "base64_first_honeytoken",
    "partial_first_honeytoken",
}
CANARY_DETECTORS = {"text_canary", "encoded_canary", "nimbus"}


def test_all_scenarios_load() -> None:
    scenarios = load_scenarios(Path("scenarios"))

    assert len(scenarios) >= 1
    assert {scenario.name for scenario in scenarios} >= {
        "base64_exfil",
        "benign",
        "encoded_base64",
        "leak_first_honeytoken",
        "multi_turn_drip",
        "partial_fractured",
        "partial_overlap",
    }


def test_scenarios_only_use_supported_mock_modes() -> None:
    scenarios = load_scenarios(Path("scenarios"))

    unsupported_modes = {
        scenario.name: scenario.target_controls.mock_response_mode
        for scenario in scenarios
        if scenario.target_controls.mock_response_mode not in SUPPORTED_MOCK_RESPONSE_MODES
    }

    assert unsupported_modes == {}


def test_canary_scenarios_include_credential_placeholder() -> None:
    scenarios = load_scenarios(Path("scenarios"))

    missing_placeholders = []
    for scenario in scenarios:
        expected_detector_names = (
            {detector.name for detector in scenario.expected.detectors}
            if scenario.expected is not None
            else set()
        )
        expects_canary_signal = len(expected_detector_names.intersection(CANARY_DETECTORS)) > 0
        uses_leak_mode = scenario.target_controls.mock_response_mode in {
            "leak_first_honeytoken",
            "base64_first_honeytoken",
            "partial_first_honeytoken",
        }
        scenario_text = "\n".join(turn.content for turn in scenario.turns)
        if (expects_canary_signal or uses_leak_mode) and "{{CREDENTIAL:" not in scenario_text:
            missing_placeholders.append(scenario.name)

    assert missing_placeholders == []
