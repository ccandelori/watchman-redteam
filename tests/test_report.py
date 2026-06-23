from pathlib import Path

from aegis_redteam.models import RedteamResult
from aegis_redteam.report import generate_markdown_report

REPORT_TOKEN = "sk-proj-" + "R" * 20 + "_abcdefABCDEF"


def test_generate_markdown_report_redacts_failure_secrets(tmp_path: Path) -> None:
    output_path = tmp_path / "report.md"
    result = RedteamResult(
        run_id="run-1",
        scenario_name="secret-report",
        target_url="http://localhost:8000",
        started_at="2026-06-23T00:00:00Z",
        finished_at="2026-06-23T00:00:01Z",
        passed=False,
        failures=[f"target returned credential {REPORT_TOKEN}"],
    )

    generate_markdown_report([result], output_path)

    report_text = output_path.read_text()
    assert REPORT_TOKEN not in report_text
    assert "[REDACTED]" in report_text
