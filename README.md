# Aegis Redteam

External red teaming framework for Aegis. The runner treats Aegis as a black-box HTTP target and does not import defense internals.

## Quick Start

```bash
uv sync --extra dev
uv run --extra dev aegis-redteam run scenarios/ --target http://localhost:8000 --output results/latest.jsonl
```

The target must expose:

- `GET /health`
- `POST /test/reset` when scenarios use `target_controls.reset_before_run: true`
- `POST /v1/chat/completions` with OpenAI-compatible response data plus top-level `aegis` metadata

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
- TUI viewer for saved JSONL results

## Current Live E2E Status

A live encoded-leakage smoke run requires a running Aegis HTTP server at the target URL. In this session, `http://localhost:8000/health` returned connection refused, and the sibling Watchman repo appeared to expose `MockProxyApp` only as an in-process test utility, not as a checked-in HTTP server entry point.

Until an HTTP wrapper/server exists, unit and contract tests cover the redteam-side runner behavior. Once the server is available, run:

```bash
uv run --extra dev aegis-redteam run scenarios/ --target http://localhost:8000 --output results/latest.jsonl
```
