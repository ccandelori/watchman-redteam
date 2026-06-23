# Campaign Baseline Promotion Implementation Plan

> **For Hermes:** Implement directly with strict TDD on `feat/redteam-campaigns-v1`. Do not push.

**Goal:** Add `aegis-redteam campaign baseline promote SOURCE BASELINE` to promote validated campaign result JSONL into a reusable baseline file.

**Architecture:** Keep baselines as plain `RedteamResult` JSONL. Do not add a baseline envelope or metadata format. Reuse the shared result loader/writer and existing campaign compare command. Promotion validates source results, writes a redacted normalized JSONL baseline, creates parent directories, rejects empty sources, and refuses to overwrite unless `--force` is passed.

**Tech Stack:** Typer nested subcommands, Pydantic `RedteamResult`, existing JSONL result contract, pytest, uv locked gates.

---

## Scope

In scope:

- Shared `write_results_jsonl` in `src/aegis_redteam/results.py`.
- Campaign baseline promotion helper in `src/aegis_redteam/campaigns/baseline.py`.
- Nested CLI command: `aegis-redteam campaign baseline promote SOURCE BASELINE [--force]`.
- README workflow docs.
- Real fixture smoke: campaign run, promote to baseline, compare against promoted baseline.

Out of scope:

- No new baseline file format.
- No automatic naming or baseline discovery.
- No remote baseline storage.
- No push.

## TDD Tasks

1. Add failing tests for shared result writer redaction and round-trip.
2. Implement `write_results_jsonl` in `results.py` and refactor CLI imports to use it.
3. Add failing tests for `promote_campaign_baseline` success, overwrite rejection, force overwrite, and empty-source rejection.
4. Implement `campaigns/baseline.py`.
5. Add failing CLI tests for `campaign baseline promote` success and overwrite failure.
6. Implement nested Typer baseline app and command.
7. Document command in README.
8. Run locked test/lint/type gates, fixture smoke, build/wheel smoke, commit locally.
