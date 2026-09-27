# M5 Full Paper Lifecycle

## Why

Research OS v2 needs a traceable path from corrected formal analysis to claims, manuscript, independent review, release approval, package reconstruction, and archive/follow-up.

## What Changes

- Freeze/version claims and invalidate dependent claims/manuscripts after analysis correction.
- Generate LaTeX manuscripts whose numbers are read from AnalysisRun records.
- Add typed review routing, rebuttal responsibility, and independent novelty callbacks.
- Add submission preflight and hash-bound human release approval.
- Export and reconstruct a complete DB/artifact/Git research package.
- Add centralized configuration, operational CLI coverage, failure injection, final architecture docs, and legacy retirement evidence.

## Scope

M5 completes the frozen migration. It does not add Neo4j, a second orchestrator, paid-by-default APIs, or automated external submission.
