# CI

The CI workflow (`.github/workflows/ci.yml`) runs on every push and pull request on
a single `quality` job using Python 3.11 and `uv`.

## Pipeline steps

1. **Tests** — `uv run --locked --extra dev pytest -q`
2. **Campaign regression gate** — `uv run --locked --extra dev pytest tests/test_campaign_regression_gate.py -q`
   (parametrized over every committed campaign+baseline pair; see
   [`campaigns.md`](./campaigns.md))
3. **Ruff** — `uv run --locked --extra dev ruff check .`
4. **Mypy (strict)** — `uv run --locked --extra dev mypy src tests`
5. **Build** — `uv build` (produces wheel + sdist in `dist/`)
6. **Installed wheel imports + TUI** — fresh venv, install `dist/*.whl`, verify
   `aegis-redteam --help` and the TUI import.
7. **Installed wheel against HTTP fixture** — `bash scripts/installed_wheel_smoke.sh`

All test/lint/type commands use `--locked` so the committed `uv.lock` is the source
of reproducibility. The cache key globs both `pyproject.toml` and `uv.lock`.

## Installed-wheel fixture smoke

`scripts/installed_wheel_smoke.sh` installs the built wheel into an isolated venv and
exercises the full packaged workflow against the deterministic fixture:

- `serve-fixture`, then wait for `/health`
- `doctor` (expects fixture classification, all checks pass)
- generates a temporary scenario (the wheel does **not** bundle `scenarios/`, so the
  smoke must not depend on the source checkout)
- `run-one`, `run` (writes JSONL), `view`, `report`
- asserts non-empty JSONL and report artifacts
- a single-wheel guard fails loudly on an ambiguous or empty `dist/` glob

Run it locally exactly as CI does:

```bash
uv build
bash scripts/installed_wheel_smoke.sh
```

## Why a floating installed-wheel install

Package metadata is intentionally lower-bound-only. The committed `uv.lock`
stabilizes source-checkout and CI runs, while the installed-wheel smoke installs
without the lockfile — acting as a floating dependency-compatibility canary that
catches runtime-vs-dev dependency misclassification before release.

## Local parity

Reproduce the full gate locally before pushing:

```bash
uv run --locked --extra dev pytest -q
uv run --locked --extra dev ruff check .
uv run --locked --extra dev mypy src tests
uv build && bash scripts/installed_wheel_smoke.sh
```
