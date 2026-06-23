from __future__ import annotations

import re
from typing import Any

_CREDENTIAL_PATTERN = re.compile(
    "|".join(
        [
            r"sk_(?:live|test)_[A-Za-z0-9]+",
            r"sk-proj-[A-Za-z0-9_-]+",
            r"Bearer\s+[A-Za-z0-9\-_.~+/]+=*",
            r"Basic\s+[A-Za-z0-9+/]+=*",
            r"gh[pousr]_[A-Za-z0-9_]{20,}",
            r"AKIA[0-9A-Z]{16}",
            r"(?i:(?:api[_-]?key|access[_-]?key|secret[_-]?key|token|password|passwd|pwd)=[^&\s]+)",
        ]
    )
)


def _redact_string(value: str) -> str:
    return _CREDENTIAL_PATTERN.sub("[REDACTED]", value)


def redact_secrets(obj: Any) -> Any:
    """Recursively redact credential-like strings from keys and values."""
    if isinstance(obj, dict):
        return {
            _redact_string(k) if isinstance(k, str) else k: redact_secrets(v)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [redact_secrets(v) for v in obj]
    if isinstance(obj, str):
        return _redact_string(obj)
    return obj
