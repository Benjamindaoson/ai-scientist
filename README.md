# AI Scientist

**Autonomous scientific reasoning and research workflow prototype**

This repository is the current canonical implementation for the AI Scientist
workstream. It contains the existing `auto_research` runtime, literature
components, multi-agent scientific debate, theory/research-court logic,
persistent research data structures, and the historical validation suite.

## Current repository boundary

The implementation currently includes:

- research-domain models and persistent research state;
- literature search, reading, and validation components;
- orchestration for multi-step research workflows;
- multi-agent debate and objection tracking;
- theory-engine and final research-court components;
- regression and scientific-validation scripts accumulated across earlier
  iterations.

The repository should be treated as an evolving research system rather than a
claim of fully autonomous science.

## Canonical status

`Benjamindaoson/ai-scientist` is the active repository for this workstream.

The separate `Benjamindaoson/scientific-agent` repository was an empty
placeholder and is safe to delete.

## Next architecture direction

Future work should extend the existing Scientific Reasoning Layer with a
controlled experiment runtime:

```text
Research Question
      ↓
Scientific Reasoning Layer
      ↓
Hypothesis Evolution
      ↓
Experiment Runtime
      ↓
Ablation / Review
      ↓
Experiment
      ↓
Revision
```

New capabilities should be added here instead of creating another AI Scientist
repository.
