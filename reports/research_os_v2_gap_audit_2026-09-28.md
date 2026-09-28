# Research OS v2 Original-Vision Gap Audit

**Audit date:** 2026-09-28

**Branch:** `research-os-v2`

**Compared against:** the frozen M0–M5 migration command, the Autonomous Research Topic Discovery specification, and the Topic Discovery Hardening command.

## 1. Executive Verdict

The original vision is **not fully implemented**.

Research OS v2 has a substantial, tested application skeleton: PostgreSQL scientific records, LangGraph routing, six role contracts, hybrid retrieval, experiment provenance, manuscript/review/approval lifecycle, and failure-injection tests exist. Those capabilities are materially more than stubs.

The production outcome requested by the original vision is nevertheless missing. The system has no valid `TOPIC_READY` survivor, no production-scale literature corpus after the database-isolation incident, no accepted >=100-question retrieval benchmark, no currently safe live topic-generation/reviewer executor, and no real topic-to-killer-experiment-to-paper run. The earlier `TOPIC_READY` dossier was invalidated and must not be used as acceptance evidence.

Overall status: **ARCHITECTURE PARTIAL / TOPIC DISCOVERY BLOCKED / PRODUCTION NOT READY**.

## 2. Evidence Snapshot

### Code and regression

- M0–M5 milestone commits and tests exist.
- Current isolated complete pytest: **167 passed, 0 failed, 14 legacy warnings**.
- All tests now use a dedicated `research_os_test` PostgreSQL service; pytest refuses non-test database names.
- A destructive database test left the production counts unchanged, proving isolation.

### Live production PostgreSQL

| Metric | Current value |
| --- | ---: |
| Opportunities | 32 |
| Workshop links | 15 |
| Active/upcoming opportunities | 0 |
| Failed/stale opportunity sources | 3 |
| Literature papers | 35 |
| Chunks | 31 |
| Embedded chunks | 27 |
| Paper claims | 1 |
| Citation edges | 4 |
| Topic candidates | 1 |
| `NOVELTY_UNCERTAIN` candidates | 1 |
| Valid `TOPIC_READY` candidates | 0 |

The earlier approximately 21,051-paper corpus was deleted when the Compose test service incorrectly pointed pytest at the production `research_os` database. No recoverable database backup was found. The Compose configuration and pytest startup guard now prevent recurrence, but corpus ingestion must be rerun.

### Retrieval evidence

- The current hardening benchmark contains 8 questions and is labeled `PROVISIONAL`.
- Recall@5: 0.25; Recall@10: 0.375; Recall@50: 0.75; MRR: 0.1389.
- It is explicitly ineligible as `TOPIC_READY` evidence.
- Older 20-query results are integration-fixture evidence, not the required production benchmark.

## 3. Research OS v2 M0–M5 Assessment

| Milestone | Original intent | Current status | Evidence-qualified assessment |
| --- | --- | --- | --- |
| M0 | Scientific decision correctness | IMPLEMENTED | Fatal precedence, executable experiment gate, four-state evidence semantics, sandbox executable validation, and arXiv metadata regressions exist. |
| M1 | PostgreSQL canonical scientific store | IMPLEMENTED, OPERATIONALLY DAMAGED | Schema, migrations, repositories, immutability and hash-bound approvals exist. Production content was damaged by test contamination; isolation is now fixed. |
| M2 | LangGraph as production orchestrator | IMPLEMENTED IN CODE/TESTS | Graph, routing, checkpoint/restart and idempotency tests exist. A long-running real research program has not been demonstrated on a valid topic. |
| M3 | Production Literature Intelligence | PARTIAL | PostgreSQL/pgvector/FTS/citations/chunks/hybrid search exist. The required production corpus, full-text coverage, claims and >=100 benchmark do not. |
| M4 | Six roles, Codex and Action Broker | PARTIAL | Role/capability contracts, general Codex executor, human executor and Action Broker exist. Unsafe live topic executors were correctly quarantined; desktop/vision remain injected handlers rather than fully validated production paths. |
| M5 | Full paper lifecycle | IMPLEMENTED AS INTEGRATION WORKFLOW, NOT REAL SCIENCE | Provenance, analysis correction, manuscript, review, approval and package reconstruction tests exist. No real valid topic has completed the scientific lifecycle. |

The previous final report's blanket statement `M1–M5 complete; deviations NONE` is too strong when interpreted as production readiness. It is defensible only as a code-and-integration-fixture milestone statement.

## 4. Autonomous Topic Discovery Acceptance Matrix

