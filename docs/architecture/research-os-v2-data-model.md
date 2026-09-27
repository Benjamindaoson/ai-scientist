# Research OS v2 Data Model

PostgreSQL is the only authoritative scientific store. The `research` and `literature` schemas are migrated with Alembic; LangGraph checkpoint tables are managed by the official PostgreSQL checkpointer.

## Research schema

The 23 Research Store tables are:

| Domain | Tables |
| --- | --- |
| Program and question | `programs`, `projects`, `ideas`, `idea_gate_evaluations`, `research_questions`, `hypotheses` |
| Frozen design | `protocol_versions`, `experiment_specs` |
| Work and execution | `tasks`, `agent_runs`, `action_requests`, `experiment_runs`, `analysis_runs` |
| Evidence and governance | `claims`, `evidence_items`, `claim_evidence_links`, `objections`, `review_findings`, `decisions`, `approvals` |
| Provenance and output | `artifacts`, `manuscript_versions`, `legacy_imports` |

Key invariants:

- A frozen protocol cannot be mutated. Revisions create a new version and content hash while retaining the original.
- An approval authorizes only the exact `target_id + target_hash`; changing a protocol or manuscript invalidates prior authority.
- A hypothesis ID cannot be reused for different scientific meaning.
- Claim/evidence relations are restricted to `SUPPORTS`, `CONTRADICTS`, `QUALIFIES`, `INCONCLUSIVE`, and `INVALID`.
- A completed analysis correction creates a new analysis run and marks dependent claims and manuscript versions `STALE`.
- Formal manuscript numbers are read from a completed `AnalysisRun`; unknown or changed values are rejected.
- Artifact rows contain URI, SHA-256, size, MIME type and metadata. Large bytes are never stored as PostgreSQL `BYTEA`.

## Scientific provenance

A major paper claim resolves through the following canonical chain:

`ManuscriptVersion -> Claim -> ClaimEvidenceLink -> EvidenceItem -> AnalysisRun -> ExperimentRun -> ExperimentSpec -> FROZEN ProtocolVersion`

Literature statements retain `paper_id`, `paper_version_id`, and `source_chunk_id`. Research packages export database rows, artifact integrity receipts, literature retrieval-run references and Git refs so the project can be reconstructed and audited.

## Literature schema

The 29 literature tables cover venue editions, paper identity/version/appearance, authors, citations, full-text artifacts/documents/sections/chunks, embedding models/vectors, notes and lazy claims, idea relations, auditable retrieval results, raw source records, ingestion cursors and merge candidates.

Database extensions used by the migration are `vector` and `pg_trgm`. Lexical retrieval uses PostgreSQL FTS; dense retrieval uses 1024-dimensional `pgvector` values.

## Migration and compatibility

Alembic revisions are ordered `20260928_0001_research_store`, `20260928_0002_literature_intelligence`, and `20260928_0003_paper_lifecycle`. The legacy SQLite reader is import-only: an idempotency receipt prevents the same database from creating duplicate canonical entities, and the source SQLite database is not modified.
