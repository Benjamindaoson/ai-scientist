# Research OS v2 Migration Specification

**Status:** FROZEN FOR IMPLEMENTATION  
**Repository:** `Benjamindaoson/ai-scientist`  
**Migration branch:** `research-os-v2`  
**Base:** current `main` at migration start (`31b560439d39b3ced6e500c3008adda9f3a3b6d3`)  
**Primary orchestrator:** LangGraph  
**Primary model execution policy:** subscription-first; paid LLM API disabled by default  
**Primary research execution:** Codex executor + deterministic local tools + Experiment Runtime  
**Browser/GUI automation:** Action Broker -> HTTP/API -> Playwright -> OS UI automation -> vision fallback  
**Primary database:** PostgreSQL + pgvector  
**Legacy SQLite:** compatibility/read-migration only after M1  
**Hard delete policy:** no legacy production file is physically deleted before M5 parity is proven.

---

## 0. Mission

Migrate the current evidence-oriented AI Scientist prototype into a persistent Research OS capable of running a complete paper lifecycle with six role-based agents:

1. **Research Scout / 选题研究员**
2. **Principal Investigator / 课题负责人**
3. **Research Engineer / 研究工程师**
4. **Data Scientist / 数据科学家**
5. **Scientific Editor / 科学编辑**
6. **Independent Reviewer / 独立评审专家**

The migration MUST preserve the strongest existing assets:

- persistent scientific objections;
- hard scientific gates;
- experiment provenance;
- claim/evidence tracing;
- bounded experiment recovery;
- integrity auditing;
- benchmark trajectories.

The migration MUST replace the current architecture weaknesses:

- monolithic `AIScientist` orchestration;
- split SQLite/in-memory research state;
- advisory-only court decisions;
- debate-as-primary-coordination;
- API-first model gateway assumptions;
- arXiv/abstract-only literature layer;
- evidence semantics that collapse INCONCLUSIVE into CONTRADICTS.

The target is **not** “six agents chatting.” The target is a durable research state machine in which every scientific transition is tied to a versioned artifact, evidence record, review finding, gate decision, or human approval.

---

# 1. Non-negotiable architecture decisions

## ADR-01 — LangGraph owns orchestration, not scientific truth

LangGraph stores execution state and checkpoints. It MUST NOT become a second research database.

LangGraph state contains IDs/references only:

```python
class ResearchExecutionState(TypedDict):
    project_id: str
    current_stage: str
    active_task_id: str | None
    active_role: str | None
    protocol_version_id: str | None
    hypothesis_id: str | None
    pending_review_finding_ids: list[str]
    pending_objection_ids: list[str]
    pending_approval_id: str | None
    active_experiment_run_id: str | None
    active_analysis_run_id: str | None
    manuscript_version_id: str | None
    last_decision_id: str | None
    artifact_refs: list[str]
    error_code: str | None
```

All scientific facts live in PostgreSQL.

## ADR-02 — PostgreSQL is the single scientific source of truth

Three logical schemas:

```text
orchestration.*   LangGraph checkpointer/store tables
research.*        projects, protocols, experiments, evidence, claims, review, approvals
literature.*      papers, authors, citations, chunks, embeddings, retrieval provenance
```

No production scientific result may exist only in an in-memory dataclass.

## ADR-03 — Six agents are roles, not graph nodes

A role can own multiple nodes. A node has exactly one accountable role, except deterministic policy/tool nodes.

## ADR-04 — Gate decisions are executable control flow

A KILL/BLOCKED decision MUST make the prohibited downstream edge unreachable.

No caller may bypass a gate by supplying an `ExperimentSpec`.

## ADR-05 — Debate is optional stress testing, not primary governance

The existing Proponent/Skeptic/Neutral/Devil's Advocate/Synthesizer debate is removed from the main graph. It may be retained as an optional adversarial review tool.

## ADR-06 — Subscription-first execution

Default:

```text
deterministic local code
    >
Codex subscription executor
    >
human-assisted ChatGPT task
    >
paid API (manual approval only)
```

No agent may autonomously enable paid LLM API usage.

## ADR-07 — Experiments remain external side effects

LangGraph does not “own” a running experiment. Experiment Runtime returns a stable `experiment_run_id`. Resume/replay MUST query existing run status before submitting again.

## ADR-08 — RPA is an execution capability, not an agent

Agents emit typed `ActionRequest` objects. The Action Broker selects the safest supported execution path.

## ADR-09 — Literature intelligence is a shared service

Research Scout, PI, and Independent Reviewer use the same literature database but MUST produce separate `retrieval_run` records for formal novelty review.

## ADR-10 — No silent overwrite

Protocols, analyses, claims, manuscripts, review findings, and approvals are versioned/append-only or retain revision history. Fixes create new versions.

---

# 2. Legacy file disposition

Legend:

- **KEEP** — retain behavior/API unless explicitly stated.
- **MODIFY** — file remains canonical but changes responsibility/API.
- **DEPRECATE** — compatibility only; main graph must stop depending on it.
- **NEW** — create during migration.
- **DELETE** — none before M5; post-M5 deletion requires explicit parity evidence.

## 2.1 Existing core files

| File | Action | Migration requirement |
|---|---|---|
| `auto_research/src/ai_scientist/orchestrator.py` | **DEPRECATE** | From M2, becomes a compatibility facade over `research_os`. No direct orchestration logic may be added. |
| `auto_research/src/ai_scientist/research_state.py` | **DEPRECATE** | Stop using as source of truth. Keep serializer/import compatibility until M5. |
| `auto_research/src/ai_scientist/core/gateway.py` | **DEPRECATE/MODIFY** | Keep legacy API gateways for compatibility only. New production role execution uses `AgentExecutor`. Paid gateways disabled by default. |
| `auto_research/src/ai_scientist/core/models/domain.py` | **KEEP/MODIFY** | Reuse scientific vocabulary where useful; remove persistence responsibility. Introduce Pydantic contracts in new package rather than expanding this dataclass file indefinitely. |
| `auto_research/src/ai_scientist/hypothesis.py` | **KEEP** | Reuse conceptual model; persistence IDs/versions live in research store. |

## 2.2 Governance and reasoning

