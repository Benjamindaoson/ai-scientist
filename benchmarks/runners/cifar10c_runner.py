from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmarks.problems.vision.cifar10c.benchmark import CIFAR10CBenchmark


def run_cifar10c(root="data/cifar10c", results_root="results/cifar10c"):
    benchmark = CIFAR10CBenchmark(root)
    output = Path(results_root)
    output.mkdir(parents=True, exist_ok=True)
    try:
        benchmark.load()
    except FileNotFoundError as exc:
        result = {"benchmark": "CIFAR-10-C", "status": "BLOCKED", "BLOCKED_REASON": str(exc), "implementation": "fallback"}
    else:
        result = {"benchmark": "CIFAR-10-C", "status": "READY", "implementation": "official_dataset_unverified_model"}
    (output / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="data/cifar10c")
    parser.add_argument("--results-root", default="results/cifar10c")
    args = parser.parse_args()
    print(json.dumps(run_cifar10c(**vars(args)), indent=2))
