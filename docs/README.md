# Documentation

Operational guides for the Aegis redteam runner. The README covers install and
quick start; these documents hold the deeper contract and workflow detail.

- [`aegis-http-contract.md`](./aegis-http-contract.md) — the authoritative HTTP
  target contract: endpoints, chat request shape, `history_mode` multi-turn
  semantics, credential placeholders vs canary seeding, and deterministic fixture
  capabilities.
- [`campaigns.md`](./campaigns.md) — campaign schema, generation, baselines, and the
  regression gate.
- [`live-targets.md`](./live-targets.md) — running against a real Watchman/Aegis
  server: doctor preflight, canary seeding, multi-turn modes, live-vs-fixture
  baselines, and result triage.
- [`ci.md`](./ci.md) — the CI pipeline and the installed-wheel fixture smoke.
