from typing import Any

from aegis_redteam.redact import redact_secrets

OPENAI_PROJECT_TOKEN = "sk-proj-" + "A" * 20 + "_abcdefABCDEF"
GITHUB_TOKEN = "ghp_" + "a" * 36
AWS_ACCESS_KEY = "AKIA" + "A" * 16
SECRET_DICT_KEY = "sk_live_" + "b" * 24
BEARER_TOKEN = "abc123." + "secret-token-value-4567"


def assert_string_mapping(value: Any) -> dict[str, str]:
    if not isinstance(value, dict):
        raise TypeError(f"Expected dict, got {type(value).__name__}")
    for key, item in value.items():
        if not isinstance(key, str):
            raise TypeError(f"Expected string key, got {type(key).__name__}")
        if not isinstance(item, str):
            raise TypeError(f"Expected string value for {key}, got {type(item).__name__}")
    return value


def test_redact_secrets_removes_common_token_formats() -> None:
    payload = {
        "openai_project": OPENAI_PROJECT_TOKEN,
        "github": GITHUB_TOKEN,
        "aws": AWS_ACCESS_KEY,
        "basic_auth": "Basic dXNlcjpwYXNz",
        "query": "api_key=secret-token-123&next=ok",
        "password": "password=hunter2",
    }

    redacted = redact_secrets(payload)

    redacted_text = str(redacted)
    assert OPENAI_PROJECT_TOKEN not in redacted_text
    assert GITHUB_TOKEN not in redacted_text
    assert AWS_ACCESS_KEY not in redacted_text
    assert "Basic dXNlcjpwYXNz" not in redacted_text
    assert "api_key=secret-token-123" not in redacted_text
    assert "password=hunter2" not in redacted_text
    assert "[REDACTED]" in redacted_text


def test_redact_secrets_redacts_secret_dictionary_keys() -> None:
    payload = {
        f"Bearer {BEARER_TOKEN}": "header value",
        "nested": {SECRET_DICT_KEY: "key value"},
    }

    redacted = redact_secrets(payload)

    redacted_text = str(redacted)
    assert BEARER_TOKEN not in redacted_text
    assert SECRET_DICT_KEY not in redacted_text
    assert "[REDACTED]" in redacted_text


def test_redact_secrets_redacts_sensitive_key_values_without_renaming_keys() -> None:
    payload = {
        "api_key": "opaque-development-secret",
        "authorization": f"Bearer {BEARER_TOKEN}",
        "cookie": "session=secret-cookie-value",
        "detector_name": "encoded_canary",
    }

    redacted = assert_string_mapping(redact_secrets(payload))

    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["authorization"] == "Bearer [REDACTED]"
    assert redacted["cookie"] == "[REDACTED]"
    assert redacted["detector_name"] == "encoded_canary"


def test_redact_secrets_preserves_bearer_scheme_and_short_detector_evidence() -> None:
    auth_prefix = "Authorization: " + "Bearer "
    payload = {
        "auth_header": auth_prefix + BEARER_TOKEN,
        "example_evidence": "Bearer encoded_canary",
    }

    redacted = assert_string_mapping(redact_secrets(payload))

    assert redacted["auth_header"] == auth_prefix + "[REDACTED]"
    assert redacted["example_evidence"] == "Bearer encoded_canary"


def test_redact_secrets_preserves_non_secret_detector_evidence() -> None:
    payload = {
        "detector_name": "encoded_canary",
        "evidence": {
            "matched_text": "NIMBUS-CANARY",
            "score": 1.0,
        },
    }

    redacted = redact_secrets(payload)

    assert redacted == payload
