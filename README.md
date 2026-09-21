# AI Scientist

CI gate: compile + autonomous research integration + scientific reasoning regressions.

**Evidence-driven autonomous research system for scientific reasoning, executable experiments, hypothesis evolution, ablation, peer review, rebuttal, and integrity verification.**

This repository keeps the original scientific reasoning layer and extends it with a ScientistTwo-inspired executable research loop. The goal is not to create many agents for their own sake. The system keeps a shared research state and requires claims to be connected to real experiment outputs.

## Core loop

```text
Research Problem
      |
Literature / Phenomenon / Puzzle
      |
Research Question / Theory
      |
Multi-Agent Scientific Debate
      |
ObjectionLedger + FinalResearchCourt
      |
Hypothesis
      |
Experiment Design / Code Generation
      |
Sandboxed Experiment Runtime
      |
Metrics + Logs + Artifacts
      |
Evidence Graph
      |
Hypothesis Evolution
      |
Automatic Ablation
      |
Peer Review
      |
Rebuttal Actions
      |
New Experiment / Revision
      |
Integrity Audit
      |
Meta Review
      |
Reproducible Research Package
```

## What is implemented

### Scientific reasoning layer

- arXiv literature search and paper reading
- research phenomenon and puzzle modeling
- research question generation
- theory / construct / mechanism modeling
- five-role multi-agent scientific debate
- persistent `ObjectionLedger`
- novelty and feasibility gates
- `FinalResearchCourt` with hard scientific constraints
- evidence-based continue / revise / kill decisions

### Experiment runtime

- typed `ExperimentSpec` and `ExperimentResult`
- workspace-scoped command execution
- environment-variable minimization so host secrets are not inherited by generated experiments
- allowlisted executables
- optional Docker backend with networking disabled
- timeout, stdout/stderr, metrics, and artifact capture
- explicit success criteria
- failure taxonomy and bounded recovery
- LLM-backed experiment code/config generation
- LLM-backed code repair without silently changing scientific objectives

### Scientific learning loop

- typed hypothesis lifecycle
- experiment-driven hypothesis evolution
- leave-one-component-out ablation planning
- automatic ablation execution
- claim-evidence-experiment-artifact graph
- supporting and contradicting evidence
- peer-review issue taxonomy
- review issue -> research action routing
- rebuttal experiments and revisions
- meta-review

### Integrity layer

- claim/evidence coverage
- experiment/spec/result alignment
- sandbox/specification compliance
- reference metadata validation
- artifact traceability
- method/code entrypoint alignment
- declared metric/result alignment
- optional score reproduction by re-running an experiment

### Research package

A completed run can export:

```text
research_package/
├── manuscript.md
├── research_state.json
├── evidence_graph.json
├── reviews/
│   ├── reviews.json
│   └── rebuttals.json
└── integrity/
    └── audits.json
```

## Design principles

### One research state

Agents do not own isolated copies of the research context. They transform a shared `ResearchState`:

```text
problem
literature
claims
hypotheses
objections
experiment_specs
experiment_runs
ablations
evidence
evidence_graph
reviews
rebuttals
decisions
integrity_audits
manuscript
```

### Evidence before prose

A scientific claim should be traceable through:

```text
Claim
  <- Evidence
      <- Experiment
          <- Code / Config
          <- Metrics
          <- Artifacts
```

The manuscript is generated from recorded research artifacts; it is not allowed to invent experiment results.

### Review must trigger action

Review is not only text editing. Review categories route to concrete actions:

| Review issue | Action |
| --- | --- |
| Missing experiment | Experiment |
| Weak baseline | Baseline experiment |
| Insufficient ablation | Ablation |
| Novelty threat | Literature search |
| Statistical weakness | Experiment |
| Claim/evidence mismatch | Evidence verification |
| Implementation concern | Engineering repair |
| Writing only | Manuscript revision |

## Quick start: deterministic experiment

