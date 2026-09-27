## Why

Research OS v2 requires one durable, versioned scientific source of truth before orchestration can migrate away from legacy SQLite and in-memory state.

## What Changes

- Add PostgreSQL configuration, SQLAlchemy models, Alembic migrations, and repository/services for the complete `research` schema.
- Enforce frozen protocol immutability, stable content hashing, immutable hypothesis identity, and approvals bound to target hashes.
- Add an immutable file Artifact Store and a non-destructive, idempotent SQLite importer.
- Persist objections in PostgreSQL while retaining the legacy SQLite reader for compatibility.
- Add real PostgreSQL restart and relation tests.

## Capabilities

### New Capabilities

- `research-store`: Canonical PostgreSQL records for projects, scientific entities, governance, experiments, evidence, artifacts, and manuscript versions.

## Impact

New production Research OS features use PostgreSQL. Legacy SQLite remains read/import-only; M2-M5 are not implemented by this change.
