# Research OS v2 Agent Contracts

Research OS v2 has exactly six permanent occupational roles. Roles are responsibility boundaries, not LangGraph nodes, and a role may serve multiple nodes.

| Role | Allowed scientific responsibilities | Explicit boundaries |
| --- | --- | --- |
| Research Scout | candidate discovery, prior search, candidate pool, novelty evidence | cannot approve own novelty claim |
| Principal Investigator | question, alternatives, study design, next action, interpretation | cannot mutate frozen protocols or raw results |
| Research Engineer | code, baselines, experiment implementation/testing/runs | cannot determine scientific support status |
| Data Scientist | measurement, formal analysis, statistics, uncertainty, evidence records | cannot act as independent reviewer |
| Scientific Editor | paper/LaTeX, figures, tables, appendix, rebuttal and package | cannot invent or alter formal scientific numbers |
| Independent Reviewer | independent novelty, protocol, result, claim and paper audits | read-only with respect to reviewed formal results |

## Typed contracts

All cross-role work uses strict Pydantic v2 contracts with unknown fields rejected:

- `TaskSpec`: stable task ID, one role/capability, bounded objective, workspace, input refs, acceptance criteria and context.
- `TaskResult`: matching task/role, terminal status, summary, output refs, structured data, usage and error code.
- `ReviewFinding`: category, severity, target, evidence refs, impact and required resolution. Blocking findings without evidence are invalid.
- `ActionRequest`: typed operation/target/domain, allowed channels, idempotency key, risk and optional approval.
- `ClaimRecord`: analysis/evidence/counterevidence IDs and four-state scientific result semantics.

`AgentLab` authorizes every TaskSpec against the static role-capability map before selecting an executor. Disallowed requests fail before any external process or tool is invoked.

## Executors

- `CodexExecutor` is the default intelligent backend and uses the installed `codex exec` interface with ephemeral sessions, bounded workspace, workspace-write sandbox, no interactive approvals, structured output schema, finite timeout and UTF-8 execution records.
- `HumanAssistedExecutor` writes a durable task package, raises a LangGraph interrupt, then validates the imported TaskResult identity and schema.
- `PaidAPIExecutor` refuses work unless paid execution is explicitly enabled and a budget approval ID is supplied. It has no default paid provider or API-key requirement.
- `MockExecutor` exists only for deterministic tests.

## Review routing

Typed paper findings route by category: writing to Editor; statistics to Analyst; implementation to Engineer; missing experiment to PI and Engineer; novelty/citation to Scout and Reviewer with independent retrieval; claim/evidence to PI and Analyst; protocol to PI and Reviewer. Findings are converted to evidence work or human decisions rather than unlimited agent debate.
