"""Failure taxonomy and deterministic recovery policy."""
from __future__ import annotations

from dataclasses import replace

from .models import ExperimentResult, ExperimentSpec


class FailureRecoveryPolicy:
    """Classify experiment failures and propose bounded retries."""

    def classify(self, result: ExperimentResult) -> str:
        if result.status == "SUCCEEDED" and result.error_type is None:
            return "NONE"
        if result.error_type == "TIMEOUT":
            return "TIMEOUT"
        if result.error_type == "INVALID_METRICS":
            return "INVALID_METRICS"
        if result.return_code != 0:
            text = (result.stderr or "").lower()
            if "modulenotfounderror" in text or "importerror" in text:
                return "DEPENDENCY_ERROR"
            if "syntaxerror" in text:
                return "CODE_ERROR"
            return "RUNTIME_ERROR"
        return "UNKNOWN"

    def retry_spec(self, spec: ExperimentSpec, result: ExperimentResult, attempt: int) -> ExperimentSpec | None:
        kind = self.classify(result)
        if attempt >= 1:
            return None
        if kind == "TIMEOUT":
            return replace(spec, timeout_seconds=min(spec.timeout_seconds * 2, 7200), id=f"{spec.id}_retry1")
        if kind in {"INVALID_METRICS", "DEPENDENCY_ERROR", "CODE_ERROR", "RUNTIME_ERROR"}:
            # A blind rerun is useful only once; engineering repair can intervene after this.
            return replace(spec, id=f"{spec.id}_retry1")
        return None
