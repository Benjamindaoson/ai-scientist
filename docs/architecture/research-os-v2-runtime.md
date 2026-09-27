# Research OS v2 Runtime

Research OS v2 uses LangGraph as its only production orchestrator. PostgreSQL is the canonical scientific source of truth; graph state contains execution status and entity identifiers only. The interactive architecture diagram is [research-os-v2.html](research-os-v2.html), generated from [research-os-v2.architecture.json](research-os-v2.architecture.json).

## Runtime components

| Component | Responsibility | Authority boundary |
| --- | --- | --- |
| Human Lab Director | goals, budgets, start/release decisions | human authority |
| LangGraph Research OS | routing, conditional gates, checkpoint, interrupt/resume | execution state only |
| Six role agents | bounded occupational work packages | cannot bypass role policy |
| Policy Engine | gate routing, permissions, paid/RPA risk rules | deterministic enforcement |
| PostgreSQL Research Store | projects, protocols, runs, analyses, claims, review and approvals | canonical scientific truth |
| Literature Intelligence | corpus, FTS, pgvector, citation graph, retrieval provenance | PostgreSQL `literature` schema |
| Codex Executor | default subscription-backed intelligent execution | bounded workspace and schema output |
| Action Broker | ordered CLI/HTTP/Playwright/UI/Vision actions | domain/risk/approval checks |
| Experiment Runtime | sandboxed commands, metrics and failure recovery | no scientific interpretation |
| Artifact Store | immutable large outputs addressed by URI and SHA-256 | bytes, not scientific truth |
| Git | code, configuration, prompt and manuscript revisions | version provenance |

## LangGraph inventory

The production graph has 38 nodes:

`bootstrap_project`, `discover_candidates`, `scout_prior_search`, `reviewer_novelty_search`, `evaluate_10_10_gate`, `human_start_approval`, `formalize_question`, `design_study`, `design_measurement`, `review_protocol`, `protocol_gate`, `freeze_protocol`, `engineering_preflight`, `implement_killer_experiment`, `submit_killer_experiment`, `wait_for_experiment`, `analyze_killer_experiment`, `interpret_killer_result`, `killer_gate`, `plan_next_research_action`, `implement_experiment`, `submit_experiment`, `wait_for_experiment_result`, `analyze_experiment`, `update_scientific_model`, `research_progress_gate`, `freeze_confirmatory_protocol`, `run_confirmation`, `formal_analysis`, `independent_result_audit`, `claim_freeze`, `draft_manuscript`, `independent_paper_review`, `revision_router`, `submission_preflight`, `human_release_approval`, `archive_project`, `seed_followup_candidates`.

Critical conditional routes are:

- Idea gate: `CONTINUE -> formalize_question`, `REFRAME -> discover_candidates`, `WAIT_FOR_HUMAN -> interrupt`, `KILL -> archive_project`.
- Protocol gate: pass, science repair, measurement repair, review repair, or archive.
- Killer gate: continue, reframe, human interrupt, or archive.
- Research progress gate: another bounded experiment, frozen confirmation, reframe, human interrupt, or archive.
- Independent audit: claim freeze, engineering repair, analysis repair, scientific-model repair, independent novelty retrieval, or archive.
- Final release: a durable interrupt followed by validation of an `APPROVED` record bound to the exact manuscript content hash.

An `OPEN FATAL`/`KILL` route makes experiment, confirmation, manuscript and release nodes unreachable. Experiment submission checks for an existing run before calling the runner, so checkpoint replay does not duplicate a scientific run.

## Execution state

`ResearchExecutionState` stores project/stage IDs, active task/role, protocol/hypothesis/spec/run/analysis/manuscript IDs, pending findings/objections/approval IDs, artifact references, last decision, reframe count and an error code. Paper text, article full text, evidence bodies, metrics and formal scientific records remain in PostgreSQL or the Artifact Store.

## Paper lifecycle routing

Runtime stage handlers bind `claim_freeze`, `draft_manuscript` and `submission_preflight` work to the graph without creating a second orchestrator. Manuscript release is not a file-system side effect: the graph validates a hash-bound approval against the canonical manuscript row, marks it `RELEASE_READY`, then archives and seeds follow-up candidates that must re-enter the novelty gate.
