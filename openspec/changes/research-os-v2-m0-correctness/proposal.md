## Why

The legacy research path can currently downgrade a fatal scientific gate, execute experiments after a non-continuation decision, and record inconclusive or failed runs as contradictory evidence. These behaviors violate the frozen Research OS v2 M0 scientific-correctness contract and must be corrected before any architecture migration begins.

## What Changes

- Preserve `KILL` when an open fatal objection also requires human review.
- Make the scientific gate control whether the legacy full pipeline may enter experiment execution.
- Represent experiment outcomes as `SUPPORTED`, `CONTRADICTED`, `INCONCLUSIVE`, or `INVALID`, and keep evidence graph and hypothesis updates consistent.
- Treat execution failures and invalid metrics as invalid evidence rather than scientific contradiction.
- Reject untrusted absolute executables that only match an allowed basename.
- Preserve parsed arXiv authors and categories in `PaperContent`.
- Add deterministic regression coverage for all six M0 defects.

## Capabilities

### New Capabilities

- `m0-scientific-correctness`: Defines the frozen scientific gate, evidence-verdict, sandbox executable, and arXiv metadata requirements required by Research OS v2 M0.

### Modified Capabilities

None.

## Impact

The change is limited to the existing court, orchestrator, experiment evaluation, evidence graph update, sandbox policy, arXiv parser, and their tests. It adds no database, orchestration framework, agents, browser automation, benchmark redesign, threshold change, or legacy-file deletion.
