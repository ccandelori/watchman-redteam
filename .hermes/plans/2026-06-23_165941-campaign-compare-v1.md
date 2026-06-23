# Campaign Compare v1 Implementation Plan

> **For Hermes:** Implement directly with strict TDD on the current `feat/redteam-campaigns-v1` branch. Do not push.

**Goal:** Add a narrow `aegis-redteam campaign compare CURRENT BASELINE` command for campaign result JSONL regression checks.

**Architecture:** Keep campaign comparison as a thin wrapper over the existing `RedteamResult` JSONL contract and comparison semantics. Do not add a campaign envelope or new baseline format. Factor shared JSONL loading into a typed helper so top-level `compare` and campaign compare do not duplicate parsing.

**Tech Stack:** Typer, Pydantic `RedteamResult`, existing `compare_results`, pytest, uv locked gates.

---

## Scope

In scope:

- Add typed JSONL reader helper for `RedteamResult` records.
- Add `CampaignComparison` dataclass/model if useful for a small wrapper return type.
- Add `campaign compare CURRENT BASELINE` CLI subcommand.
- Exit code `1` when regressions are present, matching top-level `compare`.
- Print campaign-specific context without changing the existing Rich comparison table.
- Document the command in README.

Out of scope:

- No new baseline file format.
- No campaign metadata envelope in JSONL.
- No result normalization for UUID/timestamps.
- No stored baseline management command yet.

## Task 1: Shared result JSONL reader

**Objective:** Remove duplicated JSONL parsing from CLI paths and create a reusable helper for campaign compare.

**Files:**

- Create or modify: `src/aegis_redteam/results.py`
- Modify: `src/aegis_redteam/cli.py`
- Test: `tests/test_results.py` or `tests/test_cli.py`

**TDD:**

1. Write a failing test that writes two JSONL `RedteamResult` records and asserts `load_results_jsonl(path)` returns typed `RedteamResult` instances in order.
2. Verify RED: import/function missing.
3. Implement `load_results_jsonl(path: Path) -> list[RedteamResult]` with explicit UTF-8 read and line numbers in invalid-record errors.
4. Verify GREEN with focused test.

## Task 2: Campaign comparison wrapper

**Objective:** Provide a small typed function that compares campaign result JSONL using the existing comparator.

**Files:**

- Create: `src/aegis_redteam/campaigns/compare.py`
- Test: `tests/test_campaign_compare.py`

**TDD:**

1. Write a failing test for `compare_campaign_results(current_path, baseline_path)` returning `regressions`, `improvements`, and `new_scenarios`.
2. Verify RED.
3. Implement by loading both files with `load_results_jsonl` and calling `compare_results`.
4. Verify GREEN.

## Task 3: CLI command

**Objective:** Add `aegis-redteam campaign compare CURRENT BASELINE`.

**Files:**

- Modify: `src/aegis_redteam/cli.py`
- Test: `tests/test_cli.py`

**TDD:**

1. Write a failing CLI test monkeypatching `cli.compare_campaign_results` to return no regressions; assert exit `0` and output includes `Campaign comparison`.
2. Write a failing CLI test for regressions; assert exit `1` and output includes regression count.
3. Implement `@campaign_app.command("compare")`.
4. Verify focused CLI tests pass.

## Task 4: Docs and verification

**Objective:** Document and prove the slice is merge-ready.

**Files:**

- Modify: `README.md`

**Commands:**

```bash
uv run --locked --extra dev pytest -q
uv run --locked --extra dev ruff check .
uv run --locked --extra dev mypy src tests
uv build
```

Installed wheel smoke:

```bash
python -m venv /tmp/aegis-redteam-campaign-compare-wheel-smoke
/tmp/aegis-redteam-campaign-compare-wheel-smoke/bin/python -m pip install dist/*.whl
/tmp/aegis-redteam-campaign-compare-wheel-smoke/bin/aegis-redteam campaign compare --help
/tmp/aegis-redteam-campaign-compare-wheel-smoke/bin/python -c "from aegis_redteam.campaigns.compare import compare_campaign_results; print(compare_campaign_results.__name__)"
```

Commit locally only after all gates pass.
