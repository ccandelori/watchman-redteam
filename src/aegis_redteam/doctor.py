from __future__ import annotations

from typing import Any, cast

import httpx
from pydantic import BaseModel

from aegis_redteam.redact import redact_secrets, redact_text

JsonObject = dict[str, Any]


class DoctorCheck(BaseModel):
    name: str
    required: bool
    passed: bool
    detail: str


class DoctorReport(BaseModel):
    target_url: str
    target_kind: str
    passed: bool
    checks: list[DoctorCheck]


def _is_success_status(status_code: int) -> bool:
    return 200 <= status_code < 300


def _response_body(response: httpx.Response) -> JsonObject:
    if response.text == "":
        return {}
    try:
        payload = response.json()
    except ValueError:
        return {"body": response.text}
    if isinstance(payload, dict):
        return cast(JsonObject, payload)
    return {"body": payload}


def _detail(value: object) -> str:
    return redact_text(str(redact_secrets(value)))


def _passed_check(name: str) -> DoctorCheck:
    return DoctorCheck(name=name, required=True, passed=True, detail="ok")


def _failed_check(name: str, detail: str) -> DoctorCheck:
    return DoctorCheck(name=name, required=True, passed=False, detail=redact_text(detail))


def _target_kind_from_health(body: JsonObject) -> str:
    capabilities = body.get("capabilities")
    if isinstance(capabilities, list) and "fixture" in capabilities:
        return "fixture"
    return "live_or_unknown"


def _metadata_failure(response_body: JsonObject) -> str | None:
    if "aegis" not in response_body:
        return "expected 'aegis' to be present"
    metadata = response_body["aegis"]
    if not isinstance(metadata, dict):
        return "expected 'aegis' to be an object"
    if "detector_results" not in metadata:
        return "expected 'aegis.detector_results' to be present"
    detector_payloads = metadata["detector_results"]
    if not isinstance(detector_payloads, list):
        return "expected 'aegis.detector_results' to be a list"
    for index, detector_payload in enumerate(detector_payloads):
        if not isinstance(detector_payload, dict):
            return f"expected 'aegis.detector_results[{index}]' to be an object"
        detector_name = detector_payload.get("detector_name", detector_payload.get("name"))
        if detector_name is None:
            return f"expected 'aegis.detector_results[{index}].detector_name' to be present"
        if not isinstance(detector_name, str):
            return f"expected 'aegis.detector_results[{index}].detector_name' to be a string"
    if "policy_decision" not in metadata:
        return "expected 'aegis.policy_decision' to be present"
    policy_payload = metadata["policy_decision"]
    if not isinstance(policy_payload, dict):
        return "expected 'aegis.policy_decision' to be an object"
    if "final_action" not in policy_payload:
        return "expected 'aegis.policy_decision.final_action' to be present"
    if not isinstance(policy_payload["final_action"], str):
        return "expected 'aegis.policy_decision.final_action' to be a string"
    return None


def _health_check(client: httpx.Client, base_url: str) -> tuple[DoctorCheck, str]:
    health_url = f"{base_url}/health"
    try:
        response = client.get(health_url)
    except httpx.HTTPError as exc:
        return _failed_check("health", f"Health request failed for {health_url}: {exc}"), "unknown"

    body = _response_body(response)
    if not _is_success_status(response.status_code):
        return (
            _failed_check(
                "health",
                f"Health returned HTTP {response.status_code} from {health_url}: {_detail(body)}",
            ),
            _target_kind_from_health(body),
        )
    return _passed_check("health"), _target_kind_from_health(body)


def _reset_check(client: httpx.Client, base_url: str) -> DoctorCheck:
    reset_url = f"{base_url}/test/reset"
    try:
        response = client.post(reset_url, json={})
    except httpx.HTTPError as exc:
        return _failed_check("reset", f"Reset request failed for {reset_url}: {exc}")

    body = _response_body(response)
    if not _is_success_status(response.status_code):
        return _failed_check(
            "reset",
            f"Reset returned HTTP {response.status_code} from {reset_url}: {_detail(body)}",
        )
    return _passed_check("reset")


def _chat_payload() -> JsonObject:
    return {
        "model": "mock",
        "messages": [{"role": "user", "content": "doctor probe"}],
        "metadata": {
            "session_id": "doctor-probe",
            "turn_index": 1,
            "mock_response_mode": "default",
        },
    }


def _chat_checks(client: httpx.Client, base_url: str) -> list[DoctorCheck]:
    chat_url = f"{base_url}/v1/chat/completions"
    try:
        response = client.post(chat_url, json=_chat_payload())
    except httpx.HTTPError as exc:
        return [
            _failed_check("chat", f"Chat request failed for {chat_url}: {exc}"),
            _failed_check("aegis_metadata", "chat check failed before metadata validation"),
        ]

    body = _response_body(response)
    if not _is_success_status(response.status_code):
        return [
            _failed_check(
                "chat",
                f"Chat returned HTTP {response.status_code} from {chat_url}: {_detail(body)}",
            ),
            _failed_check("aegis_metadata", "chat check failed before metadata validation"),
        ]

    metadata_failure = _metadata_failure(body)
    if metadata_failure is not None:
        return [_passed_check("chat"), _failed_check("aegis_metadata", metadata_failure)]
    return [_passed_check("chat"), _passed_check("aegis_metadata")]


def run_doctor(target_url: str, timeout: float) -> DoctorReport:
    base_url = target_url.rstrip("/")
    checks: list[DoctorCheck] = []

    with httpx.Client(timeout=timeout) as client:
        health_check, target_kind = _health_check(client, base_url)
        checks.append(health_check)
        checks.append(_reset_check(client, base_url))
        checks.extend(_chat_checks(client, base_url))

    passed = all(check.passed for check in checks if check.required)
    return DoctorReport(target_url=base_url, target_kind=target_kind, passed=passed, checks=checks)
