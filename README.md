# AI Scientist

An evidence-driven autonomous research system that connects scientific reasoning to executable experiments, hypothesis evolution, ablations, peer review, rebuttal experiments, meta review, and integrity auditing.

## What it does

The system preserves the original scientific reasoning layer:

```text
Literature Search
→ Phenomenon / Puzzle
→ Research Question
→ Theory Engine
→ Multi-Agent Debate
→ ObjectionLedger
→ Novelty / Feasibility Gates
→ FinalResearchCourt
```

and adds an executable autonomous research loop:

```text
Hypothesis
→ Structured ExperimentSpec
→ Policy-checked ExperimentRunner
→ Metrics / Logs / Artifacts
→ Evidence
→ Hypothesis Evolution
→ Automatic Ablation Execution
→ Manuscript Draft
→ Peer Review
→ Rebuttal Experiments
→ Manuscript Revision
→ Meta Review
→ Integrity Audit
→ READY / REVISE
```

## Core architecture

- **ResearchState** — one shared state for hypotheses, experiments, evidence, reviews, rebuttals, decisions and manuscript artifacts.
- **Experiment Runtime** — real subprocess execution with bounded timeout, structured metrics, logs, artifacts and deterministic recovery.
- **SandboxPolicy** — rejects shell execution by default, checks executable allow-list and enforces bounded runtime. This is a process policy, not container/VM isolation.
- **CodeEngineeringAgent + WorkspaceEditor** — structured file-change plans, with path traversal prevention.
- **HypothesisEvolver** — evolves a hypothesis from experiment outcomes and unresolved objections.
- **AblationPlanner + AblationExecutor** — generates interpretable component removals and executes them through the same experiment runtime.
- **EvidenceGraph** — Claim ↔ Evidence ↔ Experiment traceability.
- **PeerReviewer / RebuttalPlanner / MetaReviewer** — turns review criticism into follow-up actions and supplementary experiments.
- **ManuscriptWriter** — drafts from structured state and recorded evidence rather than free-form memory.
- **IntegrityAuditor** — checks recovered execution, metrics, evidence references, claim-evidence traceability and manuscript presence.

## Main API

```python
import asyncio
import sys

from ai_scientist import AIScientist, ExperimentSpec, Hypothesis, MockGateway

scientist = AIScientist(db_path="scientist.db", gateway=MockGateway())
asyncio.run(scientist.start_research("Does Method A improve accuracy?"))

hypothesis = Hypothesis(
    claim="Method A improves predictive accuracy",
    rationale="Its components address complementary error sources.",
    predicted_effect="accuracy >= 0.85",
    falsification_conditions=["accuracy < 0.85"],
)

spec = ExperimentSpec(
    hypothesis_id=hypothesis.id,
    objective="Evaluate Method A",
    command=[sys.executable, "experiment.py"],
    workspace="./research_workspace",
    success_criteria={"accuracy": {"op": ">=", "value": 0.85}},
)

result = scientist.run_complete_autonomous_cycle(
    hypothesis=hypothesis,
    experiment_spec=spec,
    ablation_components={
        "retrieval": True,
        "reranker": True,
        "verifier": True,
    },
)
```

An executable experiment should write a JSON metrics file. The runner exposes its requested file name through:

```text
AI_SCIENTIST_METRICS_FILE
```

Ablation runs additionally receive:

```text
AI_SCIENTIST_ABLATION
```

as a JSON configuration.

## Scientific review loop

Review issues are typed rather than treated as prose-only comments:

```text
MISSING_EXPERIMENT      → EXPERIMENT
WEAK_BASELINE           → BASELINE_EXPERIMENT
INSUFFICIENT_ABLATION   → ABLATION
NOVELTY_THREAT          → LITERATURE_SEARCH
STATISTICAL_WEAKNESS    → EXPERIMENT
CLAIM_EVIDENCE_MISMATCH → EVIDENCE_VERIFICATION
IMPLEMENTATION_CONCERN  → ENGINEERING_REPAIR
WRITING_ONLY            → MANUSCRIPT_REVISION
```

Supplementary experiments can be supplied to the rebuttal loop, executed, converted into evidence, and used to regenerate the manuscript before meta review.

## Verification

The repository includes deterministic tests that do not require external LLM APIs:

```bash
PYTHONPATH=auto_research/src python test_autonomous_research_loop.py
PYTHONPATH=auto_research/src python test_autonomous_research_complete.py
```

The complete suite verifies:

- experiment → evidence → hypothesis evolution;
- automatic ablation planning and execution;
- failure → bounded retry → recovery;
- review → supplementary experiment → meta review;
- claim-evidence graph creation;
- manuscript generation;
- integrity auditing;
- workspace path traversal rejection;
- shell execution rejection by default.

GitHub Actions runs these checks on pull requests and the main branch.

## Important boundary

The built-in sandbox is intentionally described as a **policy-checked local process runner**, not a hardened security isolation boundary. For untrusted generated code, run the experiment workspace inside a container, VM, or other externally isolated environment.


## Status

The autonomous research loop is validated by the repository CI workflow on pull requests.
