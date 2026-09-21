"""Metrics for evaluating autonomous scientific discovery."""
from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Iterable

from .schema import BenchmarkRecord, MetricSpec


def compute_task_improvement(metric: MetricSpec, baseline: float, candidate: float) -> float:
    """Signed relative improvement; positive is always better."""
    scale = max(abs(baseline), 1e-12)
    delta = candidate - baseline
    if metric.direction == "lower":
        delta = -delta
    return delta / scale


def research_efficiency(task_improvement: float, compute_hours: float, experiment_count: int) -> float:
    denominator = compute_hours if compute_hours > 0 else max(experiment_count, 1)
    return task_improvement / denominator


def aggregate_records(records: Iterable[BenchmarkRecord]) -> dict:
    rows = list(records)
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row.problem_id, row.variant)].append(row)

    cells = []
    for (problem_id, variant), group in sorted(grouped.items()):
        valid = [x for x in group if x.valid_discovery]
        cells.append({
            "problem_id": problem_id,
            "variant": variant,
            "runs": len(group),
            "valid_discovery_rate": len(valid) / len(group),
            "mean_task_improvement": mean(x.task_improvement for x in group),
            "mean_experiment_count": mean(x.experiment_count for x in group),
            "mean_compute_hours": mean(x.compute_hours for x in group),
            "mean_research_efficiency": mean(x.research_efficiency for x in group),
            "integrity_pass_rate": mean(1.0 if x.integrity_passed else 0.0 for x in group),
        })

    return {"runs": len(rows), "cells": cells}
