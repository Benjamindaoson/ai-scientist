# Research OS v2 M5 Report

## 1. Scope

M5 completes the versioned claim/manuscript/review/revision/release lifecycle, reconstructable research package, centralized configuration, runnable CLI, legacy disposition audit and final architecture/operations documentation. It preserves M0–M4 scientific semantics and does not automate external submission.

## 2. Paper Lifecycle Implemented

- Frozen versioned claims require a frozen protocol, completed analyses and valid analysis-bound evidence.
- Correcting an analysis creates a new canonical analysis and marks the replaced analysis, dependent claims and dependent manuscripts stale.
- LaTeX manuscript versions bind every formal number to an `AnalysisRun` metric and every major claim to the full protocol/experiment/evidence chain.
- Independent paper findings are strict typed records and route by expertise; novelty/citation findings trigger an independent retrieval callback.
- Rebuttals record PI/Analyst/Engineer/Editor/Reviewer responsibility and reviewer verification.
- Versioned venue-policy preflight verifies PDF/source integrity, references, findings, claims, numbers, sections, anonymity, disclosure, supplement, reproducibility and secret patterns.
- Final release pauses at a durable LangGraph interrupt and accepts only an explicit `APPROVED` row bound to the exact manuscript ID and content hash.
- Research packages reconstruct from PostgreSQL rows, artifact hashes and actual Git refs.
- Follow-up ideas remain `PENDING_NOVELTY_GATE` and cannot auto-publish.

## 3. End-to-End Acceptance

| # | Acceptance | Evidence | Result |
| ---: | --- | --- | --- |
| 1 | Candidate KILL before experiment | `test_kill_path_never_calls_experiment_runner`; M0 runner spy | PASS |
| 2 | Candidate REFRAME | `test_reframe_routes_back_to_discovery_without_experiment` | PASS |
| 3 | Killer CONTINUE | M5 graph E2E with `KILLER_GATE=CONTINUE` | PASS |
| 4 | INCONCLUSIVE remains distinct | `test_inconclusive_is_not_contradiction` | PASS |
| 5 | INVALID execution is not contradiction | `test_failed_execution_is_invalid_evidence` | PASS |
| 6 | Analysis correction invalidates downstream | `test_analysis_correction_invalidates_claim_and_manuscript` | PASS |
| 7 | Statistics routes to Analyst | `test_review_router_assigns_expertise_and_novelty_retrieval` | PASS |
| 8 | Implementation routes to Engineer | same typed routing test | PASS |
| 9 | Novelty triggers independent retrieval | same typed routing test and callback receipt | PASS |
| 10 | Manuscript numbers trace to AnalysisRun | `test_claim_to_protocol_chain_and_manuscript_numbers_are_traceable` | PASS |
| 11 | Main claims trace to Evidence | same provenance-chain test | PASS |
| 12 | Evidence traces to ExperimentRun | same provenance-chain test | PASS |
| 13 | ExperimentRun traces to ExperimentSpec | same provenance-chain test | PASS |
| 14 | ExperimentSpec traces to frozen ProtocolVersion | same provenance-chain test | PASS |
| 15 | Restart at human interrupt preserves state | M2 start interrupt plus M5 final-release restart E2E | PASS |
| 16 | Replay does not duplicate experiment | `test_graph_replay_does_not_duplicate_experiment` | PASS |
| 17 | No final release without Human Approval | service rejection and graph hash-bound validation tests | PASS |
| 18 | Package reconstructs from DB + artifacts + Git | two package/integrity integration tests using real Git | PASS |
| 19 | Discovery benchmark remains valid | 8 discovery/benchmark regressions and M4 real mini-E2E | PASS |
| 20 | M0–M4 regressions pass | 55 milestone tests; complete 103-test suite | PASS |

## 4. Failure Injection

