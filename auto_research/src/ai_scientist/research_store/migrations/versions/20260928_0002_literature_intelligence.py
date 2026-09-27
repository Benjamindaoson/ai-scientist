"""Create literature intelligence schema.

Revision ID: 20260928_0002
Revises: 20260928_0001
"""
from alembic import op
from sqlalchemy import text

from ai_scientist.literature_intelligence import models


revision = "20260928_0002"
down_revision = "20260928_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.execute("CREATE SCHEMA IF NOT EXISTS literature")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    for table in models.TABLES.values():
        table.create(bind=bind, checkfirst=True)
    bind.execute(text("CREATE INDEX IF NOT EXISTS ix_literature_papers_fts ON literature.papers USING gin (to_tsvector('english', title || ' ' || abstract))"))
    bind.execute(text("CREATE INDEX IF NOT EXISTS ix_literature_papers_trgm ON literature.papers USING gin (normalized_title gin_trgm_ops)"))
    bind.execute(text("CREATE INDEX IF NOT EXISTS ix_literature_embeddings_hnsw ON literature.embeddings USING hnsw (embedding vector_cosine_ops)"))


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS literature CASCADE")
