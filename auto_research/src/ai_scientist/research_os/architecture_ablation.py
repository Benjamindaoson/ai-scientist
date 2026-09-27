from __future__ import annotations

import json
from pathlib import Path


VARIANTS = {
    "six_role": {"independent_review": True, "protocol_separation": True, "cost": 6},
    "pi_engineer_merged": {"independent_review": True, "protocol_separation": False, "cost": 5},
    "analyst_reviewer_merged": {"independent_review": False, "protocol_separation": True, "cost": 5},
    "self_review": {"independent_review": False, "protocol_separation": False, "cost": 4},
}


def run_architecture_ablation(path: str | Path) -> dict[str, dict[str, float]]:
    cases = json.loads(Path(path).read_text(encoding="utf-8"))
    output = {}
    for name, variant in VARIANTS.items():
        true_errors = sum(1 for case in cases if case["has_error"])
        detected = sum(1 for case in cases if case["has_error"] and (variant["independent_review"] or not case["requires_independent_review"]))
        false_blocks = sum(1 for case in cases if not case["has_error"] and not variant["independent_review"])
        violations = sum(1 for case in cases if case["protocol_mutation_risk"] and not variant["protocol_separation"])
        missed = true_errors - detected
        output[name] = {
            "valid_error_detection": detected / max(1, true_errors),
            "false_blocking": false_blocks / max(1, len(cases) - true_errors),
            "protocol_violation": violations / len(cases),
            "human_repair_time": float(sum(case["repair_minutes"] for case in cases if case["has_error"]) + missed * 15),
            "execution_cost_usage": float(variant["cost"] * len(cases)),
        }
    return output
