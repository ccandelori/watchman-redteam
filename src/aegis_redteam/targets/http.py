from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional

import httpx

from aegis_redteam.models import Scenario, RedteamResult, TurnResult, DetectorResult, PolicyDecision


class HttpAegisTarget:
    """Black-box HTTP target for Aegis (uses the public /v1/chat/completions endpoint)."""

    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

    def _apply_controls(self, scenario: Scenario, turn_index: int) -> Dict[str, Any]:
        """Translate runner-side target_controls into Aegis metadata."""
        controls = scenario.target_controls
        metadata: Dict[str, Any] = {
            "session_id": controls.session_id or scenario.name,
            "turn_index": turn_index,
        }
        if controls.mock_response_mode:
            metadata["mock_response_mode"] = controls.mock_response_mode
        return metadata

    def run_scenario(self, scenario: Scenario) -> RedteamResult:
        run_id = str(uuid.uuid4())
        started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        turn_results = []
        raw_responses = []
        failures = []

        # Handle reset if requested
        if scenario.target_controls.reset_before_run:
            try:
                self.client.post(f"{self.base_url}/test/reset")
            except Exception as exc:
                failures.append(f"Failed to reset: {exc}")

        session_id = scenario.target_controls.session_id or scenario.name

        for idx, turn in enumerate(scenario.turns, start=1):
            if turn.role != "user":
                continue  # For v0 we only send user turns

            metadata = self._apply_controls(scenario, idx)
            metadata["session_id"] = session_id

            payload = {
                "model": "mock",
                "messages": [{"role": "user", "content": turn.content}],
                "metadata": metadata,
            }

            start = time.time()
            try:
                resp = self.client.post(
                    f"{self.base_url}/v1/chat/completions", json=payload
                )
                latency = int((time.time() - start) * 1000)
                raw = resp.json() if resp.text else {}
                raw_responses.append(raw)

                assistant_content = None
                aegis_meta = raw.get("aegis", {})
                detector_results = []
                policy_decision = None

                if "choices" in raw and raw["choices"]:
                    assistant_content = raw["choices"][0]["message"].get("content")

                # Extract detector results
                for d in aegis_meta.get("detectors", []):
                    detector_results.append(
                        DetectorResult(
                            name=d.get("name", d.get("detector_name", "unknown")),
                            evidence=d.get("evidence", {}),
                        )
                    )

                # Policy decision
                if "policy" in aegis_meta:
                    pol = aegis_meta["policy"]
                    policy_decision = PolicyDecision(
                        final_action=pol.get("final_action", pol.get("action", "unknown")),
                        reason=pol.get("reason"),
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

            except Exception as exc:
                failures.append(f"Turn {idx} failed: {exc}")

        finished_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Basic pass/fail logic (can be improved later)
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

    def close(self):
        self.client.close()
