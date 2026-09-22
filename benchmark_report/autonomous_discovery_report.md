# Autonomous Discovery Report

This report is generated from `benchmarks/trajectories/ettm1_discovery_001/`.

## Question

Can AI Scientist autonomously discover an ML improvement from a research question, without a human selecting a specific method?

## Evidence boundary

The discovery layer uses the configured `claude-opus-4-8` OpenAI-compatible gateway to generate and rank five executable candidates. It selects one candidate per round, creates an existing `ExperimentSpec`, executes it through the existing `ExperimentRunner`, evaluates the result against the fixed DLinear baseline, records a critique, runs a control ablation, and evolves to the next round. If the gateway is unavailable or returns invalid JSON, the run records a deterministic fallback source instead of treating invalid output as a hypothesis.

The ETTm1 runs are bounded CPU fallback experiments. Discovery rounds use validation only; the test split is evaluated once after the final candidate is frozen. A claim is `SUPPORTED` when the frozen final hypothesis passes the declared validation contract and the independent final test confirmation. Earlier failed search hypotheses remain search evidence and do not directly refute the frozen final hypothesis.

## Findings

- Discovery trajectory: three rounds are required and persisted with candidate-generation history, final verification, and a protocol manifest.
- Hypothesis evolution: five candidates are generated per round and ranked by novelty, feasibility, expected impact, and unseen-mutation information gain; one immutable candidate is selected per round.
- Experiment evidence: each selected hypothesis produces an actual `ExperimentSpec`, `ExperimentResult`, metrics file, and evidence record.
- Ablation: each round executes an independent unchanged-baseline `ExperimentSpec` through the existing `ExperimentRunner`.
- Failure cases: the formal PyTorch backend is unavailable in this environment, so the actual trajectory records `backend=numpy_fallback`; contradictory metrics still prevent a positive claim from being promoted.
- Integrity analysis: validation drives iteration, test is held out until freeze, immutable round/parent IDs preserve provenance, and blocked/failed experiments remain explicit in the trajectory.

## Actual ETTm1 run

The command used was:

```text
python -m benchmarks.runners.discovery_runner --benchmark ettm1 --rounds 3 --max-windows 1024
```

Observed result:

- Hypothesis source: round 1 used `deterministic_fallback_after_llm_error`; rounds 2 and 3 used `llm`
- Validation baseline: `mse=0.7518748311673912`
- Round 1 validation: search evidence recorded
- Round 2 validation: search evidence recorded
- Round 3 frozen-candidate validation: `mse=0.6720658897763956`, `SUPPORTED`
- Frozen candidate configuration: `moving_avg=3`
- Frozen candidate test: `mse=1.1516713827713367`
- Frozen control test: `mse=1.2166771283713502`
- Final validation verdict: `SUPPORTED`
- Final test verdict: `SUPPORTED`
- Final claim: `SUPPORTED`, evidence strength `strong`

The three validation experiments and three round-level control ablations completed successfully. The frozen final candidate was evaluated once on test and improved MSE over the independent frozen control by `0.06500574560001349` (`5.34%` relative). The final claim is `SUPPORTED` for this declared bounded NumPy fallback protocol, not an official PyTorch/GPU benchmark claim.

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
