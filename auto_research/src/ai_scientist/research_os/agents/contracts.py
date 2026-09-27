from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ResearchRole(str, Enum):
    SCOUT = "scout"
    PI = "pi"
    ENGINEER = "engineer"
    ANALYST = "analyst"
    EDITOR = "editor"
    REVIEWER = "reviewer"


class Capability(str, Enum):
    DISCOVER_CANDIDATES = "discover_candidates"
    PRIOR_SEARCH = "prior_search"
    CANDIDATE_POOL = "candidate_pool"
    NOVELTY_EVIDENCE = "novelty_evidence"
    FORMALIZE_QUESTION = "formalize_question"
    COMPETING_EXPLANATIONS = "competing_explanations"
    STUDY_DESIGN = "study_design"
    NEXT_RESEARCH_ACTION = "next_research_action"
    INTERPRETATION = "interpretation"
    IMPLEMENT_CODE = "implement_code"
    IMPLEMENT_BASELINE = "implement_baseline"
    IMPLEMENT_EXPERIMENT = "implement_experiment"
    TEST_CODE = "test_code"
    RECORD_RUN_ARTIFACT = "record_run_artifact"
    DESIGN_MEASUREMENT = "design_measurement"
    FORMAL_ANALYSIS = "formal_analysis"
    STATISTICS = "statistics"
    UNCERTAINTY = "uncertainty"
    FORMAL_EVIDENCE = "formal_evidence"
    DRAFT_PAPER = "draft_paper"
    LATEX = "latex"
    FIGURES_TABLES = "figures_tables"
    APPENDIX = "appendix"
    REBUTTAL_EDITING = "rebuttal_editing"
    SUBMISSION_PACKAGE = "submission_package"
    INDEPENDENT_NOVELTY_AUDIT = "independent_novelty_audit"
    PROTOCOL_AUDIT = "protocol_audit"
    INDEPENDENT_RESULT_AUDIT = "independent_result_audit"
    CLAIM_EVIDENCE_AUDIT = "claim_evidence_audit"
    PAPER_REVIEW = "paper_review"
    MODIFY_RAW_RESULT = "modify_raw_result"
    MODIFY_FROZEN_PROTOCOL = "modify_frozen_protocol"
    MODIFY_SCIENTIFIC_NUMBERS = "modify_scientific_numbers"
    APPROVE_NOVELTY = "approve_novelty"
    APPROVE_OWN_AUDIT = "approve_own_audit"


class TaskSpec(StrictModel):
    task_id: str = Field(min_length=1)
    role: ResearchRole
    capability: Capability
    objective: str = Field(min_length=1)
    workspace: str = Field(min_length=1)
    input_refs: list[str]
    acceptance_criteria: list[str] = Field(min_length=1)
    context: dict[str, Any] = Field(default_factory=dict)


class TaskResult(StrictModel):
    task_id: str
    role: ResearchRole
    status: Literal["SUCCEEDED", "FAILED", "WAIT_FOR_HUMAN"]
    summary: str
    output_refs: list[str] = Field(default_factory=list)
    findings: list[ReviewFinding] = Field(default_factory=list)
    execution_record_ref: str | None = None
    error_code: str | None = None


class ReviewFinding(StrictModel):
    finding_id: str
    category: Literal["WRITING", "STATISTICS", "IMPLEMENTATION", "MISSING_EXPERIMENT", "NOVELTY", "CITATION", "CLAIM_EVIDENCE", "PROTOCOL"]
    severity: Literal["BLOCKING", "MAJOR", "MINOR"]
    target: str
    evidence_refs: list[str]
    impact: str
    required_resolution: str

    @model_validator(mode="after")
    def blocking_has_evidence(self):
        if self.severity == "BLOCKING" and not all((self.target, self.evidence_refs, self.impact, self.required_resolution)):
            raise ValueError("blocking finding requires target, evidence, impact, and required_resolution")
        return self


class ActionRequest(StrictModel):
    action_id: str
    operation: str
    target: str
    domain: str | None = None
    allowed_channels: list[Literal["api_cli", "http", "playwright", "desktop_ui", "vision"]]
    idempotency_key: str
    risk: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"
    approval_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class ClaimRecord(StrictModel):
    claim_id: str
    text: str
    scope: str
    protocol_version_id: str
    analysis_run_ids: list[str] = Field(min_length=1)
    evidence_ids: list[str] = Field(min_length=1)
    counterevidence_ids: list[str]
    status: Literal["SUPPORTED", "CONTRADICTED", "INCONCLUSIVE", "INVALID"]
