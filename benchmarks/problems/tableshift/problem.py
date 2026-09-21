"""TableShift diabetes readmission OOD benchmark definition."""
from __future__ import annotations

import sys
from pathlib import Path

from ai_scientist.experiment import ExperimentSpec
from ai_scientist.hypothesis import Hypothesis
from benchmarks.core.schema import MetricSpec, ProblemSpec
from benchmarks.problems.base import BenchmarkProblem


TABLESHIFT_PROBLEM = ProblemSpec(
    problem_id="tableshift_diabetes_readmission",
    domain="tabular_ood",
    research_question="Can OOD hospital-readmission accuracy improve without materially reducing ID accuracy?",
    primary_metric=MetricSpec("ood_accuracy", "higher"),
    secondary_metrics=(MetricSpec("id_accuracy", "higher"), MetricSpec("ood_gap", "lower")),
    constraints={"max_id_accuracy_drop_pp": 0.5, "dataset": "diabetes_readmission"},
    upstream={
        "repository": "https://github.com/mlfoundations/tableshift",
        "dataset": "diabetes_readmission",
    },
)


class TableShiftProblem(BenchmarkProblem):
    spec = TABLESHIFT_PROBLEM

    def make_hypothesis(self) -> Hypothesis:
        return Hypothesis(
            claim="A tabular learning modification can improve diabetes-readmission OOD accuracy while preserving ID accuracy.",
            rationale="The fixed TableShift domain split exposes whether improvements transfer across admission-source shift.",
            predicted_effect="OOD accuracy improves with <=0.5pp ID accuracy loss",
            falsification_conditions=["OOD accuracy does not improve", "ID accuracy drops >0.5pp"],
        )

    def make_experiment_spec(self, workspace: str | Path, seed: int) -> ExperimentSpec:
        runner = Path(__file__).with_name("run_tableshift.py").resolve()
        root = Path(workspace).resolve()
        return ExperimentSpec(
            hypothesis_id=self.make_hypothesis().id,
            objective=self.spec.research_question,
            command=[sys.executable, str(runner), "--cache-dir", str(root/"cache"), "--seed", str(seed)],
            workspace=str(root),
            metrics_file="metrics.json",
            success_criteria={"ood_accuracy": {"op": ">=", "value": 0.0}},
            timeout_seconds=14400,
            max_attempts=1,
            metadata={"benchmark_problem": self.spec.problem_id, "gpu_count": 0},
        )

    def validate_constraints(self, baseline_metrics, final_metrics):
        violations = []
        if "id_accuracy" in baseline_metrics and "id_accuracy" in final_metrics:
            drop_pp = 100.0 * (baseline_metrics["id_accuracy"] - final_metrics["id_accuracy"])
            if drop_pp > self.spec.constraints["max_id_accuracy_drop_pp"]:
                violations.append(f"ID accuracy drop {drop_pp:.3f}pp exceeds 0.5pp")
        return violations
