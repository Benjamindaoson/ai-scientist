# Research OS v2 Final Report

## 1. Final Architecture

Research OS v2 now uses LangGraph as the sole production orchestrator, PostgreSQL as the sole canonical scientific store, the fixed six occupational roles, hybrid PostgreSQL literature intelligence, subscription-first Codex execution, an Action Broker for RPA, the retained Experiment Runtime, immutable artifact storage, Git provenance and hash-bound human approvals.

The validated interactive diagram is `docs/architecture/research-os-v2.html`; its source is `docs/architecture/research-os-v2.architecture.json`. Archify showcase validation passed 9/9 checks with zero errors/warnings, and desktop visual containment passed in light/dark evidence at 1440x900 through 2048x1320.

## 2. Legacy to V2 Mapping

| Legacy | V2 authority | Disposition |
| --- | --- | --- |
| `AIScientist` monolith | LangGraph graph + `ResearchOSRuntime` | compatibility facade retained |
| in-memory `ResearchState` | small `ResearchExecutionState` IDs + PostgreSQL | legacy only |
| SQLite repository | PostgreSQL `research` schema | read-only idempotent import fixture retained |
| multi-agent debate | six role AgentLab + typed findings/evidence tasks | legacy compatibility only |
| legacy literature search | Literature Intelligence service | legacy reader/search retained |
| legacy research package | DB/artifact/Git manifest exporter | legacy format retained for callers |

No legacy production file was deleted. The detailed import audit is in `reports/research_os_v2_legacy_retirement_report.md`.

## 3. Database Schema

Fresh migration `none -> 20260928_0001 -> 0002 -> 0003` succeeded on PostgreSQL 17.11. The result contains 23 `research` tables and 29 `literature` tables with `pg_trgm` 1.6 and `vector` 0.8.6.

Canonical research records cover programs/projects/ideas/gates, questions/hypotheses/frozen protocols, tasks/agents/actions, experiment specs/runs/analyses, claims/evidence/links, objections/findings/decisions/approvals, artifacts/manuscripts and legacy import receipts. Frozen protocols are immutable, hypothesis identity is enforced, and approvals bind target ID plus content hash.

## 4. LangGraph Node and Edge Inventory

The graph contains all 38 frozen specification nodes from project bootstrap through follow-up seeding. Conditional edges make `KILL`, `REFRAME`, repair, confirmation, independent audit and human-wait outcomes change actual reachability. PostgreSQL checkpointing preserves interrupts and run IDs across process restarts. Experiment submission checks existing runs before side effects.

The final-release node interrupts, validates an explicit approved row against the exact manuscript ID/hash and preflight status, then changes canonical manuscript status to `RELEASE_READY`. Invalid or stale approval raises instead of routing to release.

## 5. Six Agent Implementation

Strict Pydantic contracts cover TaskSpec, TaskResult, ReviewFinding, ActionRequest and ClaimRecord. `AgentLab` authorizes each work package against the role/capability table before an executor runs.

- Scout: discovery, prior search and novelty evidence.
- PI: question, alternatives, study design, next action and interpretation.
- Engineer: code, baselines, experiment implementation/test/run.
- Analyst: measurement, formal analysis, statistics, uncertainty and evidence.
- Editor: LaTeX paper, figures, tables, appendix, references, rebuttal and package; cannot alter scientific numbers.
- Reviewer: independent novelty/protocol/result/claim/paper audit; cannot mutate reviewed formal results.

## 6. Literature Coverage

The core schedule covers 14 venues and event years 2022–2026 (70 editions). The measured integration snapshot contains 33 papers, 35 versions, 3 appearances, 23 documents, 26 chunks, 25 embeddings, 4 citation edges and 1 lazy claim. Two official-source bootstrap records span ICLR and NeurIPS. External novelty expansion is distinct from core acceptance and can kill novelty.

## 7. Retrieval Benchmark

The frozen 20-query benchmark produced Top-50 recall 1.0000, Top-20 recall 1.0000, source-attribution precision 1.0000 and zero fabricated citations. Scout and Reviewer searches are independently auditable. Results are integration-fixture evidence, not a completeness claim for the bounded corpus.

## 8. Executor and RPA Status

- Real `CodexExecutor` smoke: succeeded with a schema-valid TaskResult in a bounded temporary workspace.
- Human-assisted execution: durable task package plus interrupt/resume and schema validation.
- Paid API: disabled by default and requires explicit enablement plus budget approval.
- Action Broker: `API/CLI > HTTP > Playwright > Desktop UI > Vision`, exact domain policy, high-risk approval and idempotent audit.
- Real Playwright Chromium smoke: title verified; trace ZIP, screenshot PNG and session JSON verified using an isolated research profile.
- Experiment Runtime: retained, database specs are adapted to its typed legacy model, and M0 executable hardening remains in force.

