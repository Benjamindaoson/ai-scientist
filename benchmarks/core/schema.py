"""Typed schema for autonomous-research benchmark runs."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


Direction = Literal["higher", "lower"]


@dataclass(frozen=True)
class MetricSpec:
    name: str
    direction: Direction
    weight: float = 1.0


@dataclass(frozen=True)
class ProblemSpec:
    problem_id: str
    domain: str
    research_question: str
    primary_metric: MetricSpec
    secondary_metrics: tuple[MetricSpec, ...] = ()
    seeds: tuple[int, ...] = (2021, 2022, 2023)
    constraints: dict[str, Any] = field(default_factory=dict)
    upstream: dict[str, str] = field(default_factory=dict)


@dataclass
class BenchmarkRecord:
    problem_id: str
    variant: str
    seed: int
    baseline_metrics: dict[str, float]
    final_metrics: dict[str, float]
    task_improvement: float
    valid_discovery: bool
    constraint_violations: list[str] = field(default_factory=list)
    experiment_count: int = 0
    compute_hours: float = 0.0
    research_efficiency: float = 0.0
    hypothesis_evolution_gain: float | None = None
    review_issue_count: int = 0
    review_action_count: int = 0
    review_resolution_rate: float | None = None
    integrity_passed: bool | None = None
    meta_review_decision: str | None = None
    status: str = "COMPLETED"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
