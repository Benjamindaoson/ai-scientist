# Evidence-Driven Autonomous AI Scientist Benchmark Platform

## Question

Does an evidence-driven autonomous research loop improve ML discovery?

## Results

| Benchmark | Status | Primary result | Implementation |
| --- | --- | --- | --- |
| ETTm1 | SUCCEEDED | DLinear MSE=0.401616, MAE=0.404111 | NumPy fallback |
| CIFAR-10-C | BLOCKED | CIFAR-10-C is not downloaded: data\cifar10c\CIFAR-10-C.tar | fallback |
| TableShift diabetes_readmission | SUCCEEDED | XGBoost OOD AUROC=0.6484597263048694 | NumPy fallback |

## Trajectories

ETTm1 has a complete AI Scientist trajectory with hypothesis, experiment, evidence graph, reviews, integrity audit, and meta-review. CIFAR-10-C and TableShift have auditable benchmark trajectory records; CIFAR-10-C is explicitly blocked by its unavailable 2.9GB archive.

## Ablations

The declared system ablation modes are recorded in `results/ablations/summary.json`. Modes that require changing the existing core loop are marked blocked rather than silently simulated.

## Integrity and limitations

- Core `auto_research/src/ai_scientist/` was not modified.
- ETTm1 uses real downloaded data and a complete trajectory.
- PyTorch/CUDA was unavailable; DLinear, PatchTST, XGBoost, and MLP are explicitly marked fallback implementations.
- CIFAR-10-C is blocked because downloading the official archive was not feasible in this environment.
- No claim that the research loop improves discovery is supported by this run alone; the ETTm1 meta-review remained `REVISE`.

## Next benchmark

CIFAR10-C