| File | Action | Migration requirement |
|---|---|---|
| `engine/objection_ledger.py` | **KEEP/MODIFY** | Preserve semantics; replace direct SQLite repository dependency with `ResearchRepository`. |
| `engine/final_research_court.py` | **MODIFY then DEPRECATE facade** | M0 fix precedence bug. M2 move canonical deterministic policy logic to `research_os/policy/gates.py`. |
| `engine/multi_agent_debate.py` | **DEPRECATE** | Remove from main execution path. Retain only as optional `adversarial_panel` tool/benchmark. |
| `engine/theory_engine.py` | **KEEP/MODIFY** | Becomes PI capability/service; MUST NOT control workflow. |

## 2.3 Experiment subsystem

| File | Action | Migration requirement |
|---|---|---|
| `experiment/models.py` | **KEEP/MODIFY** | Add protocol version, idempotency key, code revision, data manifest/hash, execution profile, declared outputs. |
| `experiment/runner.py` | **KEEP/MODIFY** | Add persistent run registration and idempotent `submit/status/collect/cancel` interface. Synchronous `run()` retained as adapter. |
| `experiment/recovery.py` | **KEEP** | Preserve bounded retries; retry MUST never change scientific objective/metrics silently. |
| `experiment/sandbox.py` | **MODIFY** | Harden executable resolution. Untrusted generated code defaults to Docker/stronger isolation; exact resolved interpreter allowlist. |
| `experiment/evaluator.py` | **MODIFY** | Replace binary-ish verdict handling with typed `SUPPORTED/CONTRADICTED/INCONCLUSIVE/INVALID`. |
| `experiment/engineer.py` | **MODIFY** | Stop depending directly on `BaseGateway`; use `AgentExecutor`/Codex task interface. Scientific protocol fields are immutable to repair tasks. |

## 2.4 Evidence, review, publishing

| File | Action | Migration requirement |
|---|---|---|
| `evidence_graph.py` | **MODIFY** | Becomes compatibility serializer over persistent `research.claims/evidence/claim_evidence_links`. |
| `integrity.py` | **KEEP/MODIFY** | Read from persistent store and artifacts; add version/hash checks. |
| `scientific_review.py` | **KEEP/MODIFY** | Retain issue taxonomy; output typed `ReviewFinding`. |
| `review_loop.py` | **MODIFY** | Convert from autonomous loop into deterministic issue router: finding category -> accountable role/node. |
| `research_package.py` | **MODIFY** | Export by project/version IDs from PostgreSQL + Artifact Store. No dependency on in-memory ResearchState. |

## 2.5 Database and literature

| File | Action | Migration requirement |
|---|---|---|
| `db/schema.sql` | **DEPRECATE** | Frozen legacy SQLite schema. No new production schema features. |
| `db/repository.py` | **DEPRECATE** | Compatibility/migration reader only after M1. |
| `literature/search.py` | **DEPRECATE** | Replaced by `literature_intelligence/search/*`. |
| `literature/reader.py` | **DEPRECATE** | Replaced by artifact fetch + parser + section/chunk pipeline. |
| `literature/validator.py` | **KEEP/MOVE CONCEPTS** | Evidence-quality concepts may be reused; paper retrieval is moved out. |

## 2.6 Discovery benchmark code

| File | Action | Migration requirement |
|---|---|---|
| `benchmarks/discovery/discovery_loop.py` | **KEEP** | Benchmark harness only, never production Research Scout implementation. |
| `benchmarks/discovery/hypothesis_generator.py` | **KEEP/MODIFY FOR TESTS ONLY** | Do not use mean novelty/feasibility/impact score as production start gate. |
| `benchmarks/discovery/*` | **KEEP** | Use for component ablations and Research OS regression tests. |
| `benchmarks/trajectories/*` | **KEEP** | Golden/replay data; new generated trajectories should not be committed by default unless explicitly designated fixtures. |

## 2.7 Entry points and tests

| File | Action | Migration requirement |
|---|---|---|
| `run.py` | **MODIFY** | Becomes compatibility smoke test or thin CLI; new CLI lives under `research_os/cli.py`. |
| existing `test_*.py` | **KEEP** | Must continue passing unless explicitly superseded. |
| current benchmark tests | **KEEP** | Used as regression suite. |

## 2.8 DELETE list

**No physical source-file deletion is allowed in M0–M4.**

At M5, the following may be deleted or moved under `legacy/` only if:
1. no production imports remain;
2. compatibility tests have replacement coverage;
3. a migration note is committed.

Candidates:
- legacy orchestration body in `orchestrator.py`;
- legacy autonomous orchestration body in `autonomous_loop.py`;
- main-path use of `multi_agent_debate.py`;
- SQLite FTS schema/logic.

---

# 3. New package structure

```text
auto_research/src/ai_scientist/
├── research_os/
│   ├── __init__.py
│   ├── cli.py
│   ├── graph/
│   │   ├── state.py
│   │   ├── builder.py
│   │   ├── nodes.py
│   │   ├── routes.py
│   │   └── interrupts.py
│   ├── agents/
│   │   ├── base.py
│   │   ├── scout.py
│   │   ├── pi.py
│   │   ├── engineer.py
│   │   ├── analyst.py
│   │   ├── editor.py
│   │   └── reviewer.py
│   ├── contracts/
│   │   ├── task.py
│   │   ├── result.py
│   │   ├── review.py
│   │   ├── action.py
│   │   ├── experiment.py
│   │   └── claim.py
│   ├── policy/
│   │   ├── gates.py
│   │   ├── permissions.py
│   │   ├── budget.py
│   │   └── transitions.py
│   └── execution/
│       ├── base.py
│       ├── codex.py
│       ├── human.py
│       ├── paid_api.py
│       └── action_broker.py
│
├── research_store/
│   ├── __init__.py
│   ├── db.py
│   ├── models/
│   ├── repositories/
│   ├── services/
│   └── migrations/
│
├── literature_intelligence/
│   ├── sources/
│   ├── ingest/
│   ├── fulltext/
│   ├── embeddings/
│   ├── search/
│   ├── claims/
│   └── novelty/
│
├── evidence/
│   ├── service.py
│   ├── provenance.py
│   └── integrity.py
│
└── publishing/
    ├── manuscript.py
    ├── package.py
    └── checks.py
```

Do not move all old files immediately. New code may call old experiment primitives through adapters until M5.

---

# 4. Python dependencies

Update `pyproject.toml` with minimal V2 dependencies.

Required:
- `langgraph`
- `pydantic>=2`
- `sqlalchemy>=2`
- PostgreSQL driver (`psycopg[binary]` for V1)
- `pgvector`
- `alembic`
- `httpx`
- `tenacity`

