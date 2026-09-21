from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ResearchProblem:
    title: str
    description: str
    benchmark: str
    baseline_models: list[str]
    constraints: dict[str, Any] = field(default_factory=dict)
    evaluation_metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
