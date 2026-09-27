## ADDED Requirements

### Requirement: Corrected analysis invalidates downstream text
Analysis history MUST be preserved and every dependent frozen claim and manuscript version MUST become stale after correction.

#### Scenario: Formal result is corrected
- **WHEN** a completed AnalysisRun is superseded
- **THEN** a new AnalysisRun is created and downstream claims/manuscripts are marked STALE

### Requirement: Manuscript facts are traceable
Every major claim MUST resolve to evidence and every formal number MUST be read from a named AnalysisRun metric.

#### Scenario: Editor supplies an unknown number
- **WHEN** a numeric binding names a missing metric or mismatching expected value
- **THEN** manuscript creation or preflight fails

### Requirement: Review findings route by expertise
Typed findings MUST route writing to Editor, statistics to Analyst, implementation to Engineer, missing experiments to PI+Engineer, novelty/citation to Scout+Reviewer, and claim/evidence to PI+Analyst.

#### Scenario: Novelty blocker arrives
- **WHEN** a NOVELTY finding is routed
- **THEN** a new independent retrieval callback is required

### Requirement: Release is human controlled
No release-ready package MUST be emitted without a hash-bound APPROVED human release approval.

#### Scenario: Approval is pending or stale
- **WHEN** release is requested
- **THEN** the request is rejected

### Requirement: Package reconstruction verifies integrity
The project MUST reconstruct from PostgreSQL rows, Artifact Store references, and Git refs only when every required artifact exists and matches its hash.

#### Scenario: Required artifact was deleted
- **WHEN** reconstruction or preflight runs
- **THEN** integrity fails and release remains blocked
