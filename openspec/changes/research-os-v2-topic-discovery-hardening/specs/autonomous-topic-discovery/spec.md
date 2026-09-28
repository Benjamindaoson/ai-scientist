# Autonomous Topic Discovery Hardening

## Requirements

### Requirement: Production candidates are executor generated
Production discovery SHALL reject static candidate templates and persist model, prompt hash, input signals, literature context, reasoning summary, and generation timestamp.

### Requirement: Every wave is compared
The system SHALL cheap-screen every candidate, rank all survivors, deep-audit at least five survivors when available, and select only after the audited survivor set is complete.

### Requirement: Novelty evidence is executable and structured
Scout and Reviewer SHALL use distinct retrieval runs whose declared queries are all executed. Final novelty decisions SHALL require source spans and section-level scientific overlap judgments; abstract-only evidence SHALL remain uncertain.

### Requirement: Readiness is conjunctive and evidence backed
Critical questions, eight significance gates, coherence, data labels, loader smoke, engineering smoke, and candidate-specific resource calculations SHALL all pass without unresolved blockers before TOPIC_READY.

### Requirement: Corpus and benchmark claims are qualified
Venue-year coverage SHALL be COMPLETE, PARTIAL, or UNAVAILABLE. Self-retrieval benchmarks SHALL be rejected; non-human-adjudicated v2 benchmarks SHALL be labeled PROVISIONAL and excluded as TOPIC_READY evidence.
