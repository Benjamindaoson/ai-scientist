# Design

PostgreSQL remains the sole scientific source of truth. Opportunity snapshots, signals, candidate lineage, novelty audits, feasibility records, and topic dossiers are stored in the `research` schema. Existing Literature Intelligence supplies versioned papers, chunks, embeddings, citations, and independent retrieval runs. The existing six roles retain their responsibilities; Opportunity Intelligence is a service, not a seventh agent.

The command-line entry points call the same services used by scheduled jobs. Gate decisions are deterministic and conjunctive: no score can compensate for a missing mandatory requirement. Killed candidates remain negative memory and materially equivalent renames are rejected before expensive retrieval.