| Injection | Verification | Result |
| --- | --- | --- |
| process loss after experiment submit | resume after checkpointer restart; runner called once | PASS |
| process loss while awaiting human input | restarted graph retains project and pending node | PASS |
| required artifact deleted | preflight fails and package reconstruction rejects it | PASS |
| analysis modified | old analysis superseded; claim/manuscript become stale | PASS |
| frozen object changed | old hash-bound approval does not authorize revision | PASS |
| duplicate paper ingestion | exact identifier returns same paper; fuzzy match is only a merge candidate | PASS |
| duplicate citation import | one edge/source relation remains | PASS |
| agent requests forbidden write | denied before executor invocation | PASS |
| Editor invents metric/value | manuscript creation rejects unknown/stale value | PASS |
| blocking reviewer finding lacks evidence | strict contract validation rejects finding | PASS |

The explicit failure-injection selection completed `10 passed in 3.56s`.

## 5. Database Migration

A fresh `research_os_final` database migrated from no revision through `20260928_0001`, `0002`, and `0003`. Verification found 23 `research` tables, 29 `literature` tables, both `vector` and `pg_trgm`, and all five new manuscript provenance/invalidation columns.

## 6. LaTeX and Architecture Validation

The saved M5 LaTeX source compiled with bundled Tectonic 0.17.0 in untrusted mode: exit 0, one-page PDF, 21,872 bytes. The app compiler endpoint was initially unavailable on this Windows host, so the supported bundled compiler script was used with UTF-8 enabled.

Archify delivery produced `docs/architecture/research-os-v2.html`. Showcase validation passed 9/9 checks with 0 errors and 0 warnings. Visual containment/readability passed at 1440x900, 1600x1000, 1920x1080 and 2048x1320; light/dark screenshots were inspected.

## 7. Files Changed

| Path | Change |
| --- | --- |
| `.env.example` | complete centralized environment surface without secrets |
| `Dockerfile.test` | Git in integration image for actual package provenance |
| `research_store/models.py`, `repository.py` | claim/manuscript provenance, findings, approvals and package queries |
| `20260928_0003_paper_lifecycle.py` | M5 schema migration |
| `research_os/config.py` | central validated configuration |
| `research_os/paper_lifecycle.py` | claims, correction cascade, LaTeX, review, preflight, release and follow-ups |
| `research_os/package_export.py` | DB/artifact/Git export and integrity reconstruction |
| `research_os/graph/runtime.py`, `builder.py` | production stage handlers and hash-bound release route |
| `research_store/cli.py` | runnable database, literature, research and package commands |
| `tests/test_m5_paper_lifecycle.py` | ten PostgreSQL-backed M5 integration tests |
| `docs/architecture/research-os-v2*` | runtime, data, roles, literature, operations, JSON/HTML diagram and visual receipts |
| `reports/research_os_v2_legacy_retirement_report.md` | production import classification |
| `openspec/changes/research-os-v2-m5-paper-lifecycle/` | proposal, design, spec and task ledger |

## 8. Test Results

| Command | Exit | Result |
| --- | ---: | --- |
| M5 integration pytest | 0 | 11 passed |
| M0–M5 milestone pytest | 0 | 55 passed |
| explicit failure-injection selection | 0 | 10 passed |
| complete pytest suite | 0 | 103 passed, 0 failed, 0 skipped, 14 pre-existing return-value warnings |
| discovery/planner/hypothesis/benchmark selection | 0 | 8 passed |
| legacy autonomous loop script | 0 | passed |
| legacy V4 integration script | 0 | 6/6 passed |
| legacy V1→V4 regression script | 0 | 6/6 passed |
| fresh Alembic upgrade | 0 | 0001 -> 0002 -> 0003 passed |
| `python -m compileall -q auto_research/src` | 0 | passed |
| CLI `--help` | 0 | db/literature/research/export groups present |
| bundled Tectonic compile | 0 | PDF exists; one page; 21,872 bytes |
| Archify validate/deliver/visual-check | 0 | 9/9 showcase; all desktop viewports contained |

## 9. Regression Status

All current tests and legacy/discovery regressions pass. No scientific threshold, frozen benchmark result, held-out protocol, historic trajectory or M0 evidence semantics was modified.

## 10. Deviations From Specification

NONE.

The integration corpus is intentionally bounded and is reported as such; corpus expansion is an operational data-ingestion activity, not an architectural deviation. External submission remains manual by design.

## 11. Remaining Blockers

NONE for M5.

## 12. M5 Verdict

PASS
