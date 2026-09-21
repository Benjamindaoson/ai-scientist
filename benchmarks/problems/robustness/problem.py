"""CIFAR-10 -> CIFAR-10-C robustness benchmark definition."""
from __future__ import annotations

import sys
from pathlib import Path

from ai_scientist.experiment import ExperimentSpec
from ai_scientist.hypothesis import Hypothesis
from benchmarks.core.schema import MetricSpec, ProblemSpec
from benchmarks.problems.base import BenchmarkProblem
from benchmarks.problems.protocol import materialize_locked_runner


ROBUSTNESS_PROBLEM = ProblemSpec(
    problem_id="cifar10_corruption_robustness",
    domain="vision",
    research_question="Can robustness to CIFAR-10-C improve without sacrificing clean CIFAR-10 accuracy?",
    primary_metric=MetricSpec("corruption_accuracy", "higher"),
    secondary_metrics=(
        MetricSpec("clean_accuracy", "higher"),
        MetricSpec("worst_corruption_accuracy", "higher"),
    ),
    constraints={
        "max_clean_accuracy_drop_pp": 0.5,
        "train_epochs": 20,
        "corruption_severities": [1, 2, 3, 4, 5],
        "no_corruption_test_training": True,
    },
    upstream={"dataset": "CIFAR-10-C", "reference": "https://github.com/hendrycks/robustness"},
)


class RobustnessProblem(BenchmarkProblem):
    spec = ROBUSTNESS_PROBLEM

    def make_hypothesis(self) -> Hypothesis:
        return Hypothesis(
            claim="A training modification can improve mean CIFAR-10-C accuracy while keeping clean accuracy within 0.5 percentage points of baseline.",
            rationale="Robustness gains are valid only when clean performance and test-set isolation are preserved.",
            predicted_effect="corruption accuracy increases with <=0.5pp clean accuracy drop",
            falsification_conditions=["corruption accuracy does not improve", "clean accuracy drops >0.5pp"],
        )

    def make_experiment_spec(self, workspace: str | Path, seed: int) -> ExperimentSpec:
        root = Path(workspace).resolve()
        runner_name, runner_hash = materialize_locked_runner(Path(__file__).with_name("run_cifar10c.py"), root)
        return ExperimentSpec(
            hypothesis_id=self.make_hypothesis().id,
            objective=(
                self.spec.research_question
                + " The evaluator is locked. If research code is added, place it in candidate.py; do not edit the evaluator or corruption files."
            ),
            command=[
                sys.executable, runner_name,
                "--data-root", str(root / "data"),
                "--cifar10c-root", str(root / "CIFAR-10-C"),
                "--seed", str(seed), "--epochs", str(self.spec.constraints["train_epochs"]),
            ],
            workspace=str(root),
            metrics_file="metrics.json",
            success_criteria={"corruption_accuracy": {"op": ">=", "value": 0.0}},
            timeout_seconds=21600,
            max_attempts=1,
            metadata={
                "benchmark_problem": self.spec.problem_id,
                "gpu_count": 1,
                "locked_evaluator": runner_name,
                "locked_evaluator_sha256": runner_hash,
            },
        )

    def ablation_components(self) -> dict[str, object]:
        return {"augmentation": True, "weight_decay": True}

    def validate_constraints(self, baseline_metrics, final_metrics):
        violations = []
        if "clean_accuracy" in baseline_metrics and "clean_accuracy" in final_metrics:
            drop_pp = 100.0 * (baseline_metrics["clean_accuracy"] - final_metrics["clean_accuracy"])
            if drop_pp > self.spec.constraints["max_clean_accuracy_drop_pp"]:
                violations.append(f"clean accuracy drop {drop_pp:.3f}pp exceeds 0.5pp")
        return violations
