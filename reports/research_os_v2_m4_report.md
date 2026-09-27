# Research OS v2 M4 Report

## 1. Scope

M4 implements the six occupational roles, enforceable capabilities, subscription-first execution layer, Action Broker, architecture ablation, and a mini E2E through independent result review. M5 manuscript/release lifecycle is not included.

## 2. Six Roles and Contracts

Strict Pydantic v2 contracts now cover `TaskSpec`, `TaskResult`, `ReviewFinding`, `ActionRequest`, and `ClaimRecord`; unknown fields are rejected. Blocking findings require target, evidence, impact, and required resolution.

Programmatic role policies permit only:

- Scout: discovery, prior search, candidate pool, novelty evidence.
- PI: question, competing explanations, study design, next action, interpretation.
- Engineer: code/baseline/experiment/test/run artifacts.
- Analyst: measurement, formal analysis, statistics, uncertainty, evidence.
- Editor: manuscript/LaTeX/figures/tables/appendix/rebuttal/package.
- Independent Reviewer: novelty/protocol/result/claim/paper audit.

Forbidden operations such as raw-result mutation, frozen-protocol mutation, scientific-number mutation, self-novelty approval, and self-audit approval are excluded from every role's capability set and rejected before an executor is called.

Configured LangGraph role nodes now create bounded TaskSpecs and dispatch through `AgentLab`. With no AgentLab configured, M0-M3 compatibility behavior remains unchanged.

## 3. Executors

- `CodexExecutor` uses the installed supported `codex exec` interface with an explicit workspace, ephemeral session, workspace sandbox, noninteractive approval policy, output JSON Schema, finite timeout, UTF-8 logs, and per-task input/output/execution records.
- A real subscription-backed smoke completed with `status=SUCCEEDED` and summary `Codex CLI smoke passed.` in an isolated temporary workspace.
- `HumanAssistedExecutor` writes a durable human task package, pauses with LangGraph `interrupt()`, and validates the resumed TaskResult identity and schema.
- `PaidAPIExecutor` is disabled without both explicit enablement and a budget approval ID; no paid provider is configured.
- `MockExecutor` supports deterministic tests only.

## 4. Action Broker

The single broker enforces `API/CLI > HTTP > Playwright > Desktop UI > Vision`, exact domain allowlists, approval for high-risk actions, durable JSONL audit, and idempotency keys. CLI actions reuse the existing workspace sandbox. HTTP uses bounded `httpx`. Playwright uses a per-action persistent profile, never the user's browser profile, and emits trace, screenshot, downloads directory, and sanitized session metadata.

A real local Chromium smoke loaded `Research OS Browser Smoke` and verified the `.zip` trace, `.png` screenshot, and `.json` session metadata all existed. No cookies, credentials, or browser profile content are committed.

## 5. Frozen Architecture Ablation

This evaluation did not change the frozen production six-role architecture.

| Variant | Valid error detection | False blocking | Protocol violation | Human repair time | Cost/usage units |
| --- | ---: | ---: | ---: | ---: | ---: |
| six-role | 1.000 | 0.000 | 0.000 | 45 | 30 |
| PI+Engineer merged | 1.000 | 0.000 | 0.400 | 45 | 25 |
| Analyst+Reviewer merged | 0.333 | 1.000 | 0.000 | 75 | 25 |
| self-review | 0.333 | 1.000 | 0.400 | 75 | 20 |

These are results of the frozen five-case architecture task suite, not scientific performance claims and not a mechanism for self-modifying production architecture.

## 6. Mini E2E

The existing Autonomous Discovery Benchmark executed a real ETTm1/DLinear baseline, killer experiment path, candidate freeze, and one-time final test. Six accepted work packages then covered:

`idea -> independent novelty -> protocol -> killer experiment -> analysis -> independent result review`

The final test retained the frozen `test evaluated once after candidate freeze` protocol.

## 7. Files Changed

| Path | Change |
| --- | --- |
| `auto_research/src/ai_scientist/research_os/agents/` | strict contracts, permissions, lab, four executors |
| `auto_research/src/ai_scientist/research_os/actions/` | Action Broker and CLI/HTTP/Playwright handlers |
| `auto_research/src/ai_scientist/research_os/architecture_ablation.py` | frozen variant evaluator |
| `auto_research/src/ai_scientist/research_os/graph/` | optional permissioned AgentLab dispatch from role nodes |
| `benchmarks/agent_architecture/frozen_tasks_v1.json` | frozen architecture task suite |
| `tests/test_m4_six_role_execution.py` | M4 contract, permission, executor, broker, ablation, graph, and mini-E2E tests |
| `openspec/changes/research-os-v2-m4-six-role-execution/` | M4 specification and completion record |
| `pyproject.toml` | optional Playwright browser extra |

## 8. Tests and Commands

| Command | Exit | Result |
| --- | ---: | --- |
| M4 pytest in Compose test service | 0 | 9 passed |
| M4 + M2 graph regression selection | 0 | 18 passed |
| real `CodexExecutor` subscription smoke | 0 | TaskResult SUCCEEDED; structured package and execution record captured |
| real Playwright/Chromium isolated-profile smoke | 0 | page title verified; trace/screenshot/metadata artifacts verified |
| architecture ablation command | 0 | 4 variants x 5 required metrics |
| complete pytest in Compose test service | 0 | 92 passed, 0 failed, 0 skipped, 14 pre-existing warnings |
| `python -m compileall -q auto_research/src` | 0 | passed |
| `python test_autonomous_research_loop.py` | 0 | passed |
| `python test_v4_integration.py` | 0 | 6/6 passed |
| `python test_v1_v4_regression.py` | 0 | 6/6 passed |
| discovery/planner/hypothesis/benchmark regression selection | 0 | 6 passed |
| `openspec validate research-os-v2-m4-six-role-execution` | 0 | valid |
| `git diff --check` | 0 | passed |

## 9. Regression Status

M0-M3, the complete suite, legacy integration scripts, and discovery regressions pass. No scientific threshold, frozen result, or benchmark target was changed.

## 10. Deviations From Specification

NONE.

## 11. Remaining Blockers

NONE for M4.

## 12. M4 Verdict

PASS
