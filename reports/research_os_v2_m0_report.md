# Research OS v2 M0 Report

## 1. Scope

This change implements only **M0 — Scientific correctness before architecture migration** on the existing legacy runtime. It does not begin M1, M2, M3, M4, or M5. No PostgreSQL, LangGraph, six-agent runtime, CodexExecutor, Playwright/RPA, Literature Intelligence database, SQLite migration, directory rewrite, legacy deletion, benchmark redesign, scientific-threshold change, or frozen-result change is included.

## 2. Bugs Fixed

### M0-1 — FATAL plus REQUIRES_HUMAN precedence

- **Original behavior:** An open fatal objection first selected `KILL`, but a simultaneous human-review objection overwrote it with `REVISE`.
- **Root cause:** The human-review branch assigned `REVISE` unconditionally after the fatal branch.
- **Modified file:** `auto_research/src/ai_scientist/engine/final_research_court.py`
- **New behavior:** Fatal objections keep the final decision at `KILL`; `requires_human_review` and `human_review_reason` remain populated.
- **Regression test:** `test_fatal_plus_human_is_kill`

### M0-2 — KILL did not stop experiment execution

- **Original behavior:** `run_full_research_pipeline()` entered the autonomous experiment program whenever an `experiment_spec` was supplied, regardless of the debate/court result.
- **Root cause:** The experiment branch checked only for the presence of a specification and did not make the scientific decision an executable control-flow gate.
- **Modified file:** `auto_research/src/ai_scientist/orchestrator.py`
- **New behavior:** Only an explicitly `RESEARCHABLE` debate with no court decision other than `CONTINUE` may construct or execute an experiment. All other decisions produce a `BLOCKED_BY_SCIENTIFIC_GATE` stage and do not call the runner.
- **Regression test:** `test_kill_decision_never_executes_experiment` verifies `runner.run()` is called zero times.

### M0-3 — INCONCLUSIVE was recorded as CONTRADICTS

- **Original behavior:** Every evaluation other than `SUPPORTED` created a `CONTRADICTS` edge and polluted `contradicting_evidence_ids`; the same binary mapping existed in the ablation path.
- **Root cause:** The autonomous loop collapsed a multi-state scientific verdict into a two-way conditional.
- **Modified files:** `auto_research/src/ai_scientist/autonomous_loop.py`, `auto_research/src/ai_scientist/experiment/evaluator.py`, `auto_research/src/ai_scientist/experiment/models.py`
- **New behavior:** Verdicts map explicitly as `SUPPORTED -> SUPPORTS`, `CONTRADICTED -> CONTRADICTS`, `INCONCLUSIVE -> INCONCLUSIVE`, and `INVALID -> INVALID`. Only explicit contradiction criteria can produce `CONTRADICTED`. Main and ablation paths use the same mapping.
- **Regression tests:** `test_inconclusive_is_not_contradiction`, `test_explicit_contradiction_is_contradicted`, `test_ablation_inconclusive_is_not_contradiction`

### M0-4 — Failed execution became scientific contradiction

- **Original behavior:** Failed, missing-metric, and otherwise unsupported experiment results evaluated as `INCONCLUSIVE`, after which the loop stored them as contradictory evidence.
- **Root cause:** The evaluator had only `SUPPORTED` and `INCONCLUSIVE` outcomes, and the runner accepted any JSON value as metrics.
- **Modified files:** `auto_research/src/ai_scientist/experiment/evaluator.py`, `auto_research/src/ai_scientist/experiment/runner.py`, `auto_research/src/ai_scientist/autonomous_loop.py`
- **New behavior:** Unsuccessful execution, missing declared metrics, malformed comparisons, or non-object metrics evaluate as `INVALID`. Invalid evidence is linked with an `INVALID` edge and is added to neither supporting nor contradicting evidence IDs. Non-object metrics also make the run fail with `INVALID_METRICS`.
- **Regression tests:** `test_failed_execution_is_invalid_evidence`, `test_invalid_metrics_are_invalid_evidence`

