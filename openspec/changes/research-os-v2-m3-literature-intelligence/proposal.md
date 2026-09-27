## Why

Formal novelty decisions require auditable, version-aware evidence beyond the legacy arXiv abstract search.

## What Changes

- Add the complete `literature.*` schema, venue registry, exact-identifier canonicalization, source provenance, resumable ingestion, legal full-text artifacts, section-aware chunks, pgvector embeddings, PostgreSQL FTS/pg_trgm, citation expansion, retrieval runs, and lazy claims.
- Add Core Corpus 2022-2026 policies plus external novelty hydration.
- Add a frozen 20-question Known-Prior Benchmark and independent Scout/Reviewer novelty runs.

## Capabilities

### New Capabilities

- `literature-intelligence`: Canonical literature identity, ingestion, hybrid retrieval, citation graph, and auditable novelty conclusions.

## Impact

Formal novelty services use PostgreSQL literature records. Legacy `literature/search.py` remains compatibility-only.
