import json

from benchmarks.core.benchmark import Benchmark
from benchmarks.core.registry import BenchmarkRegistry
from benchmarks.core.result import BenchmarkResult
from benchmarks.core.trajectory import Trajectory


class TinyBenchmark(Benchmark):
    name = "tiny"

    def load(self):
        return {"loaded": True}

    def evaluate(self, predictions, targets):
        return {"mae": abs(predictions[0] - targets[0])}


def test_registry_registers_and_resolves_benchmark():
    registry = BenchmarkRegistry()
    registry.register(TinyBenchmark)

    assert registry.get("tiny") is TinyBenchmark
    assert registry.names() == ["tiny"]


def test_result_serializes_uniform_metric_payload():
    result = BenchmarkResult(
        benchmark="tiny",
        model="baseline",
        seed=1,
        metrics={"mae": 0.25},
    )

    assert json.loads(result.to_json()) == {
        "benchmark": "tiny",
        "model": "baseline",
        "seed": 1,
        "metrics": {"mae": 0.25},
    }


def test_trajectory_writes_named_research_artifacts(tmp_path):
    trajectory = Trajectory(tmp_path / "run_001")
    trajectory.write("problem", {"benchmark": "tiny"})
    trajectory.write("final_decision", {"decision": "SUPPORTED"})

    assert json.loads((tmp_path / "run_001" / "problem.json").read_text()) == {
        "benchmark": "tiny"
    }
    assert json.loads((tmp_path / "run_001" / "final_decision.json").read_text()) == {
        "decision": "SUPPORTED"
    }
