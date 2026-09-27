## 1. PostgreSQL foundation

- [x] 1.1 Add dependencies, configuration, Docker Compose, SQLAlchemy metadata, and Alembic base migration.
- [x] 1.2 Implement all required `research.*` tables and constraints.

## 2. Scientific services

- [x] 2.1 Implement project, question, immutable hypothesis/protocol, experiment, analysis, evidence, claim, objection, decision, approval, artifact, and manuscript operations.
- [x] 2.2 Enforce frozen protocol and hash-bound approval rules.
- [x] 2.3 Add bounded immutable Artifact Store.

## 3. Migration and compatibility

- [x] 3.1 Add idempotent, non-destructive SQLite import and PostgreSQL objection persistence adapter.

## 4. Verification and reporting

- [x] 4.1 Run real PostgreSQL M1 integration tests, compileall, full pytest, legacy scripts, benchmark tests, diff checks, and OpenSpec validation.
- [x] 4.2 Generate the M1 report and milestone commit.
