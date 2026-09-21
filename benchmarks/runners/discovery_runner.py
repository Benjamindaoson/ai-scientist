from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _ensure_ai_scientist_path() -> None:
    source = Path(__file__).parents[2] / "auto_research" / "src"
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))


def run_discovery(
    benchmark: str = "ettm1",
    rounds: int = 3,
    data_root: str | Path = "data/ettm1",
    results_root: str | Path = "results",
    trajectory_root: str | Path = "benchmarks/trajectories",
    max_windows: int = 1024,
) -> dict:
    _ensure_ai_scientist_path()
    from benchmarks.discovery.discovery_loop import AutonomousDiscoveryLoop
    from benchmarks.discovery.problem import ResearchProblem
    from benchmarks.runners.baseline_runner import run_baseline

    if benchmark.lower() != "ettm1":
        raise ValueError("discovery runner currently supports only ettm1")
    # Recompute the control with the same bounded window budget as every
    # discovery candidate; comparing against a different run would leak a
    # protocol change into the claim.
    baseline = run_baseline("ettm1", "dlinear", data_root=data_root, results_root=results_root, max_windows=max_windows, persist=False)
    baseline_path = Path(results_root) / "ettm1" / "baseline" / "summary_discovery_control.json"
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
    problem = ResearchProblem(
        title="Improve long horizon forecasting",
        description="Find methods that improve ETTm1 forecasting under fixed compute budget.",
        benchmark="ETTm1",
        baseline_models=["DLinear"],
        constraints={"parameter_increase": "<10%", "training_budget": "fixed", "no_test_leakage": True},
        evaluation_metrics={"primary": "mse", "secondary": "mae", "direction": "lower_is_better"},
    )
    output = AutonomousDiscoveryLoop().run(
        problem=problem,
        baseline=baseline,
        data_root=data_root,
        trajectory_root=Path(trajectory_root) / "ettm1_discovery_001",
        max_rounds=rounds,
        max_windows=max_windows,
    )
    return {"benchmark": "ETTm1", "rounds": rounds, "trajectory": output["trajectory"], "claim": output["claim"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default="ettm1")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--data-root", default="data/ettm1")
    parser.add_argument("--results-root", default="results")
    parser.add_argument("--trajectory-root", default="benchmarks/trajectories")
    parser.add_argument("--max-windows", type=int, default=1024)
    args = parser.parse_args()
    print(json.dumps(run_discovery(**vars(args)), indent=2))


if __name__ == "__main__":
    main()
