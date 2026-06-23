# Aegis Redteam

External red teaming framework for Aegis.

## Quick Start

```bash
# Install
uv sync

# Run scenarios against a running Aegis instance
uv run aegis-redteam run scenarios/ --target http://localhost:8000
```

## Scenarios

Scenarios are defined in YAML. See `scenarios/` for examples.

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
