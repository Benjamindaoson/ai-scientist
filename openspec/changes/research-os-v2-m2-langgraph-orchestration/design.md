## Context

M1 supplies canonical records. M2 stores only workflow references in checkpoints and resolves every gate/result through the repository.

## Decisions

- Use official `PostgresSaver` with a PostgreSQL search path rooted at `orchestration`.
- Create all 38 named nodes; deterministic nodes set execution stage while role nodes remain replaceable work-package boundaries.
- Resolve gate decisions by type from `research.decisions`; a route, not metadata, determines reachability.
- Interrupt human boundaries with LangGraph `interrupt()` and resume with `Command(resume=...)`.
- Before experiment submission, query the persistent experiment spec/run; replay returns the existing run ID.

## Non-Goals

M3 literature, M4 role executors/permissions, and M5 publishing are not implemented here.

## Recovery

Rebuild the graph with the same PostgreSQL checkpointer and `thread_id`; checkpoint state and pending interrupts remain durable.
