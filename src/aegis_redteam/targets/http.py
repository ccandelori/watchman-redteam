from __future__ import annotations

import time
import uuid
from typing import Any, cast

import httpx

from aegis_redteam.models import DetectorResult, PolicyDecision, RedteamResult, Scenario, TurnResult
from aegis_redteam.redact import redact_secrets, redact_text


def _response_body(response: httpx.Response) -> dict[str, Any]:
    if response.text == "":
        return {}
    try:
        payload = response.json()
    except ValueError:
        return {"body": response.text}
    if isinstance(payload, dict):
        return payload
    return {"body": payload}


def _is_success_status(status_code: int) -> bool:
    return 200 <= status_code < 300


def _failure(message: str) -> str:
    return redact_text(message)


def _aegis_metadata(response_body: dict[str, Any]) -> dict[str, Any]:
    if "aegis" not in response_body:
        raise ValueError("expected 'aegis' to be present")
    metadata = response_body["aegis"]
    if not isinstance(metadata, dict):
        raise ValueError("expected 'aegis' to be an object")
    return cast(dict[str, Any], metadata)


def _assistant_content(response_body: dict[str, Any]) -> str | None:
    choices = response_body.get("choices")
    if choices is None:
        return None
    if not isinstance(choices, list):
        raise ValueError("expected 'choices' to be a list")
    if len(choices) == 0:
        return None

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise ValueError("expected 'choices[0]' to be an object")

    message = first_choice.get("message")
    if message is None:
        return None
    if not isinstance(message, dict):
        raise ValueError("expected 'choices[0].message' to be an object")

    content = message.get("content")
    if content is None:
        return None
    if not isinstance(content, str):
        raise ValueError("expected 'choices[0].message.content' to be a string")
    return content


def _detector_results(aegis_metadata: dict[str, Any]) -> list[DetectorResult]:
    if "detector_results" not in aegis_metadata:
        raise ValueError("expected 'aegis.detector_results' to be present")
    detector_payloads = aegis_metadata["detector_results"]
    if not isinstance(detector_payloads, list):
        raise ValueError("expected 'aegis.detector_results' to be a list")

    detector_results: list[DetectorResult] = []
    for index, detector_payload in enumerate(detector_payloads):
        if not isinstance(detector_payload, dict):
            raise ValueError(f"expected 'aegis.detector_results[{index}]' to be an object")

        detector_name = detector_payload.get("detector_name")
        if detector_name is None:
            detector_name = detector_payload.get("name")
        if detector_name is None:
            raise ValueError(
                f"expected 'aegis.detector_results[{index}].detector_name' to be present"
            )
        if not isinstance(detector_name, str):
            raise ValueError(f"expected 'aegis.detector_results[{index}].detector_name' to be a string")

        evidence = detector_payload.get("evidence", {})
        if not isinstance(evidence, dict):
            raise ValueError(f"expected 'aegis.detector_results[{index}].evidence' to be an object")

        detector_results.append(
            DetectorResult(
                name=detector_name,
                evidence=cast(dict[str, Any], evidence),
            )
        )
    return detector_results


def _policy_decision(aegis_metadata: dict[str, Any]) -> PolicyDecision | None:
    if "policy_decision" not in aegis_metadata:
        raise ValueError("expected 'aegis.policy_decision' to be present")
    policy_payload = aegis_metadata["policy_decision"]
    if not isinstance(policy_payload, dict):
        raise ValueError("expected 'aegis.policy_decision' to be an object")

    if "final_action" not in policy_payload:
        raise ValueError("expected 'aegis.policy_decision.final_action' to be present")
    final_action = policy_payload["final_action"]
    if not isinstance(final_action, str):
        raise ValueError("expected 'aegis.policy_decision.final_action' to be a string")

    reason = policy_payload.get("reason")
    if reason is not None and not isinstance(reason, str):
        raise ValueError("expected 'aegis.policy_decision.reason' to be a string")

    triggered_detectors_payload = policy_payload.get("triggered_detectors", [])
    if not isinstance(triggered_detectors_payload, list):
        raise ValueError("expected 'aegis.policy_decision.triggered_detectors' to be a list")

    triggered_detectors: list[str] = []
    for index, detector_name in enumerate(triggered_detectors_payload):
        if not isinstance(detector_name, str):
            raise ValueError(
                "expected 'aegis.policy_decision.triggered_detectors"
                f"[{index}]' to be a string"
            )
        triggered_detectors.append(detector_name)

    return PolicyDecision(
        final_action=final_action,
        reason=reason,
        triggered_detectors=triggered_detectors,
    )


