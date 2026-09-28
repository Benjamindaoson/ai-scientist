# Autonomous Topic Discovery Requirements

## ADDED Requirements

### Requirement: Opportunity intelligence is provenance-backed

The system SHALL prefer official sources, store content-addressed snapshots, preserve raw and normalized deadline data, and retain closed opportunities only as non-novelty research signals.

#### Scenario: An official deadline changes

- **WHEN** a later official-source fetch has different deadline content
- **THEN** the current opportunity is updated and both source snapshots remain queryable

#### Scenario: An official source is unavailable

- **WHEN** HTTP and approved browser fallback both fail
- **THEN** the system marks the record stale or unknown without fabricating a deadline

### Requirement: Discovery continues across killed candidates and waves

Each wave SHALL generate at least twenty structured candidates, run independent Scout and Reviewer searches, preserve killed-idea memory, and continue with a different strategy after a failed wave.

#### Scenario: A source-backed prior covers a renamed idea

- **WHEN** the prior covers both the scientific question and core claim despite different wording
- **THEN** the candidate is killed, the killing evidence is recorded, and the loop continues

#### Scenario: Search coverage is insufficient

- **WHEN** the novelty decision is `NOVELTY_UNCERTAIN`
- **THEN** the Reviewer expands sources, adjacent fields, exact claims, and evidence-graph relations before deciding

### Requirement: Topic readiness is conjunctive

The system SHALL emit `TOPIC_READY` only when question, claim, independent novelty audits, search coverage, significance, critical review, data, method, engineering, compute, time, venue/deadline fit, killer experiment, reviewer risks, and fatal-objection clearance all pass.

#### Scenario: Any mandatory gate is missing

- **WHEN** at least one mandatory gate lacks valid evidence
- **THEN** the candidate remains blocked and no Topic Dossier is finalized

#### Scenario: Every mandatory gate passes

- **WHEN** all mandatory gates pass with distinct Scout and Reviewer retrieval-run IDs
- **THEN** the system records `TOPIC_READY` and projects the canonical Topic Dossier

### Requirement: Topic selection stops before paper execution

The topic-discovery phase SHALL produce a Topic Dossier without starting full experiments, manuscript writing, or submission.

#### Scenario: A topic becomes ready

- **WHEN** the final topic review returns `TOPIC_READY`
- **THEN** the workflow writes the Topic Dossier and terminates before paper or full-experiment nodes
