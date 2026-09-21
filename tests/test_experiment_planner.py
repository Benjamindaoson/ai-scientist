import json
import sys

from benchmarks.discovery.experiment_planner import ExperimentPlanner


def test_planner_creates_existing_experiment_spec(tmp_path):
    spec = ExperimentPlanner().plan(
        {"id": "hyp_001", "claim": "test", "mutation": {"moving_avg": 49}},
        {"metrics": {"mse": 1.0}}, tmp_path / "workspace", tmp_path / "data", 8,
    )
    assert spec.command[0] == sys.executable
    assert (tmp_path / "workspace" / "experiment_config.json").exists()
    assert json.loads((tmp_path / "workspace" / "experiment_config.json").read_text())["moving_avg"] == 49
