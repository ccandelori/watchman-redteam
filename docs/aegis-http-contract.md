# Aegis HTTP Contract (v0)

This document defines the HTTP interface that Aegis exposes for black-box interaction. It is the target contract for `HttpAegisTarget` in the redteam framework.

## Base Assumptions

- Aegis exposes an OpenAI-compatible chat completions endpoint.
- Chat responses include a top-level `aegis` metadata block containing detector results, a policy decision, and trace identifiers.
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

Current Watchman/Aegis mock proxy responses use this top-level shape:

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

`HttpAegisTarget` treats non-2xx chat responses as failed turns and includes the response status and body in `RedteamResult.failures`.

### `GET /audit/recent`

Returns recent audit events for analysis.

## Current Live E2E Blocker

The sibling Watchman repo currently has an in-process `MockProxyApp` and unit tests around `/v1/chat/completions`, but this session did not find a checked-in HTTP server entry point that exposes that app on `localhost:8000`. A live encoded-leakage E2E run is therefore blocked until one of these is available:

- a running Aegis HTTP server exposing `/health`, `/test/reset`, and `/v1/chat/completions`; or
- a thin development HTTP wrapper around `aegis.proxy.mock_app.create_default_proxy` in the Watchman repo.

Once a server is available, the expected smoke command is:

```bash
uv run --extra dev aegis-redteam run scenarios/ --target http://localhost:8000 --output results/latest.jsonl
```