Literature/embedding optional group:
- `sentence-transformers`
- PDF parser dependency selected during M3 after parser benchmark

RPA optional group:
- `playwright`
- Windows UI automation package only on Windows

Do **not** add Redis, Celery, Ray, Neo4j, Elasticsearch, Milvus, Pinecone, Weaviate, Kubernetes, or a second multi-agent framework in V2 unless a later ADR proves necessity.

---

# 5. PostgreSQL schema

## 5.1 Schema: `research`

### `research.programs`
Cross-project long-term research program.

- `program_id UUID PK`
- `name TEXT NOT NULL`
- `description TEXT`
- `status TEXT CHECK (...)`
- `policy_version TEXT NOT NULL`
- `created_at TIMESTAMPTZ`
- `updated_at TIMESTAMPTZ`

### `research.projects`
One paper/research project.

- `project_id UUID PK`
- `program_id UUID FK nullable`
- `name TEXT`
- `domain TEXT`
- `seed_question TEXT`
- `status TEXT`
- `current_stage TEXT`
- `created_at`
- `updated_at`

### `research.ideas`
Candidate research questions before project commitment.

- `idea_id UUID PK`
- `program_id UUID FK nullable`
- `title TEXT`
- `core_question TEXT`
- `current_belief TEXT`
- `proposed_challenge TEXT`
- `falsifiable_claim TEXT`
- `status TEXT`
- `created_by_role TEXT`
- `created_at`
- `updated_at`

### `research.idea_gate_evaluations`
Store each 10/10 gate independently; no aggregate pass by mean.

- `evaluation_id UUID PK`
- `idea_id UUID FK`
- `gate_name TEXT`
- `score INTEGER CHECK(score BETWEEN 0 AND 10)`
- `rationale TEXT`
- `evidence_refs JSONB`
- `blocking_gap TEXT`
- `reviewer_role TEXT`
- `created_at`

Unique: `(idea_id, gate_name, reviewer_role, created_at)` is intentionally versioned.

### `research.research_questions`
- `research_question_id UUID PK`
- `project_id UUID FK`
- `idea_id UUID FK nullable`
- `question_text TEXT`
- `scope JSONB`
- `status TEXT`
- `version INTEGER`
- timestamps

### `research.hypotheses`
- `hypothesis_id UUID PK`
- `project_id UUID FK`
- `parent_hypothesis_id UUID nullable`
- `claim TEXT`
- `rationale TEXT`
- `predicted_effect TEXT`
- `falsification_conditions JSONB`
- `status TEXT`
- `version INTEGER`
- timestamps

### `research.protocol_versions`
Frozen scientific protocol versions.

- `protocol_version_id UUID PK`
- `project_id UUID FK`
- `research_question_id UUID FK`
- `hypothesis_id UUID FK nullable`
- `version INTEGER NOT NULL`
- `status TEXT` = DRAFT / UNDER_REVIEW / FROZEN / SUPERSEDED
- `design JSONB`
- `measurement_plan JSONB`
- `data_split_policy JSONB`
- `analysis_plan JSONB`
- `stopping_rules JSONB`
- `exclusion_rules JSONB`
- `resource_budget JSONB`
- `content_hash TEXT`
- `frozen_at TIMESTAMPTZ nullable`
- timestamps

Unique: `(project_id, version)`.

### `research.tasks`
Typed unit of work given to a role.

- `task_id UUID PK`
- `project_id UUID FK`
- `task_type TEXT`
- `owner_role TEXT`
- `status TEXT`
- `input_refs JSONB`
- `constraints JSONB`
- `acceptance_criteria JSONB`
- `budget JSONB`
- `created_at`
- `started_at`
- `completed_at`

### `research.agent_runs`
One execution attempt of a role task.

- `agent_run_id UUID PK`
- `task_id UUID FK`
- `role TEXT`
- `executor_type TEXT`
- `executor_session_id TEXT nullable`
- `prompt_contract_version TEXT`
- `status TEXT`
- `input_hash TEXT`
- `output_ref JSONB`
- `usage JSONB`
- timestamps

### `research.action_requests`
Auditable non-reasoning action request.

- `action_request_id UUID PK`
- `task_id UUID FK`
- `action_type TEXT`
- `target JSONB`
- `constraints JSONB`
- `risk_level TEXT`
- `requires_human_approval BOOLEAN`
- `status TEXT`
- `executor TEXT`
- `result_ref JSONB`
- timestamps

### `research.experiment_specs`
Persistent version of ExperimentSpec.

Required fields:
- `experiment_spec_id UUID PK`
- `project_id UUID FK`
- `protocol_version_id UUID FK`
- `hypothesis_id UUID FK`
- `idempotency_key TEXT UNIQUE`
- `objective TEXT`
- `command JSONB`
- `workspace TEXT`
- `metrics_contract JSONB`
- `controls JSONB`
- `resource_limits JSONB`
- `execution_profile TEXT`
- `code_revision TEXT`
- `data_manifest_hash TEXT nullable`
- `spec_hash TEXT UNIQUE`
- timestamps

### `research.experiment_runs`
- `experiment_run_id UUID PK`
- `experiment_spec_id UUID FK`
- `attempt INTEGER`
- `external_run_id TEXT nullable`
- `status TEXT`
- `return_code INTEGER nullable`
- `metrics JSONB`
- `error_type TEXT nullable`
- `stdout_artifact_id UUID nullable`
- `stderr_artifact_id UUID nullable`
- `started_at`
- `completed_at`
- `runtime_metadata JSONB`

Unique: `(experiment_spec_id, attempt)`.

### `research.analysis_runs`
Formal analyst output; separate from raw experiment output.

- `analysis_run_id UUID PK`
- `project_id UUID FK`
- `protocol_version_id UUID FK`
- `input_experiment_run_ids UUID[]`
- `analysis_code_revision TEXT`
- `analysis_plan_hash TEXT`
- `status TEXT`
- `results JSONB`
- `uncertainty JSONB`
- `limitations JSONB`
- `artifact_refs JSONB`
- timestamps

### `research.claims`
- `claim_id UUID PK`
- `project_id UUID FK`
- `claim_type TEXT`
- `claim_text TEXT`
- `scope JSONB`
- `status TEXT`
- `version INTEGER`
- `created_by_role TEXT`
- timestamps

