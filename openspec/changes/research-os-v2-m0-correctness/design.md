## Context

Research OS v2 freezes M0 as a correctness repair on the legacy runtime. The current court, orchestrator, evaluator, evidence update, sandbox, and arXiv parser each contain a confirmed defect; the later PostgreSQL, LangGraph, agent, executor, browser, and migration milestones are explicitly excluded.

## Goals / Non-Goals

**Goals:**

- Enforce fatal-gate precedence and make non-continuation decisions stop experiment control flow.
- Use one explicit four-state evaluation vocabulary and propagate it without collapsing uncertainty or execution failure into contradiction.
- Close the executable basename bypass while preserving trusted interpreter and PATH-resolved commands.
- Preserve arXiv author and category metadata and prove all six fixes with deterministic tests.

**Non-Goals:**

- No M1-M5 architecture or persistence migration.
- No new orchestration framework, agents, browser automation, benchmark design, threshold, or frozen-result changes.
- No claim that the local subprocess sandbox is a VM security boundary.

## Decisions

- Keep `KILL` monotonic inside `FinalResearchCourt`: human-review metadata is additive and cannot reduce fatal severity. A later precedence framework is unnecessary for this fixed rule.
- Gate the legacy full pipeline immediately after the serialized debate/court result. Only `CONTINUE` with a researchable debate may reach experiment construction or execution; existing non-continuation results return a structured blocked stage.
- Let `ExperimentEvaluator` own verdict selection and let the autonomous loop perform a direct verdict-to-edge mapping. Failed execution is `INVALID`; passed explicit success criteria is `SUPPORTED`; passed explicit contradiction criteria is `CONTRADICTED`; otherwise it is `INCONCLUSIVE`.
- Add optional contradiction criteria to the existing experiment specification rather than infer contradiction from failed success criteria.
- For path-form executables, compare the resolved executable with the trusted current interpreter or the resolved target of explicitly allowed PATH commands. Bare commands remain limited to the allowlist and must resolve on PATH.
- Pass already parsed arXiv authors and categories directly into `PaperContent`.

## Risks / Trade-offs

- [Legacy callers may omit court metadata] -> Fall back to the existing debate status and permit execution only when it is explicitly `RESEARCHABLE`.
- [An allowed PATH command may move between runs] -> Resolve it at validation time; this is executable allowlisting, not process isolation.
- [Older experiment specs lack contradiction criteria] -> The new field defaults to empty, preserving construction compatibility and yielding `INCONCLUSIVE` when support is not established.

## Migration Plan

Apply the six focused repairs, run the new M0 tests, run all legacy and benchmark/discovery regressions, generate the M0 report, and commit on `research-os-v2`. Rollback is the single milestone commit; no stored data is migrated.

## Open Questions

None for M0.
