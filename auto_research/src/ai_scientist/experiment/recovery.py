"""Failure taxonomy and bounded experiment recovery."""
from __future__ import annotations

from dataclasses import dataclass, replace

from .models import ExperimentResult, ExperimentSpec


class FailureClassifier:
    def classify(self, result: ExperimentResult) -> str:
        if result.status == "SUCCEEDED" and result.error_type is None:
            return "NONE"
        if result.error_type == "TIMEOUT":
            return "TIMEOUT"
        if result.error_type == "INVALID_METRICS":
            return "INVALID_METRICS"
        text = (result.stderr or "").lower()
        if "modulenotfounderror" in text or "importerror" in text:
            return "DEPENDENCY"
        if "out of memory" in text or "cuda out of memory" in text:
            return "RESOURCE_EXHAUSTED"
        if "syntaxerror" in text:
            return "CODE_ERROR"
        return result.error_type or "NONZERO_EXIT"


@dataclass
class RecoveryDecision:
    retry: bool
    reason: str
    updated_spec: ExperimentSpec | None = None


class RecoveryPolicy:
    """Conservative recovery: bounded retries and no silent benchmark changes."""

    def __init__(self, max_attempts: int = 2):
        self.max_attempts = max(1, max_attempts)
        self.classifier = FailureClassifier()

    def decide(self, spec: ExperimentSpec, result: ExperimentResult, attempt: int) -> RecoveryDecision:
        failure = self.classifier.classify(result)
        if failure == "NONE" or attempt >= self.max_attempts:
            return RecoveryDecision(False, failure)
        if failure == "TIMEOUT":
            return RecoveryDecision(
                True,
                "retry_with_larger_timeout",
                replace(spec, timeout_seconds=min(spec.timeout_seconds * 2, 7200)),
            )
        if failure in {"NONZERO_EXIT", "CODE_ERROR", "DEPENDENCY", "INVALID_METRICS"}:
            return RecoveryDecision(True, f"retry_after_repair:{failure}", spec)
        return RecoveryDecision(False, failure)
