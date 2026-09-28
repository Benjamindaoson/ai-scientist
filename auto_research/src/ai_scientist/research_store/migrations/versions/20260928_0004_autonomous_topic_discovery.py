"""Add autonomous topic discovery storage.

Revision ID: 20260928_0004
Revises: 20260928_0003
"""
from alembic import op

from ai_scientist.opportunity_intelligence import models


revision = "20260928_0004"
down_revision = "20260928_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE SCHEMA IF NOT EXISTS research")
    for table in models.TABLES.values():
        table.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(list(models.TABLES.values())):
        table.drop(bind=bind, checkfirst=True)
