# Aegis HTTP Target Contract

This document is the authoritative reference for how `HttpAegisTarget` talks to an
Aegis/Watchman HTTP target. It treats the target as a black box: the runner never
generates model responses, it only drives requests and asserts on responses.

## Endpoints

| Endpoint | Method | When called |
| --- | --- | --- |
| `/test/reset` | POST | Before the run when `target_controls.reset_before_run` is true |
| `/test/seed-canary` | POST | After reset and before chat when `target_controls.seed_canary` is set |
| `/v1/chat/completions` | POST | Once per `user` turn in the scenario |
| `/audit/recent` | GET | After the chat turns when `expected.egress.inspect_audit` is true |

Any non-2xx response on reset, seed-canary, or chat is a target failure. 3xx
redirects are treated as failures because they usually indicate auth/proxy
misconfiguration rather than a valid contract response.

## Chat request shape

```json
{
  "model": "mock",
  "messages": [{"role": "user", "content": "..."}],
  "metadata": {
    "session_id": "<scenario session>",
    "turn_index": 1,
    "mock_response_mode": "<optional fixture mode>"
  }
}
```

- `metadata.turn_index` is 1-based and equals the position of the turn within the
  scenario's `turns` list (it is not a count of user turns). Non-user turns occupy
  positions too, so a `user` turn at list index 2 reports `turn_index: 3`.
- `metadata.session_id` defaults to `target_controls.session_id`, falling back to the
  scenario name. It is stable across all turns in a scenario.

## Multi-turn semantics: `history_mode`

Multi-turn scenarios contain more than one turn. How prior turns reach the target is
controlled by `target_controls.history_mode`, an explicit enum rather than implicit
behavior:

| Mode | `messages` payload per chat call | Use when |
| --- | --- | --- |
| `latest_user` (default) | Only the current `user` turn | The target owns conversation memory and reconstructs history server-side keyed by `metadata.session_id` |
| `full_history` | All turns (user and assistant) up to and including the current turn | The target is a stateless OpenAI-compatible server that expects the full transcript on every request |

`latest_user` is the default to preserve the original Watchman contract, where the
proxy persists session state by `session_id`. A multi-turn scenario in `latest_user`
mode therefore only exercises real multi-turn behavior if the target actually stores
history server-side; otherwise each request is seen in isolation.

`full_history` accumulates the transcript so multi-turn attacks (for example drip
leakage across turns) can be exercised against stateless targets without relying on
target-side memory. `turn_index` and `session_id` are identical in both modes — only
the `messages` array differs.

### Example

Scenario turns: `user "u1"`, `assistant "a1"`, `user "u2"`.

- `latest_user`: first chat call sends `[u1]`, second sends `[u2]`.
- `full_history`: first chat call sends `[u1]`, second sends `[u1, a1, u2]`.

Assistant turns are never sent as standalone chat requests in either mode; they only
appear inside the `full_history` transcript as prior context.

## Seed canary ordering

When `target_controls.seed_canary` is present the runner calls `/test/seed-canary`
after `/test/reset` and before the first chat turn, using the scenario `session_id`
and the requested `slot_name`, `credential_type`, and explicit `turn_index`. The
third field of an inline `{{CREDENTIAL:slot:type}}` placeholder is a *type label*
(e.g. `openai_key`), not a literal secret value.
