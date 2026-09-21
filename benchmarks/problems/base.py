"""Base contract for real ML benchmark problems."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ai_scientist.experiment import ExperimentSpec
from ai_scientist.hypothesis import Hypothesis
from benchmarks.core.metrics import compute_task_improvement
from benchmarks.core.schema import ProblemSpec


class BenchmarkProblem(ABC):
    spec: ProblemSpec

    @abstractmethod
    def make_hypothesis(self) -> Hypothesis:
        raise NotImplementedError

    @abstractmethod
    def make_experiment_spec(self, workspace: str | Path, seed: int) -> ExperimentSpec:
        raise NotImplementedError

    @abstractmethod
    def validate_constraints(
        self,
        baseline_metrics: dict[str, float],
        final_metrics: dict[str, float],
    ) -> list[str]:
        raise NotImplementedError

    def score(self, baseline_metrics: dict[str, float], final_metrics: dict[str, float]) -> float:
        name = self.spec.primary_metric.name
        return compute_task_improvement(
            self.spec.primary_metric,
            float(baseline_metrics[name]),
            float(final_metrics[name]),
        )

    def valid_discovery(self, baseline_metrics: dict[str, float], final_metrics: dict[str, float]) -> tuple[bool, list[str]]:
        violations = self.validate_constraints(baseline_metrics, final_metrics)
        return self.score(baseline_metrics, final_metrics) > 0 and not violations, violations
