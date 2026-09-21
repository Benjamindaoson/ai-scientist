"""Unified research state for autonomous scientific workflows."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ResearchState:
    """Single source of truth shared by reasoning, execution, and review layers."""
    project_id: str
    problem: str
    literature: list[dict[str, Any]] = field(default_factory=list)
    hypotheses: list[dict[str, Any]] = field(default_factory=list)
    claims: list[dict[str, Any]] = field(default_factory=list)
    objections: list[dict[str, Any]] = field(default_factory=list)
    experiment_specs: list[dict[str, Any]] = field(default_factory=list)
    experiment_runs: list[dict[str, Any]] = field(default_factory=list)
    ablations: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    reviews: list[dict[str, Any]] = field(default_factory=list)
    rebuttals: list[dict[str, Any]] = field(default_factory=list)
    meta_reviews: list[dict[str, Any]] = field(default_factory=list)
    decisions: list[dict[str, Any]] = field(default_factory=list)
    manuscript: dict[str, Any] = field(default_factory=dict)
    evidence_graph: dict[str, Any] = field(default_factory=dict)
    integrity_report: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def append(self, collection: str, item: dict[str, Any]) -> None:
        target = getattr(self, collection)
        if not isinstance(target, list):
            raise TypeError(f"{collection} is not a list collection")
        target.append(item)
        self.touch()

    def touch(self) -> None:
        self.updated_at = datetime.utcnow().isoformat()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
