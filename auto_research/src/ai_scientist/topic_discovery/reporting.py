from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, text


class TopicReportWriter:
    def __init__(self, engine: Engine, output_root: str | Path = "reports/topic_discovery"):
        self.engine = engine
        self.root = Path(output_root)
        self.root.mkdir(parents=True, exist_ok=True)

    def write(self, *, benchmark_result: dict[str, Any] | None = None) -> list[str]:
        with self.engine.connect() as connection:
            opportunities = [dict(row._mapping) for row in connection.execute(text("""
                SELECT opportunity_type, venue_name, venue_year, title, official_url, status,
                       submission_deadline_raw, submission_deadline_utc, official_verified, stale,
                       last_checked_at, content_hash
                FROM research.opportunities ORDER BY venue_name, venue_year, opportunity_type, title
            """))]
            opportunity_counts = dict(connection.execute(text("SELECT status, count(*) FROM research.opportunities GROUP BY status")).all())
            snapshots = connection.execute(text("SELECT count(*) FROM research.opportunity_snapshots")).scalar_one()
            signals = connection.execute(text("SELECT count(*) FROM research.research_signals")).scalar_one()
            corpus = dict(connection.execute(text("""
                SELECT 'papers', count(*) FROM literature.papers UNION ALL
                SELECT 'paper_versions', count(*) FROM literature.paper_versions UNION ALL
                SELECT 'documents', count(*) FROM literature.documents UNION ALL
                SELECT 'chunks', count(*) FROM literature.chunks UNION ALL
                SELECT 'embeddings', count(*) FROM literature.embeddings UNION ALL
                SELECT 'citations', count(*) FROM literature.citations
            """)).all())
            database_bytes = connection.execute(text("SELECT pg_database_size(current_database())")).scalar_one()
            coverage = [dict(row._mapping) for row in connection.execute(text("""
                SELECT v.code AS venue, ve.event_year,
                       count(DISTINCT pa.paper_id) AS found,
                       count(DISTINCT pa.paper_id) AS accepted,
                       count(DISTINCT CASE WHEN p.title <> '' THEN pa.paper_id END) AS metadata,
                       count(DISTINCT d.paper_version_id) AS source_documents,
                       count(DISTINCT CASE WHEN lower(coalesce(a.license, '')) NOT LIKE '%abstract%'
                                                AND lower(coalesce(a.license, '')) NOT LIKE '%frozen benchmark metadata%'
                                           THEN d.paper_version_id END) AS fulltext_documents,
                       count(DISTINCT CASE WHEN em.model_name = 'BAAI/bge-m3' THEN e.chunk_id END) AS embedded_chunks,
                       count(DISTINCT c.citation_id) AS citation_edges
                FROM literature.venue_editions ve
                JOIN literature.venues v ON v.venue_id = ve.venue_id
                LEFT JOIN literature.paper_appearances pa ON pa.venue_edition_id = ve.venue_edition_id
                LEFT JOIN literature.papers p ON p.paper_id = pa.paper_id
                LEFT JOIN literature.paper_versions pv ON pv.paper_id = pa.paper_id
                LEFT JOIN literature.documents d ON d.paper_version_id = pv.paper_version_id
                LEFT JOIN literature.artifacts a ON a.literature_artifact_id = d.literature_artifact_id
                LEFT JOIN literature.chunks ch ON ch.paper_version_id = pv.paper_version_id
                LEFT JOIN literature.embeddings e ON e.chunk_id = ch.chunk_id
                LEFT JOIN literature.embedding_models em ON em.embedding_model_id = e.embedding_model_id
                LEFT JOIN literature.citations c ON c.citing_paper_id = pa.paper_id OR c.cited_paper_id = pa.paper_id
                GROUP BY v.code, ve.event_year ORDER BY v.code, ve.event_year
            """))]
            embedding_models = [dict(row._mapping) for row in connection.execute(text("""
                SELECT em.model_name, count(e.embedding_id) AS embeddings
                FROM literature.embedding_models em LEFT JOIN literature.embeddings e USING (embedding_model_id)
                GROUP BY em.model_name ORDER BY em.model_name
            """))]
            discovery = [dict(row._mapping) for row in connection.execute(text("SELECT * FROM research.discovery_runs ORDER BY started_at"))]
            state_counts = dict(connection.execute(text("SELECT state, count(*) FROM research.topic_candidates GROUP BY state")).all())
            lineage_counts = dict(connection.execute(text("SELECT status, count(*) FROM research.idea_lineage GROUP BY status")).all())
            lineage_outcomes = dict(connection.execute(text("""
                SELECT
                    count(*) FILTER (WHERE parent_idea_id IS NOT NULL) AS reframed,
                    count(*) FILTER (WHERE failed_gate = 'DATA_FEASIBILITY') AS feasibility_killed,
                    count(*) FILTER (WHERE failed_gate = 'FINAL_TOPIC_REVIEW') AS final_review_killed
                FROM research.idea_lineage
            """)).mappings().one())
            audits = [dict(row._mapping) for row in connection.execute(text("SELECT actor_role, decision, count(*) AS count FROM research.novelty_audits GROUP BY actor_role, decision ORDER BY actor_role, decision"))]
            final = connection.execute(text("SELECT * FROM research.topic_dossiers WHERE status='TOPIC_READY' ORDER BY created_at DESC LIMIT 1")).mappings().first()

        opportunity_lines = [
            "# Opportunity Intelligence Report", "", "## Execution summary", "",
            f"- Opportunities: {len(opportunities)}", f"- Status counts: `{json.dumps(opportunity_counts, default=str)}`",
            f"- Versioned snapshots: {snapshots}", f"- Research signals: {signals}",
            "- Source policy: official source first; stale/UNKNOWN rows retain provenance and never fabricate a deadline.",
            "", "## Current records", "",
            "| Type | Venue/year | Title | Status | Deadline raw | Deadline UTC | Official | Stale | Source |",
            "|---|---|---|---|---|---|---:|---:|---|",
        ]
        for item in opportunities:
            opportunity_lines.append(f"| {item['opportunity_type']} | {item['venue_name'] or ''} {item['venue_year'] or ''} | {item['title'].replace('|', '/')} | {item['status']} | {item['submission_deadline_raw'] or ''} | {item['submission_deadline_utc'] or ''} | {item['official_verified']} | {item['stale']} | {item['official_url']} |")
        self._write("opportunity_intelligence_report.md", "\n".join(opportunity_lines) + "\n")

        index_run_path = self.root / "bge_m3_index_run.json"
        index_run = json.loads(index_run_path.read_text(encoding="utf-8")) if index_run_path.exists() else {"status": "NOT RECORDED"}
        corpus_lines = [
            "# Production Literature Corpus Report", "", "## Counts", "", f"```json\n{json.dumps(corpus, indent=2)}\n```", "",
            f"- PostgreSQL database storage: {database_bytes} bytes", "", "## BGE-M3 production index execution", "",
            f"```json\n{json.dumps(index_run, indent=2)}\n```", "",
            "`documents` currently counts source-backed parsed documents; the coverage table must be read with the recorded artifact license and source URL. Abstract-only documents are not represented as complete paper full text.",
            "", "## Embedding models", "", f"```json\n{json.dumps(embedding_models, indent=2)}\n```", "",
            "## Venue/year coverage", "", "| Venue | Year | Found | Accepted | Metadata | Source documents | Full text | BGE-M3 chunks | Citation edges |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for row in coverage:
            corpus_lines.append(f"| {row['venue']} | {row['event_year']} | {row['found']} | {row['accepted']} | {row['metadata']} | {row['source_documents']} | {row['fulltext_documents']} | {row['embedded_chunks']} | {row['citation_edges']} |")
        self._write("literature_corpus_report.md", "\n".join(corpus_lines) + "\n")

        metrics = benchmark_result or {}
        benchmark_lines = [
            "# Retrieval Benchmark Report", "", "## Frozen benchmark", "",
            f"- Questions: {metrics.get('queries', 'NOT RUN')}",
            f"- Recall@10: {metrics.get('recall_at_10', 'NOT RUN')}",
            f"- Recall@20: {metrics.get('top_20_recall', 'NOT RUN')}",
            f"- Recall@50: {metrics.get('top_50_recall', 'NOT RUN')}",
            f"- MRR: {metrics.get('mrr', 'NOT RUN')}",
            f"- Dangerous-prior recall: {metrics.get('dangerous_prior_recall', 'NOT RUN')}",
            f"- External-prior recall: {metrics.get('external_prior_recall', 'N/A')}",
            f"- False-positive rate: {metrics.get('false_positive_rate', 'NOT RUN')}",
            f"- Inspectable source rate: {metrics.get('inspectable_source_rate', 'NOT RUN')}",
            f"- Fabricated IDs: {metrics.get('fabricated_ids', 'NOT RUN')}",
            "", "Each production question records its designated dangerous/closest prior, two false-friend IDs, and a source chunk. The JSON fixture is frozen at `benchmarks/literature/known_prior_production_v1.json`.",
        ]
        self._write("retrieval_benchmark_report.md", "\n".join(benchmark_lines) + "\n")

        discovery_lines = [
            "# Autonomous Discovery Loop Report", "", "## Runs", "", f"```json\n{json.dumps(discovery, indent=2, default=str)}\n```", "",
            "## Candidate and audit outcomes", "", f"- Candidate states: `{json.dumps(state_counts)}`", f"- Lineage states: `{json.dumps(lineage_counts)}`",
            f"- Ideas reframed: {lineage_outcomes['reframed']}",
            f"- Feasibility-killed: {lineage_outcomes['feasibility_killed']}",
            f"- Final-review-killed: {lineage_outcomes['final_review_killed']}",
            f"- Novelty audits (including uncertain and survived): `{json.dumps(audits)}`", "",
            "A failed candidate or wave is not a terminal condition. The loop changes strategy across CFP themes, workshop questions, limitations/contradictions, measurement/identification, cross-domain transfer, and new capabilities. Manuscript and full experiment paths are not invoked.",
        ]
        self._write("discovery_loop_report.md", "\n".join(discovery_lines) + "\n")

        if final:
            dossier = final["dossier"]
            self._write("final_topic_dossier.json", json.dumps(dossier, indent=2, default=str) + "\n")
        return [str(path) for path in sorted(self.root.glob("*.md"))] + [str(path) for path in sorted(self.root.glob("*.json"))]

    def _write(self, name: str, content: str) -> None:
        (self.root / name).write_text(content, encoding="utf-8")
