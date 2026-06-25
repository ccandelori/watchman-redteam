# Live Targets

This guide covers running against a real Watchman/Aegis HTTP server, probing it
before a run, seeding canaries, and the difference between live and fixture
baselines. For the exact request/response contract see
[`aegis-http-contract.md`](./aegis-http-contract.md).

## Prerequisites

A live run requires a running Watchman/Aegis HTTP server exposing `/health`,
`/test/reset`, `/test/seed-canary`, and `/v1/chat/completions`. The sibling Watchman
repo may only expose `aegis.proxy.mock_app.create_default_proxy` as an in-process
utility; until a real HTTP server exists, use the deterministic fixture
(`aegis-redteam serve-fixture`) to validate runner mechanics over real HTTP.

## Doctor (preflight)

```bash
uv run --locked --extra dev aegis-redteam doctor --target http://localhost:8000
```

`doctor` sends reset, seed-canary, and chat probe requests, so run it only where
test-state mutation is acceptable. It checks `/health`, `/test/reset`,
`/test/seed-canary`, `/v1/chat/completions`, and required Aegis metadata, and exits
nonzero when a required check fails.

Target classification from `/health.capabilities`:

- `fixture` → the deterministic redteam fixture.
- any of `cift`, `dp_honey`, `nimbus` → `live-compatible`.
- otherwise → `unknown-compatible` (doctor does not overclaim live status).

## Seeding canaries vs placeholders

`target_controls.seed_canary` (and the campaign-variant `seed_canary`) is the only
mechanism that plants a real honeytoken: the runner calls `/test/seed-canary` after
`/test/reset` and before the first chat turn, and the target owns the secret value.
Redteam YAML never contains the secret.

Inline `{{CREDENTIAL:slot:type}}` placeholders are **not** resolved — they are sent
to the target verbatim as prompt text. Do not put a literal secret in the type
field; loader validation rejects it. See the credential-placeholder section of
[`aegis-http-contract.md`](./aegis-http-contract.md).

## Multi-turn against live targets

`target_controls.history_mode` controls how prior turns reach the target:

- `latest_user` (default) — sends only the current user turn; the target must own
  conversation history keyed by `metadata.session_id`.
- `full_history` — sends the accumulated transcript each turn, for stateless
  OpenAI-compatible targets.

A multi-turn scenario in `latest_user` mode only exercises real multi-turn behavior
if the target persists session state. See the `history_mode` section of
[`aegis-http-contract.md`](./aegis-http-contract.md).

## Live vs fixture baselines

- **Fixture baselines** (e.g. `baselines/credential-exfil-v1.jsonl`,
  `baselines/encoding-matrix-v1.jsonl`) are strict and deterministic, enforced by
  the CI regression gate.
- **Live baselines** are promoted from real target runs and carry more variance.
  Compare them **without** `--strict` to tolerate natural response/timing drift:

```bash
uv run --locked --extra dev aegis-redteam campaign baseline promote \
  results/live-campaign.jsonl baselines/live-credential-exfil-v1.jsonl --force

uv run --locked --extra dev aegis-redteam campaign compare \
  results/live-campaign.jsonl baselines/live-credential-exfil-v1.jsonl
```

`canonicalize_campaign_baseline_result` always produces deterministic baseline
entries; keep live baselines in separate files from fixture baselines.

## Inspecting and triaging results

```bash
uv run --locked --extra dev aegis-redteam view results/live-campaign.jsonl
uv run --locked --extra dev aegis-redteam tui results/live-campaign.jsonl
uv run --locked --extra dev aegis-redteam summary results/live-campaign.jsonl
uv run --locked --extra dev aegis-redteam summary results/live-campaign.jsonl --json
```

`summary --json` emits a machine-readable root-cause breakdown (categories:
`target_contract`, `detector_expectation`, `policy_expectation`, `egress_response`,
`egress_audit`, `scenario_validation`, `other`) for CI/cron/agent consumption.
