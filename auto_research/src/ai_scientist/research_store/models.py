from __future__ import annotations

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID


metadata = MetaData()
SCHEMA = "research"


def _id(name: str) -> Column:
    return Column(name, UUID(as_uuid=False), primary_key=True)


def _timestamps() -> tuple[Column, Column]:
    return (
        Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
        Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()),
    )


programs = Table(
    "programs", metadata,
    _id("program_id"), Column("name", Text, nullable=False), Column("description", Text),
    Column("status", Text, nullable=False, server_default="ACTIVE"), Column("policy_version", Text, nullable=False),
    *_timestamps(), schema=SCHEMA,
)

projects = Table(
    "projects", metadata,
    _id("project_id"), Column("program_id", UUID(as_uuid=False), ForeignKey("research.programs.program_id")),
    Column("legacy_id", Text, unique=True), Column("name", Text, nullable=False), Column("domain", Text),
    Column("seed_question", Text), Column("description", Text), Column("status", Text, nullable=False, server_default="ACTIVE"),
    Column("current_stage", Text, nullable=False, server_default="DISCOVERY"), *_timestamps(), schema=SCHEMA,
)

ideas = Table(
    "ideas", metadata,
    _id("idea_id"), Column("program_id", UUID(as_uuid=False), ForeignKey("research.programs.program_id")),
    Column("title", Text, nullable=False), Column("core_question", Text, nullable=False), Column("current_belief", Text),
    Column("proposed_challenge", Text), Column("falsifiable_claim", Text), Column("status", Text, nullable=False, server_default="CANDIDATE"),
    Column("created_by_role", Text, nullable=False), *_timestamps(), schema=SCHEMA,
)

idea_gate_evaluations = Table(
    "idea_gate_evaluations", metadata,
    _id("evaluation_id"), Column("idea_id", UUID(as_uuid=False), ForeignKey("research.ideas.idea_id"), nullable=False),
    Column("gate_name", Text, nullable=False), Column("score", Integer, nullable=False), Column("rationale", Text, nullable=False),
    Column("evidence_refs", JSONB, nullable=False, server_default="[]"), Column("blocking_gap", Text),
    Column("reviewer_role", Text, nullable=False), Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("score BETWEEN 0 AND 10", name="ck_idea_gate_score"), schema=SCHEMA,
)

research_questions = Table(
    "research_questions", metadata,
    _id("research_question_id"), Column("project_id", UUID(as_uuid=False), ForeignKey("research.projects.project_id"), nullable=False),
    Column("idea_id", UUID(as_uuid=False), ForeignKey("research.ideas.idea_id")), Column("question_text", Text, nullable=False),
    Column("scope", JSONB, nullable=False, server_default="{}"), Column("status", Text, nullable=False, server_default="ACTIVE"),
    Column("version", Integer, nullable=False, server_default="1"), *_timestamps(), schema=SCHEMA,
)

hypotheses = Table(
    "hypotheses", metadata,
    _id("hypothesis_id"), Column("project_id", UUID(as_uuid=False), ForeignKey("research.projects.project_id"), nullable=False),
    Column("parent_hypothesis_id", UUID(as_uuid=False), ForeignKey("research.hypotheses.hypothesis_id")),
    Column("claim", Text, nullable=False), Column("rationale", Text), Column("predicted_effect", Text),
    Column("falsification_conditions", JSONB, nullable=False, server_default="[]"), Column("status", Text, nullable=False, server_default="ACTIVE"),
    Column("version", Integer, nullable=False, server_default="1"), *_timestamps(), schema=SCHEMA,
)

