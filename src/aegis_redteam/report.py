from __future__ import annotations

from pathlib import Path

from aegis_redteam.models import RedteamResult
from aegis_redteam.redact import redact_text


def generate_markdown_report(results: list[RedteamResult], output_path: Path) -> None:
    """Generate a simple Markdown report from results."""
    lines = ["# Redteam Report\n"]

    passed = sum(1 for r in results if r.passed)
    lines.append(f"**Passed:** {passed}/{len(results)}\n")

    for result in results:
        status = "Passed" if result.passed else "Failed"
        lines.append(f"## {result.scenario_name} — {status}\n")

        for tr in result.turn_results:
            policy = tr.policy_decision.final_action if tr.policy_decision else "-"
            detectors = ", ".join(d.name for d in tr.detector_results) or "-"
            lines.append(f"- Turn {tr.turn_index}: Policy={policy}, Detectors={detectors}")

        if result.failures:
            lines.append("\n**Failures:**")
            for f in result.failures:
                lines.append(f"- {f}")

        lines.append("")

    output_path.write_text(redact_text("\n".join(lines)), encoding="utf-8")
