from __future__ import annotations

import json
from pathlib import Path

from aegis_redteam.models import RedteamResult, Turn, TurnResult


def test_cli_exposes_configured_entrypoint() -> None:
    from aegis_redteam.cli import main

    assert callable(main)


def test_write_results_jsonl_redacts_secrets(tmp_path: Path) -> None:
    from aegis_redteam.cli import write_results_jsonl

    output_path = tmp_path / "results.jsonl"
    secret = "sk_live_1234567890abcdef"
    result = RedteamResult(
        run_id="run-1",
        scenario_name="secret-output",
        target_url="http://localhost:8000",
        started_at="2026-06-23T00:00:00Z",
        finished_at="2026-06-23T00:00:01Z",
        passed=True,
        turn_results=[
            TurnResult(
                turn_index=1,
                request=Turn(role="user", content=f"please encode {secret}"),
                response_status=200,
                assistant_content=f"encoded {secret}",
                aegis_metadata={"evidence": secret},
            )
        ],
        raw_responses=[{"raw_secret": secret}],
    )

    write_results_jsonl([result], output_path)

    saved_text = output_path.read_text()
    saved_record = json.loads(saved_text)

    assert secret not in saved_text
    assert "[REDACTED]" in saved_text
    assert saved_record["scenario_name"] == "secret-output"
