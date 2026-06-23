# Aegis Redteam

External red teaming framework for Aegis.

## Quick Start

```bash
# Install
uv sync --extra dev

# Run scenarios against a running Aegis instance
uv run aegis-redteam run scenarios/ --target http://localhost:8000
```

## Scenarios

Scenarios are defined in YAML. See `scenarios/` for examples.

Use Aegis credential placeholders when a scenario expects DP-HONEY, canary, or
NIMBUS behavior:

```text
{{CREDENTIAL:repo_pat:github_pat}}
```

The runner sends `target_controls` as Aegis request metadata. Supported v0 mock
response modes are:

- `default`
- `echo_last_user`
- `leak_first_honeytoken`
- `base64_first_honeytoken`
- `partial_first_honeytoken`

The runner evaluates the real Aegis response fields:

- `aegis.detector_results`
- `aegis.policy_decision`

## Architecture

- **Black-box HTTP target** (`HttpAegisTarget`)
- **Runner** evaluates scenarios and expectations
- **CLI** for running and reporting results (JSONL output)
- TUI planned for later

## Current Status (v0)

- Runs scenarios over HTTP
- Supports `mock_response_mode` controls
- Evaluates detector and policy expectations
- Produces structured `RedteamResult` JSONL

## Quality

```bash
uv run --extra dev pytest
uv run --extra dev ruff check .
uv run --extra dev mypy src
```
