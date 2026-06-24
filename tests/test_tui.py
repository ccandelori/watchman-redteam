from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from aegis_redteam.tui.app import RedteamTUI, load_results


def test_redteam_tui_runs_headless_without_external_css_file() -> None:
    async def run_app() -> None:
        async with RedteamTUI([]).run_test():
            return

    asyncio.run(run_app())


def test_tui_load_results_uses_shared_path_line_validation(tmp_path: Path) -> None:
    results_path = tmp_path / "bad.jsonl"
    results_path.write_text("not json\n", encoding="utf-8")

    with pytest.raises(ValueError, match="bad.jsonl:1: invalid JSON"):
        load_results(results_path)
