# AI Scientist

**Autonomous scientific reasoning and research workflow prototype**

This repository is the canonical implementation for the AI Scientist
workstream. The runtime lives in `auto_research/src/ai_scientist` and combines
literature analysis, multi-agent debate, persistent objection tracking,
theory development, and the hard-constraint research court.

The repository is an evolving research system, not a claim of fully autonomous
science.

## Run locally

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install -e .
python run.py
```

The default gateway is a mock gateway. Configure `ANTHROPIC_API_KEY` or
`CLAUDE_RELAY_URL` only when a real model run is intended.

## Verification

```powershell
$env:PYTHONIOENCODING = "utf-8"
python test_v1_v4_regression.py
python test_v4_integration.py
python test_comprehensive.py
```

## Current repository boundary

The implementation includes research-domain models and persistent research
state, literature search/reading/validation, orchestration, multi-agent
debate, objection tracking, theory-engine components, and research-court
decisions. Generated databases and research outputs are intentionally excluded
from Git.

Future work can extend the reasoning layer with a controlled experiment runtime:

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
Revision
```
