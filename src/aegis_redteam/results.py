from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path

from pydantic import ValidationError

from aegis_redteam.models import RedteamResult


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
                raise ValueError(f"{path}:{line_number}: invalid RedteamResult: {exc}") from exc
    return results
