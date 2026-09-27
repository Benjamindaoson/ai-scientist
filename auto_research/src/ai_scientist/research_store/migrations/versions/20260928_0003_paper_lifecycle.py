"""Add claim and manuscript lifecycle provenance.

Revision ID: 20260928_0003
Revises: 20260928_0002
"""
from alembic import op


revision = "20260928_0003"
down_revision = "20260928_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE research.claims ADD COLUMN IF NOT EXISTS parent_claim_id UUID REFERENCES research.claims(claim_id)")
    op.execute("ALTER TABLE research.claims ADD COLUMN IF NOT EXISTS content_hash TEXT")
    op.execute("ALTER TABLE research.claims ADD COLUMN IF NOT EXISTS invalidated_at TIMESTAMPTZ")
    op.execute("ALTER TABLE research.claims ADD COLUMN IF NOT EXISTS invalidation_reason TEXT")
    op.execute("ALTER TABLE research.review_findings ADD COLUMN IF NOT EXISTS assigned_roles JSONB NOT NULL DEFAULT '[]'::jsonb")
    op.execute("ALTER TABLE research.manuscript_versions ADD COLUMN IF NOT EXISTS numeric_trace JSONB NOT NULL DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE research.manuscript_versions ADD COLUMN IF NOT EXISTS literature_trace JSONB NOT NULL DEFAULT '[]'::jsonb")
    op.execute("ALTER TABLE research.manuscript_versions ADD COLUMN IF NOT EXISTS validation JSONB NOT NULL DEFAULT '{}'::jsonb")
    op.execute("ALTER TABLE research.manuscript_versions ADD COLUMN IF NOT EXISTS invalidated_at TIMESTAMPTZ")
    op.execute("ALTER TABLE research.manuscript_versions ADD COLUMN IF NOT EXISTS invalidation_reason TEXT")


def downgrade() -> None:
    for table, column in (
        ("manuscript_versions", "invalidation_reason"), ("manuscript_versions", "invalidated_at"),
        ("manuscript_versions", "validation"), ("manuscript_versions", "literature_trace"),
        ("manuscript_versions", "numeric_trace"), ("review_findings", "assigned_roles"),
        ("claims", "invalidation_reason"), ("claims", "invalidated_at"), ("claims", "content_hash"),
        ("claims", "parent_claim_id"),
    ):
        op.execute(f"ALTER TABLE research.{table} DROP COLUMN IF EXISTS {column}")
