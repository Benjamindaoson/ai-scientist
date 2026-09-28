# Design

The existing PostgreSQL stores remain authoritative. Candidate provenance is persisted in candidate payloads; per-query retrieval evidence is persisted in retrieval-run configuration; structured deep-audit and feasibility evidence stays in novelty and feasibility audit records. No paper or full experiment path is added.

The unsafe repository-adjacent Codex workspaces and live topic executor entry points are removed. Production discovery fails closed unless it receives a provenance-validated recorded candidate file. Incomplete external search short-circuits before full-text hydration or deep review. Reintroducing live model execution requires a separate security design with an enforceable filesystem boundary and bounded runtime; prompt instructions are not a sandbox.
