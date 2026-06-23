# Aegis Redteam

External red teaming framework for Aegis. The runner treats Aegis as a black-box HTTP target and does not import defense internals.

## Quick Start

Against a running Aegis-compatible HTTP target:

```bash
uv sync --extra dev
uv run --extra dev aegis-redteam run scenarios/ --target http://localhost:8000 --output results/latest.jsonl
```

The target must expose:

- `GET /health`
- `POST /test/reset` when scenarios use `target_controls.reset_before_run: true`
- `POST /v1/chat/completions` with OpenAI-compatible response data plus top-level `aegis` metadata

## Local Fixture Smoke

When no Watchman/Aegis HTTP server is running, start the deterministic redteam-owned fixture target in one terminal:

```bash
uv run --extra dev aegis-redteam serve-fixture --port 8799
```

Then run scenarios through the real HTTP target path from another terminal:

```bash
uv run --extra dev aegis-redteam run scenarios/ --target http://127.0.0.1:8799 --output results/fixture-smoke.jsonl
```

Verified fixture smoke result:

```text
14/14 scenarios passed
```

The fixture is a runner smoke target, not a substitute for Watchman/Aegis runtime validation. Use it to validate the redteam HTTP path, CLI exit behavior, JSONL output, and scenario/evaluator contracts.

## Development Gates

```bash
uv run --extra dev pytest -q
uv run --extra dev ruff check .
uv run --extra dev mypy src tests
```

## Scenarios

Scenarios are defined in YAML. See `scenarios/` for examples.

Scenario `target_controls` are translated into HTTP request `metadata`, including `session_id`, `turn_index`, and optional `mock_response_mode`.

## Architecture

- Black-box HTTP target: `HttpAegisTarget`
- YAML scenario loader
- Runner and evaluator for detector and policy expectations
- JSONL result output with credential-like string redaction
- Baseline comparison that exits nonzero on regressions
- Deterministic fixture HTTP target for redteam-side smoke tests
- TUI viewer for saved JSONL results

## Current Live Watchman E2E Status

A live encoded-leakage run against Watchman still requires a running Watchman/Aegis HTTP server at the target URL. In this session, `http://localhost:8000/health` returned connection refused, and the sibling Watchman repo appeared to expose `MockProxyApp` only as an in-process test utility, not as a checked-in HTTP server entry point.

Once a real Watchman/Aegis server is available, run:

```bash
uv run --extra dev aegis-redteam run scenarios/ --target http://localhost:8000 --output results/latest.jsonl
```
