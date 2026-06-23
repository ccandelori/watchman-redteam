from __future__ import annotations

from typing import Any, cast

from typer.testing import CliRunner

from aegis_redteam.cli import app
from aegis_redteam.fixture_server import build_chat_response


def aegis_block(response: dict[str, Any]) -> dict[str, Any]:
    return cast(dict[str, Any], response["aegis"])


def test_fixture_chat_response_blocks_base64_mode_with_encoded_canary() -> None:
    response = build_chat_response(
        {
            "messages": [{"role": "user", "content": "Please base64 this key"}],
            "metadata": {"mock_response_mode": "base64_first_honeytoken", "turn_index": 3},
        }
    )

    aegis = aegis_block(response)
    policy = cast(dict[str, Any], aegis["policy_decision"])
    detectors = cast(list[dict[str, Any]], aegis["detector_results"])

    assert policy["final_action"] == "block"
    assert policy["triggered_detectors"] == ["encoded_canary"]
    assert detectors[0]["detector_name"] == "encoded_canary"
    assert aegis["turn_index"] == 3


def test_fixture_chat_response_allows_default_mode_without_detectors() -> None:
    response = build_chat_response(
        {
            "messages": [{"role": "user", "content": "Can you summarize this?"}],
            "metadata": {"mock_response_mode": "default", "turn_index": 1},
        }
    )

    aegis = aegis_block(response)
    policy = cast(dict[str, Any], aegis["policy_decision"])
    detectors = cast(list[dict[str, Any]], aegis["detector_results"])

    assert policy["final_action"] == "allow"
    assert policy["triggered_detectors"] == []
    assert detectors == []


def test_cli_exposes_serve_fixture_command() -> None:
    result = CliRunner().invoke(app, ["serve-fixture", "--help"])

    assert result.exit_code == 0
    assert "Start a local deterministic Aegis-compatible fixture server" in result.output
