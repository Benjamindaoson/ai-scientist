## ADDED Requirements

### Requirement: Role boundaries are executable policy
Every task MUST identify one of the six frozen roles and one permitted capability before execution.

#### Scenario: Editor attempts to change scientific numbers
- **WHEN** an Editor task requests `MODIFY_SCIENTIFIC_NUMBERS`
- **THEN** permission validation rejects the task before the executor runs

### Requirement: Subscription-first executors are auditable
Codex tasks MUST use a supported non-interactive CLI with explicit workspace, structured result schema, task package, and execution record; paid API execution MUST be disabled by default.

#### Scenario: Paid executor has no approval configuration
- **WHEN** it receives a task
- **THEN** it raises a permission error without making an API call

### Requirement: Human-assisted tasks pause durably
Tasks that require manual subscription capability MUST create a human package and use a LangGraph interrupt before accepting a schema-validated result.

#### Scenario: Human result is absent
- **WHEN** the human-assisted executor runs inside the graph
- **THEN** the graph exposes a resumable interrupt containing the package reference

### Requirement: Actions use a single policy broker
External actions MUST select API/CLI before HTTP, Playwright, desktop UI, or vision, enforce domain/risk rules, and persist an idempotent audit record.

#### Scenario: API and browser handlers are available
- **WHEN** the same action can use both
- **THEN** the API handler is selected and no browser handler runs

### Requirement: Six-role architecture is evaluated without self-selection
The frozen ablation MUST compare six-role, PI+Engineer merged, Analyst+Reviewer merged, and self-review configurations on the five specified measures without changing production architecture.

#### Scenario: Ablation completes
- **WHEN** the frozen suite is evaluated
- **THEN** all four configurations and five measures are reported
