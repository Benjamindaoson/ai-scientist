from __future__ import annotations

from sqlalchemy import Engine, text

from ai_scientist.research_store.models import metadata

from . import models  # noqa: F401


def initialize_literature_database(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS literature"))
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
    metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_literature_papers_fts ON literature.papers USING gin (to_tsvector('english', title || ' ' || abstract))"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_literature_papers_trgm ON literature.papers USING gin (normalized_title gin_trgm_ops)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_literature_embeddings_hnsw ON literature.embeddings USING hnsw (embedding vector_cosine_ops)"))
