"""Claim-driven ablation planning."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AblationPlan:
    hypothesis_id: str
    full_configuration: dict
    variants: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "hypothesis_id": self.hypothesis_id,
            "full_configuration": self.full_configuration,
            "variants": self.variants,
        }


class AblationPlanner:
    """Generate minimal, interpretable ablations rather than exhaustive combinations."""

    def plan(self, hypothesis_id: str, components: dict[str, object]) -> AblationPlan:
        variants = []
        for name in components:
            cfg = dict(components)
            cfg[name] = False
            variants.append({
                "name": f"without_{name}",
                "configuration": cfg,
                "tests_claim": f"Whether {name} is necessary for the observed effect",
            })
        return AblationPlan(hypothesis_id=hypothesis_id, full_configuration=dict(components), variants=variants)
