"""Claim-driven ablation planning and execution."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

from .experiment.models import ExperimentSpec


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
    """Generate minimal, interpretable leave-one-component-out ablations."""

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


class AblationExecutor:
    """Execute ablation variants by exposing component configuration through env vars."""

    PREFIX = "AI_SCIENTIST_COMPONENT_"

    def __init__(self, runner):
        self.runner = runner

    def spec_for_variant(self, base_spec: ExperimentSpec, variant: dict) -> ExperimentSpec:
        spec = deepcopy(base_spec)
        spec.id = f"{base_spec.id}_{variant['name']}"
        spec.objective = f"{base_spec.objective} [ablation: {variant['name']}]"
        env = dict(spec.env)
        for name, value in variant.get("configuration", {}).items():
            env[f"{self.PREFIX}{name.upper()}"] = "1" if bool(value) else "0"
        spec.env = env
        spec.metadata = dict(spec.metadata)
        spec.metadata["ablation_variant"] = variant["name"]
        return spec

    def execute(self, plan: AblationPlan, base_spec: ExperimentSpec, repair_callback=None) -> list[dict]:
        outputs = []
        for variant in plan.variants:
            spec = self.spec_for_variant(base_spec, variant)
            result = self.runner.run(spec, repair_callback=repair_callback)
            outputs.append({
                "variant": variant,
                "spec": spec.to_dict(),
                "result": result.to_dict(),
            })
        return outputs