### `research.evidence_items`
- `evidence_id UUID PK`
- `project_id UUID FK`
- `evidence_type TEXT` = EXPERIMENT / ANALYSIS / LITERATURE / THEORY / MANUAL
- `source_ref JSONB`
- `content_summary TEXT`
- `validity_status TEXT`
- `content_hash TEXT`
- timestamps

### `research.claim_evidence_links`
This replaces ambiguous in-memory graph relations.

- `claim_id UUID FK`
- `evidence_id UUID FK`
- `relation TEXT` = SUPPORTS / CONTRADICTS / QUALIFIES / INCONCLUSIVE / INVALID
- `rationale TEXT`
- `created_by_role TEXT`
- `review_status TEXT`
- `created_at`

PK: `(claim_id, evidence_id, relation)`.

### `research.objections`
Persistent objection ledger.

- `objection_id UUID PK`
- `project_id UUID FK`
- `target_type TEXT`
- `target_id UUID`
- `category TEXT`
- `severity TEXT` = FATAL / MAJOR / MINOR
- `title TEXT`
- `argument TEXT`
- `supporting_evidence_ids UUID[]`
- `status TEXT` = OPEN / UNDER_REVIEW / RESOLVED / INVALIDATED / ACCEPTED_RISK / REQUIRES_HUMAN
- `resolution_type TEXT nullable`
- `resolution_reason TEXT nullable`
- `raised_by_role TEXT`
- timestamps

### `research.review_findings`
Reviewer output, not synonymous with objection.

- `review_finding_id UUID PK`
- `project_id UUID FK`
- `review_stage TEXT`
- `category TEXT`
- `severity TEXT`
- `target_type TEXT`
- `target_id UUID`
- `finding TEXT`
- `evidence_refs JSONB`
- `required_resolution TEXT`
- `status TEXT`
- timestamps

### `research.decisions`
- `decision_id UUID PK`
- `project_id UUID FK`
- `decision_type TEXT`
- `decision TEXT` = CONTINUE / REFRAME / KILL / BLOCKED / WAIT_FOR_HUMAN / READY
- `gate_results JSONB`
- `reason_refs JSONB`
- `policy_version TEXT`
- timestamps

### `research.approvals`
- `approval_id UUID PK`
- `project_id UUID FK`
- `approval_type TEXT`
- `target_type TEXT`
- `target_id UUID`
- `target_hash TEXT`
- `status TEXT` = PENDING / APPROVED / REJECTED / EXPIRED
- `approved_by TEXT nullable`
- `budget_authorized JSONB nullable`
- timestamps

Approval becomes invalid when `target_hash` changes.

### `research.artifacts`
- `artifact_id UUID PK`
- `project_id UUID FK nullable`
- `artifact_type TEXT`
- `uri TEXT`
- `sha256 TEXT`
- `mime_type TEXT`
- `size_bytes BIGINT`
- `created_by_task_id UUID nullable`
- timestamps

### `research.manuscript_versions`
- `manuscript_version_id UUID PK`
- `project_id UUID FK`
- `version INTEGER`
- `source_artifact_id UUID FK`
- `pdf_artifact_id UUID nullable`
- `claim_ids UUID[]`
- `status TEXT`
- `content_hash TEXT`
- timestamps

---

## 5.2 Schema: `literature`

V1 required tables:

- `venues`
- `venue_editions`
- `papers`
- `paper_appearances`
- `paper_identifiers`
- `paper_versions`
- `authors`
- `author_identifiers`
- `paper_authors`
- `citations`
- `citation_sources`
- `topics`
- `paper_topics`
- `artifacts`
- `documents`
- `sections`
- `chunks`
- `embedding_models`
- `embeddings`
- `paper_notes`
- `paper_claims`
- `paper_claim_evidence`
- `idea_paper_relations`
- `retrieval_runs`
- `retrieval_results`
- `source_records`
- `ingestion_runs`
- `sync_state`
- `merge_events`

### Mandatory semantic rules

1. Core corpus membership is determined by `paper_appearances.is_core_accepted`, not arXiv claims.
2. Paper identity is separate from paper version and venue appearance.
3. Citation edges are bibliographic facts; semantic relations such as “contradicts” are claims with provenance.
4. A verified paper claim MUST reference an exact paper version and source chunk.
5. Formal novelty audits MUST store their own `retrieval_run`.
6. Research Scout and Independent Reviewer MUST NOT share the same formal retrieval run ID.
7. Full-text embeddings are recomputed only when content hash or embedding model changes.

### Search stack

- PostgreSQL full-text search;
- `pg_trgm` fuzzy matching;
- pgvector HNSW cosine index;
- citation expansion through relational edges;
- RRF/hybrid ranking in service code.

No Neo4j in V2.

---

# 6. Core contracts

All new role/node boundaries use Pydantic v2 models.

## `TaskSpec`

```text
task_id
project_id
task_type
owner_role
goal
input_refs
constraints
permissions
budget
acceptance_criteria
forbidden_actions
```

## `TaskResult`

```text
task_id
status
summary
artifact_refs
created_entity_refs
unresolved_items
execution_record
```

## `ReviewFinding`

```text
finding_id
review_stage
category
severity
target_ref
finding
evidence_refs
impact
required_resolution
status
```

A blocking finding without evidence/target/resolution requirement is invalid.

## `ActionRequest`

```text
action_request_id
task_id
action_type
target
inputs
constraints
risk_level
requires_human_approval
expected_outputs
idempotency_key
```

## `ClaimRecord`

```text
claim_id
claim_type
claim_text
scope
evidence_refs
counterevidence_refs
assumptions
status
version
```

---

# 7. Six Agent Contracts

Canonical role IDs:
`scout`, `pi`, `engineer`, `analyst`, `editor`, `reviewer`.

## 7.1 Research Scout / 选题研究员

**Mission:** maintain the cross-project opportunity pipeline and produce candidate research questions grounded in literature.

**Reads**
- research program;
- rejected/killed idea history;
- literature intelligence;
- active project summaries;
- resource constraints.

**Writes**
- `research.ideas`;
- Scout retrieval runs;
- `idea_paper_relations`;
- candidate novelty evidence;
- post-project future-question archive.

**Tools**
- Literature Intelligence;
- web/browser actions through Action Broker;
- deterministic text/data tools.

**Forbidden**
- approve own idea;
- freeze protocol;
- run confirmatory experiments;
- modify experiment data;
- mark novelty as verified without Reviewer audit.

