from __future__ import annotations

import re
from typing import Any

_AUTH_TOKEN_PATTERN = re.compile(r"\b(Bearer)\s+([A-Za-z0-9\-_.~+/]{16,}=*)")
_BASIC_TOKEN_PATTERN = re.compile(r"\b(Basic)\s+([A-Za-z0-9+/]{12,}=*)")
_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?key|secret[_-]?key|token|password|passwd|pwd)=([^&\s]+)"
)
_TOKEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"sk_(?:live|test)_[A-Za-z0-9]+"),
    re.compile(r"sk-proj-[A-Za-z0-9_-]+"),
    re.compile(r"sk-ant-[A-Za-z0-9_-]+"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{20,}"),
    re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}"),
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    re.compile(r"ya29\.[0-9A-Za-z_-]+"),
    re.compile(r"[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
)
_SENSITIVE_KEYS = {
    "authorization",
    "proxy_authorization",
    "cookie",
    "set_cookie",
    "api_key",
    "apikey",
    "access_key",
    "secret_key",
    "private_key",
    "access_token",
    "refresh_token",
    "client_secret",
    "password",
    "passwd",
    "pwd",
    "secret",
    "token",
}
_SENSITIVE_KEY_SUFFIXES = ("_token", "_secret", "_password")
_REDACTION_MARKER = "[REDACTED]"


def _redact_auth_match(match: re.Match[str]) -> str:
    return f"{match.group(1)} {_REDACTION_MARKER}"


def _redact_assignment_match(match: re.Match[str]) -> str:
    return f"{match.group(1)}={_REDACTION_MARKER}"


def _normalized_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")


def _is_sensitive_key(key: str) -> bool:
    normalized = _normalized_key(key)
    if normalized in _SENSITIVE_KEYS:
        return True
    return normalized.endswith(_SENSITIVE_KEY_SUFFIXES)


def _redact_string(value: str) -> str:
    result = _AUTH_TOKEN_PATTERN.sub(_redact_auth_match, value)
    result = _BASIC_TOKEN_PATTERN.sub(_redact_auth_match, result)
    result = _ASSIGNMENT_PATTERN.sub(_redact_assignment_match, result)
    for pattern in _TOKEN_PATTERNS:
        result = pattern.sub(_REDACTION_MARKER, result)
    return result


def _redact_sensitive_string(key: str, value: str) -> str:
    normalized = _normalized_key(key)
    if normalized in {"authorization", "proxy_authorization"}:
        redacted = _redact_string(value)
        if redacted != value:
            return redacted
    return _REDACTION_MARKER


def _redact_value(obj: Any, parent_key: str | None) -> Any:
    if isinstance(obj, dict):
        redacted: dict[Any, Any] = {}
        for key, value in obj.items():
            redacted_key = _redact_string(key) if isinstance(key, str) else key
            if isinstance(key, str) and _is_sensitive_key(key):
                if isinstance(value, str):
                    redacted[redacted_key] = _redact_sensitive_string(key, value)
                else:
                    redacted[redacted_key] = redact_secrets(value)
            else:
                redacted[redacted_key] = _redact_value(value, key if isinstance(key, str) else None)
        return redacted
    if isinstance(obj, list):
        return [_redact_value(v, parent_key) for v in obj]
    if isinstance(obj, str):
        if parent_key is not None and _is_sensitive_key(parent_key):
            return _redact_sensitive_string(parent_key, obj)
        return _redact_string(obj)
    return obj


def redact_secrets(obj: Any) -> Any:
    """Recursively redact credential-like strings from keys and values."""
    return _redact_value(obj, None)


def redact_text(value: str) -> str:
    """Redact credential-like strings from plain text."""
    return _redact_string(value)
