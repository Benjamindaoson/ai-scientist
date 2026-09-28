from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import Engine, func, insert, select, text, update

from ai_scientist.research_store.repository import canonical_hash

from . import models


IDENTIFIER_PRIORITY = ("doi", "openreview", "arxiv", "proceedings", "openalex", "s2")


def _uuid() -> str:
    return str(uuid.uuid4())


def normalize_text(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


def normalize_identifier(kind: str, value: str) -> str:
    value = value.strip().lower()
    if kind == "doi":
        value = value.removeprefix("https://doi.org/").removeprefix("doi:")
    if kind == "arxiv":
        value = value.removeprefix("arxiv:").split("v")[0]
    return value


class LiteratureRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def insert(self, table, **values: Any) -> dict[str, Any]:
        with self.engine.begin() as connection:
            return dict(connection.execute(insert(table).values(**values).returning(table)).one()._mapping)

    def count(self, table_name: str) -> int:
        with self.engine.connect() as connection:
            return int(connection.execute(select(func.count()).select_from(models.TABLES[table_name])).scalar_one())

    def find_paper_by_identifiers(self, identifiers: dict[str, str]) -> dict[str, Any] | None:
        normalized = [(kind, normalize_identifier(kind, identifiers[kind])) for kind in IDENTIFIER_PRIORITY if identifiers.get(kind)]
        with self.engine.connect() as connection:
            for kind, value in normalized:
                row = connection.execute(
                    select(models.papers).join(models.paper_identifiers).where(
                        models.paper_identifiers.c.identifier_type == kind,
                        models.paper_identifiers.c.identifier_value == value,
                    )
                ).first()
                if row:
                    return dict(row._mapping)
        return None

    def find_fuzzy_candidate(self, normalized_title: str, threshold: float = 0.80) -> tuple[dict[str, Any], float] | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(models.papers, func.similarity(models.papers.c.normalized_title, normalized_title).label("similarity"))
                .where(func.similarity(models.papers.c.normalized_title, normalized_title) >= threshold)
                .order_by(text("similarity DESC")).limit(1)
            ).first()
        if not row:
            return None
        data = dict(row._mapping)
        similarity = float(data.pop("similarity"))
        return data, similarity

    def get_source_record(self, source: str, native_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = connection.execute(select(models.source_records).where(models.source_records.c.source == source, models.source_records.c.native_id == native_id)).first()
        return dict(row._mapping) if row else None

    def get_paper(self, paper_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = connection.execute(select(models.papers).where(models.papers.c.paper_id == paper_id)).first()
        return dict(row._mapping) if row else None

    def get_paper_version(self, paper_version_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = connection.execute(select(models.paper_versions).where(models.paper_versions.c.paper_version_id == paper_version_id)).first()
        return dict(row._mapping) if row else None

    def get_or_create_version(self, paper_id: str, version_label: str, source_url: str, content_hash: str) -> dict[str, Any]:
        with self.engine.connect() as connection:
            row = connection.execute(select(models.paper_versions).where(
                models.paper_versions.c.paper_id == paper_id,
                models.paper_versions.c.version_label == version_label,
                models.paper_versions.c.content_hash == content_hash,
            )).first()
        return dict(row._mapping) if row else self.insert(models.paper_versions, paper_version_id=_uuid(), paper_id=paper_id, version_label=version_label, source_url=source_url, content_hash=content_hash)

    def list_appearances(self, paper_id: str) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            return [dict(row._mapping) for row in connection.execute(select(models.paper_appearances).where(models.paper_appearances.c.paper_id == paper_id))]

    def get_document_by_content(self, paper_version_id: str, content_hash: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = connection.execute(select(models.documents).where(models.documents.c.paper_version_id == paper_version_id, models.documents.c.content_hash == content_hash)).first()
        return dict(row._mapping) if row else None

    def list_document_chunks(self, document_id: str) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            return [dict(row._mapping) for row in connection.execute(select(models.chunks).where(models.chunks.c.document_id == document_id).order_by(models.chunks.c.ordinal))]

    def get_or_create_embedding_model(self, model_name: str, dimension: int, config: dict) -> dict[str, Any]:
        config_hash = canonical_hash(config)
        with self.engine.connect() as connection:
            row = connection.execute(select(models.embedding_models).where(models.embedding_models.c.model_name == model_name, models.embedding_models.c.config_hash == config_hash)).first()
        return dict(row._mapping) if row else self.insert(models.embedding_models, embedding_model_id=_uuid(), model_name=model_name, dimension=dimension, config=config, config_hash=config_hash)

    def ensure_embedding(self, chunk: dict[str, Any], model: dict[str, Any], vector: list[float]) -> dict[str, Any]:
        with self.engine.connect() as connection:
            row = connection.execute(select(models.embeddings).where(
                models.embeddings.c.chunk_id == chunk["chunk_id"], models.embeddings.c.embedding_model_id == model["embedding_model_id"],
                models.embeddings.c.content_hash == chunk["content_hash"],
            )).first()
        return dict(row._mapping) if row else self.insert(models.embeddings, embedding_id=_uuid(), chunk_id=chunk["chunk_id"], embedding_model_id=model["embedding_model_id"], content_hash=chunk["content_hash"], embedding=vector)

    def retrieval_results(self, retrieval_run_id: str) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(models.retrieval_results, models.papers.c.title, models.papers.c.abstract, models.papers.c.publication_year).join(models.papers, models.papers.c.paper_id == models.retrieval_results.c.paper_id)
                .where(models.retrieval_results.c.retrieval_run_id == retrieval_run_id).order_by(models.retrieval_results.c.rank)
            )
            return [dict(row._mapping) for row in rows]