**Required output**
- candidate question;
- current belief;
- proposed challenge;
- falsifiable claim;
- closest prior work with provenance;
- cheapest falsifier;
- resource estimate.

## 7.2 Principal Investigator / 课题负责人

**Mission:** own scientific coherence of one project and select the next information-gaining research action.

**Reads**
- approved idea;
- literature evidence;
- protocols;
- analysis results;
- review findings;
- objection ledger.

**Writes**
- research question versions;
- hypotheses;
- study design;
- scientific decisions/recommendations;
- task requests for Engineer/Analyst/Editor.

**Tools**
- literature service;
- Research Store;
- deterministic scientific utilities;
- Codex executor for reasoning tasks if needed.

**Forbidden**
- approve own novelty gate;
- alter raw experiment output;
- silently alter frozen protocol;
- close Reviewer findings without evidence;
- submit/publish without human approval.

**Required output**
- formal question;
- competing explanations;
- evidence map;
- requested next task and why it changes the scientific judgment.

## 7.3 Research Engineer / 研究工程师

**Mission:** correctly implement and execute authorized scientific protocols.

**Reads**
- frozen/draft protocol relevant to task;
- ExperimentSpec;
- codebase/worktree;
- engineering review findings.

**Writes**
- code patches;
- tests;
- ExperimentSpec implementation fields;
- experiment run records/artifacts.

**Tools**
- Codex;
- Git/worktree;
- shell/Python;
- Experiment Runtime;
- Docker sandbox.

**Forbidden**
- change primary metric, data split, success criterion, scientific objective, or confirmatory protocol without a new protocol version;
- delete unfavorable valid runs;
- reinterpret results as scientific claims.

**Required output**
- patch/commit;
- tests;
- run ID;
- artifact hashes;
- implementation deviations, if any.

## 7.4 Data Scientist / 数据科学家

**Mission:** define measurement/analysis and convert raw outputs into defensible evidence.

**Reads**
- protocol;
- raw experiment outputs;
- data manifests;
- prior analysis versions.

**Writes**
- measurement plan contribution;
- analysis code;
- analysis runs;
- formal results;
- uncertainty/sensitivity;
- evidence items;
- proposed claim scope constraints.

**Tools**
- Python/statistics;
- Codex;
- Research Store;
- Artifact Store.

**Forbidden**
- alter raw experiment outputs;
- silently change frozen analysis plan;
- choose a favorable subset without versioned disclosure;
- approve own independent audit.

**Required output**
- reproducible analysis run;
- exact sample/support definition;
- results and uncertainty;
- negative/inconclusive results;
- limitations.

## 7.5 Scientific Editor / 科学编辑

**Mission:** transform verified research objects into an accurate paper and submission package.

**Reads**
- verified/frozen claims;
- analysis results;
- literature claims;
- review findings;
- venue policy configuration.

**Writes**
- manuscript versions;
- figures/tables generated from formal results;
- appendices;
- disclosure/reproducibility material;
- rebuttal drafts.

**Tools**
- Codex;
- LaTeX/build tools;
- publication checks;
- RPA only for supported external publishing workflows.

**Forbidden**
- invent/modify result numbers;
- broaden claim scope without PI+Analyst revision;
- create unsupported citations;
- submit without human approval.

**Required output**
- manuscript source;
- compiled artifact;
- claim-to-text mapping;
- citation support report;
- unresolved writing/science issues.

## 7.6 Independent Reviewer / 独立评审专家

**Mission:** independently detect substantive failures without owning project success.

**Reads**
- frozen artifacts directly;
- complete negative/failed run history when relevant;
- literature intelligence;
- source code and raw outputs.

**Writes**
- independent retrieval runs;
- review findings;
- objections;
- audit artifacts;
- review recommendation to Gate Engine.

**Tools**
- Literature Intelligence;
- independent analysis workspace;
- Codex;
- deterministic checks.

**Forbidden**
- overwrite official analysis/results;
- silently repair the object being reviewed;
- approve based only on producer summary;
- issue blocking findings with no evidence, target, or resolution condition.

**Required output**
- what was independently checked;
- what was not checked;
- concrete findings;
- evidence refs;
- required resolution;
- residual uncertainty.

---

# 8. Permission matrix

| Object | Scout | PI | Engineer | Analyst | Editor | Reviewer |
|---|---:|---:|---:|---:|---:|---:|
| Idea candidate | W | R | R | R | R | R/audit |
| Research question | R | W | R | R | R | R/audit |
| Protocol draft | R | W | comment | W measurement fields | R | audit |
| Frozen protocol | R | request new version | R | request new version | R | audit |
| Source code | R | R | W | W analysis-only | R | independent workspace only |
| Raw experiment output | R | R | produce append-only | R | R | R |
| Formal analysis | R | R | R | W/version | R | audit only |
| Claim | R | W proposal | R | W scope/evidence proposal | R | audit |
| Manuscript | R | scientific approve | R | numerical check | W | audit |
| Review finding | R | resolve via evidence | resolve assigned | resolve assigned | resolve assigned | W |
| Gate decision | no | no | no | no | no | no — **Policy Engine only** |
| Final external release | no | no | no | no | prepare only | no — **Human only** |

---

# 9. LangGraph state machine

## 9.1 Node catalogue

### Program/Discovery

1. `bootstrap_project` — deterministic
2. `discover_candidates` — Scout
3. `scout_prior_search` — Scout
4. `reviewer_novelty_search` — Reviewer
5. `evaluate_10_10_gate` — deterministic Policy Engine
6. `human_start_approval` — interrupt when configured/required

### Scientific design

7. `formalize_question` — PI
8. `design_study` — PI
9. `design_measurement` — Analyst
10. `review_protocol` — Reviewer
11. `protocol_gate` — deterministic
12. `freeze_protocol` — deterministic version/hash operation

### Killer experiment

13. `engineering_preflight` — Engineer
14. `implement_killer_experiment` — Engineer
15. `submit_killer_experiment` — deterministic Experiment Runtime adapter
16. `wait_for_experiment` — durable wait/poll/event boundary
17. `analyze_killer_experiment` — Analyst
18. `interpret_killer_result` — PI
19. `killer_gate` — deterministic

### Full research loop