## 9. Experiment Idempotency Evidence

Two independent graph threads replaying the same experiment spec produced one canonical `experiment_run` and one runner call. A process was stopped at a running-experiment interrupt, the database row was completed, and a new graph/checkpointer instance resumed analysis without resubmission.

## 10. End-to-End Paper Lifecycle

The PostgreSQL-backed E2E proves:

`idea gates -> frozen protocol -> killer continue -> confirmation/audit -> frozen claim -> evidence/analysis/experiment/spec/protocol provenance -> LaTeX manuscript -> independent review routing -> preflight -> durable human interrupt -> process restart -> hash-bound approval -> release-ready -> archive`

Formal numbers are loaded from AnalysisRun. The LaTeX path supports generated tables, artifact-backed figures, appendix, references and compilation. Analysis correction cascades stale status to claims/manuscripts. Rebuttal responsibilities are explicit. Follow-up ideas re-enter novelty gating.

The supported bundled Tectonic 0.17.0 compiled the saved smoke document in untrusted mode: exit 0, one page, 21,872 bytes.

## 11. Tests

| Verification | Result |
| --- | --- |
| M5 PostgreSQL integration | 11 passed |
| M0–M5 milestone selection | 55 passed |
| complete pytest suite | 103 passed, 0 failed, 0 skipped, 14 pre-existing return-value warnings |
| explicit failure-injection selection | 10 passed |
| discovery/planner/hypothesis/benchmark selection | 8 passed |
| legacy autonomous loop | passed |
| legacy V4 integration | 6/6 passed |
| legacy V1→V4 regression | 6/6 passed |
| compileall | passed |
| fresh Alembic migration | passed |
| all five OpenSpec validations | passed |
| Git diff check | passed |

## 12. Failure Injection Results

All required injections passed: one run after submit/restart; pending human state after restart; deleted artifact rejected; corrected analysis stales dependents; old approval cannot authorize a changed frozen object; duplicate paper/citation ingestion remains idempotent; forbidden agent write is denied before execution; invented metric/value is rejected; blocking finding without evidence is rejected.

## 13. Remaining Limitations

- The checked literature database is a bounded integration corpus, not the full scheduled 14-venue corpus.
- Hashing embeddings make deterministic CI possible; full local BGE-M3 ingestion quality/cost over the complete corpus is not claimed by this run.
- Desktop UI and vision are broker channels for injected platform handlers; CLI/HTTP/Playwright are the concrete handlers validated here.
- Venue submission itself is intentionally manual. Research OS produces a release-ready package and cannot formally submit without a human-operated external step.
- The app-integrated LaTeX compiler endpoint failed to locate its platform directories on this host; the supported bundled Tectonic compiler path succeeded.

## 14. Deferred Features

Neo4j, Microsoft GraphRAG, Elasticsearch, external vector databases, paid-API default execution, a seventh agent, a second orchestrator and automatic external submission remain deliberately out of scope. Corpus-scale ingestion is an operational expansion, not an additional architecture milestone.

## 15. Dependency Versions

| Dependency | Verified version |
| --- | --- |
| PostgreSQL | 17.11 |
| pgvector Python | 0.5.0 |
| vector extension | 0.8.6 |
| pg_trgm extension | 1.6 |
| SQLAlchemy | 2.1.1 |
| psycopg | 3.3.6 |
| Alembic | 1.20.0 |
| Pydantic | 2.13.5 |
| LangGraph | 1.2.12 |
| LangGraph PostgreSQL checkpointer | 3.1.2 |
| httpx | 0.28.1 |
| tenacity | 9.1.4 |
| pytest | 9.1.1 |
| Tectonic | 0.17.0+20260731 |

## 16. Milestone Commit SHAs

- M0: `63479794230119ff2be82cadd0a94669dd251bde`
- M1: `82c3bd546388ea8b76267be6e19fa897da8a0ddd`
- M2: `837bd09b8ecb47f76028cd2a284195d130d63cf2`
- M3: `69684d2fa46c380fd46b651b25b8300b5464d8a7`
- M4: `620eaf09a6eceea71bf8dd4963740b72688c22ee`
- M5: `d5b7ea8b5128ace6652e742c1a1226e4b3898635`

## 17. Final Branch SHA

The final implementation baseline at acceptance is `d5b7ea8b5128ace6652e742c1a1226e4b3898635`; local and `origin/research-os-v2` were independently verified equal at that milestone. The documentation commit containing this report necessarily changes the branch hash; its exact local/remote SHA is verified after push and reported in the final delivery response rather than self-embedded in this immutable commit.

## Final Verdict

PASS — M0 remains frozen; M1–M5 implementation and acceptance are complete. Specification deviations: NONE.
