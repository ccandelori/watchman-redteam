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
  "status": "ok",
  "version": "0.1.0",
  "capabilities": ["cift", "dp_honey", "nimbus"]
}
```

### `POST /v1/chat/completions`

This is the primary endpoint. It follows the OpenAI Chat Completions format with Aegis-specific extensions in the response.

#### Request

Standard OpenAI format is accepted:

```json
{
  "model": "gpt-4o-mini",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "tools": [...],
  "temperature": 0.7
}
```

Aegis does not require any custom fields in the request for basic operation.

#### Response

The response follows the OpenAI format but adds an `aegis` top-level field:

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1712345678,
  "model": "gpt-4o-mini",
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
  "usage": { ... },
  "aegis": {
    "trace_id": "trace-abc123",
    "session_id": "sess-xyz789",
    "turn_index": 3,
    "detectors": [
      {
        "name": "TextCanaryDetector",
        "triggered": false,
        "evidence": {}
      },
      {
        "name": "CiftRuntimeDetector",
        "triggered": true,
        "evidence": {
          "cift_window_family": "selected_choice",
          "score": 0.87,
          "degradation_reason": null
        }
      }
    ],
    "policy": {
      "decision": "allow",
      "reason": "no_violation"
    },
    "canaries": {
      "total_detected": 0,
      "by_type": {}
    },
    "nimbus": {
      "session_budget_used": 0.12,
      "session_budget_limit": 1.0
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

## Error Responses

| Status | Description | Body |
|--------|-------------|------|
| 400    | Bad Request | `{ "error": { "message": "..." } }` |
| 500    | Internal Error | `{ "error": { "message": "..." } }` |

## Authentication (Future)

- Currently none.
- Future versions may support an `Authorization: Bearer <token>` header.

## Non-Goals (v0)

- Real model inference (mock provider is acceptable)
- Persistent storage of traces
- Multi-turn session management on the server side (redteam handles this)

---

This contract will be used as the specification for `HttpAegisTarget`. The `InProcessAegisTarget` should aim to produce responses that are structurally compatible with this shape.