# Aegis HTTP Contract (v0)

This document defines the HTTP interface that Aegis exposes for black-box interaction. It is the target contract for `HttpAegisTarget` in the redteam framework.

## Base Assumptions

- Aegis exposes an **OpenAI-compatible** chat completions endpoint.
- All responses include an `aegis` metadata block containing detector results, policy decisions, and trace identifiers.
- The service is intended to be run locally during development and testing.
- No authentication is required in the initial version (can be added later).

## Endpoints

### `GET /health`

**Purpose**: Health check and basic capability reporting.

**Response (200 OK)**

```json
{
  "status": "ok"
}
```

### `POST /v1/chat/completions`

This is the primary endpoint. It follows the OpenAI Chat Completions format with Aegis-specific extensions in the response.

#### Request

Standard OpenAI format is accepted:

```json
{
  "model": "mock-model",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "metadata": {
    "trace_id": "trace-abc123",
    "session_id": "sess-xyz789",
    "turn_index": 1,
    "mock_response_mode": "base64_first_honeytoken"
  }
}
```

The `metadata` object is optional for basic operation. The redteam runner uses
it to pass deterministic development controls to Aegis. Supported
`mock_response_mode` values are `default`, `echo_last_user`,
`leak_first_honeytoken`, `base64_first_honeytoken`, and
`partial_first_honeytoken`.

#### Response

The response follows the OpenAI format but adds an `aegis` top-level field:

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "mock-model",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "..."
      },
      "finish_reason": "stop"
    }
  ],
  "aegis": {
    "trace_id": "trace-abc123",
    "detector_results": [
      {
        "detector_name": "encoded_canary",
        "component": "text_canary",
        "score": 1.0,
        "confidence": 1.0,
        "recommended_action": "escalate",
        "capability_required": null,
        "capability_status": "active",
        "evidence": {
          "reason": "encoded_canary_leak_detected"
        },
        "latency_ms": 0.0
      },
      {
        "detector_name": "nimbus",
        "component": "nimbus",
        "score": 1.0,
        "confidence": 0.8,
        "recommended_action": "block",
        "capability_required": null,
        "capability_status": "active",
        "evidence": {
          "turn_estimated_leakage_bits": 0.4,
          "cumulative_estimated_leakage_bits": 1.2
        },
        "latency_ms": 0.0
      }
    ],
    "policy_decision": {
      "final_action": "block",
      "reasons": ["detector_recommended_block"],
      "evidence": {}
    }
  }
}
```

### `GET /audit/recent`

Returns recent audit events (useful for red team analysis).

**Query Parameters**
- `limit` (optional, default: 20)
- `trace_id` (optional)

**Response**

```json
{
  "events": [
    {
      "timestamp": "2026-06-23T12:34:56Z",
      "trace_id": "trace-abc123",
      "event_type": "policy_decision",
      "data": { ... }
    }
  ]
}
```

### `POST /test/reset`

Development-only route used to isolate repeatable redteam runs.

**Request**

```json
{
  "session_id": "sess-xyz789"
}
```

**Response**

```json
{
  "status": "reset",
  "audit_events_cleared": true,
  "session_id": "sess-xyz789"
}
```

## Error Responses

| Status | Description | Body |
|--------|-------------|------|
| 400    | Bad Request | `{ "error": "..." }` |
| 500    | Internal Error | `{ "error": "..." }` |

## Authentication (Future)

- Currently none.
- Future versions may support an `Authorization: Bearer <token>` header.

## Credential Placeholders

Redteam scenarios can ask Aegis to plant fake honeytokens by including a
credential placeholder in a chat message:

```text
{{CREDENTIAL:repo_pat:github_pat}}
```

Aegis replaces the placeholder before model generation. Scenario content should
not contain raw production secrets.

## Non-Goals (v0)

- Real model inference (mock provider is acceptable)
- Persistent storage of traces
- Production use of deterministic mock response controls

---

This contract is the specification for `HttpAegisTarget`.
