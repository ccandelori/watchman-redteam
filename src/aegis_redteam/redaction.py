from __future__ import annotations

import re
from typing import Any, Dict, List

_SECRET_PATTERNS = [
    r"sk_live_[0-9a-zA-Z]{10,}",
    r"sk_test_[0-9a-zA-Z]{10,}",
    r"AIza[0-9A-Za-z\-_]{35}",
    r"-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----",
]

def _redact_text(text: str) -> str:
    for pattern in _SECRET_PATTERNS:
        text = re.sub(pattern, "[REDACTED]", text)
    return text

def redact_result(result: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively redact potential secrets from a result dict."""
    if isinstance(result, dict):
        return {k: redact_result(v) for k, v in result.items()}
    elif isinstance(result, list):
        return [redact_result(item) for item in result]
    elif isinstance(result, str):
        return _redact_text(result)
    else:
        return result