protocol_versions = Table(
    "protocol_versions", metadata,
    _id("protocol_version_id"), Column("project_id", UUID(as_uuid=False), ForeignKey("research.projects.project_id"), nullable=False),
    Column("research_question_id", UUID(as_uuid=False), ForeignKey("research.research_questions.research_question_id"), nullable=False),
    Column("hypothesis_id", UUID(as_uuid=False), ForeignKey("research.hypotheses.hypothesis_id")),
    Column("version", Integer, nullable=False), Column("status", Text, nullable=False, server_default="DRAFT"),
    Column("design", JSONB, nullable=False, server_default="{}"), Column("measurement_plan", JSONB, nullable=False, server_default="{}"),
    Column("data_split_policy", JSONB, nullable=False, server_default="{}"), Column("analysis_plan", JSONB, nullable=False, server_default="{}"),
    Column("stopping_rules", JSONB, nullable=False, server_default="{}"), Column("exclusion_rules", JSONB, nullable=False, server_default="{}"),
    Column("resource_budget", JSONB, nullable=False, server_default="{}"), Column("content_hash", Text, nullable=False),
    Column("frozen_at", DateTime(timezone=True)), *_timestamps(),
    UniqueConstraint("project_id", "version", name="uq_protocol_project_version"), schema=SCHEMA,
)

tasks = Table(
    "tasks", metadata,
    _id("task_id"), Column("project_id", UUID(as_uuid=False), ForeignKey("research.projects.project_id"), nullable=False),
    Column("task_type", Text, nullable=False), Column("owner_role", Text, nullable=False), Column("status", Text, nullable=False),
    Column("input_refs", JSONB, nullable=False, server_default="{}"), Column("constraints", JSONB, nullable=False, server_default="{}"),
    Column("acceptance_criteria", JSONB, nullable=False, server_default="[]"), Column("budget", JSONB, nullable=False, server_default="{}"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()), Column("started_at", DateTime(timezone=True)),
    Column("completed_at", DateTime(timezone=True)), schema=SCHEMA,
)

agent_runs = Table(
    "agent_runs", metadata,
    _id("agent_run_id"), Column("task_id", UUID(as_uuid=False), ForeignKey("research.tasks.task_id"), nullable=False),
    Column("role", Text, nullable=False), Column("executor_type", Text, nullable=False), Column("executor_session_id", Text),
    Column("prompt_contract_version", Text, nullable=False), Column("status", Text, nullable=False), Column("input_hash", Text, nullable=False),
    Column("output_ref", JSONB, nullable=False, server_default="{}"), Column("usage", JSONB, nullable=False, server_default="{}"), *_timestamps(), schema=SCHEMA,
)

action_requests = Table(
    "action_requests", metadata,
    _id("action_request_id"), Column("task_id", UUID(as_uuid=False), ForeignKey("research.tasks.task_id"), nullable=False),
    Column("action_type", Text, nullable=False), Column("target", JSONB, nullable=False), Column("constraints", JSONB, nullable=False, server_default="{}"),
    Column("risk_level", Text, nullable=False), Column("requires_human_approval", Boolean, nullable=False, server_default="false"),
    Column("status", Text, nullable=False), Column("executor", Text), Column("result_ref", JSONB, nullable=False, server_default="{}"), *_timestamps(), schema=SCHEMA,
)

experiment_specs = Table(
    "experiment_specs", metadata,
    _id("experiment_spec_id"), Column("project_id", UUID(as_uuid=False), ForeignKey("research.projects.project_id"), nullable=False),
    Column("protocol_version_id", UUID(as_uuid=False), ForeignKey("research.protocol_versions.protocol_version_id"), nullable=False),
    Column("hypothesis_id", UUID(as_uuid=False), ForeignKey("research.hypotheses.hypothesis_id"), nullable=False),
    Column("idempotency_key", Text, nullable=False, unique=True), Column("objective", Text, nullable=False), Column("command", JSONB, nullable=False),
    Column("workspace", Text, nullable=False), Column("metrics_contract", JSONB, nullable=False), Column("controls", JSONB, nullable=False, server_default="{}"),
    Column("resource_limits", JSONB, nullable=False, server_default="{}"), Column("execution_profile", Text, nullable=False),
    Column("code_revision", Text, nullable=False), Column("data_manifest_hash", Text), Column("declared_seed", Integer),
    Column("spec_hash", Text, nullable=False, unique=True), *_timestamps(), schema=SCHEMA,
)

