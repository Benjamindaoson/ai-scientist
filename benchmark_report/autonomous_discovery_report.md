# Autonomous Discovery Report

This report is generated from `benchmarks/trajectories/ettm1_discovery_001/`.

## Question

Can AI Scientist autonomously discover an ML improvement from a research question, without a human selecting a specific method?

## Evidence boundary

The discovery layer uses the configured `claude-opus-4-8` OpenAI-compatible gateway to generate and rank five executable candidates. It selects one candidate per round, creates an existing `ExperimentSpec`, executes it through the existing `ExperimentRunner`, evaluates the result against the fixed DLinear baseline, records a critique, runs a control ablation, and evolves to the next round. If the gateway is unavailable or returns invalid JSON, the run records a deterministic fallback source instead of treating invalid output as a hypothesis.

The ETTm1 runs are bounded CPU fallback experiments. A claim is `SUPPORTED` only if every executed round improves the baseline MSE; mixed or contradictory evidence is `INCONCLUSIVE`, and no improvement is `REJECTED`.

## Findings

- Discovery trajectory: three rounds are required and persisted as eleven JSON artifacts.
- Hypothesis evolution: five candidates are generated and ranked by novelty, feasibility, and expected impact; one is selected per round.
- Experiment evidence: each selected hypothesis produces an actual `ExperimentSpec`, `ExperimentResult`, metrics file, and evidence record.
- Ablation: each round records an executed unchanged-baseline control when the experiment succeeds.
- Failure cases: bounded NumPy fallback and any contradictory metric prevent a positive claim from being promoted.
- Integrity analysis: no test split is used for candidate selection, and blocked/failed experiments remain explicit in the trajectory.

## Actual ETTm1 run

The command used was:

```text
python -m benchmarks.runners.discovery_runner --benchmark ettm1 --rounds 3 --max-windows 1024
```

Observed result:

- Hypothesis source: `llm`
- Round 1: `moving_avg=37`, `mse=0.588135609272831`, `REJECTED`
- Round 2: `moving_avg=13`, `mse=0.588135609272831`, `REJECTED`
- Round 3: `moving_avg=3`, `mse=0.588135609272831`, `REJECTED`
- Fixed bounded DLinear control: `mse=0.588135609272831`
- Final claim: `REJECTED`, confidence `0.65`

The three experiments completed successfully after LLM-generated hypothesis selection, but none improved the matched control. The negative result is retained as evidence rather than converted into an improvement claim.

## Actual ablation

`results/ablations/discovery_summary.json` contains executed records for:

| Mode | Experiments | Hypotheses | Valid claims | Trajectory completeness |
|---|---:|---:|---:|---:|
| Full | 3 | 5 | 0 | 1.0 |
| Single Shot | 1 | 5 | 0 | 1.0 |
| No Evolution | 3 | 5 | 0 | 1.0 |
| No Review | 3 | 5 | 0 | 1.0 |
| No Integrity | 3 | 5 | 0 | 1.0 |

The final claim in `final_claim.json` is the authoritative result. This report deliberately does not convert a fallback or mixed result into a success claim.
