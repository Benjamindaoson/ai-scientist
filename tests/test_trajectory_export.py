import json

from benchmarks.core.trajectory import Trajectory


def test_trajectory_export_preserves_full_research_loop_artifacts(tmp_path):
    names = (
        "problem",
        "baseline",
        "hypothesis_history",
        "experiment_history",
        "evidence_graph",
        "reviews",
        "final_decision",
    )
    trajectory = Trajectory(tmp_path / "ettm1_run_001")
    for name in names:
        trajectory.write(name, {"name": name})

    for name in names:
        path = tmp_path / "ettm1_run_001" / f"{name}.json"
        assert path.exists()
        assert json.loads(path.read_text())["name"] == name
