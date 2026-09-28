# Topic Discovery Hardening Root Cause Report

## Invalid prior readiness

The previous `Measurement audit for Embodied AI` dossier was invalidated. Its candidate came from a static Python tuple, discovery returned the first formal pass, Reviewer external expansion used only the first Crossref query, lexical overlap acted as the final novelty judge, critical answers and significance passes were templates, an HTTP 200 homepage check was treated as data readiness, and compute/time/method values were reused constants.

The dossier, candidate, and lineage are now `NOVELTY_UNCERTAIN`; a separate `FEASIBILITY_UNCERTAIN` audit records the missing data-label and executable-preflight evidence.

## Corrective controls

- Unsafe live topic generation and scientific-gate execution are quarantined. Production discovery accepts only a recorded candidate file with model, prompt hash, signal IDs, literature IDs, reasoning summary, and timestamp.
- The repository-adjacent `.research-os-executor` workspace and the `topic generate-candidates` command were removed. Prompt instructions are not treated as a filesystem sandbox.
- Incomplete required external-source coverage short-circuits to `NOVELTY_UNCERTAIN` before full-text hydration or deep review.
- All candidates are cheap-screened before survivor ranking; at least five ranked survivors receive deep audit.
- Every declared Scout and Reviewer query executes FTS and BGE-M3 dense retrieval and records per-query counts/ranks plus multi-query RRF fusion.
- External expansion probes Crossref, OpenAlex, Semantic Scholar, arXiv, and OpenReview and records failed sources.
- Lexical overlap is cheap-screening only. Final novelty requires section-level structured comparisons and source spans; unavailable full text produces `UNKNOWN` and cannot pass.
- Readiness now requires 15 executed critical answers, eight evidence-backed significance gates, construct coherence, a real target label, loader/metric smoke artifacts, and candidate-specific resource calculations.
- A provisional benchmark cannot act as TOPIC_READY evidence.

## Scope boundary

No killer experiment, paper writing, or full research experiment was started.

The historical discovery executions above are retained only as audit evidence. They do not prove that the current cleaned runtime is ready for unattended execution.

## Database isolation incident

The former Compose `test` service pointed `RESEARCH_DATABASE_URL` at the production
`research_os` database. Tests that intentionally delete table contents therefore removed
the live literature corpus. No recoverable SQL dump or alternate PostgreSQL volume was
found. The incident is not treated as a scientific result or silently repaired in reports;
the production corpus must be re-ingested.

The corrective control is enforced in two places: Compose routes tests to the ephemeral
`postgres-test` service, and pytest aborts at session start unless the database name ends
in `_test`. A destructive regression run was executed while comparing production counts
before and after; the production counts were unchanged.

## Cleanup verification

- Removed 192 lines of unsafe live topic-executor implementation and the production CLI entry point that invoked it.
- Removed seven unreferenced BGE-M3 intermediate JSON reports whose point-in-time counts no longer matched the live database.
- Added fail-closed regression coverage for CLI candidate provenance, removed live executor exports, executor-free deep-audit collection, and incomplete-search short-circuiting.
- `python -m compileall -q auto_research/src`: exit 0 in the project test container.
- `python -m pytest -q`: 167 passed, 0 failed, 14 pre-existing return-value warnings.
- `openspec validate research-os-v2-topic-discovery-hardening --strict`: valid.
- `ai-scientist topic status`: exit 0 without constructing or invoking a Codex topic executor.

