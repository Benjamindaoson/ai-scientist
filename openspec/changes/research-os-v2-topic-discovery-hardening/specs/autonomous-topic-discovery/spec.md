# Autonomous Topic Discovery Hardening

## MODIFIED Requirements

### Requirement: Production candidates are executor generated
Production discovery SHALL reject static candidate templates and persist model, prompt hash, input signals, literature context, reasoning summary, and generation timestamp.

#### Scenario: Production generation is requested
- **WHEN** a discovery wave starts
- **THEN** an executor-backed Scout generates candidates and every persisted candidate has complete provenance

### Requirement: Every wave is compared
The system SHALL cheap-screen every candidate, rank all survivors, deep-audit at least five survivors when available, and select only after the audited survivor set is complete.

#### Scenario: First candidate passes
- **WHEN** the first candidate satisfies formal gates
- **THEN** the system still screens the full wave and audits the ranked top survivor set before selection

### Requirement: Novelty evidence is executable and structured
Scout and Reviewer SHALL use distinct retrieval runs whose declared queries are all executed. Final novelty decisions SHALL require source spans and section-level scientific overlap judgments; abstract-only evidence SHALL remain uncertain.

#### Scenario: Dangerous prior has only an abstract
- **WHEN** a prior lacks legally available section-level full text
- **THEN** its overlap fields remain UNKNOWN and novelty cannot pass on that prior

### Requirement: Readiness is conjunctive and evidence backed
Critical questions, eight significance gates, coherence, data labels, loader smoke, engineering smoke, and candidate-specific resource calculations SHALL all pass without unresolved blockers before TOPIC_READY.

#### Scenario: Target label is missing
- **WHEN** the declared dataset lacks the scientific outcome variable and no reviewed derived label exists
- **THEN** readiness is DATA_LABEL_GAP and TOPIC_READY is forbidden

### Requirement: Corpus and benchmark claims are qualified
Venue-year coverage SHALL be COMPLETE, PARTIAL, or UNAVAILABLE. Self-retrieval benchmarks SHALL be rejected; non-human-adjudicated v2 benchmarks SHALL be labeled PROVISIONAL and excluded as TOPIC_READY evidence.

#### Scenario: Benchmark copies target language
- **WHEN** a benchmark query substantially copies its designated paper title or abstract
- **THEN** benchmark construction fails as self-retrieval
