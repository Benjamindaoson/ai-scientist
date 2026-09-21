from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from benchmarks.core.trajectory import Trajectory


def _load_ai_scientist():
    source = Path(__file__).parents[2] / "auto_research" / "src"
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    from ai_scientist import AIScientist, ExperimentSpec, Hypothesis, MockGateway

    return AIScientist, ExperimentSpec, Hypothesis, MockGateway


def run_scientist(
    results_root: str | Path = "results",
    trajectory_root: str | Path = "benchmarks/trajectories",
    data_root: str | Path = "data/ettm1",
    run_id: str = "ettm1_run_001",
    python_executable: str = sys.executable,
    dataset_kwargs: dict | None = None,
) -> dict:
    AIScientist, ExperimentSpec, Hypothesis, MockGateway = _load_ai_scientist()
    results_path = Path(results_root) / "ettm1" / "baseline" / "summary_dlinear.json"
    if not results_path.exists():
        raise FileNotFoundError(f"baseline result required before scientist run: {results_path}")
    baseline = json.loads(results_path.read_text(encoding="utf-8"))
    root = Path(trajectory_root) / run_id
    workspace = root / "experiment_workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    kwargs = dataset_kwargs or {}
    script = workspace / "run_benchmark.py"
    script.write_text(
        "import json\n"
        "from benchmarks.runners.baseline_runner import run_baseline\n"
        f"summary = run_baseline(benchmark_name='ettm1', model_name='dlinear', data_root={str(Path(data_root).resolve())!r}, persist=False, **{kwargs!r})\n"
        "json.dump(summary['metrics'], open('metrics.json', 'w'), indent=2)\n",
        encoding="utf-8",
    )
    hypothesis = Hypothesis(
        claim="DLinear provides a reproducible long-horizon ETTm1 result under the benchmark protocol",
        rationale="The baseline establishes a fixed compute and data reference for subsequent research.",
        predicted_effect=f"mse <= {baseline['metrics']['mse']}",
        falsification_conditions=[f"mse > {baseline['metrics']['mse']}"],
    )
    spec = ExperimentSpec(
        hypothesis_id=hypothesis.id,
        objective="Reproduce the ETTm1 DLinear baseline under the fixed benchmark protocol",
        command=[python_executable, "run_benchmark.py"],
        workspace=str(workspace),
        metrics_file="metrics.json",
        baseline=baseline,
        success_criteria={"mse": {"op": "<=", "value": baseline["metrics"]["mse"]}},
        env={"PYTHONPATH": str(Path(__file__).parents[2].resolve()) + os.pathsep + str(Path(__file__).parents[2].resolve() / "auto_research" / "src")},
        max_attempts=1,
        metadata={"benchmark": "ETTm1", "model": "DLinear", "run_id": run_id},
    )
    scientist = AIScientist(db_path=root / "research.db", gateway=MockGateway())
    asyncio.run(scientist.start_research(
        "Improve long horizon forecasting on ETTm1 under fixed compute budget.",
        project_name=f"ETTm1 {run_id}",
        domain="time-series forecasting",
    ))
    output = scientist.run_autonomous_research_program(
        hypothesis=hypothesis,
        experiment_spec=spec,
        max_review_rounds=1,
        output_dir=root / "research_package",
    )
    state = output["research_package"]
    trajectory = Trajectory(root)
    trajectory.write("problem", {
        "benchmark": "ETTm1",
        "research_problem": "Improve long horizon forecasting on ETTm1 under fixed compute budget.",
        "run_id": run_id,
    })
    trajectory.write("baseline", baseline)
    trajectory.write("hypothesis_history", state["hypotheses"])
    trajectory.write("experiment_history", {
        "specs": state["experiment_specs"],
        "runs": state["experiment_runs"],
        "evidence": state["evidence"],
    })
    trajectory.write("evidence_graph", state["evidence_graph"])
    trajectory.write("reviews", {"reviews": state["reviews"], "rebuttals": state["rebuttals"]})
    trajectory.write("final_decision", {
        "decisions": state["decisions"],
        "integrity_audits": state["integrity_audits"],
        "meta_review": output["review_cycle"]["meta_review"],
    })
    return {"success": True, "run_id": run_id, "trajectory": str(root), "result": output}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-root", default="results")
    parser.add_argument("--trajectory-root", default="benchmarks/trajectories")
    parser.add_argument("--data-root", default="data/ettm1")
    parser.add_argument("--run-id", default="ettm1_run_001")
    args = parser.parse_args()
    result = run_scientist(**vars(args))
    print(json.dumps({k: v for k, v in result.items() if k != "result"}, indent=2))


if __name__ == "__main__":
    main()
