from __future__ import annotations

from aegis_redteam.models import RedteamResult
from aegis_redteam.summary import (
    FailureCategory,
    categorize_failure,
    summarize_results,
)


def _result(name: str, passed: bool, failures: list[str]) -> RedteamResult:
    return RedteamResult(
        run_id=f"run-{name}",
        scenario_name=name,
        target_url="http://fixture",
        started_at="2026-06-25T00:00:00Z",
        finished_at="2026-06-25T00:00:01Z",
        passed=passed,
        failures=failures,
    )


def test_categorize_detector_expectation() -> None:
    failure = "Detector expectation failed for s: text_canary expected triggered=True observed triggered=False"
    assert categorize_failure(failure) == FailureCategory.DETECTOR_EXPECTATION


def test_categorize_policy_expectation() -> None:
    failure = "Policy expectation failed for s: expected minimum action block observed allow on turn 1"
    assert categorize_failure(failure) == FailureCategory.POLICY_EXPECTATION


def test_categorize_egress_response() -> None:
    response_substring = "Egress expectation failed for s: forbidden response substring 'sk_live_' was present"
    assistant_content = "Egress expectation failed for s: expected assistant content 'x' observed 'y'"
    assert categorize_failure(response_substring) == FailureCategory.EGRESS_RESPONSE
    assert categorize_failure(assistant_content) == FailureCategory.EGRESS_RESPONSE


def test_categorize_egress_audit() -> None:
    audit_substring = "Egress expectation failed for s: forbidden audit substring 'sk_live_' was present"
    audit_http = "Audit inspection returned HTTP 500 from http://fixture/audit/recent: {}"
    audit_conn = "Failed to inspect audit at http://fixture/audit/recent: boom"
    assert categorize_failure(audit_substring) == FailureCategory.EGRESS_AUDIT
    assert categorize_failure(audit_http) == FailureCategory.EGRESS_AUDIT
    assert categorize_failure(audit_conn) == FailureCategory.EGRESS_AUDIT


def test_categorize_target_contract() -> None:
    samples = [
        "Turn 1 returned HTTP 500 from http://fixture/v1/chat/completions: {}",
        "Reset returned HTTP 503 from http://fixture/test/reset: {}",
        "Seed canary returned HTTP 503 from http://fixture/test/seed-canary: {}",
        "Failed to seed canary at http://fixture/test/seed-canary: boom",
        "Could not connect to http://fixture: boom",
        "Turn 1 HTTP request failed: boom",
        "Malformed target response on turn 1: expected 'aegis' to be present",
        "Failed to reset: boom",
    ]
    for failure in samples:
        assert categorize_failure(failure) == FailureCategory.TARGET_CONTRACT, failure


def test_categorize_scenario_validation() -> None:
    failure = "scenarios/x.yaml: invalid scenario: turns: List should have at least 1 item [too_short]"
    assert categorize_failure(failure) == FailureCategory.SCENARIO_VALIDATION


def test_categorize_unknown_falls_back_to_other() -> None:
    assert categorize_failure("something totally unexpected") == FailureCategory.OTHER


def test_summarize_results_counts_pass_fail_and_categories() -> None:
    results = [
        _result("pass1", True, []),
        _result(
            "fail_detector",
            False,
            ["Detector expectation failed for fail_detector: text_canary expected triggered=True observed triggered=False"],
        ),
        _result(
            "fail_mixed",
            False,
            [
                "Policy expectation failed for fail_mixed: expected minimum action block observed allow on turn 1",
                "Turn 1 returned HTTP 500 from http://fixture/v1/chat/completions: {}",
            ],
        ),
    ]

    summary = summarize_results(results)

    assert summary.total == 3
    assert summary.passed == 1
    assert summary.failed == 2
    assert summary.category_counts[FailureCategory.DETECTOR_EXPECTATION] == 1
    assert summary.category_counts[FailureCategory.POLICY_EXPECTATION] == 1
    assert summary.category_counts[FailureCategory.TARGET_CONTRACT] == 1


def test_summary_to_json_is_stable_and_serializable() -> None:
    import json

    results = [
        _result(
            "fail_detector",
            False,
            ["Detector expectation failed for fail_detector: text_canary expected triggered=True observed triggered=False"],
        ),
    ]
    summary = summarize_results(results)
    payload = summary.to_json_dict()

    # Round-trips through json and category keys are stable strings.
    encoded = json.dumps(payload, sort_keys=True)
    decoded = json.loads(encoded)
    assert decoded["total"] == 1
    assert decoded["failed"] == 1
    assert decoded["category_counts"]["detector_expectation"] == 1
    assert decoded["failed_scenarios"][0]["scenario_name"] == "fail_detector"
    assert decoded["failed_scenarios"][0]["categories"] == ["detector_expectation"]
