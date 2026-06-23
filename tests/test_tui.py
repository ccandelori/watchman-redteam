from __future__ import annotations

import asyncio

from aegis_redteam.tui.app import RedteamTUI


def test_redteam_tui_runs_headless_without_external_css_file() -> None:
    async def run_app() -> None:
        async with RedteamTUI([]).run_test():
            return

    asyncio.run(run_app())
