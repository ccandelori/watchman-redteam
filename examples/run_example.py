"""Example script showing how to run the redteam pipeline."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Sequence

from aegis_redteam.models import RedteamResult
from aegis_redteam.runner import run_scenarios
from aegis_redteam.scenarios.loader import load_scenarios
from aegis_redteam.summary import print_summary

DEFAULT_TARGET_URL = "http://localhost:8000"
TARGET_ENV_VAR = "AEGIS_TARGET"


def target_url_from_args(argv: Sequence[str]) -> str:
    if len(argv) > 2:
        raise ValueError("Usage: python examples/run_example.py [target_url]")
    if len(argv) == 2:
        return argv[1]
    return os.environ.get(TARGET_ENV_VAR, DEFAULT_TARGET_URL)


def exit_code_from_results(results: Sequence[RedteamResult]) -> int:
    if any(not result.passed for result in results):
        return 1
    return 0


def main(argv: Sequence[str]) -> int:
    try:
        target_url = target_url_from_args(argv)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    scenarios_dir = Path(__file__).parent.parent / "scenarios"
    scenarios = load_scenarios(scenarios_dir)

    print(f"Loaded {len(scenarios)} scenarios")
    print(f"Target: {target_url}")

    results = run_scenarios(scenarios, target_url)
    print_summary(results)
    return exit_code_from_results(results)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
