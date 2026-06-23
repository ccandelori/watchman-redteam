from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast

from typer.testing import CliRunner

from aegis_redteam.cli import app


@dataclass(frozen=True)
class RecordedRequest:
    path: str
    body: dict[str, Any]


@dataclass
class FixtureState:
    requests: list[RecordedRequest] = field(default_factory=list)


def make_handler(state: FixtureState) -> type[BaseHTTPRequestHandler]:
    class AegisFixtureHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return

        def do_GET(self) -> None:
            if self.path == "/health":
                self.send_json(200, {"status": "ok", "capabilities": ["encoded_canary"]})
                return
            self.send_json(404, {"error": "not found"})

        def do_POST(self) -> None:
            body = self.read_json_body()
            state.requests.append(RecordedRequest(path=self.path, body=body))

            if self.path == "/test/reset":
                self.send_json(200, {"status": "reset"})
                return

            if self.path == "/v1/chat/completions":
                self.send_json(200, make_chat_response(body))
                return

            self.send_json(404, {"error": "not found"})

        def read_json_body(self) -> dict[str, Any]:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length == 0:
                return {}
            raw_body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(raw_body)
            if not isinstance(payload, dict):
                return {}
            return cast(dict[str, Any], payload)

        def send_json(self, status_code: int, payload: dict[str, Any]) -> None:
            encoded = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return AegisFixtureHandler


def make_chat_response(request_body: dict[str, Any]) -> dict[str, Any]:
    metadata = request_body.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    turn_index = metadata.get("turn_index", 1)

    return {
        "id": "chatcmpl-fixture",
        "object": "chat.completion",
        "model": "mock",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "blocked encoded canary exfiltration"},
                "finish_reason": "stop",
            }
        ],
        "aegis": {
            "trace_id": "trace-fixture",
            "turn_index": turn_index,
            "detector_results": [
                {
                    "detector_name": "encoded_canary",
                    "component": "post_generation",
                    "score": 1.0,
                    "confidence": 1.0,
                    "recommended_action": "block",
                    "capability_required": False,
                    "capability_status": "available",
                    "evidence": {},
                    "latency_ms": 0.1,
                }
            ],
            "policy_decision": {
                "final_action": "block",
                "reason": "fixture encoded canary match",
                "triggered_detectors": ["encoded_canary"],
                "risk_score": 1.0,
                "sanitized_output": None,
            },
        },
    }


@contextmanager
def fixture_server() -> Iterator[tuple[str, FixtureState]]:
    state = FixtureState()
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state))
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
