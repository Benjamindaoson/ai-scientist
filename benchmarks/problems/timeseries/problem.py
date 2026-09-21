"""PatchTST/DLinear long-horizon forecasting benchmark definition."""
from __future__ import annotations

import sys
from pathlib import Path

from ai_scientist.experiment import ExperimentSpec
from ai_scientist.hypothesis import Hypothesis
from benchmarks.core.schema import MetricSpec, ProblemSpec
from benchmarks.problems.base import BenchmarkProblem


TIME_SERIES_PROBLEM = ProblemSpec(
    problem_id="long_horizon_forecasting",
    domain="time_series",
    research_question=(
        "Can an autonomous research loop reduce average long-horizon forecasting "
        "MSE on ETTm1 and Weather under a fixed training budget?"
    ),
    primary_metric=MetricSpec("mse", "lower"),
    secondary_metrics=(MetricSpec("mae", "lower"),),
    constraints={
        "max_parameter_increase_ratio": 0.10,
        "prediction_horizons": [96, 192, 336, 720],
        "datasets": ["ETTm1", "weather"],
        "fixed_train_epochs": 30,
    },
    upstream={
        "repository": "https://github.com/yuqinie98/PatchTST",
        "implementation": "PatchTST_supervised/run_longExp.py",
    },
)


class TimeSeriesProblem(BenchmarkProblem):
    spec = TIME_SERIES_PROBLEM

    def make_hypothesis(self) -> Hypothesis:
        return Hypothesis(
            claim="A targeted modification can reduce average long-horizon MSE without increasing parameters by more than 10%.",
            rationale="The benchmark exposes eight dataset-horizon conditions, discouraging one-horizon overfitting.",
            predicted_effect="average MSE decreases across ETTm1 and Weather",
            falsification_conditions=[
                "average MSE does not improve",
                "parameter count rises by more than 10%",
            ],
        )

    def make_experiment_spec(self, workspace: str | Path, seed: int) -> ExperimentSpec:
        runner = Path(__file__).with_name("run_patchtst.py").resolve()
        return ExperimentSpec(
            hypothesis_id=self.make_hypothesis().id,
            objective=self.spec.research_question,
            command=[
                sys.executable, str(runner),
                "--upstream", str(Path(workspace).resolve()),
                "--seed", str(seed),
                "--epochs", str(self.spec.constraints["fixed_train_epochs"]),
            ],
            workspace=str(Path(workspace).resolve()),
            metrics_file="metrics.json",
            success_criteria={"mse": {"op": "<", "value": 1e9}},
            timeout_seconds=21600,
            max_attempts=1,
            metadata={"benchmark_problem": self.spec.problem_id, "gpu_count": 1},
        )

    def validate_constraints(self, baseline_metrics, final_metrics):
        violations = []
        if baseline_metrics.get("params") and final_metrics.get("params"):
            ratio = final_metrics["params"] / baseline_metrics["params"] - 1.0
            if ratio > self.spec.constraints["max_parameter_increase_ratio"]:
                violations.append(f"parameter increase {ratio:.3f} exceeds 0.10")
        return violations
