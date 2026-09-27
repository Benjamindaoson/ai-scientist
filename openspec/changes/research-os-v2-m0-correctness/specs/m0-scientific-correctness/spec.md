## ADDED Requirements

### Requirement: Fatal decisions are monotonic
The final research court MUST return `KILL` whenever an open fatal objection exists, even when the same decision also requires human review.

#### Scenario: Fatal objection plus human review
- **WHEN** the objection gate contains both an open fatal objection and a human-review objection
- **THEN** the final decision is `KILL` and the human-review metadata remains available

### Requirement: Scientific gates control experiment execution
The legacy full research pipeline MUST NOT construct or execute an autonomous experiment program after a `KILL`, revision, blocked, human-required, rejected, or otherwise non-continuation scientific result.

#### Scenario: Killed direction has an experiment specification
- **WHEN** the scientific debate/court returns `KILL` and the caller supplies an experiment specification
- **THEN** the experiment runner is not called and no experiment run is created

### Requirement: Evidence verdicts preserve scientific meaning
Experiment evaluation and evidence propagation MUST distinguish `SUPPORTED`, `CONTRADICTED`, `INCONCLUSIVE`, and `INVALID`. Failure to meet a support criterion MUST NOT by itself mean contradiction.

#### Scenario: Insufficient evidence
- **WHEN** an experiment runs successfully but neither explicit support nor explicit contradiction criteria pass
- **THEN** its verdict and claim edge are `INCONCLUSIVE` and it is not recorded as contradicting evidence

#### Scenario: Explicit contradiction
- **WHEN** an experiment runs successfully and explicit contradiction criteria pass
- **THEN** its verdict is `CONTRADICTED` and its claim edge is `CONTRADICTS`

### Requirement: Execution failures are invalid evidence
Non-zero exits, timeouts, missing or invalid metrics, sandbox failures, dependency failures, and code failures MUST evaluate as `INVALID` evidence and MUST NOT support or contradict a hypothesis.

#### Scenario: Failed experiment execution
- **WHEN** an experiment result is not successful
- **THEN** its verdict and claim edge are `INVALID` and its evidence ID is absent from both supporting and contradicting evidence lists

### Requirement: Executable allowlisting validates resolved identity
The local sandbox MUST reject an absolute or path-form executable unless it resolves to the trusted Python interpreter or the resolved executable of an explicitly allowed PATH command.

#### Scenario: Untrusted executable reuses an allowed basename
- **WHEN** an absolute untrusted path ends in `python.exe` or another allowed basename
- **THEN** executable validation rejects it

#### Scenario: Trusted supported commands
- **WHEN** the command uses the current Python interpreter or an installed allowlisted bare command
- **THEN** executable validation accepts it

### Requirement: arXiv metadata is retained
The arXiv paper parser MUST copy parsed author names and categories into `PaperContent`.

#### Scenario: Fixed arXiv XML entry
- **WHEN** an XML entry contains multiple authors and categories
- **THEN** the returned paper contains those authors and categories in source order
