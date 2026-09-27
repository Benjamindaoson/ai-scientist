## Context

M0 fixed scientific semantics but the existing runtime still stores authoritative state in SQLite and memory. M1 introduces the shared persistence boundary consumed by later milestones.

## Goals / Non-Goals

**Goals:** complete `research.*` schema, transactional repository, append-only protocol versions, hash-bound approvals, artifact integrity, idempotent SQLite import, and real PostgreSQL integration coverage.

**Non-Goals:** LangGraph orchestration, literature schema, role agents, browser automation, and paper lifecycle.

## Decisions

- Use SQLAlchemy 2 Core metadata as the single schema definition and Alembic for deployed migrations.
- Keep protocol rows append-only after `FROZEN`; revisions create a new row and content hash.
- Bind approvals to `(target_id, target_hash)` and validate the current target hash on use.
- Store artifact bytes on a bounded filesystem root and only URI/hash/metadata in PostgreSQL.
- Record source database identity plus source row identity so repeated SQLite imports are no-ops.

## Risks / Trade-offs

- Local integration requires PostgreSQL with pgvector available; Docker Compose supplies it.
- Legacy SQLite shapes vary; the importer copies recognized entities and records every imported row for safe replay.

## Migration Plan

Apply the Alembic base revision, import legacy SQLite without mutation, run real persistence/restart tests, then switch later Research OS features to the repository.
