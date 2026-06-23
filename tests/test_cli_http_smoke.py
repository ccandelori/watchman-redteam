from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import cast

from typer.testing import CliRunner

from aegis_redteam.cli import app
from aegis_redteam.fixture_server import FixtureState, create_fixture_server


@contextmanager
def fixture_server() -> Iterator[tuple[str, FixtureState]]:
    state = FixtureState()
    server = create_fixture_server("127.0.0.1", 0, state)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = cast(tuple[str, int], server.server_address)
    try:
        yield f"http://{host}:{port}", state
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_run_one_passes_base64_exfil_against_http_fixture() -> None:
    scenario_path = Path("scenarios/base64_exfil.yaml")

    with fixture_server() as (base_url, state):
        result = CliRunner().invoke(app, ["run-one", str(scenario_path), "--target", base_url])

    assert result.exit_code == 0
    assert "base64_exfil" in result.output
    assert "Passed: PASS" in result.output
    assert "Turns: 1" in result.output
    assert "encoded_canary" in result.output
    assert [request.path for request in state.requests] == ["/test/reset", "/v1/chat/completions"]

    chat_request = state.requests[1].body
    metadata = chat_request["metadata"]
    assert metadata["session_id"] == "base64-exfil-smoke"
    assert metadata["turn_index"] == 1
    assert metadata["mock_response_mode"] == "base64_first_honeytoken"
