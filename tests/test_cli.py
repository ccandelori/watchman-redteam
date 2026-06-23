from __future__ import annotations

from aegis_redteam.cli import main


def test_console_script_entrypoint_exists() -> None:
    assert callable(main)
