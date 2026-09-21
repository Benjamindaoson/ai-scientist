"""Execute planned ablations through the same experiment runtime."""
from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from .experiment import ExperimentEvaluator, ExperimentRunner, ExperimentSpec


class AblationExecutor:
    def __init__(self, runner: ExperimentRunner | None = None):
        self.runner = runner or ExperimentRunner()
        self.evaluator = ExperimentEvaluator()

    def execute(self, base_spec: ExperimentSpec, ablation_plan: dict[str, Any]) -> list[dict[str, Any]]:
        outputs = []
        for index, variant in enumerate(ablation_plan.get("variants", []), start=1):
            env = dict(base_spec.env)
            env["AI_SCIENTIST_ABLATION"] = json.dumps(variant.get("configuration", {}), sort_keys=True)
            metrics_file = f"metrics_ablation_{index}.json"
            spec = replace(
                base_spec,
                id=f"{base_spec.id}_abl{index}",
                env=env,
                metrics_file=metrics_file,
            )
            results = self.runner.run_with_recovery(spec)
            final = results[-1]
            outputs.append({
                "variant": variant,
                "spec": spec.to_dict(),
                "attempts": [x.to_dict() for x in results],
                "result": final.to_dict(),
                "evaluation": self.evaluator.evaluate(spec, final),
            })
        return outputs
