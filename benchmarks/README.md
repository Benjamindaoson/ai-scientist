# AI Scientist Benchmark v1

Benchmark v1 freezes the AI Scientist architecture and evaluates whether the research loop creates **valid empirical discoveries**, rather than adding more agents.

## Fixed matrix

The predeclared matrix is:

- 3 real ML research problems
- 4 system variants
- 3 seeds

Total: **36 autonomous research runs**, excluding the frozen baseline runs.

System variants:

1. `full`
2. `no_hypothesis_evolution`
3. `no_review_experiment`
4. `single_shot`

Generate the matrix without running expensive experiments:

```bash
PYTHONPATH=auto_research/src:. python -m benchmarks.matrix
```

## Problems

### 1. Long-horizon forecasting

Primary metric: average MSE, lower is better.

Protocol:
- ETTm1 + Weather
- horizons 96 / 192 / 336 / 720
- fixed 30 training epochs
- DLinear frozen baseline
- PatchTST candidate starting point
- checkpoint-size proxy may not increase by more than 10%

Upstream implementation:
https://github.com/yuqinie98/PatchTST

Prepare a clean checkout containing:

```text
PatchTST_supervised/run_longExp.py
PatchTST_supervised/dataset/ETTm1.csv
PatchTST_supervised/dataset/weather.csv
```

The official PatchTST repository documents both the supervised scripts and these datasets.

### 2. CIFAR-10 corruption robustness

Primary metric: mean CIFAR-10-C corruption accuracy, higher is better.

Constraints:
- train only on clean CIFAR-10
- evaluate on the pre-generated CIFAR-10-C files
- clean accuracy may fall by at most 0.5 percentage points
- 20 fixed training epochs

Reference benchmark:
https://github.com/hendrycks/robustness

Prepare:

```text
workspace/
├── data/             # torchvision CIFAR-10 files
└── CIFAR-10-C/
    ├── labels.npy
    ├── gaussian_noise.npy
    └── ...
```

The locked evaluator rejects a `candidate.py` that directly references CIFAR-10-C paths/labels.

### 3. TableShift hospital readmission

Primary metric: TableShift `diabetes_readmission` OOD accuracy, higher is better.

Constraint:
- ID accuracy may fall by at most 0.5 percentage points

Upstream:
https://github.com/mlfoundations/tableshift

TableShift exposes fixed `train`, `id_test`, and `ood_test` splits. Cache the public
`diabetes_readmission` data before autonomous execution.

The locked evaluator rejects a `candidate.py` that accesses TableShift or `ood_test` directly;
candidate code may provide only a classifier factory.

## Locked evaluator rule

Every problem materializes:

```text
_benchmark_locked_runner.py
```

and stores its SHA-256 in the `ExperimentSpec`.

The research system may explore, generate code, evolve hypotheses, run ablations, and answer review comments.
However, the final benchmark score is produced by a **fresh locked-evaluator execution**.

If the evaluator hash changes:

```text
valid_discovery = false
protocol violation = locked evaluator hash mismatch
```

This prevents an agent from improving its score by redefining the metric.

## Baselines

Generate baseline results in a clean workspace:

```bash
PYTHONPATH=auto_research/src:. python benchmarks/run_baseline.py \
  --problem robustness \
  --workspace /path/to/fresh/baseline_workspace \
  --seed 2021 \
  --output benchmark_results/baselines/robustness_2021.json
```

Use a separate fresh workspace for each candidate run. Do not reuse the baseline workspace.

## Run one system cell

```bash
PYTHONPATH=auto_research/src:. python benchmarks/run_one.py \
  --problem robustness \
  --variant full \
  --workspace /path/to/fresh/candidate_workspace \
  --baseline-json benchmark_results/baselines/robustness_2021.json \
  --seed 2021 \
  --gateway anthropic \
  --output benchmark_results/runs/robustness_full_2021.json
```

For a no-API structural run, use `--gateway mock`.

## Aggregate

```bash
PYTHONPATH=auto_research/src:. python benchmarks/report.py benchmark_results/runs \
  --output benchmark_results/benchmark_summary.json
```

The summary reports, per problem and system variant:

- Valid Discovery Rate
- mean task improvement
- experiment count
- compute hours
- research efficiency
- integrity pass rate

Each raw record also contains:

- Hypothesis Evolution Gain
- review issue/action counts
- Review Resolution Rate
- constraint violations
- final meta-review decision

## Scientific interpretation

A result is **not** a valid discovery merely because the task metric improves.

A run is valid only when:

```text
task improvement > 0
AND problem constraints pass
AND locked evaluator is unchanged
AND integrity audit passes
```

The expensive 36-run matrix is intentionally not executed in GitHub CI. CI runs deterministic smoke tests for
the benchmark harness, matrix, variant routing, locked evaluator behavior, and aggregation.