artifacts = Table(
    "artifacts", metadata,
    _id("artifact_id"), Column("project_id", UUID(as_uuid=False), ForeignKey("research.projects.project_id")),
    Column("artifact_type", Text, nullable=False), Column("uri", Text, nullable=False, unique=True), Column("sha256", Text, nullable=False),
    Column("mime_type", Text), Column("size_bytes", BigInteger, nullable=False), Column("metadata", JSONB, nullable=False, server_default="{}"),
    Column("created_by_task_id", UUID(as_uuid=False), ForeignKey("research.tasks.task_id")),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()), schema=SCHEMA,
)

experiment_runs = Table(
    "experiment_runs", metadata,
    _id("experiment_run_id"), Column("experiment_spec_id", UUID(as_uuid=False), ForeignKey("research.experiment_specs.experiment_spec_id"), nullable=False),
    Column("attempt", Integer, nullable=False), Column("external_run_id", Text), Column("status", Text, nullable=False), Column("return_code", Integer),
    Column("metrics", JSONB, nullable=False, server_default="{}"), Column("error_type", Text),
    Column("stdout_artifact_id", UUID(as_uuid=False), ForeignKey("research.artifacts.artifact_id")),
    Column("stderr_artifact_id", UUID(as_uuid=False), ForeignKey("research.artifacts.artifact_id")),
    Column("started_at", DateTime(timezone=True), server_default=func.now()), Column("completed_at", DateTime(timezone=True)),
    Column("runtime_metadata", JSONB, nullable=False, server_default="{}"),
    UniqueConstraint("experiment_spec_id", "attempt", name="uq_experiment_attempt"), schema=SCHEMA,
)

analysis_runs = Table(
    "analysis_runs", metadata,
    _id("analysis_run_id"), Column("project_id", UUID(as_uuid=False), ForeignKey("research.projects.project_id"), nullable=False),
    Column("protocol_version_id", UUID(as_uuid=False), ForeignKey("research.protocol_versions.protocol_version_id"), nullable=False),
    Column("input_experiment_run_ids", ARRAY(UUID(as_uuid=False)), nullable=False), Column("analysis_code_revision", Text, nullable=False),
    Column("analysis_plan_hash", Text, nullable=False), Column("status", Text, nullable=False), Column("results", JSONB, nullable=False, server_default="{}"),
    Column("uncertainty", JSONB, nullable=False, server_default="{}"), Column("limitations", JSONB, nullable=False, server_default="{}"),
    Column("artifact_refs", JSONB, nullable=False, server_default="[]"), *_timestamps(), schema=SCHEMA,
)

claims = Table(
    "claims", metadata,
    _id("claim_id"), Column("project_id", UUID(as_uuid=False), ForeignKey("research.projects.project_id"), nullable=False),
    Column("claim_type", Text, nullable=False), Column("claim_text", Text, nullable=False), Column("scope", JSONB, nullable=False, server_default="{}"),
    Column("status", Text, nullable=False, server_default="DRAFT"), Column("version", Integer, nullable=False, server_default="1"),
    Column("created_by_role", Text, nullable=False), *_timestamps(), schema=SCHEMA,
)

evidence_items = Table(
    "evidence_items", metadata,
    _id("evidence_id"), Column("project_id", UUID(as_uuid=False), ForeignKey("research.projects.project_id"), nullable=False),
    Column("evidence_type", Text, nullable=False), Column("source_ref", JSONB, nullable=False), Column("content_summary", Text, nullable=False),
    Column("validity_status", Text, nullable=False), Column("content_hash", Text, nullable=False), *_timestamps(), schema=SCHEMA,
)

