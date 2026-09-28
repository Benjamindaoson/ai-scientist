# Research OS v2 Operations

## Local environment

Use the repository-local `.venv` for host commands. PostgreSQL development and integration tests use Docker Compose:

```powershell
docker compose up -d postgres
docker compose --profile test build test
docker compose --profile test run --rm test alembic upgrade head
docker compose --profile test run --rm test python -m pytest -q
```

The Compose `test` service uses the dedicated, ephemeral `postgres-test` service and the
`research_os_test` database. The root pytest guard refuses any database name that does
not end in `_test`; never override this guard to point tests at `research_os`.

The database URL, artifact roots and executor settings belong in environment variables. Copy `.env.example` to a private local file; never commit credentials.

## CLI

The `ai-scientist` entry point provides:

```text
ai-scientist db init
ai-scientist db migrate
ai-scientist db import-sqlite PATH

ai-scientist literature sync
ai-scientist literature ingest-core
ai-scientist literature search QUERY
ai-scientist literature novelty-audit QUERY

ai-scientist research create --name NAME
ai-scientist research run PROJECT_ID
ai-scientist research resume PROJECT_ID THREAD_ID
ai-scientist research status PROJECT_ID
ai-scientist research approve APPROVAL_ID
ai-scientist research reject APPROVAL_ID

ai-scientist export package PROJECT_ID DESTINATION
```

Codex is the default executor for `research run`; mock execution must be requested explicitly. Formal external submission is deliberately absent from the CLI.

## Central configuration

`ResearchOSConfig` reads the PostgreSQL URL, research/literature artifact roots, Codex executable and timeout, optional LaTeX compiler path, browser and RPA flags, paid-API flag, resource budgets, local embedding model, conference years and log level. Paid API, browser automation and RPA are disabled by default.

## Recovery

- LangGraph checkpoints use the official PostgreSQL saver and a stable thread ID.
- On process restart, call `research resume` with the existing thread ID and the human/experiment result payload.
- Experiment submission first loads an existing run for the spec, preventing replay duplication.
- Pending approvals are canonical database rows and survive graph/process restart.
- Artifact integrity is checked by SHA-256 before preflight or package reconstruction.

## Paper and package operations

LaTeX compilation uses `RESEARCH_LATEX_COMPILER` when set, otherwise `tectonic` or `pdflatex` from `PATH`. Submission preflight checks the PDF, source hash, references, blocking findings, current claims, numeric analysis bindings, required sections, anonymity, disclosure, supplement, reproducibility assets and obvious secret patterns. Venue policies are passed as versioned data rather than hard-coded permanent rules.

`export package` writes a content-hashed manifest containing canonical research rows, claim/evidence links, artifacts and integrity status, literature retrieval-run IDs and actual Git commit/branch/remote refs. Reconstruction verifies the manifest and every required artifact.

## Security boundaries

- Experiment child environments use the existing sandbox filtering and executable allowlist; an untrusted same-basename Python path is rejected.
- Codex workspaces are resolved and bounded, and tasks run without full-access approval bypasses.
- Action Broker enforces exact domain allowlists, channel priority, idempotency and human approval for high-risk actions.
- Playwright uses a dedicated per-action profile and stores trace/screenshot/download/session metadata, not cookies or credentials.
- Artifact paths resolve beneath the configured root; SHA-256 detects replacement or deletion.
- Final release requires a database `APPROVED` record bound to the exact manuscript ID and content hash.