20. `plan_next_research_action` — PI
21. `implement_experiment` — Engineer
22. `submit_experiment` — deterministic
23. `wait_for_experiment_result` — deterministic
24. `analyze_experiment` — Analyst
25. `update_scientific_model` — PI
26. `research_progress_gate` — deterministic
27. `freeze_confirmatory_protocol` — deterministic after PI+Analyst authored protocol and Reviewer clearance
28. `run_confirmation` — Engineer/runtime
29. `formal_analysis` — Analyst

### Audit/paper

30. `independent_result_audit` — Reviewer
31. `claim_freeze` — deterministic after PI/Analyst proposal + Reviewer conditions satisfied
32. `draft_manuscript` — Editor
33. `independent_paper_review` — Reviewer
34. `revision_router` — deterministic finding-category router
35. `submission_preflight` — Editor + deterministic checks
36. `human_release_approval` — mandatory interrupt
37. `archive_project` — deterministic
38. `seed_followup_candidates` — Scout
39. `END`

## 9.2 Main edges

```text
bootstrap_project
 -> discover_candidates
 -> scout_prior_search
 -> reviewer_novelty_search
 -> evaluate_10_10_gate
```

Gate routes:
- `START` -> `human_start_approval` or `formalize_question`
- `REFRAME` -> `discover_candidates`
- `KILL` -> `archive_project`
- `WAIT_FOR_HUMAN` -> interrupt
- insufficient evidence -> `scout_prior_search` or reviewer search, never auto-upscore

Design:
```text
formalize_question
 -> design_study
 -> design_measurement
 -> review_protocol
 -> protocol_gate
```

Protocol gate:
- PASS -> freeze_protocol -> engineering_preflight
- REVISE_SCIENCE -> design_study
- REVISE_MEASUREMENT -> design_measurement
- REVIEW_REQUIRED -> review_protocol
- KILL -> archive_project

Killer:
```text
engineering_preflight
 -> implement_killer_experiment
 -> submit_killer_experiment
 -> wait_for_experiment
 -> analyze_killer_experiment
 -> interpret_killer_result
 -> killer_gate
```

Killer gate:
- CONTINUE -> plan_next_research_action
- REFRAME -> formalize_question or discover_candidates, depending decision target
- KILL -> archive_project
- INCONCLUSIVE -> explicit PI choice: additional diagnostic task or BLOCKED; never convert to contradiction

Research loop:
```text
plan_next_research_action
 -> implement_experiment
 -> submit_experiment
 -> wait_for_experiment_result
 -> analyze_experiment
 -> update_scientific_model
 -> research_progress_gate
```

Progress routes:
- MORE_EVIDENCE -> plan_next_research_action
- READY_TO_CONFIRM -> freeze_confirmatory_protocol
- REFRAME -> formalize_question
- KILL -> archive_project
- BLOCKED -> interrupt/status

Confirmation:
```text
freeze_confirmatory_protocol
 -> run_confirmation
 -> formal_analysis
 -> independent_result_audit
```

Audit routes:
- PASS -> claim_freeze
- ENGINEERING_ISSUE -> implement_experiment
- ANALYSIS_ISSUE -> formal_analysis with new version
- SCIENTIFIC_SCOPE_ISSUE -> update_scientific_model
- NOVELTY_ISSUE -> reviewer_novelty_search
- FATAL -> archive_project or human interrupt according to policy

Paper:
```text
claim_freeze
 -> draft_manuscript
 -> independent_paper_review
 -> revision_router
```

Revision router:
- WRITING -> draft_manuscript
- CITATION/NOVELTY -> reviewer_novelty_search / Scout support
- STATISTICS -> formal_analysis
- IMPLEMENTATION -> implement_experiment
- MISSING_EXPERIMENT -> plan_next_research_action
- CLAIM_EVIDENCE -> update_scientific_model/formal_analysis
- PASS -> submission_preflight

Release:
```text
submission_preflight
 -> human_release_approval
 -> archive_project
 -> seed_followup_candidates
 -> END
```

---

# 10. Deterministic policy rules

## 10.1 Scientific decision precedence

Exact precedence:

1. OPEN FATAL objection -> `KILL`
2. FATAL + REQUIRES_HUMAN -> still `KILL`; human review flag may be recorded but MUST NOT downgrade KILL
3. REQUIRES_HUMAN without FATAL -> `WAIT_FOR_HUMAN`
4. invalid/missing required evidence -> `BLOCKED` or `REFRAME`, never PASS
5. novelty gate failure -> `REFRAME` unless an explicit fatal overlap policy says KILL
6. feasibility failure -> `BLOCKED` or `REFRAME`
7. all mandatory gates pass -> `CONTINUE`

## 10.2 10/10 idea gate

Mandatory gates:
- Fundamental
- Surprising
- Broad
- Actionable
- Cheap to falsify
- Hard to explain away
- Defensible novelty
- Positive-result value >> engineering cost

```python
START = all(g.score == 10 for g in required_gates)
```

No average. No weighted score. Missing evidence caps a gate below 10.

## 10.3 Evidence verdicts

Allowed:
- `SUPPORTED`
- `CONTRADICTED`
- `INCONCLUSIVE`
- `INVALID`

Execution failure => `INVALID`, not scientific contradiction.

## 10.4 Idempotency

Every side-effecting action has an `idempotency_key`.

Experiment submission:
```text
idempotency_key =
sha256(protocol_version_id + spec_hash + code_revision + data_manifest_hash + declared_seed)
```

On graph resume/replay, query existing run by idempotency key before submit.

---

# 11. Executor architecture

## `AgentExecutor` interface

```python
class AgentExecutor(Protocol):
    def run(self, task: TaskSpec) -> TaskResult: ...
```

Implementations:

### `CodexExecutor` — primary
- invokes supported Codex CLI/SDK workflow;
- isolated workspace/worktree;
- explicit input/output files;
- no paid API key required by default;
- captures execution record.

### `HumanChatGPTExecutor` — fallback
- emits a task package for manual handoff;
- system waits on interrupt;
- human imports result artifact;
- result must validate against TaskResult schema.

### `PaidAPIExecutor` — disabled by default
- requires explicit approval object;
- hard per-task budget;
- no autonomous fallback into paid API.

### `MockExecutor`
- deterministic tests.

---

# 12. Action Broker / RPA

Order of execution:

```text
native API/CLI
 > HTTP/static parser
 > Playwright DOM automation
 > OS accessibility/UI automation
 > vision + pointer fallback
```

The broker persists:
- request;
- executor selected;
- screenshots/traces when applicable;
- result;
- retries;
- human takeover.