claim_evidence_links = Table(
    "claim_evidence_links", metadata,
    Column("claim_id", UUID(as_uuid=False), ForeignKey("research.claims.claim_id"), primary_key=True),
    Column("evidence_id", UUID(as_uuid=False), ForeignKey("research.evidence_items.evidence_id"), primary_key=True),
    Column("relation", Text, primary_key=True), Column("rationale", Text, nullable=False), Column("created_by_role", Text, nullable=False),
    Column("review_status", Text, nullable=False, server_default="UNVERIFIED"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("relation IN ('SUPPORTS','CONTRADICTS','QUALIFIES','INCONCLUSIVE','INVALID')", name="ck_claim_evidence_relation"), schema=SCHEMA,
)

objections = Table(
    "objections", metadata,
    _id("objection_id"), Column("project_id", UUID(as_uuid=False), ForeignKey("research.projects.project_id"), nullable=False),
    Column("target_type", Text, nullable=False), Column("target_id", UUID(as_uuid=False), nullable=False), Column("category", Text, nullable=False),
    Column("severity", Text, nullable=False), Column("title", Text, nullable=False), Column("argument", Text, nullable=False),
    Column("supporting_evidence_ids", ARRAY(UUID(as_uuid=False)), nullable=False, server_default="{}"),
    Column("status", Text, nullable=False, server_default="OPEN"), Column("resolution_type", Text), Column("resolution_reason", Text),
    Column("raised_by_role", Text, nullable=False), *_timestamps(), schema=SCHEMA,
)

review_findings = Table(
    "review_findings", metadata,
    _id("review_finding_id"), Column("project_id", UUID(as_uuid=False), ForeignKey("research.projects.project_id"), nullable=False),
    Column("review_stage", Text, nullable=False), Column("category", Text, nullable=False), Column("severity", Text, nullable=False),
    Column("target_type", Text, nullable=False), Column("target_id", UUID(as_uuid=False), nullable=False), Column("finding", Text, nullable=False),
    Column("evidence_refs", JSONB, nullable=False), Column("impact", Text), Column("required_resolution", Text, nullable=False),
    Column("status", Text, nullable=False, server_default="OPEN"), *_timestamps(), schema=SCHEMA,
)

decisions = Table(
    "decisions", metadata,
    _id("decision_id"), Column("project_id", UUID(as_uuid=False), ForeignKey("research.projects.project_id"), nullable=False),
    Column("decision_type", Text, nullable=False), Column("decision", Text, nullable=False), Column("gate_results", JSONB, nullable=False, server_default="{}"),
    Column("reason_refs", JSONB, nullable=False, server_default="[]"), Column("policy_version", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()), schema=SCHEMA,
)

approvals = Table(
    "approvals", metadata,
    _id("approval_id"), Column("project_id", UUID(as_uuid=False), ForeignKey("research.projects.project_id"), nullable=False),
    Column("approval_type", Text, nullable=False), Column("target_type", Text, nullable=False), Column("target_id", UUID(as_uuid=False), nullable=False),
    Column("target_hash", Text, nullable=False), Column("status", Text, nullable=False, server_default="PENDING"), Column("approved_by", Text),
    Column("budget_authorized", JSONB), *_timestamps(), schema=SCHEMA,
)

manuscript_versions = Table(
    "manuscript_versions", metadata,
    _id("manuscript_version_id"), Column("project_id", UUID(as_uuid=False), ForeignKey("research.projects.project_id"), nullable=False),
    Column("version", Integer, nullable=False), Column("source_artifact_id", UUID(as_uuid=False), ForeignKey("research.artifacts.artifact_id"), nullable=False),
    Column("pdf_artifact_id", UUID(as_uuid=False), ForeignKey("research.artifacts.artifact_id")),
    Column("claim_ids", ARRAY(UUID(as_uuid=False)), nullable=False, server_default="{}"), Column("status", Text, nullable=False),
    Column("content_hash", Text, nullable=False), *_timestamps(),
    UniqueConstraint("project_id", "version", name="uq_manuscript_project_version"), schema=SCHEMA,
)

legacy_imports = Table(
    "legacy_imports", metadata,
    _id("legacy_import_id"), Column("source_hash", Text, nullable=False), Column("source_table", Text, nullable=False),
    Column("source_row_id", Text, nullable=False), Column("target_type", Text, nullable=False), Column("target_id", UUID(as_uuid=False), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    UniqueConstraint("source_hash", "source_table", "source_row_id", name="uq_legacy_source_row"), schema=SCHEMA,
)


TABLES = {table.name: table for table in metadata.tables.values() if table.schema == SCHEMA}
