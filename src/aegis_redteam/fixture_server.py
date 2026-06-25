from __future__ import annotations

import json
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

JsonObject = dict[str, Any]

# Deterministic audit-safe leak token used only when a scenario explicitly
# requests the audit_leak directive. It is a recognizable secret-family token so
# redteam egress assertions and redaction can be exercised, kept out of the
# default audit-safe path.
_AUDIT_LEAK_TOKEN = "ghp_" + "A" * 36


@dataclass(frozen=True)
class SeededCanary:
    slot_name: str
    credential_type: str
    turn_index: int


@dataclass
class SessionState:
    seeded_canaries: list[SeededCanary] = field(default_factory=list)
    audit_events: list[JsonObject] = field(default_factory=list)


@dataclass(frozen=True)
class RecordedRequest:
    path: str
    body: JsonObject


@dataclass
class FixtureState:
    requests: list[RecordedRequest] = field(default_factory=list)
    sessions: dict[str, SessionState] = field(default_factory=dict)

    def session(self, session_id: str) -> SessionState:
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionState()
        return self.sessions[session_id]


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


def fixture_directive(request_body: JsonObject) -> str | None:
    directive = metadata_from_request(request_body).get("fixture_directive")
    if isinstance(directive, str):
        return directive
    return None


def session_id_from_request(request_body: JsonObject) -> str | None:
    session_id = metadata_from_request(request_body).get("session_id")
    if isinstance(session_id, str):
        return session_id
    return None


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
    directive = fixture_directive(request_body)
    detector_name = detector_for_request(request_body)
    detector_results = [] if detector_name is None else [build_detector_result(detector_name)]
    assistant_content = "fixture response" if detector_name is None else "[aegis output withheld]"

    response: JsonObject = {
        "id": "chatcmpl-fixture",
        "object": "chat.completion",
        "model": "mock",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": assistant_content},
                "finish_reason": "stop",
            }
        ],
    }

    if directive == "malformed_missing_aegis":
        return response

    aegis: JsonObject = {
        "trace_id": "trace-fixture",
        "turn_index": turn_index,
        "detector_results": detector_results,
    }
    if directive != "malformed_missing_policy":
        aegis["policy_decision"] = build_policy_decision(detector_name)
    response["aegis"] = aegis
    return response


def build_audit_event(
    session_id: str,
    session_state: SessionState,
    request_body: JsonObject,
) -> JsonObject:
    detector_name = detector_for_request(request_body)
    policy = build_policy_decision(detector_name)
    slots = [canary.slot_name for canary in session_state.seeded_canaries]
    event: JsonObject = {
        "session_id": session_id,
        "turn_index": metadata_from_request(request_body).get("turn_index", 1),
        "final_action": policy["final_action"],
        "triggered_detectors": policy["triggered_detectors"],
        "honeytoken_slot": slots[0] if len(slots) > 0 else None,
    }
    if fixture_directive(request_body) == "audit_leak":
        event["leaked_value"] = _AUDIT_LEAK_TOKEN
    return event


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


def recent_audit_events(state: FixtureState, session_id: str | None, limit: int) -> list[JsonObject]:
    if session_id is not None:
        session_state = state.sessions.get(session_id)
        events = list(session_state.audit_events) if session_state is not None else []
    else:
        events = [event for session in state.sessions.values() for event in session.audit_events]
    return events[-limit:] if limit > 0 else events


def make_handler(state: FixtureState) -> type[BaseHTTPRequestHandler]:
    class AegisFixtureHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                send_json(self, 200, {"status": "ok", "capabilities": ["fixture"]})
                return
            if parsed.path == "/audit/recent":
                query = parse_qs(parsed.query)
                session_values = query.get("session_id")
                session_id = session_values[0] if session_values else None
                limit_values = query.get("limit")
                limit = int(limit_values[0]) if limit_values else 20
                send_json(
                    self,
                    200,
                    {"events": recent_audit_events(state, session_id, limit)},
                )
                return
            send_json(self, 404, {"error": "not found"})

        def do_POST(self) -> None:
            body = read_json_body(self)
            state.requests.append(RecordedRequest(path=self.path, body=body))

            if self.path == "/test/reset":
                state.sessions.clear()
                send_json(self, 200, {"status": "reset"})
                return
            if self.path == "/test/seed-canary":
                self._record_seed(body)
                send_json(self, 200, {"status": "seeded"})
                return
            if self.path == "/v1/chat/completions":
                self._record_audit(body)
                send_json(self, 200, build_chat_response(body))
                return
            send_json(self, 404, {"error": "not found"})

        def _record_seed(self, body: JsonObject) -> None:
            session_id = body.get("session_id")
            if not isinstance(session_id, str):
                return
            slot_name = body.get("slot_name")
            credential_type = body.get("credential_type")
            turn_index = body.get("turn_index")
            if not (isinstance(slot_name, str) and isinstance(credential_type, str)):
                return
            state.session(session_id).seeded_canaries.append(
                SeededCanary(
                    slot_name=slot_name,
                    credential_type=credential_type,
                    turn_index=turn_index if isinstance(turn_index, int) else 0,
                )
            )

        def _record_audit(self, body: JsonObject) -> None:
            session_id = session_id_from_request(body)
            if session_id is None:
                return
            session_state = state.session(session_id)
            session_state.audit_events.append(
                build_audit_event(session_id, session_state, body)
            )

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
