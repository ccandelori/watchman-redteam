import respx
from httpx import Response

from aegis_redteam.doctor import run_doctor


def test_doctor_passes_fixture_contract() -> None:
    base_url = "http://fixture.local"

    with respx.mock:
        respx.get(f"{base_url}/health").mock(
            return_value=Response(200, json={"status": "ok", "capabilities": ["fixture"]})
        )
        respx.post(f"{base_url}/test/reset").mock(
            return_value=Response(200, json={"status": "reset"})
        )
        respx.post(f"{base_url}/v1/chat/completions").mock(
            return_value=Response(
                200,
                json={
                    "choices": [{"message": {"content": "fixture response"}}],
                    "aegis": {
                        "detector_results": [],
                        "policy_decision": {
                            "final_action": "allow",
                            "triggered_detectors": [],
                        },
                    },
                },
            )
        )

        report = run_doctor(base_url, 5.0)

    assert report.passed is True
    assert report.target_kind == "fixture"
    assert [(check.name, check.passed) for check in report.checks] == [
        ("health", True),
        ("reset", True),
        ("chat", True),
        ("aegis_metadata", True),
    ]


def test_doctor_fails_missing_aegis_metadata() -> None:
    base_url = "http://target.local"

    with respx.mock:
        respx.get(f"{base_url}/health").mock(return_value=Response(200, json={"status": "ok"}))
        respx.post(f"{base_url}/test/reset").mock(return_value=Response(200, json={"status": "reset"}))
        respx.post(f"{base_url}/v1/chat/completions").mock(
            return_value=Response(200, json={"choices": [{"message": {"content": "ok"}}]})
        )

        report = run_doctor(base_url, 5.0)

    assert report.passed is False
    failed_checks = [check for check in report.checks if not check.passed]
    assert [(check.name, check.required) for check in failed_checks] == [("aegis_metadata", True)]
    assert "expected 'aegis' to be present" in failed_checks[0].detail


def test_doctor_redacts_failure_details() -> None:
    base_url = "http://target.local"
    token = "sk-proj-" + "D" * 20 + "_abcdefABCDEF"

    with respx.mock:
        respx.get(f"{base_url}/health").mock(return_value=Response(500, json={"error": token}))
        respx.post(f"{base_url}/test/reset").mock(return_value=Response(200, json={"status": "reset"}))
        respx.post(f"{base_url}/v1/chat/completions").mock(
            return_value=Response(
                200,
                json={
                    "choices": [{"message": {"content": "ok"}}],
                    "aegis": {
                        "detector_results": [],
                        "policy_decision": {"final_action": "allow"},
                    },
                },
            )
        )

        report = run_doctor(base_url, 5.0)

    report_text = report.model_dump_json()
    assert report.passed is False
    assert token not in report_text
    assert "[REDACTED]" in report_text
