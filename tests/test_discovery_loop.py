import csv
import json

from benchmarks.discovery.discovery_loop import AutonomousDiscoveryLoop
from benchmarks.discovery.problem import ResearchProblem
from benchmarks.runners.baseline_runner import run_baseline


def _dataset(root):
    fields = ["date", "HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"]
    with (root / "ETTm1.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for i in range(40):
            writer.writerow({field: i + (j * 0.1) for j, field in enumerate(fields)})


def test_discovery_loop_runs_multiple_real_experiments(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    _dataset(data)
    baseline = run_baseline("ettm1", "dlinear", data_root=data, max_windows=4, persist=False, lookback=4, horizon=2, split_points=(20, 30))
    output = AutonomousDiscoveryLoop().run(
        ResearchProblem("t", "d", "ETTm1", ["DLinear"]), baseline, data, tmp_path / "trajectory", max_rounds=3, max_windows=4,
        dataset_kwargs={"lookback": 4, "horizon": 2, "split_points": (20, 30)},
    )
    assert len(output["state"].experiment_results) == 3
    assert (tmp_path / "trajectory" / "final_claim.json").exists()
    assert all(item["result"]["metrics"]["split"] == "val" for item in output["state"].experiment_results)
    assert all(item["spec"]["metadata"]["evaluation_split"] == "val" for item in output["state"].experiment_plans)
    assert output["state"].final_test["protocol"] == "test evaluated once after candidate freeze"
    ids = [item["id"] for item in output["state"].selected_hypotheses]
    assert len(ids) == len(set(ids))
    all_candidates = [candidate["id"] for pool in output["state"].candidate_history for candidate in pool["candidates"]]
    assert len(all_candidates) == len(set(all_candidates))
    assert all(item["status"] == "EXECUTED" and item["result"]["experiment_id"] for item in output["state"].ablation_results)
