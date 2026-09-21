import json
import sys
import csv

from benchmarks.runners.scientist_runner import run_scientist


def test_scientist_runner_exports_research_state(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    fields = ["date", "HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"]
    with (data / "ETTm1.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(20):
            writer.writerow({field: index if field != "date" else str(index) for field in fields})
    results = tmp_path / "results" / "ettm1" / "baseline"
    results.mkdir(parents=True)
    (results / "summary_dlinear.json").write_text(json.dumps({
        "benchmark": "ETTm1",
        "model": "DLinear",
        "seed": 1,
        "metrics": {"mse": 0.4, "mae": 0.5},
    }))

    output = run_scientist(
        results_root=tmp_path / "results",
        trajectory_root=tmp_path / "trajectories",
        data_root=data,
        run_id="test_run",
        python_executable=sys.executable,
        dataset_kwargs={"lookback": 4, "horizon": 2, "split_points": (10, 15)},
    )

    assert output["success"] is True
    assert (tmp_path / "trajectories" / "test_run" / "final_decision.json").exists()
