from __future__ import annotations

from typing import TypedDict


class ResearchExecutionState(TypedDict, total=False):
    project_id: str
    current_stage: str
    active_task_id: str | None
    active_role: str | None
    protocol_version_id: str | None
    hypothesis_id: str | None
    active_experiment_spec_id: str | None
    pending_review_finding_ids: list[str]
    pending_objection_ids: list[str]
    pending_approval_id: str | None
    active_experiment_run_id: str | None
    active_analysis_run_id: str | None
    manuscript_version_id: str | None
    last_decision_id: str | None
    artifact_refs: list[str]
    error_code: str | None
    reframe_count: int


def default_state(project_id: str, hypothesis_id: str | None = None, protocol_version_id: str | None = None, experiment_spec_id: str | None = None, decision_id: str | None = None) -> ResearchExecutionState:
    return {
        "project_id": project_id,
        "current_stage": "BOOTSTRAP",
        "active_task_id": None,
        "active_role": None,
        "protocol_version_id": protocol_version_id,
        "hypothesis_id": hypothesis_id,
        "active_experiment_spec_id": experiment_spec_id,
        "pending_review_finding_ids": [],
        "pending_objection_ids": [],
        "pending_approval_id": None,
        "active_experiment_run_id": None,
        "active_analysis_run_id": None,
        "manuscript_version_id": None,
        "last_decision_id": decision_id,
        "artifact_refs": [],
        "error_code": None,
        "reframe_count": 0,
    }