Mandatory human approval for:
- final paper submission;
- public release;
- destructive external actions;
- credentials/2FA handoff;
- purchases or paid API activation.

Agents MUST NOT directly own mouse/keyboard primitives.

---

# 13. Literature Intelligence v1

## Core corpus window

Conference/event years: 2022–2026 at V2 launch.

Initial conference policy:
- ICLR
- ICML
- NeurIPS
- AISTATS
- AAAI
- CVPR
- ICCV
- ECCV
- ACL
- EMNLP
- CoRL
- RSS
- ICRA
- IROS

Core corpus means official accepted main research tracks according to venue policy.

Novelty universe is **not** limited to core corpus. External expansion may import arXiv, workshop, journal, Findings, technical report, or adjacent-field work.

## Retrieval pipeline

```text
idea/question
 -> 3–8 query formulations
 -> keyword retrieval
 -> dense paper retrieval
 -> metadata filters
 -> RRF
 -> citation/reference expansion
 -> candidate pool
 -> full-text chunk retrieval
 -> deep read top papers
 -> lazy claim extraction
 -> idea_paper_relations
 -> novelty audit
```

Formal novelty audit stores:
- query;
- filters;
- retrieval config;
- candidate count;
- ranks;
- deep-read set;
- exact source chunks used in conclusions.

---

# 14. Migration milestones

# M0 — Scientific correctness before architecture migration

**Goal:** eliminate known correctness bugs so V2 does not inherit corrupted semantics.

### Required changes
1. Fix FATAL + REQUIRES_HUMAN precedence.
2. Make court/gate decision actually block experiment execution in legacy path.
3. Add `CONTRADICTED/INCONCLUSIVE/INVALID` distinction.
4. Do not append inconclusive evidence to `contradicting_evidence_ids`.
5. Harden Sandbox executable resolution.
6. Fix arXiv author/category mapping if legacy reader remains exercised.
7. Add regression tests.

### Acceptance tests

- `test_fatal_plus_human_is_kill`
- `test_kill_decision_never_executes_experiment`
- `test_inconclusive_is_not_contradiction`
- `test_failed_execution_is_invalid_evidence`
- `test_sandbox_rejects_untrusted_same_basename_executable`
- `test_arxiv_parser_preserves_authors_categories`
- all pre-existing tests pass

**M0 exit condition:** no known P0/P1 scientific correctness bug remains unfixed or explicitly documented as blocked.

---

# M1 — PostgreSQL Research Store

**Goal:** create one durable scientific source of truth.

### Deliverables
- PostgreSQL bootstrap/config;
- Alembic migrations;
- `research.*` schema;
- repository/service layer;
- SQLite import utility;
- Artifact Store abstraction;
- conversion of objection ledger to ResearchRepository;
- persistence tests.

### Acceptance tests

- create project -> restart process -> all scientific entities remain available;
- protocol version hash stable across restart;
- object mutation creates version/history rather than silent overwrite;
- objection lifecycle persists;
- experiment spec/run persists;
- analysis/claim/evidence link persists;
- approval invalidates when target hash changes;
- SQLite import is idempotent;
- repeated migration produces no duplicate entities.

**M1 exit condition:** new production features MUST NOT write scientific truth exclusively to SQLite or in-memory ResearchState.

---

# M2 — LangGraph orchestration skeleton

**Goal:** replace monolithic orchestration with executable state transitions.

### Deliverables
- LangGraph state;
- checkpoint persistence in PostgreSQL;
- graph builder/routes;
- Policy Engine;
- interrupt/resume;
- legacy `AIScientist` compatibility facade;
- Experiment Runtime adapter with idempotent submission.

### Acceptance tests

1. gate KILL path has no reachable experiment node;
2. WAIT_FOR_HUMAN survives process restart;
3. approving a stale protocol hash is rejected;
4. graph replay does not duplicate an existing experiment run;
5. experiment completion after orchestrator restart resumes analysis;
6. REFRAME routes to correct upstream node;
7. unresolved FATAL prevents confirmation and manuscript-ready states;
8. legacy smoke test can still call facade without direct old orchestration.

**M2 exit condition:** `run_full_research_pipeline()` is no longer the canonical production orchestration path.

---

# M3 — Literature Intelligence

**Goal:** replace arXiv-only abstract search with auditable hybrid literature intelligence.

### Deliverables
- PostgreSQL `literature.*` tables;
- source adapters in staged order;
- paper canonicalization/dedup;
- PDF/artifact hydration;
- section-aware parser/chunker;
- local embedding pipeline;
- FTS + vector + citation retrieval;
- retrieval provenance;
- Core Corpus + external expansion;
- novelty service API.

### First adapters
1. OpenReview
2. PMLR
3. CVF
4. ACL Anthology
5. NeurIPS proceedings
6. Crossref
7. OpenAlex
8. Semantic Scholar

Later adapters:
- ECCV-specific source if needed
- RSS
- IEEE/ICRA/IROS
- AAAI

### Acceptance tests

- known exact identifiers never create duplicate papers;
- fuzzy title match never silently merges without canonicalization rule;
- paper/version/appearance are distinct;
- legal full-text artifact hash is stable;
- section chunks retain page/section provenance;
- changed content invalidates only affected embeddings/claims;
- citation edge stores source provenance;
- Core membership can be explained from official source;
- external novelty paper can be imported on demand;
- Scout and Reviewer formal novelty searches produce different retrieval_run IDs.

### Retrieval quality gate

Create a frozen **Known-Prior Benchmark** of at least 20 research questions with manually specified dangerous/closest prior papers.

Pass criteria:
- >= 90% of benchmark queries retrieve at least one designated dangerous prior in Top-50;
- >= 80% retrieve a designated dangerous prior in Top-20;
- 100% of novelty conclusions cite inspectable source chunks for deep-read papers;
- zero fabricated paper IDs in benchmark output.

The benchmark set MUST be versioned and not silently tuned after observing retrieval failures.

**M3 exit condition:** formal novelty review no longer depends on legacy `literature/search.py`.

---

# M4 — Six Agents + subscription-first execution

**Goal:** activate role separation and Codex/RPA execution without paid-API dependence.

### Deliverables
- six Agent Contracts;
- role implementations;
- `AgentExecutor` abstraction;
- Codex executor;
- human-assisted executor;
- paid API kill switch;
- Action Broker;
- permissions;
- per-task budget/accounting;
- structured TaskSpec/TaskResult.

