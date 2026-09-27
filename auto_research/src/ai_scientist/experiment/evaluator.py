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

    def _check(self, criteria: dict, metrics: dict) -> tuple[list[dict], bool]:
        checks = []
        valid = True
        for metric, rule in criteria.items():
            op = str(rule.get("op", ">="))
            target = rule.get("value")
            actual = metrics.get(metric)
            check_valid = actual is not None and op in self.OPERATORS
            try:
                passed = check_valid and self.OPERATORS[op](actual, target)
            except (TypeError, ValueError):
                passed = False
                check_valid = False
            valid = valid and check_valid
            checks.append({"metric": metric, "actual": actual, "op": op, "target": target, "passed": passed})
        return checks, valid

    def evaluate(self, spec: ExperimentSpec, result: ExperimentResult) -> dict:
        metrics_valid = isinstance(result.metrics, dict)
        metrics = result.metrics if metrics_valid else {}
        checks, success_valid = self._check(spec.success_criteria, metrics)
        contradiction_checks, contradiction_valid = self._check(
            spec.contradiction_criteria, metrics
        )
        criteria_pass = bool(checks) and all(c["passed"] for c in checks)
        contradiction_pass = bool(contradiction_checks) and all(
            c["passed"] for c in contradiction_checks
        )

        if (
            result.status != "SUCCEEDED"
            or not metrics_valid
            or not success_valid
            or not contradiction_valid
        ):
            verdict = "INVALID"
        elif criteria_pass:
            verdict = "SUPPORTED"
        elif contradiction_pass:
            verdict = "CONTRADICTED"
        else:
            verdict = "INCONCLUSIVE"

        return {
            "experiment_id": result.experiment_id,
            "execution_succeeded": result.status == "SUCCEEDED",
            "criteria_passed": criteria_pass,
            "checks": checks,
            "contradiction_criteria_passed": contradiction_pass,
            "contradiction_checks": contradiction_checks,
            "verdict": verdict,
        }
