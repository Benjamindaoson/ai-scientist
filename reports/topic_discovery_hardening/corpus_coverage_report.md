# Corpus Coverage Report

## Qualification rule

`COMPLETE` requires an uncapped official-proceedings traversal with an official expected count or an exhausted official index. `PARTIAL` includes capped or visibly incomplete ingestion. `UNAVAILABLE` is reserved for a venue-year with no proceedings because it is future, not held, or the official source is unavailable. Zero is never treated as complete.

## Venue/year state

| Venue | 2022 | 2023 | 2024 | 2025 | 2026 | Qualification |
|---|---:|---:|---:|---:|---:|---|
| AAAI | 1624 | 2022 | 924 | 120 | 120 | PARTIAL; no official expected-count reconciliation |
| ACL | 240 | 120 | 120 | 120 | 120 | PARTIAL; capped editions |
| AISTATS | 491 | 496 | 547 | 583 | 0 | COMPLETE for exhausted 2022–2025 PMLR indices; 2026 UNAVAILABLE |
| CoRL | 197 | 199 | 264 | 0 | 0 | COMPLETE for exhausted 2022–2024 PMLR indices; later editions UNAVAILABLE |
| CVPR | 0 | 120 | 120 | 120 | 120 | PARTIAL; 2022 missing and later editions capped |
| ECCV | 120 | 0 | 120 | 0 | 0 | PARTIAL for held editions; odd/non-held years UNAVAILABLE |
| EMNLP | 120 | 120 | 120 | 120 | 0 | PARTIAL; capped editions, 2026 UNAVAILABLE |
| ICCV | 0 | 120 | 0 | 120 | 0 | PARTIAL for held editions; even years UNAVAILABLE |
| ICLR | 3 | 4 | 4 | 3 | 0 | PARTIAL; severe source-resolution undercoverage |
| ICML | 1233 | 1827 | 2609 | 3328 | 0 | COMPLETE for exhausted 2022–2025 PMLR indices; 2026 UNAVAILABLE |
| ICRA | 228 | 120 | 120 | 120 | 0 | PARTIAL; Crossref/proceedings coverage not reconciled |
| IROS | 120 | 120 | 120 | 120 | 0 | PARTIAL; capped editions |
| NeurIPS | 30 | 5 | 8 | 8 | 1 | PARTIAL; severe source-resolution undercoverage |
| RSS | 74 | 112 | 120 | 120 | 120 | PARTIAL; later editions capped |

## Correctness conclusion

The corpus is operational but is not a complete five-year top-venue corpus. Production defaults no longer impose `limit=120`; rerunning `sync-production` with the default `--max-per-edition 0` traverses pagination/indexes to exhaustion. Existing capped historical rows remain explicitly PARTIAL until those runs finish and are reconciled.

## Full text and citation graph

Abstract-backed documents are not counted as complete paper full text. Hardened novelty audit lazily attempts legal arXiv HTML hydration for dangerous priors and otherwise records `FULL_TEXT_UNAVAILABLE`. Citation-graph coverage is reported per candidate neighborhood; the global graph is not represented as complete.

