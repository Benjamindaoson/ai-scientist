"""Create the canonical Research OS research schema.

Revision ID: 20260928_0001
Revises: None
"""
from alembic import op

from ai_scientist.research_store.models import metadata


revision = "20260928_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE SCHEMA IF NOT EXISTS research")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    metadata.create_all(bind=bind)


def downgrade() -> None:
    metadata.drop_all(bind=op.get_bind())
    op.execute("DROP SCHEMA IF EXISTS research CASCADE")
