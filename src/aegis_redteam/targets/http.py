from __future__ import annotations

import time
import uuid
from typing import Any

import httpx

from aegis_redteam.models import Scenario, RedteamResult, TurnResult, DetectorResult, PolicyDecision
from aegis_redteam.redact import redact_secrets


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


def _aegis_metadata(response_body: dict[str, Any]) -> dict[str, Any]:
    metadata = response_body.get("aegis", {})
    if not isinstance(metadata, dict):
        raise ValueError("expected 'aegis' to be an object")
    return metadata


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
                if reset_response.status_code >= 400:
                    failures.append(
                        f"Reset returned HTTP {reset_response.status_code} from {reset_url}: "
                        f"{reset_body}"
                    )
            except httpx.HTTPError as exc:
                failures.append(f"Failed to reset: {exc}")

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

                if resp.status_code >= 400:
                    failures.append(
                        f"Turn {idx} returned HTTP {resp.status_code} from {chat_url}: "
                        f"{redact_secrets(raw)}"
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

                assistant_content = None
                aegis_meta = _aegis_metadata(raw)
                detector_results: list[DetectorResult] = []
                policy_decision = None

                if "choices" in raw and raw["choices"]:
                    assistant_content = raw["choices"][0]["message"].get("content")

                for d in aegis_meta.get("detector_results", []):
                    detector_results.append(
                        DetectorResult(
                            name=d.get("name", d.get("detector_name", "unknown")),
                            evidence=d.get("evidence", {}),
                        )
                    )

                if "policy_decision" in aegis_meta:
                    pol = aegis_meta["policy_decision"]
                    policy_decision = PolicyDecision(
                        final_action=pol.get("final_action", "unknown"),
                        reason=pol.get("reason"),
                        triggered_detectors=[
                            detector_name
                            for detector_name in pol.get("triggered_detectors", [])
                            if isinstance(detector_name, str)
                        ],
                    )

                turn_results.append(
                    TurnResult(
                        turn_index=idx,
                        request=turn,
                        response_status=resp.status_code,
                        assistant_content=assistant_content,
                        aegis_metadata=aegis_meta,
                        detector_results=detector_results,
                        policy_decision=policy_decision,
                        latency_ms=latency,
                    )
                )

            except httpx.ConnectError as exc:
                failures.append(f"Could not connect to {self.base_url}: {exc}")
            except httpx.HTTPError as exc:
                failures.append(f"Turn {idx} HTTP request failed: {exc}")
            except ValueError as exc:
                failures.append(f"Malformed target response on turn {idx}: {exc}")

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
