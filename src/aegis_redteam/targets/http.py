from __future__ import annotations

import time
import uuid
from typing import Any, cast

import httpx

from aegis_redteam.models import DetectorResult, PolicyDecision, RedteamResult, Scenario, TurnResult


class HttpAegisTarget:
    """Black-box HTTP target for Aegis."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

    def _metadata_for_turn(
        self, scenario: Scenario, turn_index: int, session_id: str
    ) -> dict[str, Any]:
        controls = scenario.target_controls
        metadata: dict[str, Any] = {
            "session_id": session_id,
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
        session_id = scenario.target_controls.session_id or scenario.name

        if scenario.target_controls.reset_before_run:
            try:
                reset_response = self.client.post(
                    f"{self.base_url}/test/reset", json={"session_id": session_id}
                )
                if reset_response.status_code >= 400:
                    failures.append(
                        f"Reset failed with status {reset_response.status_code}: {reset_response.text}"
                    )
            except httpx.HTTPError as exc:
                failures.append(f"Failed to reset: {exc}")

        messages: list[dict[str, str]] = []
        submitted_turn_index = 0

        for turn in scenario.turns:
            messages.append({"role": turn.role, "content": turn.content})
            if turn.role != "user":
                continue

            submitted_turn_index += 1
            metadata = self._metadata_for_turn(
                scenario=scenario,
                turn_index=submitted_turn_index,
                session_id=session_id,
            )

            payload = {
                "model": "mock",
                "messages": messages,
                "metadata": metadata,
            }

            start = time.time()
            try:
                response = self.client.post(f"{self.base_url}/v1/chat/completions", json=payload)
                latency = int((time.time() - start) * 1000)
                raw = _response_json(response)
                raw_responses.append(raw)
                aegis_meta = _object_value(raw.get("aegis"))

                turn_results.append(
                    TurnResult(
                        turn_index=submitted_turn_index,
                        request=turn,
                        response_status=response.status_code,
                        assistant_content=_assistant_content(raw),
                        aegis_metadata=aegis_meta,
                        detector_results=_detector_results(aegis_meta),
                        policy_decision=_policy_decision(aegis_meta),
                        latency_ms=latency,
                    )
                )
            except httpx.ConnectError as exc:
                failures.append(f"Could not connect to {self.base_url}: {exc}")
            except httpx.HTTPError as exc:
                failures.append(f"Turn {submitted_turn_index} failed: {exc}")

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


def _response_json(response: httpx.Response) -> dict[str, Any]:
    if response.text == "":
        return {}
    try:
        raw = response.json()
    except ValueError:
        return {"raw_text": response.text}
    if not isinstance(raw, dict):
        return {"raw": raw}
    return cast(dict[str, Any], raw)


def _assistant_content(raw: dict[str, Any]) -> str | None:
    choices = raw.get("choices")
    if not isinstance(choices, list) or len(choices) == 0:
        return None
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return None
    message = first_choice.get("message")
    if not isinstance(message, dict):
        return None
    content = message.get("content")
    if isinstance(content, str):
        return content
    return None


def _detector_results(aegis_meta: dict[str, Any]) -> list[DetectorResult]:
    raw_results = aegis_meta.get("detector_results")
    if not isinstance(raw_results, list):
        return []
    results: list[DetectorResult] = []
    for raw_result in raw_results:
        if not isinstance(raw_result, dict):
            continue
        detector_name = raw_result.get("detector_name")
        evidence = _object_value(raw_result.get("evidence"))
        results.append(
            DetectorResult(
                name=detector_name
                if isinstance(detector_name, str) and detector_name != ""
                else "unknown",
                score=_optional_float(raw_result.get("score")),
                recommended_action=_optional_string(raw_result.get("recommended_action")),
                capability_status=_optional_string(raw_result.get("capability_status")),
                evidence=evidence,
            )
        )
    return results


def _policy_decision(aegis_meta: dict[str, Any]) -> PolicyDecision | None:
    raw_policy = aegis_meta.get("policy_decision")
    if not isinstance(raw_policy, dict):
        return None
    final_action = raw_policy.get("final_action")
    if not isinstance(final_action, str) or final_action == "":
        return None
    return PolicyDecision(
        final_action=final_action,
        reason=_policy_reason(raw_policy),
        evidence=_object_value(raw_policy.get("evidence")),
    )


def _object_value(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return cast(dict[str, Any], value)


def _optional_float(value: object) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _optional_string(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None


def _policy_reason(raw_policy: dict[str, Any]) -> str | None:
    reason = _optional_string(raw_policy.get("reason"))
    if reason is not None:
        return reason
    reasons = raw_policy.get("reasons")
    if not isinstance(reasons, list):
        return None
    string_reasons = [value for value in reasons if isinstance(value, str)]
    if len(string_reasons) == 0:
        return None
    return ", ".join(string_reasons)
