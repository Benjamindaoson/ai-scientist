from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiscoveryState:
    problem: dict[str, Any]
    baseline: dict[str, Any]
    hypothesis_candidates: list[dict[str, Any]] = field(default_factory=list)
    selected_hypotheses: list[dict[str, Any]] = field(default_factory=list)
    experiment_plans: list[dict[str, Any]] = field(default_factory=list)
    experiment_results: list[dict[str, Any]] = field(default_factory=list)
    ablation_results: list[dict[str, Any]] = field(default_factory=list)
    evolution_history: list[dict[str, Any]] = field(default_factory=list)
    evidence_graph: dict[str, Any] = field(default_factory=lambda: {"nodes": [], "edges": []})
    review_history: list[dict[str, Any]] = field(default_factory=list)
