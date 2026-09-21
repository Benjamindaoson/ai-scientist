from __future__ import annotations

import argparse
import json
from pathlib import Path


def generate_report(trajectory_root: str | Path, output_path: str | Path) -> Path:
    root = Path(trajectory_root)
    baseline = json.loads((root / "baseline.json").read_text(encoding="utf-8"))
    history = json.loads((root / "experiment_history.json").read_text(encoding="utf-8"))
    decision = json.loads((root / "final_decision.json").read_text(encoding="utf-8"))
    run = history["runs"][0]
    meta = decision.get("meta_review", {})
    report = f"""# ETTm1 Benchmark Report

## Run

- Benchmark: ETTm1
- Baseline model: {baseline.get('model', 'N/A')}
- Seed: {baseline.get('seed', 'N/A')}
- Forecast horizon: {baseline.get('horizon', 'N/A')}
- Train windows: {baseline.get('train_windows', 'N/A')}
- Test windows: {baseline.get('test_windows', 'N/A')}

## Baseline

| Metric | Value |
| --- | ---: |
| MSE | {baseline['metrics']['mse']:.12f} |
| MAE | {baseline['metrics']['mae']:.12f} |

## AI Scientist trajectory

- Experiment status: `{run.get('status')}`
- Return code: `{run.get('return_code')}`
- Integrity passed: `{decision.get('integrity_audits', [{}])[-1].get('passed', 'N/A')}`
- Meta-review decision: `{meta.get('decision', 'N/A')}`
- Major issues: `{meta.get('major_issues', 'N/A')}`

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
"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trajectory", default="benchmarks/trajectories/ettm1_run_001")
    parser.add_argument("--output", default="benchmarks/reports/ettm1_run_001.md")
    args = parser.parse_args()
    print(generate_report(args.trajectory, args.output))


if __name__ == "__main__":
    main()
