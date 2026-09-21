from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Benchmark(ABC):
    """Small adapter contract shared by benchmark problems and runners."""

    name: str

    @abstractmethod
    def load(self) -> Any:
        """Load or prepare the benchmark dataset."""

    @abstractmethod
    def evaluate(self, predictions: Any, targets: Any) -> dict[str, float]:
        """Evaluate predictions against targets."""

    def setup(self) -> Any:
        return self.load()

    def baseline(self, model: Any) -> Any:
        return model

    def experiment(self, spec: Any) -> Any:
        return spec

    def trajectory_export(self, state: Any, root: str) -> Any:
        return state


ResearchBenchmark = Benchmark
