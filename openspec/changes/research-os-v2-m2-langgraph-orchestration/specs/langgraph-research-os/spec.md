## ADDED Requirements

### Requirement: Gates control reachable nodes
Scientific gate outcomes MUST select conditional edges and MUST make prohibited experiment, confirmation, and manuscript nodes unreachable.

#### Scenario: Idea is killed
- **WHEN** the latest idea gate decision is `KILL`
- **THEN** the graph archives the project without calling the Experiment Runtime

### Requirement: Human waits are durable
Human-required nodes MUST use a PostgreSQL-backed LangGraph interrupt that remains pending after graph/process reconstruction.

#### Scenario: Restart while waiting
- **WHEN** a workflow reaches `WAIT_FOR_HUMAN` and a new graph instance loads the same thread
- **THEN** the interrupt and compact state remain available for resume

### Requirement: Experiment submission is idempotent
Submission MUST query the canonical store by experiment identity before invoking the external runner.

#### Scenario: Replay after submit
- **WHEN** the same checkpoint/spec is replayed after a run was registered
- **THEN** the existing run ID is returned and the runner is not called again

### Requirement: Checkpoint state contains references only
Checkpoint values MUST contain IDs, stages, small lists of references, and errors; scientific documents/results MUST remain in PostgreSQL or Artifact Store.

#### Scenario: Inspect checkpoint
- **WHEN** a graph checkpoint is read
- **THEN** it contains no paper full text, full result payload, or manuscript body
