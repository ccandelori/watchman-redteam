from __future__ import annotations

import re

from aegis_redteam.redact import looks_like_secret

_PLACEHOLDER_PATTERN = re.compile(r"\{\{CREDENTIAL:(?P<slot>[^:}]+):(?P<type>[^}]+)\}\}")


def validate_credential_placeholders(text: str) -> None:
    """Validate inline ``{{CREDENTIAL:slot:type}}`` placeholders fail closed.

    The third field is a credential *type label* (e.g. ``openai_key``), not a
    literal secret value. A literal secret in that position is audit-unsafe
    because the runtime preserves it as non-secret type metadata. Raise a
    sanitized ``ValueError`` that never echoes the offending value.
    """
    for match in _PLACEHOLDER_PATTERN.finditer(text):
        type_field = match.group("type")
        if looks_like_secret(type_field):
            slot = match.group("slot")
            raise ValueError(
                f"credential placeholder type field for slot '{slot}' looks like a "
                "literal secret; use a type label such as 'openai_key' instead"
            )
