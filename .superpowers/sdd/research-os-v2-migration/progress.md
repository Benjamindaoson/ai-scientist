# Research OS v2 M1-M5 execution ledger

- Binding implementation directive: `C:\Users\Admin（无密码）\.codex\attachments\9c8c5b3f-3e65-4642-840d-5621da4150c6\已粘贴的文本.txt`
- Frozen architecture: `docs/architecture/research-os-v2-migration-spec.md`
- Frozen M0 base: `63479794230119ff2be82cadd0a94669dd251bde`

## Shared interfaces

- M1 owns PostgreSQL scientific records, hash-bound approvals, artifacts, and import idempotency.
- M2 stores only execution references in LangGraph and calls M1 repositories for facts and idempotency.
- M3 adds literature schemas and services on the same PostgreSQL instance; novelty runs are durable records.
- M4 adds role contracts, permission enforcement, executors, and Action Broker on M1-M3 interfaces.
- M5 adds append-only claims/manuscripts, traceability, review routing, approval-gated release, and package export.

## Progress

- [ ] M1 PostgreSQL Research Store
- [ ] M2 LangGraph Research OS
- [ ] M3 Literature Intelligence
- [ ] M4 Six-role runtime and execution
- [ ] M5 Paper lifecycle and legacy retirement
- [ ] Final regression, documentation, architecture diagram, push, remote verification

## Rulings

- None.
