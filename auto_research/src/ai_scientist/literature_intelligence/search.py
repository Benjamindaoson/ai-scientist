from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, insert, or_, select, update

from . import models
from .repository import LiteratureRepository


def _uuid() -> str:
    return str(uuid.uuid4())


class HybridSearch:
    def __init__(self, repository: LiteratureRepository, embedding_provider):
        self.repository = repository
        self.embedding_provider = embedding_provider

    def search(self, query: str, *, actor_role: str, idea_ref: str | None = None, query_variants: list[str] | None = None, filters: dict | None = None, limit: int = 50) -> dict[str, Any]:
        variants = list(dict.fromkeys(query_variants or [query]))
        run = self.repository.insert(
            models.retrieval_runs, retrieval_run_id=_uuid(), idea_ref=idea_ref, actor_role=actor_role, query=query,
            query_variants=variants, filters=filters or {},
            retrieval_config={"keyword": "postgresql_fts+pg_trgm", "dense": "pgvector_cosine", "fusion": "rrf", "rrf_k": 60},
            embedding_model=self.embedding_provider.model_name, candidate_count=0, deep_read_set=[],
        )
        document = func.to_tsvector("english", models.papers.c.title + " " + models.papers.c.abstract)
        keyword_rank: dict[str, int] = {}
        dense_rank: dict[str, int] = {}
        with self.repository.engine.connect() as connection:
            model = connection.execute(select(models.embedding_models).where(models.embedding_models.c.model_name == self.embedding_provider.model_name).order_by(models.embedding_models.c.created_at.desc()).limit(1)).first()
            vectors = self.embedding_provider.embed_many(variants) if model and hasattr(self.embedding_provider, "embed_many") else None
            for variant_index, variant in enumerate(variants):
                query_expr = func.plainto_tsquery("english", variant)
                keyword_rows = connection.execute(
                    select(models.papers.c.paper_id, func.ts_rank_cd(document, query_expr).label("rank_score"), func.similarity(models.papers.c.normalized_title, variant.lower()).label("trgm"))
                    .where(or_(document.op("@@")(query_expr), func.similarity(models.papers.c.normalized_title, variant.lower()) > 0.1))
                    .order_by((func.ts_rank_cd(document, query_expr) + func.similarity(models.papers.c.normalized_title, variant.lower())).desc()).limit(limit)
                ).all()
                for index, row in enumerate(keyword_rows, 1):
                    keyword_rank[row.paper_id] = min(index, keyword_rank.get(row.paper_id, index))
                if model:
                    vector = vectors[variant_index] if vectors is not None else self.embedding_provider.embed(variant)
                    distance = models.embeddings.c.embedding.cosine_distance(vector)
                    dense_rows = connection.execute(
                        select(models.paper_versions.c.paper_id, func.min(distance).label("distance"))
                        .join(models.chunks, models.chunks.c.paper_version_id == models.paper_versions.c.paper_version_id)
                        .join(models.embeddings, models.embeddings.c.chunk_id == models.chunks.c.chunk_id)
                        .where(models.embeddings.c.embedding_model_id == model._mapping["embedding_model_id"])
                        .group_by(models.paper_versions.c.paper_id).order_by(func.min(distance)).limit(limit)
                    ).all()
                    for index, row in enumerate(dense_rows, 1):
                        dense_rank[row.paper_id] = min(index, dense_rank.get(row.paper_id, index))
        paper_ids = set(keyword_rank) | set(dense_rank)
        scores = {paper_id: (1 / (60 + keyword_rank[paper_id]) if paper_id in keyword_rank else 0) + (1 / (60 + dense_rank[paper_id]) if paper_id in dense_rank else 0) for paper_id in paper_ids}
        ordered = sorted(scores, key=scores.get, reverse=True)[:limit]
        deep_read = []
        with self.repository.engine.begin() as connection:
            for rank, paper_id in enumerate(ordered, 1):
                chunks = connection.execute(
                    select(models.chunks.c.chunk_id).join(models.paper_versions, models.paper_versions.c.paper_version_id == models.chunks.c.paper_version_id)
                    .where(models.paper_versions.c.paper_id == paper_id).order_by(models.chunks.c.ordinal).limit(3)
                ).all()
                source_chunk_ids = [row.chunk_id for row in chunks]
                if source_chunk_ids:
                    deep_read.append(paper_id)
                connection.execute(insert(models.retrieval_results).values(
                    retrieval_result_id=_uuid(), retrieval_run_id=run["retrieval_run_id"], paper_id=paper_id, rank=rank,
                    score=scores[paper_id], keyword_rank=keyword_rank.get(paper_id), dense_rank=dense_rank.get(paper_id), source_chunk_ids=source_chunk_ids,
                ))
            connection.execute(update(models.retrieval_runs).where(models.retrieval_runs.c.retrieval_run_id == run["retrieval_run_id"]).values(candidate_count=len(ordered), deep_read_set=deep_read))
        return {"retrieval_run_id": run["retrieval_run_id"], "results": self.repository.retrieval_results(run["retrieval_run_id"]), "source_chunk_ids": [chunk for row in self.repository.retrieval_results(run["retrieval_run_id"]) for chunk in row["source_chunk_ids"]]}


class NoveltyService:
    def __init__(self, search: HybridSearch):
        self.search = search

    def audit(self, idea_ref: str, query: str, *, actor_role: str, external: bool = True) -> dict[str, Any]:
        result = self.search.search(query, actor_role=actor_role, idea_ref=idea_ref, filters={"external_expansion": external})
        with self.search.repository.engine.begin() as connection:
            for item in result["results"]:
                connection.execute(insert(models.idea_paper_relations).values(
                    idea_paper_relation_id=_uuid(), idea_ref=idea_ref, paper_id=item["paper_id"], relation="NOVELTY_CANDIDATE",
                    retrieval_run_id=result["retrieval_run_id"],
                ))
        return result
