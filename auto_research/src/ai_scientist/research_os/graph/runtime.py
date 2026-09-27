from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from ai_scientist.research_store import ResearchRepository


@dataclass
class ResearchOSRuntime:
    repository: ResearchRepository
    experiment_runner: Any
    max_reframes: int = 2
    agent_lab: Any | None = None
    task_workspace: str = "."

    def dispatch_task(self, stage: str, role: str, capability: str, state: dict[str, Any]) -> dict[str, Any]:
        if self.agent_lab is None:
            return {}
        from ai_scientist.research_os.agents import TaskSpec

        identity = f"{state['project_id']}:{stage}:{state.get('protocol_version_id')}:{state.get('active_experiment_run_id')}"
        task_id = f"{stage}-{hashlib.sha256(identity.encode()).hexdigest()[:12]}"
        task = TaskSpec(
            task_id=task_id, role=role, capability=capability,
            objective=f"Complete the bounded Research OS stage: {stage}",
            workspace=self.task_workspace,
            input_refs=[f"project:{state['project_id']}"] + [
                f"{key}:{state[key]}" for key in (
                    "protocol_version_id", "hypothesis_id", "active_experiment_spec_id",
                    "active_experiment_run_id", "active_analysis_run_id", "manuscript_version_id",
                ) if state.get(key)
            ],
            acceptance_criteria=["Return a schema-valid TaskResult bound to this task and role."],
            context={"stage": stage},
        )
        result = self.agent_lab.run(task)
        return {
            "active_task_id": task_id,
            "artifact_refs": list(dict.fromkeys([*state.get("artifact_refs", []), *result.output_refs])),
            "error_code": result.error_code if result.status == "FAILED" else state.get("error_code"),
        }

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
