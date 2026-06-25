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

## Credential placeholders vs canary seeding

There are two distinct, non-interchangeable mechanisms. Confusing them is the most
common authoring mistake.

### `seed_canary` is the live secret mechanism

`target_controls.seed_canary` (and the campaign variant `seed_canary`) is the only
path that plants a real honeytoken in the target. The runner calls
`/test/seed-canary`; the target owns and stores the secret value. Redteam YAML never
contains the secret. This is the mechanism to use for live-target credential-exfil
testing.

### Inline `{{CREDENTIAL:slot:type}}` placeholders are literal, unresolved text

The inline placeholder `{{CREDENTIAL:slot_name:type_label}}` is **not** resolved by
the runner — it is sent to the target verbatim as prompt text. It exists to shape the
prompt, not to inject a secret. Against the deterministic fixture, leak behavior is
driven entirely by `mock_response_mode`, not by any value in the placeholder.

The campaign-template marker `{{credential}}` (lowercase, no fields) is a separate
thing: the campaign generator substitutes it with the campaign-level `credential`
string when generating scenarios.

### Fail-closed validation

The third placeholder field is a **type label** (e.g. `openai_key`, `github_pat`),
never a literal secret. If it looks like a known credential token family
(`sk_live_…`, `sk-proj-…`, `ghp_…`, etc.), scenario and campaign loading fails closed
with a sanitized error that never echoes the offending value. This prevents authors
from mistaking the placeholder for secret injection and from committing literal
secrets into the corpus. Correct: `{{CREDENTIAL:api_key:openai_key}}`. Rejected:
`{{CREDENTIAL:api_key:sk_live_1234}}`.

Note: `forbidden_response_substrings`/`forbidden_audit_substrings` entries such as
`"sk_live_"` are unaffected — validation only inspects the type field *inside* a
`{{CREDENTIAL:…}}` placeholder.

## Deterministic fixture capabilities

The redteam-owned fixture server (`aegis-redteam serve-fixture`) is a deterministic,
black-box-preserving stand-in for a real Aegis/Watchman target. It advertises
`capabilities: ["fixture"]` on `/health` so `doctor` classifies it as a fixture. Its
behavior is driven entirely by request metadata, never by any secret value in the
prompt.

### Session-keyed state

Fixture state is keyed by `metadata.session_id`:

- `/test/seed-canary` records the seeded canary (`slot_name`, `credential_type`,
  `turn_index`) under its session.
- `/v1/chat/completions` appends an audit event to its session.
- `/audit/recent?session_id=<id>&limit=<n>` returns the most recent events for that
  session; omitting `session_id` returns events across all sessions.
- `/test/reset` clears all session state (seeded canaries and audit events). It does
  not clear the in-process request-recording log used by tests.

### Audit-safe by default

Audit events use neutral field names (`session_id`, `turn_index`, `final_action`,
`triggered_detectors`, `honeytoken_slot`) and never contain a secret value. The
`honeytoken_slot` field reports the seeded slot label (e.g. `api_key`), not a
credential.

### Test-only directives

A scenario may set `metadata.fixture_directive` to exercise edge cases. These are
fixture capabilities for redteam runner testing, not part of the real target
contract:

| Directive | Effect |
| --- | --- |
| `audit_leak` | Audit event includes a recognizable secret-family token, so egress assertions and redaction can be exercised |
| `malformed_missing_aegis` | Chat response omits the top-level `aegis` object |
| `malformed_missing_policy` | Chat response omits `aegis.policy_decision` |

The malformed directives let tests assert the runner reports a clean target failure
rather than a traceback.
