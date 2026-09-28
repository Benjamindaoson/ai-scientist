# Topic Discovery Hardening Root Cause Report

## Invalid prior readiness

The previous `Measurement audit for Embodied AI` dossier was invalidated. Its candidate came from a static Python tuple, discovery returned the first formal pass, Reviewer external expansion used only the first Crossref query, lexical overlap acted as the final novelty judge, critical answers and significance passes were templates, an HTTP 200 homepage check was treated as data readiness, and compute/time/method values were reused constants.

The dossier, candidate, and lineage are now `NOVELTY_UNCERTAIN`; a separate `FEASIBILITY_UNCERTAIN` audit records the missing data-label and executable-preflight evidence.

## Corrective controls

- Production candidate generation requires a real `AgentExecutor` and persists model, prompt hash, signal IDs, literature IDs, reasoning summary, and timestamp.
- All candidates are cheap-screened before survivor ranking; at least five ranked survivors receive deep audit.
- Every declared Scout and Reviewer query executes FTS and BGE-M3 dense retrieval and records per-query counts/ranks plus multi-query RRF fusion.
- External expansion probes Crossref, OpenAlex, Semantic Scholar, arXiv, and OpenReview and records failed sources.
- Lexical overlap is cheap-screening only. Final novelty requires section-level structured comparisons and source spans; unavailable full text produces `UNKNOWN` and cannot pass.
- Readiness now requires 15 executed critical answers, eight evidence-backed significance gates, construct coherence, a real target label, loader/metric smoke artifacts, and candidate-specific resource calculations.
- A provisional benchmark cannot act as TOPIC_READY evidence.

## Scope boundary

No killer experiment, paper writing, or full research experiment was started.

