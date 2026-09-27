## ADDED Requirements

### Requirement: PostgreSQL is canonical scientific storage
Research OS scientific entities MUST be stored in the `research` schema and remain queryable after connections and processes restart.

#### Scenario: Full scientific chain survives restart
- **WHEN** a project, question, hypothesis, protocol, experiment, analysis, evidence, claim, and link are committed
- **THEN** a new engine/session reconstructs the same linked records

### Requirement: Frozen protocols are immutable and versioned
A `FROZEN` protocol MUST reject in-place scientific content mutation; revisions MUST create a new version with a distinct content hash while retaining the old row.

#### Scenario: Revise a frozen protocol
- **WHEN** a caller revises frozen protocol v1
- **THEN** v1 remains unchanged and protocol v2 has a different hash

### Requirement: Approvals are hash-bound
An approval MUST authorize only the exact target ID and content hash it records.

#### Scenario: Target changes after approval
- **WHEN** protocol v1 is approved and v2 is created
- **THEN** the v1 approval does not authorize v2

### Requirement: Artifacts are immutable and verified
Artifact content MUST remain outside PostgreSQL and registration MUST record a SHA-256 digest that can be verified within a bounded root.

#### Scenario: Artifact changes or disappears
- **WHEN** a registered file is modified or removed
- **THEN** integrity verification fails

### Requirement: Legacy import is idempotent
Importing the same SQLite database and rows repeatedly MUST NOT create duplicate scientific entities and MUST NOT modify the source database.

#### Scenario: Repeat import
- **WHEN** the same SQLite database is imported twice
- **THEN** the second import creates zero duplicates
