import json

from benchmarks.reports.generate_report import generate_report


def test_report_generation_reads_baseline_and_trajectory(tmp_path):
    trajectory = tmp_path / "trajectory"
    trajectory.mkdir()
    (trajectory / "baseline.json").write_text(json.dumps({"model": "DLinear", "metrics": {"mse": 0.4, "mae": 0.5}}))
    (trajectory / "experiment_history.json").write_text(json.dumps({"runs": [{"status": "SUCCEEDED", "metrics": {"mse": 0.4, "mae": 0.5}}]}))
    (trajectory / "final_decision.json").write_text(json.dumps({"meta_review": {"decision": "REVISE"}}))

    path = generate_report(trajectory, tmp_path / "report.md")

    assert path.exists()
    text = path.read_text()
    assert "ETTm1 Benchmark Report" in text
    assert "DLinear" in text
    assert "REVISE" in text
