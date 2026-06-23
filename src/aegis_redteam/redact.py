from __future__ import annotations

import re
from typing import Any

_CREDENTIAL_PATTERN = re.compile(r"sk_live_[A-Za-z0-9]+|sk_test_[A-Za-z0-9]+|Bearer [A-Za-z0-9\-_.~+/]+=*")


def redact_secrets(obj: Any) -> Any:
    """Recursively redact credential-like strings from a dict/list/str."""
    if isinstance(obj, dict):
        return {k: redact_secrets(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_secrets(v) for v in obj]
    if isinstance(obj, str):
        return _CREDENTIAL_PATTERN.sub("[REDACTED]", obj)
    return obj
