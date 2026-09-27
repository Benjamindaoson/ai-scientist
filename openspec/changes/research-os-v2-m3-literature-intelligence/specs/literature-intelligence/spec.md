## ADDED Requirements

### Requirement: Literature identity is version- and appearance-aware
Exact identifiers MUST deduplicate papers while versions and venue appearances remain separate records; fuzzy similarity MUST NOT silently merge.

#### Scenario: Same arXiv identifier arrives twice
- **WHEN** two source records contain the same normalized arXiv ID
- **THEN** one paper exists and ingestion remains idempotent

### Requirement: Core membership requires official evidence
`is_core_accepted` MUST be set only on a venue appearance with official acceptance provenance and a configured venue/year/track policy.

#### Scenario: arXiv claims conference acceptance
- **WHEN** only an arXiv record claims acceptance
- **THEN** no Core accepted appearance is created

### Requirement: Hybrid retrieval is auditable
Formal searches MUST persist queries, variants, filters, configuration, candidate ranks, deep-read set, model metadata, and exact source chunks.

#### Scenario: Scout and Reviewer audit the same idea
- **WHEN** both roles run formal novelty search
- **THEN** they receive distinct retrieval-run IDs and inspectable result provenance

### Requirement: Full text and embeddings are content-addressed
Section chunks MUST retain version/section/page/character provenance, and embeddings MUST be recomputed only when content or model changes.

#### Scenario: One chunk changes
- **WHEN** its content hash changes
- **THEN** only that chunk/model embedding identity changes

### Requirement: Citation ingestion is idempotent
Repeated citation facts MUST create one edge and retain source provenance.

#### Scenario: Citation source repeats
- **WHEN** the same source imports the same citing/cited pair twice
- **THEN** one citation edge and one source record exist
