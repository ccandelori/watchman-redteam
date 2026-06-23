from __future__ import annotations

import json
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast

JsonObject = dict[str, Any]


@dataclass(frozen=True)
class RecordedRequest:
    path: str
    body: JsonObject


@dataclass
class FixtureState:
    requests: list[RecordedRequest] = field(default_factory=list)


def latest_user_content(request_body: JsonObject) -> str:
    messages = request_body.get("messages")
    if not isinstance(messages, list):
        return ""

    for message in reversed(messages):
        if not isinstance(message, dict):
            continue
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content
    return ""


def metadata_from_request(request_body: JsonObject) -> JsonObject:
    metadata = request_body.get("metadata")
    if not isinstance(metadata, dict):
        return {}
    return cast(JsonObject, metadata)


def detector_for_request(request_body: JsonObject) -> str | None:
    metadata = metadata_from_request(request_body)
    mode = metadata.get("mock_response_mode")
    user_content = latest_user_content(request_body).lower()

    if mode in {None, "default"}:
        return None
    if mode in {"base64_first_honeytoken", "partial_first_honeytoken"}:
        return "encoded_canary"
    if mode == "leak_first_honeytoken":
        if "hex" in user_content or "reverse" in user_content:
            return "encoded_canary"
        return "text_canary"
    return None


def build_detector_result(detector_name: str) -> JsonObject:
    return {
        "detector_name": detector_name,
        "component": "post_generation",
        "score": 1.0,
        "confidence": 1.0,
        "recommended_action": "block",
        "capability_required": False,
        "capability_status": "available",
        "evidence": {},
        "latency_ms": 0.1,
    }


def build_policy_decision(detector_name: str | None) -> JsonObject:
    if detector_name is None:
        return {
            "final_action": "allow",
            "reason": "fixture allow path",
            "triggered_detectors": [],
            "risk_score": 0.0,
            "sanitized_output": None,
        }
    return {
        "final_action": "block",
        "reason": "fixture detector match",
        "triggered_detectors": [detector_name],
        "risk_score": 1.0,
        "sanitized_output": None,
    }


def build_chat_response(request_body: JsonObject) -> JsonObject:
    metadata = metadata_from_request(request_body)
    turn_index = metadata.get("turn_index", 1)
    detector_name = detector_for_request(request_body)
    detector_results = [] if detector_name is None else [build_detector_result(detector_name)]

    return {
        "id": "chatcmpl-fixture",
        "object": "chat.completion",
        "model": "mock",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "fixture response"},
                "finish_reason": "stop",
            }
        ],
        "aegis": {
            "trace_id": "trace-fixture",
            "turn_index": turn_index,
            "detector_results": detector_results,
            "policy_decision": build_policy_decision(detector_name),
        },
    }


def read_json_body(handler: BaseHTTPRequestHandler) -> JsonObject:
    content_length = int(handler.headers.get("Content-Length", "0"))
    if content_length == 0:
        return {}
    raw_body = handler.rfile.read(content_length).decode("utf-8")
    payload = json.loads(raw_body)
    if not isinstance(payload, dict):
        return {}
    return cast(JsonObject, payload)


def send_json(handler: BaseHTTPRequestHandler, status_code: int, payload: JsonObject) -> None:
    encoded = json.dumps(payload).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(encoded)))
    handler.end_headers()
    handler.wfile.write(encoded)


def make_handler(state: FixtureState) -> type[BaseHTTPRequestHandler]:
    class AegisFixtureHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return

        def do_GET(self) -> None:
            if self.path == "/health":
                send_json(self, 200, {"status": "ok", "capabilities": ["fixture"]})
                return
            send_json(self, 404, {"error": "not found"})

        def do_POST(self) -> None:
            body = read_json_body(self)
            state.requests.append(RecordedRequest(path=self.path, body=body))

            if self.path == "/test/reset":
                send_json(self, 200, {"status": "reset"})
                return
            if self.path == "/v1/chat/completions":
                send_json(self, 200, build_chat_response(body))
                return
            send_json(self, 404, {"error": "not found"})

    return AegisFixtureHandler


def create_fixture_server(host: str, port: int, state: FixtureState) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(state))


def serve_fixture_server(host: str, port: int) -> None:
    state = FixtureState()
    server = create_fixture_server(host, port, state)
    try:
        server.serve_forever()
    finally:
        server.server_close()