### M0-5 — Sandbox executable basename bypass

- **Original behavior:** Any path ending in an allowed basename such as `python.exe` passed the sandbox executable check.
- **Root cause:** `SandboxPolicy.executable_allowed()` compared only `Path(executable).name`.
- **Modified file:** `auto_research/src/ai_scientist/experiment/sandbox.py`
- **New behavior:** Path-form executables must resolve to `sys.executable` or to the resolved target of an explicitly allowed PATH command. Bare commands remain allowlisted and must resolve on PATH. This remains a guarded subprocess policy, not a VM security boundary.
- **Regression test:** `test_sandbox_rejects_untrusted_same_basename_executable`

### M0-6 — arXiv authors and categories were dropped

- **Original behavior:** The parser collected author names and categories but omitted them when constructing `PaperContent`; standard Atom-namespace category elements were also not selected.
- **Root cause:** The `PaperContent` constructor did not receive the parsed lists, and category lookup covered only the arXiv namespace variant.
- **Modified file:** `auto_research/src/ai_scientist/literature/reader.py`
- **New behavior:** Parsed authors and categories are retained in source order; both standard Atom and arXiv namespace category elements are accepted.
- **Regression test:** `test_arxiv_parser_preserves_authors_categories` uses a fixed offline XML fixture.

## 3. Files Changed

| Path | Change | Reason |
|---|---|---|
| `auto_research/src/ai_scientist/engine/final_research_court.py` | Made human-review metadata non-overriding for fatal decisions | Preserve deterministic fatal precedence |
| `auto_research/src/ai_scientist/orchestrator.py` | Added the executable scientific gate before experiment construction/execution | Make `KILL` and other non-continuation outcomes change real control flow |
| `auto_research/src/ai_scientist/experiment/models.py` | Added optional `contradiction_criteria` with an empty default | Require explicit conditions for scientific contradiction while preserving existing specs |
| `auto_research/src/ai_scientist/experiment/evaluator.py` | Added four-state evaluation and metric-validity checks | Separate support, contradiction, uncertainty, and invalid execution |
| `auto_research/src/ai_scientist/experiment/runner.py` | Reject non-object metrics payloads as `INVALID_METRICS` | Prevent malformed output from becoming scientific evidence |
| `auto_research/src/ai_scientist/autonomous_loop.py` | Unified verdict-to-edge mapping and evidence-list updates across main and ablation paths | Eliminate `not supported == contradicted` |
| `auto_research/src/ai_scientist/experiment/sandbox.py` | Validate executable identity through resolved trusted paths | Close the same-basename absolute-path bypass |
| `auto_research/src/ai_scientist/literature/reader.py` | Retained authors/categories and accepted Atom category elements | Preserve arXiv metadata |
| `tests/test_m0_scientific_correctness.py` | Added nine deterministic M0 tests, including all six required names | Prove each correction and the shared ablation/invalid-metric semantics |
| `openspec/changes/research-os-v2-m0-correctness/.openspec.yaml` | Declared the project-local OpenSpec change schema | Track the M0 change |
| `openspec/changes/research-os-v2-m0-correctness/proposal.md` | Recorded M0 motivation, scope, capability, and impact | Keep specification scope limited to M0 |
| `openspec/changes/research-os-v2-m0-correctness/design.md` | Recorded the focused implementation decisions and non-goals | Preserve frozen architectural boundaries |
| `openspec/changes/research-os-v2-m0-correctness/specs/m0-scientific-correctness/spec.md` | Defined testable M0 requirements and scenarios | Make the correctness contract explicit |
| `openspec/changes/research-os-v2-m0-correctness/tasks.md` | Tracked implementation, regression, verification, reporting, and commit work | Synchronize actual milestone progress |
| `reports/research_os_v2_m0_report.md` | Added this evidence-based completion report | Satisfy the M0 reporting contract |