| Original acceptance requirement | Status | Current evidence |
| --- | --- | --- |
| Production opportunity database works | IMPLEMENTED | Real sync persisted 32 rows. |
| Current/upcoming CFPs fetched | PARTIAL | Official pages were fetched, but 0 rows are currently active/upcoming; three sources failed. |
| Workshops fetched | PARTIAL | 15 workshop links were discovered, but deadlines/details remain `UNKNOWN`. |
| Official provenance stored | IMPLEMENTED | URL, retrieval method, hashes, verification and check timestamps are stored. |
| 2022–2026 production corpus actually ingested | NOT MET | Live corpus contains 35 papers after test contamination. |
| BGE-M3 production indexing executed/resumable | PARTIAL | Resumable indexer exists; live coverage is 27/31 and the large prior index was lost with the corpus. |
| >=100 real benchmark questions or justified maximum | NOT MET | Current benchmark has 8 provisional questions; older fixture has 20. |
| Scout novelty search | IMPLEMENTED | Auditable query matrices and retrieval runs exist. |
| Independent Reviewer novelty search | PARTIAL / QUARANTINED | Independent retrieval structures exist; the unsafe live model reviewer was removed. |
| Gap kill | IMPLEMENTED | Source-backed covering-prior decisions and regression tests exist. |
| Reframe | IMPLEMENTED IN STATE MACHINE | Routing/tests exist; no successful real reframe-to-ready trajectory exists. |
| Killed-idea memory | PARTIAL | Lineage storage exists; the currently safe recorded-candidate path cannot autonomously learn and regenerate. |
| Repeated candidate loop | IMPLEMENTED IN CONTROL LOGIC | Waves and strategy changes are tested; no current safe live generator drives the loop. |
| Failed wave automatically continues | IMPLEMENTED IN TESTS | Control-loop regression exists. |
| Critical question loop | PARTIAL | Fifteen-answer validation exists; no safe live assessor currently produces them. |
| Data feasibility | PARTIAL | Schema/HTTP/label checks exist; no candidate has a complete real loader receipt. |
| Method feasibility | PARTIAL | Contracts and gates exist; no valid candidate-specific real method preflight exists. |
| Engineering preflight | NOT OPERATIONAL | The unsafe executor path was removed; a secure replacement is not implemented. |
| Compute estimate | PARTIAL | Candidate-specific validation exists; no accepted live estimate exists. |
| Time estimate | PARTIAL | Validation and deadline arithmetic exist; no accepted live estimate exists. |
| Deadline fit | PARTIAL | Code exists; live opportunity set currently has no active deadline. |
| Killer experiment design | PARTIAL | Contract/gate exists; no valid topic has an approved killer experiment. |
| Final topic review | PARTIAL / QUARANTINED | Formal gate exists; safe independent live reviewer execution does not. |
| Real autonomous run produced `TOPIC_READY` | NOT MET | Current valid count is zero. |
| Final topic was not hardcoded | NOT EVALUABLE | There is no valid final topic. The old template-derived topic was invalidated. |
| Full evidence/provenance exists | NOT MET | No candidate has complete novelty, feasibility and review receipts. |
| Full regression passes | IMPLEMENTED | 167 passed against isolated test PostgreSQL. |

## 5. What Is Real Versus What Is Only a Fixture

### Real and currently usable

- PostgreSQL schemas and migrations.
- LangGraph state/routing/checkpoint code.
- Four-state scientific evidence semantics.
- Experiment idempotency and provenance enforcement.
- Six role authorization contracts.
- Opportunity HTTP sync and persisted provenance.
- Literature ingestion/search/indexing infrastructure.
- Recorded-candidate screening and fail-closed novelty handling.
- Human approval and release guards.

### Implemented but only proven with bounded fixtures

- End-to-end paper lifecycle.
- Independent review routing.
- Full research-package reconstruction.
- RPA/Playwright path.
- Corpus benchmark quality.
- Process-restart scenarios.

### Missing or currently disabled

- Production-scale live corpus after the database loss.
- Secure live Scout candidate generation.
- Secure live Independent Reviewer novelty assessment.
- Real engineering/data smoke execution for a candidate.
- >=100-question adjudicated retrieval benchmark.
- A valid `TOPIC_READY` topic.
- A real killer experiment and resulting scientific analysis.
- A real paper generated from real accepted experimental evidence.

## 6. Incidents and Corrective State

1. External topic executors used repository-adjacent workspaces and were associated with destructive workspace mutations. They are removed from the production Topic CLI.
2. Incomplete external search previously invoked expensive review before the completeness decision. It now short-circuits before hydration/deep audit.
3. Compose tests targeted the production database. The test service now has a separate `postgres-test` service and `research_os_test` database, and pytest refuses any database name not ending in `_test`.
4. The lost production corpus cannot be claimed as current evidence. Reports that depended on it are historical only.

## 7. Required Development Order

1. Rebuild the production literature corpus with resumable, observable venue/year batches.
2. Rebuild BGE-M3 embeddings only for missing chunks and measure live coverage.
3. Construct and adjudicate at least 100 non-self-retrieval benchmark questions.
4. Complete workshop detail/deadline extraction and refresh failed opportunity sources.
5. Implement a genuinely isolated, bounded execution environment for Scout/Reviewer work; do not treat prompts or working directories as a sandbox.
6. Run a one-candidate canary with repository and database integrity read-back.
7. Only after the canary passes, run a bounded top-five discovery wave.
8. Require real data-loader, engineering-smoke, compute/time and independent-review receipts before `TOPIC_READY`.

## 8. Verdict

**Research OS v2 architecture:** PARTIAL PASS

**Autonomous Topic Discovery:** BLOCKED

**Original complete vision:** NOT YET ACHIEVED

**Current system safe for unattended live model execution:** NO