class HttpAegisTarget:
    """Black-box HTTP target for Aegis."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

    def _apply_controls(self, scenario: Scenario, turn_index: int) -> dict[str, Any]:
        controls = scenario.target_controls
        metadata: dict[str, Any] = {
            "session_id": controls.session_id or scenario.name,
            "turn_index": turn_index,
        }
        if controls.mock_response_mode:
            metadata["mock_response_mode"] = controls.mock_response_mode
        return metadata

    def run_scenario(self, scenario: Scenario) -> RedteamResult:
        run_id = str(uuid.uuid4())
        started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        turn_results: list[TurnResult] = []
        raw_responses: list[dict[str, Any]] = []
        failures: list[str] = []

        if scenario.target_controls.reset_before_run:
            reset_url = f"{self.base_url}/test/reset"
            try:
                reset_response = self.client.post(reset_url, json={})
                reset_body = redact_secrets(_response_body(reset_response))
                if not _is_success_status(reset_response.status_code):
                    failures.append(
                        _failure(
                            f"Reset returned HTTP {reset_response.status_code} from {reset_url}: "
                            f"{reset_body}"
                        )
                    )
            except httpx.HTTPError as exc:
                failures.append(_failure(f"Failed to reset: {exc}"))

        session_id = scenario.target_controls.session_id or scenario.name

        for idx, turn in enumerate(scenario.turns, start=1):
            if turn.role != "user":
                continue

            metadata = self._apply_controls(scenario, idx)
            metadata["session_id"] = session_id

            payload = {
                "model": "mock",
                "messages": [{"role": "user", "content": turn.content}],
                "metadata": metadata,
            }

            start = time.time()
            try:
                chat_url = f"{self.base_url}/v1/chat/completions"
                resp = self.client.post(chat_url, json=payload)
                latency = int((time.time() - start) * 1000)
                raw = _response_body(resp)
                raw_responses.append(redact_secrets(raw))

                if not _is_success_status(resp.status_code):
                    failures.append(
                        _failure(
                            f"Turn {idx} returned HTTP {resp.status_code} from {chat_url}: "
                            f"{redact_secrets(raw)}"
                        )
                    )
                    turn_results.append(
                        TurnResult(
                            turn_index=idx,
                            request=turn,
                            response_status=resp.status_code,
                            latency_ms=latency,
                        )
                    )
                    continue

                aegis_meta = _aegis_metadata(raw)
                turn_results.append(
                    TurnResult(
                        turn_index=idx,
                        request=turn,
                        response_status=resp.status_code,
                        assistant_content=_assistant_content(raw),
                        aegis_metadata=aegis_meta,
                        detector_results=_detector_results(aegis_meta),
                        policy_decision=_policy_decision(aegis_meta),
                        latency_ms=latency,
                    )
                )

            except httpx.ConnectError as exc:
                failures.append(_failure(f"Could not connect to {self.base_url}: {exc}"))
            except httpx.HTTPError as exc:
                failures.append(_failure(f"Turn {idx} HTTP request failed: {exc}"))
            except ValueError as exc:
                failures.append(_failure(f"Malformed target response on turn {idx}: {exc}"))

        finished_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        passed = len(failures) == 0

        return RedteamResult(
            run_id=run_id,
            scenario_name=scenario.name,
            target_url=self.base_url,
            started_at=started_at,
            finished_at=finished_at,
            passed=passed,
            turn_results=turn_results,
            failures=failures,
            raw_responses=raw_responses,
        )

    def close(self) -> None:
        self.client.close()
