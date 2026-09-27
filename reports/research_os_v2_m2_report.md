# Research OS v2 M2 Report

## 1. Scope

M2 replaces the new production orchestration entry with a durable LangGraph Research OS while keeping M0/M1 behavior and legacy APIs intact. M3-M5 features are outside this milestone.

## 2. Implementation

- Added official LangGraph 1.2.12 and `langgraph-checkpoint-postgres` 3.1.2.
- Added compact `ResearchExecutionState`; it contains entity IDs, small reference lists, execution stages, and error codes only.
- Implemented all 38 frozen Research OS nodes plus `END` and the specified discovery, design, killer, research, confirmation, audit, paper, and release edges.
- Added deterministic conditional routes for idea, protocol, killer, progress, and result-audit gates.
- Added PostgreSQL checkpoints under `orchestration.checkpoints`, `checkpoint_blobs`, `checkpoint_writes`, and `checkpoint_migrations` using the official `PostgresSaver`.
- Added durable `interrupt()` boundaries for human start/release and pending experiment completion.
- Added the idempotent Experiment Runtime adapter: an existing persistent run is returned before the external runner can be called.
- Added `AIScientist.run_research_os()` as the compatibility facade. Existing legacy entry points remain available but are no longer the new production path.

## 3. Acceptance Results

| Requirement | Evidence |
| --- | --- |
| KILL prevents experiment | graph completed at archive; runner call count 0 |
| WAIT_FOR_HUMAN survives restart | rebuilt graph returned the same pending `human_start_approval` node and project ID |
| stale approval rejected | v1 approval did not authorize v2 ID/hash |
| replay does not duplicate experiment | two graph threads using the same spec produced one run and one runner call |
| experiment restart resumes analysis | pending run interrupted, external completion was recorded, rebuilt graph resumed through analysis and gate |
| REFRAME routes upstream | discovery re-entry occurred and bounded reframe policy archived with explicit error rather than running an experiment |
| FATAL blocks confirmation/manuscript | progress KILL archived; checkpoint history contained neither confirmation nor manuscript stages |
| legacy facade works | `AIScientist` invoked the Research OS graph while preserving its legacy constructor/API |

## 4. Tests and Commands

| Command | Exit | Result |
| --- | ---: | --- |
| `pytest -q tests/test_m2_langgraph_orchestration.py` in Compose test service | 0 | 9 passed |
| `python -m compileall -q auto_research/src` | 0 | passed |
| complete pytest in Compose test service | 0 | 73 passed, 0 failed, 0 skipped, 14 pre-existing warnings |
| `python test_autonomous_research_loop.py` | 0 | passed |
| `python test_v4_integration.py` | 0 | 6/6 passed |
| `python test_v1_v4_regression.py` | 0 | 6/6 passed |
| discovery/planner/hypothesis regression selection | 0 | 4 passed |
| `openspec validate research-os-v2-m2-langgraph-orchestration` | 0 | valid |
| `git diff --check` | 0 | passed |

## 5. Failure/Recovery Evidence

- Process-bound object state was discarded between checkpointer contexts; a new graph instance loaded the pending human interrupt.
- A run registered as `RUNNING` was completed through PostgreSQL between graph instances; resume continued without a second submission.

## 6. Regression Status

M0 and M1 tests, complete legacy scripts, and discovery regressions passed. Scientific thresholds and benchmark fixtures were unchanged.

## 7. Deviations From Specification

NONE.

## 8. Remaining Blockers

NONE for M2.

## 9. M2 Verdict

PASS
