# Hardened Discovery Execution Report

> Historical run record. The live Codex topic executor used by this run was subsequently quarantined and removed from the production CLI after an isolation and bounded-runtime failure. This report is not evidence that unattended execution is currently enabled.

## Codex Scout generation

- Model/executor: `codex-cli` through `CodexExecutor`
- Candidates returned: 26
- Static production lenses: none
- Provenance artifact: `reports/topic_discovery_hardening/codex_candidates_wave1.json`
- Each record contains prompt hash, input signal IDs, literature context IDs, reasoning summary, and generation timestamp.

## Actual wave execution

- Candidates generated: 26
- Candidates cheap-screened: 26
- Candidates deep-audited: 5
- Candidates reaching TOPIC_READY: 0
- Run status: `NO_TOPIC_READY_WITHIN_LIMIT`

The wave did not short-circuit on candidate 1. All candidates were screened, survivors were ranked, and five candidates received distinct Scout and Reviewer retrieval runs. Hardened gates correctly refused to turn unresolved scientific-structure/full-text evidence into TOPIC_READY.

