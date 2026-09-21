# ETTm1 Benchmark Report

## Run

- Benchmark: ETTm1
- Baseline model: DLinear
- Seed: 1
- Forecast horizon: 96
- Train windows: 34369
- Test windows: 23409

## Baseline

| Metric | Value |
| --- | ---: |
| MSE | 0.401616309885 |
| MAE | 0.404111380558 |

## AI Scientist trajectory

- Experiment status: `SUCCEEDED`
- Return code: `0`
- Integrity passed: `True`
- Meta-review decision: `REVISE`
- Major issues: `1`

The complete hypothesis, experiment, evidence, review, rebuttal, and decision
records are stored in the trajectory directory beside this report.

## Known issues

- PyTorch could not be installed in the project environment; the DLinear and
  PatchTST adapters use the documented NumPy fallback. PatchTST was evaluated
  with the bounded `--max-windows 4096` fallback because the full run exceeded
  the available execution resources.
- The existing reviewer returned `REVISE`; this is preserved as evidence and
  is not promoted to a successful research conclusion.

## Next benchmark

CIFAR10-C
