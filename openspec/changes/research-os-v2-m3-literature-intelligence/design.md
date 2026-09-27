## Context

M1/M2 provide persistent facts and orchestration. M3 adds one shared literature service used through distinct retrieval-run provenance.

## Decisions

- Separate Paper, PaperVersion, and PaperAppearance tables.
- Canonicalize only exact identifiers in DOI → OpenReview → arXiv → proceedings → OpenAlex/S2 order; fuzzy similarity records a merge candidate.
- Store legal full text in Artifact Store, then persist section/page/character-aware chunks.
- Use PostgreSQL FTS + pg_trgm + pgvector and reciprocal-rank fusion; dense search first narrows papers, then full-text chunks.
- Default production embedding metadata is `BAAI/bge-m3`; tests use a versioned local deterministic provider while exercising the real vector column/operator.
- Extract claims only for explicitly deep-read papers and bind them to exact version/chunk.

## Recovery

Each ingestion run and source record is idempotency-keyed; failed work remains resumable without duplicate papers, versions, citations, chunks, or embeddings.
