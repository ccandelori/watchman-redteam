from __future__ import annotations

from pathlib import Path
from threading import Thread

import pytest

from aegis_redteam.campaigns.compare import compare_campaign_results
from aegis_redteam.campaigns.runner import run_campaign
from aegis_redteam.fixture_server import FixtureState, create_fixture_server
from aegis_redteam.results import load_results_jsonl, write_results_jsonl
from aegis_redteam.runner import run_scenarios
from aegis_redteam.scenarios.loader import load_scenarios


@pytest.mark.parametrize(
    ("campaign_name", "baseline_name", "expected_variants"),
    [
        ("credential_exfil.yaml", "credential-exfil-v1.jsonl", 5),
        ("encoding_matrix.yaml", "encoding-matrix-v1.jsonl", 6),
    ],
)
def test_campaign_matches_committed_baseline(
    tmp_path: Path,
    campaign_name: str,
    baseline_name: str,
    expected_variants: int,
) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    campaign_path = repo_root / "campaigns" / campaign_name
    baseline_path = repo_root / "baselines" / baseline_name
    current_path = tmp_path / "current.jsonl"
    replay_path = tmp_path / "replay.jsonl"
    generated_dir = tmp_path / "generated"

    state = FixtureState()
    server = create_fixture_server("127.0.0.1", 0, state)
    port = server.server_port
    server_thread = Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        target_url = f"http://127.0.0.1:{port}"
        campaign_run = run_campaign(campaign_path, target_url, generated_dir)
        write_results_jsonl(campaign_run.results, current_path)

        generated_scenarios = load_scenarios(generated_dir)
        replay_results = run_scenarios(generated_scenarios, target_url)
        write_results_jsonl(replay_results, replay_path)

        baseline_results = load_results_jsonl(baseline_path)
        campaign_comparison = compare_campaign_results(current_path, baseline_path)
        replay_comparison = compare_campaign_results(replay_path, baseline_path)
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)

    assert len(campaign_run.generated_paths) == expected_variants
    assert all(result.passed for result in campaign_run.results)
    assert all(result.passed for result in replay_results)
    assert {result.run_id for result in baseline_results} == {
        f"baseline:{result.scenario_name}" for result in baseline_results
    }
    assert {result.target_url for result in baseline_results} == {"baseline://campaign-regression"}
    assert {result.started_at for result in baseline_results} == {"1970-01-01T00:00:00Z"}
    assert {result.finished_at for result in baseline_results} == {"1970-01-01T00:00:00Z"}
    for comparison in (campaign_comparison, replay_comparison):
        assert comparison.regressions == 0
        assert comparison.improvements == 0
        assert comparison.new_scenarios == 0
        assert comparison.changed_scenarios == 0
