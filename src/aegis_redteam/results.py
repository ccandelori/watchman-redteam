from __future__ import annotations

import json
from collections.abc import Sequence
from json import JSONDecodeError
from pathlib import Path

from pydantic import ValidationError

from aegis_redteam.models import RedteamResult
from aegis_redteam.redact import redact_secrets
from aegis_redteam.validation_errors import format_validation_error_details


def load_results_jsonl(path: Path) -> list[RedteamResult]:
    results: list[RedteamResult] = []
    with path.open(encoding="utf-8") as result_file:
        for line_number, line in enumerate(result_file, start=1):
            stripped_line = line.strip()
            if stripped_line == "":
                continue
            try:
                payload = json.loads(stripped_line)
                results.append(RedteamResult.model_validate(payload))
            except JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
            except ValidationError as exc:
                detail = format_validation_error_details(exc)
                raise ValueError(f"{path}:{line_number}: invalid RedteamResult: {detail}") from exc
    return results


def write_results_jsonl(results: Sequence[RedteamResult], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output_file:
        for result in results:
            redacted_result = redact_secrets(result.model_dump())
            output_file.write(RedteamResult.model_validate(redacted_result).model_dump_json() + "\n")
