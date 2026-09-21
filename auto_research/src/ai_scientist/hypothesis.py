"""Hypothesis lifecycle and evidence-driven evolution."""
from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from .core.gateway import BaseGateway


@dataclass
class Hypothesis:
    claim: str
    rationale: str
    predicted_effect: str
    falsification_conditions: list[str]
    id: str = field(default_factory=lambda: f"hyp_{uuid.uuid4().hex[:10]}")
    parent_hypothesis_id: str | None = None
    status: str = "PROPOSED"
    supporting_evidence_ids: list[str] = field(default_factory=list)
    contradicting_evidence_ids: list[str] = field(default_factory=list)
    experiment_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class HypothesisEvolver:
    """Create a child hypothesis from empirical outcomes and unresolved objections."""

    def __init__(self, gateway: BaseGateway | None = None):
        self.gateway = gateway

    def evolve(self, current: Hypothesis, experiment: dict, objections: list[dict]) -> Hypothesis:
        if self.gateway:
            prompt = (
                "Revise the hypothesis using the experiment and unresolved objections. "
                "Return JSON with claim, rationale, predicted_effect, falsification_conditions.\n"
                f"HYPOTHESIS={json.dumps(current.to_dict())}\n"
                f"EXPERIMENT={json.dumps(experiment)}\n"
                f"OBJECTIONS={json.dumps(objections)}"
            )
            try:
                data = json.loads(self.gateway.generate(prompt))
                return Hypothesis(
                    claim=data["claim"],
                    rationale=data.get("rationale", ""),
                    predicted_effect=data.get("predicted_effect", ""),
                    falsification_conditions=data.get("falsification_conditions", []),
                    parent_hypothesis_id=current.id,
                    status="EVOLVED",
                )
            except Exception:
                pass

        metrics = experiment.get("metrics", {})
        return Hypothesis(
            claim=f"Refined: {current.claim}",
            rationale=f"Updated after experiment {experiment.get('experiment_id')} with metrics {metrics}.",
            predicted_effect=current.predicted_effect,
            falsification_conditions=current.falsification_conditions,
            parent_hypothesis_id=current.id,
            status="EVOLVED",
        )
