from __future__ import annotations

from .benchmark import Benchmark


class BenchmarkRegistry:
    def __init__(self):
        self._benchmarks: dict[str, type[Benchmark]] = {}

    def register(self, benchmark: type[Benchmark]) -> None:
        name = getattr(benchmark, "name", "")
        if not name:
            raise ValueError("benchmark must define a non-empty name")
        if name in self._benchmarks:
            raise ValueError(f"benchmark already registered: {name}")
        self._benchmarks[name] = benchmark

    def get(self, name: str) -> type[Benchmark]:
        try:
            return self._benchmarks[name]
        except KeyError as exc:
            raise KeyError(f"unknown benchmark: {name}") from exc

    def names(self) -> list[str]:
        return sorted(self._benchmarks)
