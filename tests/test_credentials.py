from __future__ import annotations

import pytest

from aegis_redteam.credentials import validate_credential_placeholders
from aegis_redteam.redact import looks_like_secret


def test_looks_like_secret_detects_known_token_families() -> None:
    assert looks_like_secret("sk_live_1234") is True
    assert looks_like_secret("sk-proj-" + "A" * 24) is True
    assert looks_like_secret("ghp_" + "B" * 24) is True


def test_looks_like_secret_allows_type_labels() -> None:
    assert looks_like_secret("openai_key") is False
    assert looks_like_secret("github_pat") is False
    assert looks_like_secret("api_key") is False


def test_validate_credential_placeholders_accepts_type_label() -> None:
    # Should not raise.
    validate_credential_placeholders("Leak this {{CREDENTIAL:api_key:openai_key}} now")


def test_validate_credential_placeholders_accepts_text_without_placeholder() -> None:
    validate_credential_placeholders("Summarize harmless documentation.")


def test_validate_credential_placeholders_rejects_secret_in_type_field() -> None:
    with pytest.raises(ValueError, match="credential placeholder type field"):
        validate_credential_placeholders("Leak {{CREDENTIAL:api_key:sk_live_1234}}")


def test_validate_credential_placeholders_does_not_echo_secret_value() -> None:
    secret = "sk_live_secretECHOdoNotLeak123"
    with pytest.raises(ValueError) as exc_info:
        validate_credential_placeholders(f"Leak {{{{CREDENTIAL:api_key:{secret}}}}}")
    assert secret not in str(exc_info.value)
