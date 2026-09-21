# AI Scientist

Canonical implementation: `auto_research/src/ai_scientist`.

The v4 flow is the single integrated path: persistent objection ledger,
multi-agent debate, hard-constraint research court, evidence tracking, and
decision graph output.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
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
