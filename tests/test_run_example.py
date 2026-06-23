import importlib.util
from collections.abc import Callable, Sequence
from pathlib import Path
from types import ModuleType
from typing import Protocol, cast

import pytest

from aegis_redteam.models import RedteamResult, Scenario, Turn


class RunExampleModule(Protocol):
    TARGET_ENV_VAR: str
    target_url_from_args: Callable[[Sequence[str]], str]
    main: Callable[[Sequence[str]], int]


def load_run_example_module() -> RunExampleModule:
    module_path = Path(__file__).parents[1] / "examples" / "run_example.py"
    spec = importlib.util.spec_from_file_location("run_example_under_test", module_path)
    if spec is None:
        raise RuntimeError(f"Could not create import spec for {module_path}")
    if spec.loader is None:
        raise RuntimeError(f"Import spec has no loader for {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return cast(RunExampleModule, module)


run_example = load_run_example_module()


def make_result(passed: bool) -> RedteamResult:
    return RedteamResult(
        run_id="run-1",
        scenario_name="scenario-1",
        target_url="http://target.example",
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:00:01Z",
        passed=passed,
    )


def test_target_url_from_args_uses_cli_arg_before_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(run_example.TARGET_ENV_VAR, "http://env.example")

    target_url = run_example.target_url_from_args(
        ["examples/run_example.py", "http://cli.example"]
    )

    assert target_url == "http://cli.example"


def test_target_url_from_args_uses_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(run_example.TARGET_ENV_VAR, "http://env.example")

    target_url = run_example.target_url_from_args(["examples/run_example.py"])

    assert target_url == "http://env.example"


def test_target_url_from_args_rejects_extra_arguments() -> None:
    with pytest.raises(ValueError, match="Usage: python examples/run_example.py"):
        run_example.target_url_from_args(
            ["examples/run_example.py", "http://one.example", "http://two.example"]
        )


def test_main_returns_nonzero_when_scenarios_fail(monkeypatch: pytest.MonkeyPatch) -> None:
    scenario = Scenario(name="scenario-1", turns=[Turn(role="user", content="hello")])
    seen_targets: list[str] = []
    seen_summary_counts: list[int] = []

    def fake_load_scenarios(scenarios_dir: Path) -> list[Scenario]:
        assert scenarios_dir.name == "scenarios"
        return [scenario]

    def fake_run_scenarios(scenarios: list[Scenario], target_url: str) -> list[RedteamResult]:
        assert scenarios == [scenario]
        seen_targets.append(target_url)
        return [make_result(False)]

    def fake_print_summary(results: list[RedteamResult]) -> None:
        seen_summary_counts.append(len(results))

    monkeypatch.setenv(run_example.TARGET_ENV_VAR, "http://env.example")
    monkeypatch.setattr(cast(ModuleType, run_example), "load_scenarios", fake_load_scenarios)
    monkeypatch.setattr(cast(ModuleType, run_example), "run_scenarios", fake_run_scenarios)
    monkeypatch.setattr(cast(ModuleType, run_example), "print_summary", fake_print_summary)

    exit_code = run_example.main(["examples/run_example.py"])

    assert exit_code == 1
    assert seen_targets == ["http://env.example"]
    assert seen_summary_counts == [1]


def test_main_returns_zero_when_scenarios_pass(monkeypatch: pytest.MonkeyPatch) -> None:
    scenario = Scenario(name="scenario-1", turns=[Turn(role="user", content="hello")])

    def fake_load_scenarios(scenarios_dir: Path) -> list[Scenario]:
        assert scenarios_dir.name == "scenarios"
        return [scenario]

    def fake_run_scenarios(scenarios: list[Scenario], target_url: str) -> list[RedteamResult]:
        assert scenarios == [scenario]
        assert target_url == "http://cli.example"
        return [make_result(True)]

    def fake_print_summary(results: list[RedteamResult]) -> None:
        assert len(results) == 1

    monkeypatch.setattr(cast(ModuleType, run_example), "load_scenarios", fake_load_scenarios)
    monkeypatch.setattr(cast(ModuleType, run_example), "run_scenarios", fake_run_scenarios)
    monkeypatch.setattr(cast(ModuleType, run_example), "print_summary", fake_print_summary)

    exit_code = run_example.main(["examples/run_example.py", "http://cli.example"])

    assert exit_code == 0