### Acceptance tests

- each role rejects writes outside its permission contract;
- Engineer cannot mutate frozen metric/split fields;
- Analyst cannot mutate raw experiment artifacts;
- Editor cannot introduce a number absent from formal analysis without failing manuscript check;
- Reviewer cannot overwrite official analysis;
- Scout cannot approve own novelty gate;
- a blocking review finding without evidence/target/resolution is rejected as invalid;
- paid API execution fails closed without approval;
- RPA action is logged and idempotency-keyed;
- Codex task produces structured TaskResult;
- human-assisted task can interrupt and resume;
- one mini research case completes: idea -> novelty -> protocol -> killer experiment -> analysis -> review.

### Agent architecture ablation

On a frozen task suite, compare:
- role separation;
- merged PI+Engineer;
- merged Analyst+Reviewer;
- self-review instead of Independent Reviewer.

Measure:
- valid error detection;
- false blocking;
- protocol violations;
- human repair time;
- total executor usage.

Do not alter six-role production architecture solely on self-reported agent scores.

**M4 exit condition:** six roles are real permission/accountability boundaries, not prompt labels.

---

# M5 — Full paper lifecycle and legacy retirement

**Goal:** complete research -> paper -> review -> revision -> release package.

### Deliverables
- claim freeze;
- manuscript versioning;
- tables/figures from formal results;
- citation/claim support checks;
- independent paper review;
- revision router;
- submission preflight;
- mandatory human release approval;
- research package export;
- archive/follow-up pipeline;
- legacy retirement report.

### Acceptance tests

End-to-end replay MUST demonstrate:

1. a candidate can be killed before experimentation;
2. a candidate can be reframed and re-enter discovery;
3. a valid killer experiment can advance;
4. an inconclusive experiment stays inconclusive;
5. analysis correction invalidates downstream claim/manuscript versions;
6. Reviewer statistical finding routes to Analyst;
7. Reviewer implementation finding routes to Engineer;
8. novelty finding routes to literature audit;
9. manuscript numbers trace to formal analysis artifacts;
10. every main claim traces to evidence;
11. every experiment evidence traces to ExperimentSpec and ProtocolVersion;
12. process restart at every human interrupt preserves state;
13. no experiment is duplicated after resume/replay;
14. final release cannot occur without explicit human approval;
15. exported research package can be reconstructed from DB + artifact refs.

### Legacy retirement criteria

Only after M5 passes:
- old orchestrator logic may be moved to `legacy/` or removed;
- `autonomous_loop.py` may become compatibility adapter or be retired;
- `multi_agent_debate.py` remains only if benchmark/tool use justifies it;
- SQLite becomes migration fixture only;
- old FTS is removed.

**M5 exit condition:** a paper lifecycle is reproducible without relying on legacy orchestration state.

---

# 15. Migration implementation order

Codex MUST implement in this order:

```text
M0 correctness
 -> M1 store
 -> M2 graph
 -> M3 literature
 -> M4 agents/executors
 -> M5 paper lifecycle
```

Do not start later milestones by stubbing away failed earlier acceptance gates.

Each milestone:
1. create/update OpenSpec change or implementation checklist;
2. implement smallest coherent slice;
3. run milestone tests + full regression suite;
4. write migration report;
5. commit before starting next milestone.

---

# 16. Required branch/commit discipline

Development branch: `research-os-v2`.

Suggested milestone commit prefixes:
- `M0:`
- `M1:`
- `M2:`
- `M3:`
- `M4:`
- `M5:`

No direct commits to `main`.

For large milestones, use sub-branches if needed:
- `research-os-v2-m0-correctness`
- `research-os-v2-m1-store`
- etc.

Before merge:
- full tests pass;
- migration notes updated;
- no hidden paid API dependency;
- no generated secrets/cookies/session profiles committed.

---

# 17. Definition of architectural success

Research OS v2 is successful only when all of the following are true:

1. **Single truth:** scientific entities survive restart and have one canonical persistent record.
2. **Executable gates:** a blocked scientific decision changes reachable execution paths.
3. **Role accountability:** six roles have different write permissions and auditable outputs.
4. **Evidence semantics:** supported, contradicted, inconclusive, and invalid are distinct.
5. **Experiment idempotency:** graph resume cannot duplicate a scientific run.
6. **Novelty intelligence:** formal novelty claims are backed by auditable retrieval and exact paper evidence.
7. **No API dependency:** the normal path can operate with paid LLM API disabled.
8. **Human sovereignty:** final release and exceptional costly/risky actions require explicit approval.
9. **Reproducible paper:** manuscript claims and numbers trace back to analysis, experiment, protocol, code/data versions, and artifacts.
10. **Benchmarkability:** architecture components can be ablated without changing the scientific task definition.

---

# 18. Explicit non-goals for V2

Do not add unless separately approved:

- general-purpose distributed compute platform;
- Kubernetes;
- autonomous financial purchasing;
- automatic final paper submission;
- automatic author-list decisions;
- heavy LLM-extracted global knowledge graph;
- replacing PostgreSQL with a specialized vector/graph database;
- arbitrary browser automation of unsupported services as a fake API;
- dozens of permanent agent personas;
- optimizing for agent self-rating or simulated reviewer score.

---

# 19. Codex implementation command contract

The first Codex task on this branch should be:

> Read this specification and the current repository. Implement **M0 only**. Do not begin M1. Add targeted regression tests for every M0 acceptance criterion, preserve current passing behavior, and produce `reports/research_os_v2_m0_report.md` containing: files changed, tests run, exact results, unresolved blockers, and any deviation from this specification. Do not change scientific thresholds, benchmark definitions, or frozen research results to make tests pass.

After M0 is reviewed and committed, issue a separate task for M1.

---

# 20. Freeze statement

This specification freezes the **V2 migration architecture**, not every implementation detail.

The following require a new ADR before changing:
- six role boundaries;
- LangGraph as primary orchestrator;
- PostgreSQL as scientific source of truth;
- subscription-first / paid-API-disabled default;
- deterministic Gate Engine ownership of transitions;
- distinction between raw experiment output and formal analysis;
- independent Reviewer separation from Analyst;
- Core Corpus + external novelty expansion;
- evidence verdict semantics;
- mandatory human final-release approval.

Implementation details may evolve when tests show a better choice, but changes MUST be documented and MUST NOT silently weaken the scientific controls above.
