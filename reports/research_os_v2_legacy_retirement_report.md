# Research OS v2 Legacy Retirement Report

## Scope

This audit was performed only after the M5 paper lifecycle E2E passed. It classifies production imports and preserves useful legacy code; it does not delete files for directory cleanliness.

## Production Import Audit

| Legacy surface | Current imports | Classification | Disposition |
| --- | --- | --- | --- |
| `orchestrator.py` / `AIScientist` | package public API and M0/M2 compatibility tests | compatibility facade | retain; `run_research_os()` delegates new production execution to LangGraph |
| `autonomous_loop.py` / `AutonomousResearchLoop` | compatibility orchestrator, M0 tests and discovery protocol | legacy scientific regression harness | retain; not the Research OS v2 production orchestrator |
| `engine/multi_agent_debate.py` | legacy orchestrator and public compatibility exports | legacy governance mechanism | retain for callers; not used by the Research OS graph or six-role AgentLab |
| `engine/objection_ledger.py` | legacy orchestrator/debate | compatibility adapter candidate | retain; canonical Research OS objections are PostgreSQL-backed |
| `db/repository.py` and `db/schema.sql` | legacy orchestrator/runtime | legacy SQLite store | retain read/compatibility behavior; not authoritative for new Research OS runs |
| `research_store/sqlite_import.py` | CLI and package exports | migration fixture | retain read-only importer with idempotency receipt |
| `research_state.py` | legacy orchestration paths | compatibility execution object | retain; prohibited as a new canonical scientific truth source |
| `research_package.py` | legacy callers | legacy package format | retain; new canonical exporter is `research_os/package_export.py` |

## V2 Production Entry Points

- CLI: `ai_scientist.research_store.cli:main`
- Orchestration: `research_os.graph.build_research_graph`
- Canonical store: `research_store.ResearchRepository`
- Literature: `literature_intelligence.LiteratureService`
- Six-role runtime: `research_os.agents.AgentLab`
- Paper lifecycle: `research_os.paper_lifecycle.PaperLifecycleService`
- Reconstructable package: `research_os.package_export.ResearchPackageExporter`

## Evidence

Repository-wide import search found direct production imports of the legacy autonomous loop, debate and SQLite repository only through the compatibility facade/public API. M2 verifies that the facade reaches LangGraph and that a KILL path never calls the experiment runner. M0 and the discovery suite continue to exercise the retained legacy scientific semantics.

The M5 graph integration test executes claim freeze, manuscript creation, submission preflight, durable final-release interrupt, process/checkpointer restart, hash-bound human approval and archive through the LangGraph runtime.

## Removed Code

NONE.

## Remaining Compatibility Risk

External consumers can still instantiate `AIScientist.run_full_research_pipeline()` and legacy exported classes. They remain supported compatibility surfaces, but new production automation must use `run_research_os()` or the `ai-scientist` CLI. Removing these surfaces requires a separately versioned deprecation milestone and consumer inventory.

## Verdict

PASS — legacy code is classified and isolated from the Research OS v2 production authority path without destructive deletion.
