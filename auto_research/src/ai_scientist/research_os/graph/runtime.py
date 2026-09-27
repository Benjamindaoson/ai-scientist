from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ai_scientist.research_store import ResearchRepository


@dataclass
class ResearchOSRuntime:
    repository: ResearchRepository
    experiment_runner: Any
    max_reframes: int = 2

    def decision(self, project_id: str, decision_type: str, fallback_id: str | None = None) -> dict[str, Any] | None:
        decision = self.repository.get_latest_decision(project_id, decision_type)
        return decision or (self.repository.get_decision(fallback_id) if fallback_id else None)

    def submit_experiment(self, experiment_spec_id: str) -> dict[str, Any]:
        existing = self.repository.list_experiment_runs(experiment_spec_id)
        if existing:
            return existing[-1]
        spec = self.repository.get_experiment_spec(experiment_spec_id)
        if not spec:
            raise KeyError(experiment_spec_id)
        result = self.experiment_runner.run(spec)
        if isinstance(result, dict):
            status = result.get("status", "SUCCEEDED")
            return_code = result.get("return_code")
            metrics = result.get("metrics", {})
            error_type = result.get("error_type")
        else:
            status = "SUCCEEDED" if getattr(result, "success", False) else "FAILED"
            return_code = getattr(result, "return_code", None)
            metrics = getattr(result, "metrics", {})
            error_type = getattr(result, "error_type", None)
        return self.repository.create_experiment_run(
            experiment_spec_id, attempt=1, status=status, return_code=return_code,
            metrics=metrics, error_type=str(error_type) if error_type else None,
            runtime_metadata={"submitted_by": "langgraph"},
        )

    def complete_run(self, experiment_run_id: str, **result: Any) -> dict[str, Any]:
        return self.repository.update_experiment_run(experiment_run_id, completed_at=datetime.now(timezone.utc), **result)
