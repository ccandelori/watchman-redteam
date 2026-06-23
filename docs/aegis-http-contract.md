# Aegis HTTP Contract (v0)

This document defines the HTTP interface that Aegis exposes for black-box interaction. It is the target contract for `HttpAegisTarget` in the redteam framework.

## Base Assumptions

- Aegis exposes an OpenAI-compatible chat completions endpoint.
- Chat responses include a required top-level `aegis` metadata block containing detector results, a policy decision, and trace identifiers when available.
- The service is intended to run locally during development and testing.
- No authentication is required in the initial version.

## Endpoints

### `GET /health`

Purpose: health check and basic capability reporting.

Example response:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "capabilities": ["cift", "dp_honey", "nimbus"]
}
```

### `POST /test/reset`

Purpose: reset target-side test/session state before a scenario when `target_controls.reset_before_run` is true.

Expected response: any 2xx status. Non-2xx responses are treated as redteam run failures.

### `POST /test/seed-canary`

Purpose: plant a target-side canary before a scenario asks Aegis to leak the first honeytoken. Scenarios use this when they intentionally do not include a `{{CREDENTIAL:...}}` placeholder in the chat turn.

Request:

```json
{
  "session_id": "leak-smoke",
  "slot_name": "api_key",
  "credential_type": "openai_key",
  "turn_index": 0
}
```

Expected response: any 2xx status. Non-2xx responses are treated as redteam run failures.

### `POST /v1/chat/completions`

Primary OpenAI-compatible chat endpoint.

#### Request

The runner sends standard OpenAI-style chat fields and translates scenario `target_controls` into request `metadata`.

```json
{
  "model": "mock",
  "messages": [
    {"role": "user", "content": "..."}
  ],
  "metadata": {
    "session_id": "base64-exfil-smoke",
    "turn_index": 1,
    "mock_response_mode": "base64_first_honeytoken"
  }
}
```

#### Response

The response must be OpenAI-compatible enough for the runner to read assistant content from `choices[0].message.content` when present. The Aegis metadata block is required.

Minimal valid allow response:

```json
{
  "choices": [
    {
      "message": {"role": "assistant", "content": "..."}
    }
  ],
  "aegis": {
    "detector_results": [],
    "policy_decision": {
      "final_action": "allow",
      "triggered_detectors": []
    }
  }
}
```

Detector response shape:

```json
{
  "id": "chatcmpl-trace-abc123",
  "object": "chat.completion",
  "model": "mock",
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "..."},
      "finish_reason": "stop"
    }
  ],
  "aegis": {
    "trace_id": "trace-abc123",
    "policy_decision": {
      "final_action": "block",
      "reason": "highest severity detector fired",
      "triggered_detectors": ["encoded_canary"],
      "risk_score": 1.0,
      "sanitized_output": null
    },
    "detector_results": [
      {
        "detector_name": "encoded_canary",
        "component": "post_generation",
        "score": 1.0,
        "confidence": 1.0,
        "recommended_action": "block",
        "capability_required": false,
        "capability_status": "available",
        "evidence": {},
        "latency_ms": 0.1
      }
    ]
  }
}
```

`HttpAegisTarget` fails closed when required fields are missing or malformed:

- top-level `aegis`
- `aegis.detector_results`
- `aegis.policy_decision`
- `aegis.policy_decision.final_action`
- `aegis.detector_results[*].detector_name` or `aegis.detector_results[*].name`

`HttpAegisTarget` treats every non-2xx chat response as a failed turn and includes the response status and redacted body in `RedteamResult.failures`.

### `GET /audit/recent`

Returns recent audit events for analysis. This endpoint is optional for the redteam runner v0 and is not required by the current CLI scenario execution path.

## Live Target Requirements

A live encoded-leakage E2E run requires a running Aegis HTTP server exposing `/health`, `/test/reset`, and `/v1/chat/completions`. The deterministic fixture server in this repository is only a redteam-owned smoke target for validating the runner path.

Expected live smoke command from a source checkout:

```bash
uv run --locked --extra dev aegis-redteam run scenarios/ --target http://localhost:8000 --output results/latest.jsonl
```