```python
import asyncio
import sys
from pathlib import Path

from ai_scientist import AIScientist, ExperimentSpec, Hypothesis

workspace = Path("example_workspace")
workspace.mkdir(exist_ok=True)
(workspace / "run_exp.py").write_text(
    "import json\n"
    "json.dump({'accuracy': 0.91}, open('metrics.json', 'w'))\n"
)

scientist = AIScientist(db_path="research.db")
asyncio.run(scientist.start_research("Does Method A improve accuracy?"))

hypothesis = Hypothesis(
    claim="Method A improves accuracy",
    rationale="Method A should reduce estimation error",
    predicted_effect="accuracy >= 0.90",
    falsification_conditions=["accuracy < 0.90"],
)

spec = ExperimentSpec(
    hypothesis_id=hypothesis.id,
    objective="Test Method A",
    command=[sys.executable, "run_exp.py"],
    workspace=str(workspace),
    success_criteria={"accuracy": {"op": ">=", "value": 0.90}},
)

result = scientist.run_autonomous_research_program(
    hypothesis=hypothesis,
    experiment_spec=spec,
    ablation_components={"module_a": True, "module_b": True},
    output_dir="research_package",
)

print(result["review_cycle"]["meta_review"])
```

## Autonomous code generation

With a real Claude gateway configured:

```bash
export ANTHROPIC_API_KEY=...
```

the system can design and materialize a minimal experiment inside an approved workspace:

```python
result = scientist.design_and_run_autonomous_research(
    hypothesis=hypothesis,
    objective="Test the hypothesis on the declared benchmark",
    workspace="experiment_workspace",
    ablation_components={"component_a": True, "component_b": True},
    output_dir="research_package",
)
```

Generated files are confined to the experiment workspace. Shell-form commands are not used.

## Sandbox model

The default local backend is a **guarded workspace subprocess**, not a virtual-machine security boundary. It prevents path escape, restricts executable entrypoints, avoids inheriting arbitrary host environment variables, and does not use `shell=True`.

For stronger isolation, use the Docker backend. The Docker backend disables networking unless explicitly permitted.

## Main APIs

- `AIScientist.run_full_research_pipeline(...)`
- `AIScientist.run_autonomous_research_program(...)`
- `AIScientist.design_and_run_autonomous_research(...)`
- `AutonomousResearchLoop.run_program(...)`
- `ExperimentEngineer`
- `ExperimentRunner`
- `AblationExecutor`
- `ScientificReviewer`
- `RebuttalPlanner`
- `MetaReviewer`
- `IntegrityAuditor`
- `ResearchPackageWriter`

## Testing

The CI suite compiles the package and runs:

```text
test_autonomous_research_loop.py
test_final_research_court.py
test_v4_integration.py
test_v1_v4_regression.py
```

The autonomous-loop integration test covers:

- workspace path traversal rejection
- host-secret environment isolation
- bounded failure recovery
- experiment -> evidence -> hypothesis evolution
- automatic ablation execution
- review -> rebuttal action -> revision
- integrity audit
- meta-review
- research package export
- result reproduction

## Benchmark v1: does the research loop actually help?

The architecture is now frozen for evaluation. The repository includes a real-ML benchmark under `benchmarks/` with a predeclared **3 problems × 4 system variants × 3 seeds = 36-run** matrix:

- long-horizon forecasting: ETTm1 + Weather with PatchTST;
- corruption robustness: CIFAR-10 → CIFAR-10-C;
- real tabular distribution shift: TableShift `diabetes_readmission`.

System ablations are `full`, `no_hypothesis_evolution`, `no_review_experiment`, and `single_shot`. Final task scores come only from a SHA-256-locked evaluator re-run; exploratory self-reported metrics cannot become the benchmark score. See [benchmarks/README.md](benchmarks/README.md) for setup and execution.

## Relationship to ScientistTwo

The architecture borrows the idea of an experiment-driven research cycle:

```text
Hypothesis -> Experiment -> Evidence -> Critique -> Revision
```

but retains this repository's original differentiators:

- persistent scientific objections
- hard decision gates
- theory / mechanism modeling
- explicit claim-evidence traceability
- integrity checks as first-class state

The project is therefore not a line-by-line reimplementation of ScientistTwo.

## Current boundary

The system can autonomously generate and run code when a real LLM gateway is configured and a workspace is supplied. Scientific validity still depends on the benchmark, data, metrics, controls, and experimental environment supplied to the system. The integrity layer makes those dependencies inspectable rather than treating an LLM-generated conclusion as proof.
