from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import insert, select, update, func

from ai_scientist.research_store.db import ResearchStoreConfig
from ai_scientist.research_store.repository import canonical_hash

from . import models
from .repository import LiteratureRepository, normalize_identifier, normalize_text


CORE_VENUES = {
    "ICLR": "machine-learning", "ICML": "machine-learning", "NeurIPS": "machine-learning", "AISTATS": "machine-learning", "AAAI": "artificial-intelligence",
    "CVPR": "computer-vision", "ICCV": "computer-vision", "ECCV": "computer-vision",
    "ACL": "natural-language-processing", "EMNLP": "natural-language-processing",
    "CoRL": "robot-learning", "RSS": "robotics", "ICRA": "robotics", "IROS": "robotics",
}
CORE_YEARS = tuple(range(2022, 2027))

SECTION_TYPES = {
    "abstract": "abstract", "introduction": "introduction", "related work": "related_work", "method": "method", "methods": "method",
    "theory": "theory", "experiments": "experiments", "results": "experiments", "limitations": "limitations",
    "conclusion": "conclusion", "appendix": "appendix", "references": "references",
}


def _uuid() -> str:
    return str(uuid.uuid4())


class LiteratureService:
    def __init__(self, repository: LiteratureRepository, artifact_root: str | Path | None = None):
        self.repository = repository
        root = Path(artifact_root or ResearchStoreConfig.from_env().artifact_root) / "literature"
        self.artifact_root = root.resolve()
        self.artifact_root.mkdir(parents=True, exist_ok=True)

    def bootstrap_core_venues(self) -> None:
        for code, field in CORE_VENUES.items():
            with self.repository.engine.connect() as connection:
                venue_row = connection.execute(select(models.venues).where(models.venues.c.code == code)).first()
            venue = dict(venue_row._mapping) if venue_row else self.repository.insert(
                models.venues, venue_id=_uuid(), code=code, name=code, field=field,
                policy={"official_acceptance_required": True, "main_tracks_only": True},
            )
            for year in CORE_YEARS:
                with self.repository.engine.connect() as connection:
                    existing = connection.execute(select(models.venue_editions.c.venue_edition_id).where(models.venue_editions.c.venue_id == venue["venue_id"], models.venue_editions.c.event_year == year)).first()
                if not existing:
                    self.repository.insert(models.venue_editions, venue_edition_id=_uuid(), venue_id=venue["venue_id"], event_year=year, status="CONFIGURED", include_tracks=["main", "research"], exclude_tracks=["workshop", "demo", "tutorial"])

    def bootstrap_core_records(self, records: list[dict[str, Any]]) -> dict[str, int]:
        """Hydrate a frozen official-source bootstrap snapshot across core venues."""
        paper_ids: set[str] = set()
        venues: set[str] = set()
        for record in records:
            appearance = record["official_appearance"]
            paper = self.ingest_record(record["paper"])
            paper_ids.add(paper["paper_id"])
            venues.add(appearance["venue_code"])
            if not self.repository.list_appearances(paper["paper_id"]):
                self.add_official_appearance(paper["paper_id"], **appearance)
        return {"papers": len(paper_ids), "venues": len(venues)}

    def ingest_record(self, record: dict[str, Any]) -> dict[str, Any]:
        source = record["source"].lower()
        native_id = record["source_record_id"]
        existing_source = self.repository.get_source_record(source, native_id)
        if existing_source:
            paper = self.repository.get_paper(existing_source["paper_id"])
            with self.repository.engine.connect() as connection:
                version = connection.execute(select(models.paper_versions).where(models.paper_versions.c.paper_id == existing_source["paper_id"]).order_by(models.paper_versions.c.created_at.desc())).first()
            return {**paper, "paper_version_id": version._mapping["paper_version_id"]}  # type: ignore[arg-type]

        identifiers = {kind.lower(): normalize_identifier(kind.lower(), value) for kind, value in record.get("identifiers", {}).items() if value}
        paper = self.repository.find_paper_by_identifiers(identifiers)
        fuzzy = None if paper else self.repository.find_fuzzy_candidate(normalize_text(record["title"]))
        if not paper:
            paper = self.repository.insert(
                models.papers, paper_id=_uuid(), title=record["title"], normalized_title=normalize_text(record["title"]),
                abstract=record.get("abstract", ""), publication_year=record.get("publication_year"),
            )
            for kind, value in identifiers.items():
                self.repository.insert(models.paper_identifiers, paper_identifier_id=_uuid(), paper_id=paper["paper_id"], identifier_type=kind, identifier_value=value)
            if fuzzy:
                self.repository.insert(models.merge_events, merge_event_id=_uuid(), candidate_paper_id=paper["paper_id"], existing_paper_id=fuzzy[0]["paper_id"], reason="fuzzy_title_candidate", similarity=fuzzy[1])
        else:
            with self.repository.engine.begin() as connection:
                for kind, value in identifiers.items():
                    exists = connection.execute(select(models.paper_identifiers.c.paper_identifier_id).where(models.paper_identifiers.c.identifier_type == kind, models.paper_identifiers.c.identifier_value == value)).first()
                    if not exists:
                        connection.execute(insert(models.paper_identifiers).values(paper_identifier_id=_uuid(), paper_id=paper["paper_id"], identifier_type=kind, identifier_value=value))

        version_data = record.get("version", {})
        version_hash = canonical_hash({"title": record["title"], "abstract": record.get("abstract", ""), "version": version_data.get("version_label", "v1")})
        version = self.repository.get_or_create_version(paper["paper_id"], version_data.get("version_label", "v1"), version_data.get("source_url", ""), version_hash)
        for author in record.get("authors", []):
            normalized_name = normalize_text(author["name"])
            with self.repository.engine.connect() as connection:
                author_row = connection.execute(select(models.authors).where(models.authors.c.normalized_name == normalized_name)).first()
            saved_author = dict(author_row._mapping) if author_row else self.repository.insert(models.authors, author_id=_uuid(), name=author["name"], normalized_name=normalized_name)
            with self.repository.engine.begin() as connection:
                relation = connection.execute(select(models.paper_authors.c.paper_id).where(models.paper_authors.c.paper_id == paper["paper_id"], models.paper_authors.c.author_id == saved_author["author_id"])).first()
                if not relation:
                    connection.execute(insert(models.paper_authors).values(paper_id=paper["paper_id"], author_id=saved_author["author_id"], position=author.get("position", 1), is_corresponding=author.get("is_corresponding", False)))
        self.repository.insert(models.source_records, source_record_id=_uuid(), source=source, native_id=native_id, paper_id=paper["paper_id"], raw_payload=record, payload_hash=canonical_hash(record))
        return {**paper, "paper_version_id": version["paper_version_id"]}

    def ingest_records(
        self,
        records: list[dict[str, Any]],
        *,
        job_type: str,
        idempotency_key: str,
        source: str,
        scope: str,
        cursor: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run one resumable ingestion batch without duplicating a completed job."""
        with self.repository.engine.connect() as connection:
            existing = connection.execute(
                select(models.ingestion_runs).where(models.ingestion_runs.c.idempotency_key == idempotency_key)
            ).first()
        if existing and existing._mapping["status"] == "COMPLETE":
            return dict(existing._mapping)
        run_id = existing._mapping["ingestion_run_id"] if existing else _uuid()
        if not existing:
            self.repository.insert(
                models.ingestion_runs,
                ingestion_run_id=run_id,
                job_type=job_type,
                idempotency_key=idempotency_key,
                status="RUNNING",
                cursor=cursor or {},
                counts={"seen": 0, "ingested": 0},
            )
        counts = {"seen": 0, "ingested": 0}
        try:
            for record in records:
                counts["seen"] += 1
                self.ingest_record(record)
                counts["ingested"] += 1
            next_cursor = cursor or {}
            with self.repository.engine.begin() as connection:
                connection.execute(
                    update(models.ingestion_runs)
                    .where(models.ingestion_runs.c.ingestion_run_id == run_id)
                    .values(status="COMPLETE", cursor=next_cursor, counts=counts, completed_at=func.now())
                )
                state = connection.execute(
                    select(models.sync_state.c.sync_state_id).where(
                        models.sync_state.c.source == source, models.sync_state.c.scope == scope
                    )
                ).first()
                if state:
                    connection.execute(
                        update(models.sync_state)
                        .where(models.sync_state.c.sync_state_id == state.sync_state_id)
                        .values(cursor=next_cursor, last_success_at=func.now())
                    )
                else:
                    connection.execute(
                        insert(models.sync_state).values(
                            sync_state_id=_uuid(), source=source, scope=scope,
                            cursor=next_cursor, last_success_at=func.now(),
                        )
                    )
        except Exception:
            with self.repository.engine.begin() as connection:
                connection.execute(
                    update(models.ingestion_runs)
                    .where(models.ingestion_runs.c.ingestion_run_id == run_id)
                    .values(status="FAILED", counts=counts)
                )
            raise
        with self.repository.engine.connect() as connection:
            return dict(connection.execute(
                select(models.ingestion_runs).where(models.ingestion_runs.c.ingestion_run_id == run_id)
            ).one()._mapping)

    def add_official_appearance(self, paper_id: str, venue_code: str, event_year: int, track: str, *, official_source_url: str) -> dict[str, Any]:
        if not official_source_url.startswith("https://"):
            raise ValueError("official acceptance source must be HTTPS")
        with self.repository.engine.connect() as connection:
            edition = connection.execute(select(models.venue_editions).join(models.venues).where(models.venues.c.code == venue_code, models.venue_editions.c.event_year == event_year)).first()
        if not edition:
            raise KeyError((venue_code, event_year))
        with self.repository.engine.connect() as connection:
            existing = connection.execute(select(models.paper_appearances).where(
                models.paper_appearances.c.paper_id == paper_id,
                models.paper_appearances.c.venue_edition_id == edition._mapping["venue_edition_id"],
                models.paper_appearances.c.track == track,
            )).first()
        if existing:
            return dict(existing._mapping)
        return self.repository.insert(models.paper_appearances, paper_appearance_id=_uuid(), paper_id=paper_id, venue_edition_id=edition._mapping["venue_edition_id"], track=track, acceptance_status="ACCEPTED", is_core_accepted=track in {"main", "research"}, official_source_url=official_source_url)

    def ingest_full_text(self, paper_version_id: str, content: str, *, source_url: str, license_name: str) -> dict[str, Any]:
        if not source_url.startswith("https://") or not license_name:
            raise ValueError("full text requires a public HTTPS source and license/provenance label")
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        existing = self.repository.get_document_by_content(paper_version_id, content_hash)
        if existing:
            return existing
        relative = Path(content_hash[:2]) / f"{content_hash}.txt"
        target = (self.artifact_root / relative).resolve()
        if self.artifact_root not in target.parents:
            raise ValueError("literature artifact path escapes root")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text(content, encoding="utf-8")
        artifact = self.repository.insert(models.artifacts, literature_artifact_id=_uuid(), paper_version_id=paper_version_id, uri=relative.as_posix(), sha256=content_hash, source_url=source_url, license=license_name, mime_type="text/plain")
        document = self.repository.insert(models.documents, document_id=_uuid(), paper_version_id=paper_version_id, literature_artifact_id=artifact["literature_artifact_id"], content_hash=content_hash, parser_version="section-text-v1")
        sections = self._sections(content)
        chunk_ordinal = 0
        for ordinal, section in enumerate(sections):
            saved = self.repository.insert(models.sections, section_id=_uuid(), document_id=document["document_id"], section_type=section["type"], heading=section["heading"], ordinal=ordinal, page_start=1, page_end=1, char_start=section["start"], char_end=section["end"], content_hash=hashlib.sha256(section["content"].encode()).hexdigest())
            words = section["content"].split()
            for start in range(0, max(1, len(words)), 1000):
                chunk_text = " ".join(words[start:start + 1000])
                if not chunk_text:
                    continue
                char_start = content.find(chunk_text.split()[0], section["start"])
                char_end = min(section["end"], char_start + len(chunk_text))
                self.repository.insert(models.chunks, chunk_id=_uuid(), document_id=document["document_id"], section_id=saved["section_id"], paper_version_id=paper_version_id, ordinal=chunk_ordinal, content=chunk_text, token_count=len(words[start:start + 1000]), page_start=1, page_end=1, char_start=char_start, char_end=char_end, content_hash=hashlib.sha256(chunk_text.encode()).hexdigest())
                chunk_ordinal += 1
        return document

    def _sections(self, content: str) -> list[dict[str, Any]]:
        lines = content.splitlines(keepends=True)
        starts: list[tuple[int, str, str]] = []
        offset = 0
        for line in lines:
            heading = line.strip().lower().rstrip(":")
            if heading in SECTION_TYPES:
                starts.append((offset, SECTION_TYPES[heading], line.strip()))
            offset += len(line)
        if not starts:
            starts = [(0, "other", "")]
        output = []
        for index, (start, section_type, heading) in enumerate(starts):
            end = starts[index + 1][0] if index + 1 < len(starts) else len(content)
            body_start = start + (len(heading) if heading else 0)
            section_content = content[body_start:end].strip()
            output.append({"type": section_type, "heading": heading, "start": body_start, "end": end, "content": section_content})
        return output

    def embed_document(self, document_id: str, provider) -> int:
        model = self.repository.get_or_create_embedding_model(provider.model_name, provider.dimension, provider.config)
        chunks = self.repository.list_document_chunks(document_id)
        for chunk in chunks:
            self.repository.ensure_embedding(chunk, model, provider.embed(chunk["content"]))
        return len(chunks)

    def add_citation(self, citing_paper_id: str, cited_paper_id: str, *, source: str, source_record_id: str) -> dict[str, Any]:
        with self.repository.engine.connect() as connection:
            edge_row = connection.execute(select(models.citations).where(models.citations.c.citing_paper_id == citing_paper_id, models.citations.c.cited_paper_id == cited_paper_id)).first()
        edge = dict(edge_row._mapping) if edge_row else self.repository.insert(models.citations, citation_id=_uuid(), citing_paper_id=citing_paper_id, cited_paper_id=cited_paper_id)
        with self.repository.engine.connect() as connection:
            source_row = connection.execute(select(models.citation_sources).where(models.citation_sources.c.citation_id == edge["citation_id"], models.citation_sources.c.source == source, models.citation_sources.c.source_record_id == source_record_id)).first()
        if not source_row:
            self.repository.insert(models.citation_sources, citation_source_id=_uuid(), citation_id=edge["citation_id"], source=source, source_record_id=source_record_id)
        return edge

    def expand_citations(self, paper_id: str, hops: int = 2) -> set[str]:
        frontier = {paper_id}
        seen = {paper_id}
        for _ in range(max(0, min(hops, 2))):
            with self.repository.engine.connect() as connection:
                rows = connection.execute(select(models.citations.c.citing_paper_id, models.citations.c.cited_paper_id).where((models.citations.c.citing_paper_id.in_(frontier)) | (models.citations.c.cited_paper_id.in_(frontier))))
                next_ids = {value for row in rows for value in row if value not in seen}
            seen |= next_ids
            frontier = next_ids
        return seen - {paper_id}

    def co_citations(self, paper_id: str) -> set[str]:
        """Papers cited alongside ``paper_id`` by the same citing works."""
        first = models.citations.alias("first")
        second = models.citations.alias("second")
        with self.repository.engine.connect() as connection:
            rows = connection.execute(
                select(second.c.cited_paper_id)
                .select_from(first.join(second, first.c.citing_paper_id == second.c.citing_paper_id))
                .where(first.c.cited_paper_id == paper_id, second.c.cited_paper_id != paper_id)
            )
            return {row.cited_paper_id for row in rows}

    def bibliographic_coupling(self, paper_id: str) -> set[str]:
        """Papers sharing at least one cited reference with ``paper_id``."""
        first = models.citations.alias("first")
        second = models.citations.alias("second")
        with self.repository.engine.connect() as connection:
            rows = connection.execute(
                select(second.c.citing_paper_id)
                .select_from(first.join(second, first.c.cited_paper_id == second.c.cited_paper_id))
                .where(first.c.citing_paper_id == paper_id, second.c.citing_paper_id != paper_id)
            )
            return {row.citing_paper_id for row in rows}

    def same_author_papers(self, paper_id: str) -> set[str]:
        first = models.paper_authors.alias("first")
        second = models.paper_authors.alias("second")
        with self.repository.engine.connect() as connection:
            rows = connection.execute(
                select(second.c.paper_id)
                .select_from(first.join(second, first.c.author_id == second.c.author_id))
                .where(first.c.paper_id == paper_id, second.c.paper_id != paper_id)
            )
            return {row.paper_id for row in rows}

    def add_topic(self, paper_id: str, name: str, score: float | None = None) -> dict[str, Any]:
        normalized = normalize_text(name)
        with self.repository.engine.connect() as connection:
            row = connection.execute(select(models.topics).where(models.topics.c.name == normalized)).first()
        topic = dict(row._mapping) if row else self.repository.insert(
            models.topics, topic_id=_uuid(), name=normalized, description=None,
        )
        with self.repository.engine.begin() as connection:
            relation = connection.execute(select(models.paper_topics).where(
                models.paper_topics.c.paper_id == paper_id,
                models.paper_topics.c.topic_id == topic["topic_id"],
            )).first()
            if not relation:
                connection.execute(insert(models.paper_topics).values(
                    paper_id=paper_id, topic_id=topic["topic_id"], score=score,
                ))
        return topic

    def topic_expansion(self, paper_id: str) -> set[str]:
        first = models.paper_topics.alias("first")
        second = models.paper_topics.alias("second")
        with self.repository.engine.connect() as connection:
            rows = connection.execute(
                select(second.c.paper_id)
                .select_from(first.join(second, first.c.topic_id == second.c.topic_id))
                .where(first.c.paper_id == paper_id, second.c.paper_id != paper_id)
            )
            return {row.paper_id for row in rows}

    @staticmethod
    def load_known_prior_benchmark(path: str | Path) -> list[dict[str, Any]]:
        return json.loads(Path(path).read_text(encoding="utf-8"))

    def run_known_prior_benchmark(self, benchmark: list[dict[str, Any]], search) -> dict[str, Any]:
        top10 = top20 = top50 = inspectable = fabricated = external_total = external_found = false_friend_hits = false_friend_total = 0
        reciprocal_ranks = 0.0
        for item in benchmark:
            paper = self.repository.get_paper(item["designated_paper_id"]) if item.get("designated_paper_id") else self.repository.find_paper_by_identifiers({"arxiv": item["designated_identifier"].split(":", 1)[1]})
            if not paper:
                continue
            with self.repository.engine.connect() as connection:
                version = connection.execute(select(models.paper_versions).where(models.paper_versions.c.paper_id == paper["paper_id"]).limit(1)).first()
                document = connection.execute(select(models.documents).where(models.documents.c.paper_version_id == version._mapping["paper_version_id"])).first()
            if not document:
                document_data = self.ingest_full_text(version._mapping["paper_version_id"], f"Abstract\n{paper['abstract']}", source_url=item["paper"]["version"]["source_url"], license_name="frozen benchmark metadata")
                self.embed_document(document_data["document_id"], search.embedding_provider)
            result = search.search(item["question"], actor_role="benchmark", limit=50)
            ids = [row["paper_id"] for row in result["results"]]
            if paper["paper_id"] in ids[:50]:
                top50 += 1
            if paper["paper_id"] in ids[:20]:
                top20 += 1
            if paper["paper_id"] in ids[:10]:
                top10 += 1
            if paper["paper_id"] in ids:
                reciprocal_ranks += 1 / (ids.index(paper["paper_id"]) + 1)
            if item.get("source_scope") == "EXTERNAL":
                external_total += 1
                external_found += int(paper["paper_id"] in ids[:50])
            false_friends = set(item.get("false_friend_paper_ids", []))
            false_friend_total += len(false_friends)
            false_friend_hits += len(false_friends & set(ids[:10]))
            designated = next((row for row in result["results"] if row["paper_id"] == paper["paper_id"]), None)
            if designated and designated["source_chunk_ids"]:
                inspectable += 1
            fabricated += sum(1 for paper_id in ids if self.repository.get_paper(paper_id) is None)
        total = len(benchmark)
        return {
            "queries": total, "recall_at_10": top10 / total, "top_20_recall": top20 / total,
            "top_50_recall": top50 / total, "mrr": reciprocal_ranks / total,
            "dangerous_prior_recall": top50 / total,
            "external_prior_recall": external_found / external_total if external_total else None,
            "false_positive_rate": false_friend_hits / false_friend_total if false_friend_total else 0.0,
            "inspectable_source_rate": inspectable / total, "fabricated_ids": fabricated,
        }
