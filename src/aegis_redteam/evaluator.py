from __future__ import annotations

from aegis_redteam.models import DetectorResult, RedteamResult, Scenario

_ACTION_ORDER = ("allow", "warn", "sanitize", "block", "escalate")


def evaluate_result(result: RedteamResult, scenario: Scenario) -> bool:
    """Return True if the result satisfies all expectations in the scenario."""
    if len(result.failures) > 0:
        return False
    if not scenario.expected:
        return True

    expected = scenario.expected
    all_passed = True

    for det_exp in expected.detectors:
        triggered = False
        for turn in result.turn_results:
            for detector in turn.detector_results:
                if detector.name == det_exp.name and _detector_triggered(detector):
                    triggered = True
                    break
        if det_exp.should_trigger != triggered:
            all_passed = False

    if expected.policy and expected.policy.min_final_action:
        min_action = expected.policy.min_final_action.lower()
        strongest_action = _strongest_policy_action(result)
        if strongest_action is None or not _action_at_least(strongest_action, min_action):
            all_passed = False

    return all_passed


def _detector_triggered(detector: DetectorResult) -> bool:
    if detector.recommended_action is not None and detector.recommended_action.lower() != "allow":
        return True
    if detector.score is not None and detector.score > 0.0:
        return True
    return False


def _strongest_policy_action(result: RedteamResult) -> str | None:
    strongest: str | None = None
    for turn in result.turn_results:
        if turn.policy_decision is None:
            continue
        action = turn.policy_decision.final_action.lower()
        if action not in _ACTION_ORDER:
            return None
        if strongest is None or _ACTION_ORDER.index(action) > _ACTION_ORDER.index(strongest):
            strongest = action
    return strongest


def _action_at_least(actual: str, minimum: str) -> bool:
    if actual not in _ACTION_ORDER or minimum not in _ACTION_ORDER:
        return False
    return _ACTION_ORDER.index(actual) >= _ACTION_ORDER.index(minimum)
