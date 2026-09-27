# Research OS v2 Literature Intelligence

Literature Intelligence runs entirely on PostgreSQL FTS, `pg_trgm`, `pgvector`, a citation graph, section-aware full text and lazy claim extraction. It does not use Neo4j, GraphRAG, Elasticsearch or an external vector database.

## Corpus policy

The core schedule contains 14 venues for event years 2022–2026: ICLR, ICML, NeurIPS, AISTATS, AAAI, CVPR, ICCV, ECCV, ACL, EMNLP, CoRL, RSS, ICRA and IROS. Core acceptance is recorded only from official venue evidence. arXiv, workshop, journal, Findings, technical-report and adjacent-field records are external novelty expansion, not core-acceptance proof.

The M3 integration corpus is intentionally bounded: it proves the ingestion and retrieval machinery but is not a claimed complete 50,000-paper production corpus. The measured snapshot contained 33 papers, 35 paper versions, 3 venue appearances, 23 documents, 26 section-aware chunks, 25 embeddings, 4 citation edges and 1 lazily extracted claim. Two official-source records were bootstrapped across ICLR and NeurIPS; all 70 venue/year editions were scheduled.

## Ingestion

Adapters normalize records from OpenAlex, Crossref, Semantic Scholar, OpenReview, ACL Anthology, arXiv and official conference sources. Exact identifiers are idempotent; fuzzy title similarity produces a merge candidate rather than silently merging papers. Raw source records and payload hashes preserve provenance. Full-text acquisition records the source URL, license, byte hash, parser version, section offsets and chunk offsets.

Ingestion jobs have idempotency keys, status, cursor and counts. Daily, weekly, monthly, quarterly and annual schedules are exposed through the CLI. Re-running the same job or citation import does not duplicate papers, versions, documents, chunks or citation edges.

## Hybrid retrieval

Retrieval first ranks papers, then expands only the selected deep-read set to section-aware chunks. Lexical and dense ranks are fused with Reciprocal Rank Fusion; citation-neighbor expansion is capped. Every retrieval run stores actor role, query variants, filters, model/config, candidate count, ranked results and source chunk IDs.

Formal novelty uses two independent runs: Scout and Independent Reviewer do not share a mutable result set. Both core corpus and external expansion can produce novelty-killing evidence. Claim extraction remains lazy and source-chunk bound.

## Frozen benchmark

The frozen 20-query benchmark produced:

| Metric | Result |
| --- | ---: |
| Top-50 recall | 1.0000 |
| Top-20 recall | 1.0000 |
| source-attribution precision | 1.0000 |
| fabricated citations | 0 |

These are retrieval-fixture results, not a claim that the bounded integration corpus has full field coverage or that local BGE-M3 quality was benchmarked on all target papers.
