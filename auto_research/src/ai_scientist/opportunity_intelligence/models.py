from __future__ import annotations

from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, Table, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from ai_scientist.research_store.models import metadata


SCHEMA = "research"
OPPORTUNITY_TYPES = (
    "MAIN_CONFERENCE_CFP", "WORKSHOP_CFP", "SPECIAL_TRACK", "DATASET_BENCHMARK_TRACK",
    "CHALLENGE", "COMPETITION", "POSITION_PAPER_CALL", "BLUE_SKY_CALL",
    "JOURNAL_SPECIAL_ISSUE", "TUTORIAL_THEME", "COMMUNITY_OPEN_PROBLEM",
)


def _id(name: str) -> Column:
    return Column(name, UUID(as_uuid=False), primary_key=True)


opportunities = Table(
    "opportunities", metadata,
    _id("opportunity_id"), Column("opportunity_type", Text, nullable=False), Column("title", Text, nullable=False),
    Column("venue_name", Text), Column("venue_year", Integer), Column("parent_event", Text), Column("track_name", Text),
    Column("official_url", Text, nullable=False, unique=True), Column("cfp_text", Text, nullable=False, server_default=""),
    Column("topic_text", Text, nullable=False, server_default=""), Column("submission_open", DateTime(timezone=True)),
    Column("submission_deadline_raw", Text), Column("submission_deadline_utc", DateTime(timezone=True)),
    Column("timezone", Text), Column("deadline_type", Text), Column("event_start", Date), Column("event_end", Date),
    Column("status", Text, nullable=False, server_default="UNKNOWN"), Column("source_priority", Integer, nullable=False),
    Column("official_verified", Boolean, nullable=False, server_default="false"),
    Column("first_seen_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("last_checked_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("content_hash", Text), Column("retrieval_method", Text), Column("stale", Boolean, nullable=False, server_default="false"),
    schema=SCHEMA,
)
opportunity_topics = Table(
    "opportunity_topics", metadata, _id("opportunity_topic_id"),
    Column("opportunity_id", UUID(as_uuid=False), ForeignKey("research.opportunities.opportunity_id"), nullable=False),
    Column("topic", Text, nullable=False), Column("normalized_topic", Text, nullable=False), Column("source_span", Text),
    Column("weight", Float, nullable=False, server_default="1"),
    UniqueConstraint("opportunity_id", "normalized_topic", name="uq_opportunity_topic"), schema=SCHEMA,
)
opportunity_snapshots = Table(
    "opportunity_snapshots", metadata, _id("snapshot_id"),
    Column("opportunity_id", UUID(as_uuid=False), ForeignKey("research.opportunities.opportunity_id"), nullable=False),
    Column("raw_content", Text, nullable=False), Column("retrieved_at", DateTime(timezone=True), nullable=False),
    Column("content_hash", Text, nullable=False), Column("source_url", Text, nullable=False),
    Column("retrieval_method", Text, nullable=False), schema=SCHEMA,
)
research_signals = Table(
    "research_signals", metadata, _id("signal_id"), Column("signal_type", Text, nullable=False),
    Column("source_type", Text, nullable=False), Column("source_id", Text, nullable=False), Column("title", Text, nullable=False),
    Column("description", Text, nullable=False), Column("evidence_refs", JSONB, nullable=False),
    Column("domain", Text, nullable=False), Column("topic_tags", JSONB, nullable=False), Column("novelty_hint", Text),
    Column("fingerprint", Text, nullable=False, unique=True),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()), schema=SCHEMA,
)
idea_lineage = Table(
    "idea_lineage", metadata, _id("idea_lineage_id"), Column("idea_id", Text, nullable=False, unique=True),
    Column("parent_idea_id", Text), Column("generation", Integer, nullable=False, server_default="0"),
    Column("origin_signal_ids", JSONB, nullable=False), Column("normalized_question", Text, nullable=False),
    Column("semantic_fingerprint", Text, nullable=False), Column("reframe_reason", Text), Column("kill_reason", Text),
    Column("killing_papers", JSONB, nullable=False, server_default="[]"), Column("failed_gate", Text),
    Column("status", Text, nullable=False), Column("material_change_refs", JSONB, nullable=False, server_default="[]"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()), schema=SCHEMA,
)
topic_candidates = Table(
    "topic_candidates", metadata, _id("candidate_row_id"), Column("idea_id", Text, nullable=False, unique=True),
    Column("wave", Integer, nullable=False), Column("strategy", Text, nullable=False), Column("payload", JSONB, nullable=False),
    Column("state", Text, nullable=False), Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()), schema=SCHEMA,
)
novelty_audits = Table(
    "novelty_audits", metadata, _id("novelty_audit_id"), Column("idea_id", Text, nullable=False),
    Column("actor_role", Text, nullable=False), Column("retrieval_run_id", UUID(as_uuid=False), nullable=False),
    Column("decision", Text, nullable=False), Column("search_matrix", JSONB, nullable=False),
    Column("dangerous_priors", JSONB, nullable=False), Column("coverage", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()), schema=SCHEMA,
)
feasibility_audits = Table(
    "feasibility_audits", metadata, _id("feasibility_audit_id"), Column("idea_id", Text, nullable=False),
    Column("audit_type", Text, nullable=False), Column("status", Text, nullable=False), Column("evidence", JSONB, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()), schema=SCHEMA,
)
topic_dossiers = Table(
    "topic_dossiers", metadata, _id("topic_id"), Column("idea_id", Text, nullable=False, unique=True),
    Column("status", Text, nullable=False), Column("dossier", JSONB, nullable=False), Column("content_hash", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()), schema=SCHEMA,
)
discovery_runs = Table(
    "discovery_runs", metadata, _id("discovery_run_id"), Column("program", JSONB, nullable=False),
    Column("status", Text, nullable=False), Column("wave", Integer, nullable=False, server_default="0"),
    Column("counts", JSONB, nullable=False, server_default="{}"), Column("current_strategy", Text), Column("topic_id", UUID(as_uuid=False)),
    Column("error", Text), Column("started_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("completed_at", DateTime(timezone=True)), schema=SCHEMA,
)

TABLES = {table.name: table for table in metadata.tables.values() if table.schema == SCHEMA and table.name in {
    "opportunities", "opportunity_topics", "opportunity_snapshots", "research_signals", "idea_lineage",
    "topic_candidates", "novelty_audits", "feasibility_audits", "topic_dossiers", "discovery_runs",
}}
