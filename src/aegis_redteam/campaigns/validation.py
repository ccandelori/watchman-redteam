from __future__ import annotations

from pathlib import Path

from aegis_redteam.models import RedteamResult


def validate_unique_scenario_names(results: list[RedteamResult], source_path: Path) -> None:
    seen_names: set[str] = set()
    duplicate_names: set[str] = set()
    for result in results:
        if result.scenario_name in seen_names:
            duplicate_names.add(result.scenario_name)
        seen_names.add(result.scenario_name)

    if len(duplicate_names) > 0:
        duplicate_name = sorted(duplicate_names)[0]
        raise ValueError(f"{source_path}: duplicate scenario_name: {duplicate_name}")
