# Research OS v2 M3 Report

## 1. Scope

M3 implements PostgreSQL Literature Intelligence only. It does not implement the six role agents, Codex/RPA execution, manuscript lifecycle, or legacy retirement assigned to M4-M5.

## 2. System Implemented

- Added `pg_trgm`, pgvector, and PostgreSQL FTS with 29 `literature.*` tables.
- Kept Paper, PaperVersion, and PaperAppearance as distinct records. Exact identifiers deduplicate by DOI, OpenReview, arXiv, proceedings, OpenAlex, and Semantic Scholar priority; fuzzy title matches create reviewable merge candidates only.
- Registered 14 core venues for every 2022-2026 edition (70 configured venue editions) with track include/exclude policies and official-evidence-only Core acceptance.
- Added eight source endpoints: OpenReview, PMLR, CVF, ACL Anthology, NeurIPS Proceedings, Crossref, OpenAlex, and Semantic Scholar.
- Added a frozen, official-source multi-venue bootstrap snapshot for ICLR 2022 and NeurIPS 2022. The bootstrap is idempotent and records two official appearances.
- Added content-addressed legal full-text artifacts, version-aware documents, section-aware 700-1200 target chunks (1000-word ceiling), source/page/character provenance, and local versioned embeddings. `BAAI/bge-m3` is the production provider; tests use the deterministic local 1024-dimensional provider and no paid API.
- Added paper FTS/trigram search, pgvector cosine search, reciprocal-rank fusion, exact source chunks, retrieval-run provenance, independent Scout/Reviewer runs, and external novelty candidate relations.
- Added citation/reference one/two-hop, co-citation, bibliographic-coupling, same-author, and topic expansion.
- Added on-demand claim extraction bound to exact paper versions and source chunks with `review_status=unverified`.
- Added idempotent resumable ingestion state and CLI schedules for daily, weekly, monthly, and on-demand jobs.

## 3. Actual Ingestion Coverage

This is a deliberately small verified bootstrap, not a claim that the complete 2022-2026 corpus has already downloaded.

| Measure | Actual |
| --- | ---: |
| configured venues | 14 |
| configured venue editions | 70 (14 venues x 2022-2026) |
| official multi-venue bootstrap | 2 papers across ICLR and NeurIPS |
| papers after integration/benchmark fixtures | 33 |
| paper versions | 35 |
| official appearances exercised | 3 |
| PDF files | 0 |
| public/frozen text documents | 23 |
| chunks | 26 |
| embeddings | 25 |
| citation edges | 4 |
| lazy claims | 1 |
| retrieval runs after benchmark/audits | 22 |

The resumable full-ingest path is verified through PostgreSQL ingestion-run and sync-state checkpoints. Long-running full-corpus acquisition remains an operational data job and was not represented as complete.

## 4. Known-Prior Benchmark

The frozen benchmark contains 20 public research questions and designated real arXiv identifiers. Its file was created before executing the benchmark and was not altered in response to results.

| Metric | Required | Actual |
| --- | ---: | ---: |
| designated prior Top-50 recall | >= 90% | 100% (20/20) |
| designated prior Top-20 recall | >= 80% | 100% (20/20) |
| conclusions with inspectable source chunk | 100% | 100% (20/20) |
| fabricated paper IDs | 0 | 0 |

## 5. External Expansion Test

An external arXiv prior outside the Core appearance set was hydrated, sectioned, embedded, and recovered by hybrid retrieval. Scout and Independent Reviewer audits produced distinct retrieval-run IDs and persisted source-chunk provenance.

## 6. Files Changed

| Path | Change |
| --- | --- |
| `auto_research/src/ai_scientist/literature_intelligence/` | schema, repository, ingestion, source adapters, embeddings, full text, claims, graph expansion, hybrid search, novelty audit |
| `auto_research/src/ai_scientist/research_store/cli.py` | scheduled literature sync CLI |
| `auto_research/src/ai_scientist/research_store/migrations/versions/20260928_0001_research_store.py` | constrain historical M1 migration to its own schema when later metadata is loaded |
| `auto_research/src/ai_scientist/research_store/migrations/versions/20260928_0002_literature_intelligence.py` | M3 schema/extensions/index migration |
| `benchmarks/literature/` | frozen 20-question known-prior benchmark and official two-venue bootstrap snapshot |
| `tests/test_m3_literature_intelligence.py` | real PostgreSQL/vector M3 acceptance tests |
| `openspec/changes/research-os-v2-m3-literature-intelligence/` | M3 proposal, design, requirements, and completed tasks |
| `pyproject.toml` | HTTP/retry dependencies and optional local literature embedding dependency |

## 7. Tests and Commands

| Command | Exit | Result |
| --- | ---: | --- |
| `pytest -q tests/test_m3_literature_intelligence.py` in Compose test service | 0 | 10 passed |
| fresh database `alembic upgrade head` | 0 | revisions 0001 and 0002 applied; 23 research tables, 29 literature tables, `pg_trgm` and `vector` present |
| complete pytest in Compose test service | 0 | 83 passed, 0 failed, 0 skipped, 14 pre-existing warnings |
| `python -m compileall -q auto_research/src` | 0 | passed |
| `python test_autonomous_research_loop.py` | 0 | passed |
| `python test_v4_integration.py` | 0 | 6/6 passed |
| `python test_v1_v4_regression.py` | 0 | 6/6 passed |
| discovery/planner/hypothesis/benchmark regression selection | 0 | 6 passed |
| `openspec validate research-os-v2-m3-literature-intelligence` | 0 | valid |
| `git diff --check` | 0 | passed |

## 8. Regression Status

M0-M2, complete pytest, legacy integration scripts, and discovery/benchmark regressions pass. No frozen scientific threshold or prior result was changed.

## 9. Deviations From Specification

NONE. The specification explicitly permits the full corpus download to continue as an operational job when code, a real multi-venue bootstrap, resumability, and actual coverage are reported. This report does not claim full-corpus completion.

## 10. Remaining Blockers

NONE for M3 implementation. Full 2022-2026 corpus hydration is pending operational execution, not an M3 code blocker.

## 11. M3 Verdict

PASS
