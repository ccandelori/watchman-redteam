from aegis_redteam.redact import redact_secrets

OPENAI_PROJECT_TOKEN = "sk-proj-1234567890abcdefABCDEF"
GITHUB_TOKEN = "ghp_1234567890abcdefghijklmnopqrstuvwxyzABCDEF"
AWS_ACCESS_KEY = "AKIA1234567890ABCDEF"
SECRET_DICT_KEY = "sk_live_dictionarykey123"


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
        "Bearer abc123.secret-token": "header value",
        "nested": {SECRET_DICT_KEY: "key value"},
    }

    redacted = redact_secrets(payload)

    redacted_text = str(redacted)
    assert "Bearer abc123.secret-token" not in redacted_text
    assert SECRET_DICT_KEY not in redacted_text
    assert "[REDACTED]" in redacted_text


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
