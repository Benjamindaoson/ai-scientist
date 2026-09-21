# Benchmark Layer

This directory contains benchmark adapters, baselines, runners, trajectories,
and reports for evaluating the existing AI Scientist research loop.

Benchmark code stays outside `auto_research/src/ai_scientist/`. It calls the
existing `AIScientist` APIs and preserves the research state as external,
inspectable trajectory artifacts.

Implemented benchmark adapters:

- ETTm1 long-horizon forecasting: real downloaded data, DLinear full run,
  PatchTST NumPy fallback run, and a complete AI Scientist trajectory.
- CIFAR-10-C: official archive download path and explicit blocked result when
  the 2.9GB archive is unavailable locally.
- TableShift `diabetes_readmission`: real UCI download, ID/OOD AUROC metrics,
  and explicitly labelled NumPy fallbacks for XGBoost/MLP.

Run the ETTm1 baseline with:

```bash
python -m benchmarks.runners.baseline_runner --benchmark ettm1 --model dlinear
```

Run the existing AI Scientist loop with:

```bash
python -m benchmarks.runners.scientist_runner --run-id ettm1_run_001
```

Every blocked or fallback result is written with `status`, `implementation`,
or `BLOCKED_REASON`; no unavailable model or dataset is presented as official.
