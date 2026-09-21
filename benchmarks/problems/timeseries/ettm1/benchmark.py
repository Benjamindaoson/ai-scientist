from __future__ import annotations

from pathlib import Path

from benchmarks.core.benchmark import Benchmark

from .dataset import ETTm1Dataset
from .evaluator import evaluate_forecasts


class ETTm1Benchmark(Benchmark):
    name = "ettm1"

    def __init__(self, root: str | Path = "data/ettm1", **dataset_kwargs):
        self.dataset = ETTm1Dataset(root=root, **dataset_kwargs)

    def load(self) -> ETTm1Dataset:
        return self.dataset

    def evaluate(self, predictions, targets) -> dict[str, float]:
        return evaluate_forecasts(predictions, targets)
