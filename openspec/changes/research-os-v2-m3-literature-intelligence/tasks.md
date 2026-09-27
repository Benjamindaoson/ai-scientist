## 1. Schema and ingestion

- [x] 1.1 Add pg_trgm/vector extensions and all required `literature.*` tables.
- [x] 1.2 Add 2022-2026 venue registry, source adapters, exact identity, merge candidates, and resumable idempotent ingestion.

## 2. Full text and retrieval

- [x] 2.1 Add legal artifact hydration, section parser/chunker, versioned local embeddings, FTS/vector/RRF retrieval, and citation expansion.
- [x] 2.2 Add lazy claim extraction, external expansion, retrieval provenance, and independent novelty audits.

## 3. Quality and operations

- [x] 3.1 Add daily/weekly/monthly/on-demand CLI paths and frozen 20-question Known-Prior Benchmark.
- [x] 3.2 Run real PostgreSQL/vector integration, full regressions, report actual coverage/counts, validate OpenSpec, and commit.
