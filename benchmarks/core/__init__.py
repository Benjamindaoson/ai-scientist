"""Shared benchmark definitions, metrics, and harness."""
from .schema import BenchmarkRecord, MetricSpec, ProblemSpec
from .variants import SystemVariant, VariantConfig
from .metrics import aggregate_records, compute_task_improvement
from .harness import BenchmarkHarness

__all__ = [
    "BenchmarkRecord", "MetricSpec", "ProblemSpec",
    "SystemVariant", "VariantConfig",
    "aggregate_records", "compute_task_improvement", "BenchmarkHarness",
]
