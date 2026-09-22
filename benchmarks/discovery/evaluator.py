from __future__ import annotations

from typing import Any


def evaluate_experiment(
    baseline: dict[str, Any],
    result: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw_metrics = result.get("metrics", {})
    metrics = raw_metrics.get("metrics", raw_metrics) if isinstance(raw_metrics, dict) else {}
    if result.get("status") != "SUCCEEDED" or "mse" not in metrics:
        return {"verdict": "INCONCLUSIVE", "reason": "experiment did not produce valid metrics"}
    contract = contract or {"primary_metric": "mse", "direction": "decrease", "minimum_effect": 1e-6}
    metric = contract.get("primary_metric", "mse")
    if metric not in baseline.get("metrics", {}) or metric not in metrics:
        return {"verdict": "INCONCLUSIVE", "reason": f"metric contract requires {metric}"}
    baseline_value = float(baseline["metrics"][metric])
    result_value = float(metrics[metric])
    direction = contract.get("direction", "decrease")
    improvement = baseline_value - result_value if direction == "decrease" else result_value - baseline_value
    minimum_effect = float(contract.get("minimum_effect", 1e-6))
    # Treat numerical noise as no effect; a scientific claim needs a
    # measurable margin, not a signed least-bit difference.
    tolerance = max(1e-9, abs(baseline_value) * 1e-6, minimum_effect)
    verdict = "SUPPORTED" if improvement > tolerance else "REJECTED"
    return {
        "verdict": verdict,
        "metric": metric,
        "direction": direction,
        "minimum_effect": minimum_effect,
        "baseline_value": baseline_value,
        "result_value": result_value,
        "baseline_mse": float(baseline.get("metrics", {}).get("mse", float("nan"))),
        "result_mse": float(metrics.get("mse", float("nan"))),
        "improvement": improvement,
        "relative_improvement": improvement / baseline_value if baseline_value else 0.0,
    }


def final_claim(state: dict[str, Any]) -> dict[str, Any]:
    final_hypothesis = state.get("final_hypothesis", {})
    final_validation = state.get("final_validation", {})
    test_confirmation = state.get("final_test", {})
    validation_verdict = final_validation.get("verdict", "INCONCLUSIVE")
    test_verdict = test_confirmation.get("evaluation", {}).get("verdict", "INCONCLUSIVE")
    if validation_verdict == "SUPPORTED" and test_verdict == "SUPPORTED":
        status = "SUPPORTED"
    elif validation_verdict == "REJECTED" or test_verdict == "REJECTED":
        status = "REJECTED"
    else:
        status = "INCONCLUSIVE"
    test_confirmation = state.get("final_test", {})
    return {
        "claim": "The frozen final hypothesis improves ETTm1 long-horizon forecasting under the declared protocol",
        "final_hypothesis_id": final_hypothesis.get("id"),
        "final_configuration": final_hypothesis.get("mutation", {}),
        "validation_metrics": final_validation.get("metrics", {}).get("metrics", final_validation.get("metrics", {})),
        "test_metrics": test_confirmation.get("candidate", {}).get("metrics", {}),
        "baseline_validation_metrics": state.get("baseline_validation_metrics", {}),
        "baseline_test_metrics": test_confirmation.get("control", {}).get("metrics", {}),
        "validation_verdict": validation_verdict,
        "final_test_verdict": test_verdict,
        "evidence": [final_validation.get("experiment_id"), test_confirmation.get("candidate", {}).get("experiment_id")],
        "evidence_strength": "strong" if status == "SUPPORTED" else "insufficient",
        "status": status,
        "reason": "The final claim is about the frozen hypothesis only; earlier search failures remain trajectory evidence, not direct refutation.",
        "test_confirmation": test_confirmation,
    }
