# Campaign Regression Gate Implementation Plan

> **For Hermes:** Implement directly on `feat/redteam-campaigns-v1` using TDD. Do not push.

**Goal:** Turn deterministic campaign tooling into a CI-enforced regression gate.

**Architecture:** Commit a canonical `RedteamResult` JSONL baseline for the credential-exfil campaign. Add a pytest integration gate that starts the redteam fixture in-process, runs the campaign, replays generated YAML, writes current JSONL, and compares against the committed baseline. Keep baseline format as plain `RedteamResult` JSONL with stable run metadata.

**Tech Stack:** pytest, in-process `ThreadingHTTPServer` fixture target, existing campaign runner, scenario runner, baseline compare, GitHub Actions.

---

## Tasks

1. Add canonical baseline normalization to campaign baseline promotion.
2. Add tests proving baseline promotion stabilizes `run_id`, `target_url`, `started_at`, and `finished_at` while preserving scenario/pass signal.
3. Generate and commit `baselines/credential-exfil-v1.jsonl` through the fixture-backed promotion path.
4. Add `tests/test_campaign_regression_gate.py` to run fixture -> campaign -> generated replay -> compare against committed baseline.
5. Add an explicit CI step for the campaign regression gate.
6. Document the baseline and gate workflow in README.
7. Run full locked gates, fixture smoke, build/wheel smoke, independent review, and commit locally.
