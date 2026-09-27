"""Create the canonical Research OS research schema.

Revision ID: 20260928_0001
Revises: None
"""
from alembic import op

from ai_scientist.research_store.models import TABLES


revision = "20260928_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE SCHEMA IF NOT EXISTS research")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    for table in TABLES.values():
        table.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(TABLES.values()):
        table.drop(bind=bind, checkfirst=True)
    op.execute("DROP SCHEMA IF EXISTS research CASCADE")
