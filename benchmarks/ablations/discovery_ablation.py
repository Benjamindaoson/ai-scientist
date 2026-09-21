from __future__ import annotations

import json
from pathlib import Path

from benchmarks.discovery.discovery_loop import AutonomousDiscoveryLoop
from benchmarks.discovery.problem import ResearchProblem
from benchmarks.runners.baseline_runner import run_baseline


def run_discovery_ablations(
    data_root: str | Path = "data/ettm1",
    results_root: str | Path = "results",
    trajectory_root: str | Path = "benchmarks/trajectories",
    max_windows: int = 1024,
) -> list[dict]:
    baseline = run_baseline("ettm1", "dlinear", data_root=data_root, max_windows=max_windows, persist=False)
    problem = ResearchProblem(
        "Improve long horizon forecasting", "Find methods that improve ETTm1 forecasting under fixed compute budget.",
        "ETTm1", ["DLinear"], {"training_budget": "fixed", "no_test_leakage": True}, {"primary": "mse"},
    )
    modes = [("full", 3), ("single_shot", 1), ("no_evolution", 3), ("no_review", 3), ("no_integrity", 3)]
    rows = []
    for mode, rounds in modes:
        output = AutonomousDiscoveryLoop().run(
            problem, baseline, data_root, Path(trajectory_root) / f"ettm1_ablation_{mode}",
            max_rounds=rounds, max_windows=max_windows, mode=mode,
        )
        state = output["state"]
        evaluations = [item["evaluation"] for item in state.experiment_results]
        rows.append({
            "mode": mode,
            "status": "EXECUTED",
            "final_improvement": min((float(item.get("improvement", 0.0)) for item in evaluations), default=0.0),
            "number_experiments": len(state.experiment_results),
            "hypothesis_count": len(state.hypothesis_candidates),
            "valid_claims": int(output["claim"]["status"] == "SUPPORTED"),
            "cost": sum(float(item["result"].get("duration_seconds", 0.0)) for item in state.experiment_results),
            "trajectory_completeness": len(state.experiment_results) / rounds,
            "claim": output["claim"],
        })
    path = Path(results_root) / "ablations" / "discovery_summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    return rows


if __name__ == "__main__":
    print(json.dumps(run_discovery_ablations(), indent=2))
