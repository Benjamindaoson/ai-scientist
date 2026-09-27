## Why

The canonical PostgreSQL store exists, but legacy `AIScientist` still owns orchestration. M2 makes scientific decisions executable through one durable LangGraph state machine.

## What Changes

- Add the compact ID-only `ResearchExecutionState`, complete node catalogue, conditional routes, and deterministic policy engine.
- Use the official PostgreSQL LangGraph checkpointer for restart-safe interrupts and replay.
- Add an idempotent Experiment Runtime adapter that resolves existing runs before side effects.
- Make `AIScientist` a compatibility facade for the new graph without deleting legacy APIs.

## Capabilities

### New Capabilities

- `langgraph-research-os`: Durable Research OS state transitions, executable gates, interrupts, and experiment replay protection.

## Impact

LangGraph becomes the production orchestration path. Scientific facts remain in PostgreSQL and experiment execution remains an external side effect.
