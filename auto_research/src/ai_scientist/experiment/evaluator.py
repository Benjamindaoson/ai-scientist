"""Evaluate experiment results against explicit scientific criteria."""
from __future__ import annotations

from .models import ExperimentResult, ExperimentSpec


class ExperimentEvaluator:
    OPERATORS = {
        ">": lambda a, b: a > b,
        ">=": lambda a, b: a >= b,
        "<": lambda a, b: a < b,
        "<=": lambda a, b: a <= b,
        "==": lambda a, b: a == b,
    }

    def evaluate(self, spec: ExperimentSpec, result: ExperimentResult) -> dict:
        checks = []
        for metric, rule in spec.success_criteria.items():
            op = str(rule.get("op", ">="))
            target = rule.get("value")
            actual = result.metrics.get(metric)
            passed = actual is not None and op in self.OPERATORS and self.OPERATORS[op](actual, target)
            checks.append({"metric": metric, "actual": actual, "op": op, "target": target, "passed": passed})
        criteria_pass = bool(checks) and all(c["passed"] for c in checks)
        return {
            "experiment_id": result.experiment_id,
            "execution_succeeded": result.status == "SUCCEEDED",
            "criteria_passed": criteria_pass,
            "checks": checks,
            "verdict": "SUPPORTED" if result.status == "SUCCEEDED" and criteria_pass else "INCONCLUSIVE",
        }
