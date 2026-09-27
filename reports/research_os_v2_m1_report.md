# Research OS v2 M1 Report

## 1. Scope

This milestone implements M1 only: the PostgreSQL canonical research store, migrations, versioning rules, artifact registration, legacy import, objection compatibility, and persistence verification. LangGraph, literature intelligence, six-role execution, and paper lifecycle remain subsequent milestones.

## 2. Architecture Implemented

- PostgreSQL 17 with pgvector through `compose.yaml`.
- SQLAlchemy 2 Core schema and transactional repository under `ai_scientist.research_store`.
- Alembic base revision `20260928_0001`.
- Twenty-two required `research.*` tables plus the internal `research.legacy_imports` idempotency ledger.
- Append-only frozen protocol revisions with canonical SHA-256 content hashes.
- Approval validation bound to exact target ID and target hash.
- Immutable hypothesis identity enforcement.
- Five-valued claim/evidence relation constraint: `SUPPORTS`, `CONTRADICTS`, `QUALIFIES`, `INCONCLUSIVE`, `INVALID`.
- Filesystem Artifact Store with bounded paths and database URI/SHA-256 metadata.
- Read-only, idempotent SQLite importer and PostgreSQL adapter for the legacy `ObjectionLedger`.

## 3. Files Changed

| Path | Change | Reason |
| --- | --- | --- |
| `pyproject.toml` | Added M1 dependencies and CLI entry point | Install the required PostgreSQL persistence stack |
| `.env.example` | Added non-secret database/artifact configuration | Document runtime configuration |
| `compose.yaml`, `Dockerfile.test` | Added pgvector PostgreSQL and repeatable integration-test service | Exercise a real database, including on this Docker Desktop host |
| `alembic.ini`, `research_store/migrations/*` | Added Alembic environment and base revision | Version the canonical schema |
| `research_store/models.py` | Defined the complete research schema and constraints | Canonical scientific records |
| `research_store/db.py` | Added centralized connection/bootstrap | One database configuration boundary |
| `research_store/repository.py` | Added transactional persistence, versioning, provenance, approvals, and idempotency | Enforce scientific storage contracts |
| `research_store/artifact_store.py` | Added immutable, hash-verified external artifact storage | Keep large outputs outside PostgreSQL |
| `research_store/sqlite_import.py` | Added read-only idempotent legacy import | Migrate without damaging SQLite |
| `research_store/objections.py` | Added legacy ledger compatibility over PostgreSQL | Preserve objection semantics while changing the source of truth |
| `research_store/cli.py` | Added `db init`, `db migrate`, and `db import-sqlite` commands | Provide developer operations |
| `tests/test_m1_research_store.py` | Added seven real PostgreSQL tests | Prove M1 acceptance behavior |
| `openspec/changes/research-os-v2-m1-research-store/*` | Added and completed M1 OpenSpec | Auditable milestone contract |

## 4. Acceptance Evidence

- A project and the complete question → hypothesis → frozen protocol → experiment spec/run → analysis → evidence → claim chain remained queryable through a newly created engine after disposal of the original engine.
- A direct mutation of a frozen protocol raised `FrozenRecordError`.
- Protocol v2 retained v1 and produced a different content hash.
- A v1 approval authorized only v1's ID/hash and rejected v2.
- An objection and experiment/evidence relationship survived a repository restart.
- Importing one SQLite project twice produced `1` then `0` imported projects, with the source file SHA-256 unchanged.
- Artifact tampering changed `verify_hash()` from true to false.
- A fresh Alembic migration database contained 23 `research` tables and the `vector` extension was present.

## 5. Tests and Commands

| Command | Exit | Result |
| --- | ---: | --- |
| `docker compose --profile test run --rm test python -m pytest -q tests/test_m1_research_store.py` | 0 | 7 passed |
| fresh `research_os_migration` database + `alembic upgrade head` | 0 | revision applied; 23 research tables |
| `python -m compileall -q auto_research/src` | 0 | passed |
| `docker compose --profile test run --rm test python -m pytest -q` | 0 | 64 passed, 0 failed, 0 skipped, 14 pre-existing return-value warnings |
| `python test_autonomous_research_loop.py` in test service | 0 | integration tests passed |
| `python test_v4_integration.py` in test service | 0 | 6/6 passed |
| `python test_v1_v4_regression.py` in test service | 0 | 6/6 passed |
| discovery/planner/hypothesis pytest selection | 0 | 4 passed |
| `openspec validate research-os-v2-m1-research-store` | 0 | valid |
| `git diff --check` | 0 | passed |
| `ai-scientist db init` in test service | 0 | passed |

## 6. Dependency Versions

- Alembic 1.20.0
- pgvector Python 0.5.0; PostgreSQL vector extension installed from `pgvector/pgvector:pg17`
- psycopg 3.3.6
- Pydantic 2.13.5
- SQLAlchemy 2.1.1

## 7. Regression Status

All M0, legacy, complete pytest, and selected discovery regression checks passed. Scientific thresholds, benchmark fixtures, and frozen trajectories were not changed.

## 8. Deviations From Specification

NONE.

The local Docker Desktop instance did not expose the declared host port even though the Compose port binding was present. Real PostgreSQL integration therefore ran through the Compose test service on the same Docker network. This changes neither the committed development configuration nor the database implementation.

## 9. Remaining Blockers

NONE for M1.

## 10. M1 Verdict

PASS