## 4. Tests Added

- `test_fatal_plus_human_is_kill`: verifies fatal plus human review remains `KILL` while retaining the human-review flag and reason.
- `test_kill_decision_never_executes_experiment`: uses a spy runner and verifies exactly zero `run()` calls after a `KILL` court result.
- `test_inconclusive_is_not_contradiction`: verifies an inconclusive result creates an `INCONCLUSIVE` edge and does not enter `contradicting_evidence_ids`.
- `test_failed_execution_is_invalid_evidence`: verifies a non-zero execution result becomes `INVALID`, creates no support/contradiction, and does not pollute either evidence-ID list.
- `test_sandbox_rejects_untrusted_same_basename_executable`: rejects an untrusted path with the trusted interpreter basename while accepting `sys.executable` and installed allowlisted commands.
- `test_arxiv_parser_preserves_authors_categories`: verifies authors and categories from a fixed offline arXiv XML fixture are retained.
- `test_invalid_metrics_are_invalid_evidence`: verifies non-object metrics make the run fail with `INVALID_METRICS` and evaluate as `INVALID`.
- `test_explicit_contradiction_is_contradicted`: verifies only a passed explicit contradiction criterion produces `CONTRADICTED` and contradicting evidence.
- `test_ablation_inconclusive_is_not_contradiction`: verifies the ablation path uses the same `INCONCLUSIVE` relation.

## 5. Test Results

All commands used the project-local `.venv`. Python test commands ran with `PYTHONIOENCODING=utf-8`.

| Command | Exit code | Passed | Failed | Skipped |
|---|---:|---:|---:|---:|
| `.\.venv\Scripts\python.exe -m compileall -q auto_research/src` | 0 | N/A (byte compilation succeeded) | 0 | 0 |
| `.\.venv\Scripts\python.exe -m pytest -q tests/test_m0_scientific_correctness.py` | 0 | 9 | 0 | 0 |
| `.\.venv\Scripts\python.exe -m pytest -q` | 0 | 57 | 0 | 0 |
| `.\.venv\Scripts\python.exe -m pytest -q tests` | 0 | 34 | 0 | 0 |
| `.\.venv\Scripts\python.exe -m pytest -q tests/test_discovery_loop.py tests/test_discovery_trajectory.py tests/test_hypothesis_generator.py tests/test_experiment_planner.py tests/test_claim_generation.py tests/test_scientist_runner.py` | 0 | 8 | 0 | 0 |
| `.\.venv\Scripts\python.exe test_autonomous_research_loop.py` | 0 | 5 integration checks | 0 | 0 |
| `.\.venv\Scripts\python.exe test_v4_integration.py` | 0 | 6 | 0 | 0 |
| `.\.venv\Scripts\python.exe test_v1_v4_regression.py` | 0 | 6 | 0 | 0 |
| `.\.venv\Scripts\python.exe test_comprehensive.py` | 0 | 6 | 0 | 0 |
| `openspec validate research-os-v2-m0-correctness` | 0 | 1 change valid | 0 | 0 |
| `git diff --check` | 0 | N/A (no whitespace errors) | 0 | 0 |

The final full pytest run reported 14 `PytestReturnNotNoneWarning` warnings from pre-existing legacy tests that return `True`; the pre-change baseline had the same 14 warnings. They are not failures and were not weakened, skipped, or suppressed.

## 6. Regression Status

All pre-existing pytest tests remain passing. The pre-change baseline was 48 passed with 14 warnings; the final suite is 57 passed with the same 14 warnings. Legacy autonomous-loop, V4 integration, V1-to-V4 regression, comprehensive, benchmark, and discovery tests all passed. No existing test was deleted, relaxed, skipped, marked xfail, or changed. No benchmark threshold, benchmark definition, trajectory fixture, or frozen result was modified.

## 7. Deviations From Specification

NONE

## 8. Remaining Blockers

NONE

## 9. M0 Verdict

PASS

M1 has not been started.
