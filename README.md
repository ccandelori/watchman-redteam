# Aegis Redteam

External red teaming framework for Aegis. The runner treats Aegis as a black-box HTTP target and does not import defense internals.

## Prerequisites

Use Python 3.11 to match CI, and install `uv` before running the quick-start commands. The repository includes `.python-version` so `uv` and common Python version managers default to the CI Python family.

```bash
python3 --version
uv --version
```

If `uv` is missing, install it with the official installer and restart your shell:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

See the upstream `uv` installation docs for platform-specific alternatives: <https://docs.astral.sh/uv/getting-started/installation/>.

## Quick Start

Against a running Aegis-compatible HTTP target from a source checkout:

```bash
uv sync --python 3.11 --locked --extra dev
uv run --locked --extra dev aegis-redteam run scenarios/ --target http://localhost:8000 --output results/latest.jsonl
```

The `scenarios/` directory is part of the source checkout. Installed wheels provide the CLI and Python package, but do not currently install the top-level example scenarios.

The target must expose:

- `GET /health`
- `POST /test/reset` when scenarios use `target_controls.reset_before_run: true`
- `POST /v1/chat/completions` with OpenAI-compatible response data plus required top-level `aegis` metadata

Minimal valid no-detector response:

```json
{
  "choices": [{"message": {"content": "assistant response"}}],
  "aegis": {
    "detector_results": [],
    "policy_decision": {
      "final_action": "allow",
      "triggered_detectors": []
    }
  }
}
```

Detector entries must include `detector_name` or `name`. `HttpAegisTarget` treats every non-2xx reset/chat response as a target failure.

## Local Fixture Smoke

When no Watchman/Aegis HTTP server is running, start the deterministic redteam-owned fixture target in one terminal:

```bash
uv run --locked --extra dev aegis-redteam serve-fixture --port 8799
```

Then run scenarios through the real HTTP target path from another terminal:

```bash
uv run --locked --extra dev aegis-redteam run scenarios/ --target http://127.0.0.1:8799 --output results/fixture-smoke.jsonl
```

Expected fixture smoke result:

```text
14/14 scenarios passed
```

The fixture is a runner smoke target, not a substitute for Watchman/Aegis runtime validation. Use it to validate the redteam HTTP path, CLI exit behavior, JSONL output, and scenario/evaluator contracts.

## Inspecting Results

Run one scenario with detailed per-turn output:

```bash
uv run --locked --extra dev aegis-redteam run-one scenarios/base64_exfil.yaml --target http://127.0.0.1:8799
```

View a saved JSONL result as a Rich table:

```bash
uv run --locked --extra dev aegis-redteam view results/fixture-smoke.jsonl
```

Generate a Markdown report:

```bash
uv run --locked --extra dev aegis-redteam report results/fixture-smoke.jsonl results/fixture-smoke.md
```

Compare a current run against a baseline. The command exits nonzero when regressions are detected.

```bash
uv run --locked --extra dev aegis-redteam compare results/fixture-smoke.jsonl results/fixture-smoke.jsonl
```

Expected self-compare summary:

```text
Regressions: 0 | Improvements: 0 | New: 0
```

## Build and Installed-Wheel Smoke

CI builds the package and verifies that a normal wheel install can import the CLI/TUI dependencies.

```bash
uv build
uv venv /tmp/aegis-redteam-smoke --python 3.11
uv pip install --python /tmp/aegis-redteam-smoke/bin/python dist/*.whl
/tmp/aegis-redteam-smoke/bin/aegis-redteam --help
/tmp/aegis-redteam-smoke/bin/python -c "from aegis_redteam.tui.app import RedteamTUI; print(RedteamTUI.__name__)"
```

Installed wheels do not include the source-checkout `scenarios/` directory. Run scenario smoke tests from the repository checkout, or pass paths to your own scenario YAML files.

## Development Gates

```bash
uv run --locked --extra dev pytest -q
uv run --locked --extra dev ruff check .
uv run --locked --extra dev mypy src tests
```

The repository commits `uv.lock` for source-checkout and CI reproducibility. To intentionally refresh dependencies, run `uv lock --upgrade`, then rerun the locked development gates before committing the lockfile update.

## Scenarios

Scenarios are defined in YAML. In a source checkout, see `scenarios/` for examples.

Scenario `target_controls` are translated into HTTP request `metadata`, including `session_id`, `turn_index`, and optional `mock_response_mode`.

## Architecture

- Black-box HTTP target: `HttpAegisTarget`
- YAML scenario loader
- Runner and evaluator for detector and policy expectations
- JSONL result output with credential-like string redaction
- Baseline comparison that exits nonzero on regressions
- Deterministic fixture HTTP target for redteam-side smoke tests
- Rich table viewer for saved JSONL results
- Textual TUI components available for future interactive result browsing

## Live Target Requirements

A live encoded-leakage E2E run requires a running Watchman/Aegis HTTP server at the target URL. The server must expose `/health`, `/test/reset`, and `/v1/chat/completions` using the contract documented in `docs/aegis-http-contract.md`.

Once a real Watchman/Aegis server is available, run:

```bash
uv run --locked --extra dev aegis-redteam run scenarios/ --target http://localhost:8000 --output results/latest.jsonl
```
