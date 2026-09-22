from __future__ import annotations

from typing import Any


def evaluate_experiment(baseline: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    raw_metrics = result.get("metrics", {})
    metrics = raw_metrics.get("metrics", raw_metrics) if isinstance(raw_metrics, dict) else {}
    if result.get("status") != "SUCCEEDED" or "mse" not in metrics:
        return {"verdict": "INCONCLUSIVE", "reason": "experiment did not produce valid metrics"}
    baseline_mse = float(baseline["metrics"]["mse"])
    result_mse = float(metrics["mse"])
    improvement = baseline_mse - result_mse
    # Treat numerical noise as no effect; a scientific claim needs a
    # measurable margin, not a signed least-bit difference.
    tolerance = max(1e-9, abs(baseline_mse) * 1e-6)
    verdict = "SUPPORTED" if improvement > tolerance else "REJECTED"
    return {
        "verdict": verdict,
        "baseline_mse": baseline_mse,
        "result_mse": result_mse,
        "improvement": improvement,
        "relative_improvement": improvement / baseline_mse if baseline_mse else 0.0,
    }


def final_claim(state: dict[str, Any]) -> dict[str, Any]:
    evaluations = [item["evaluation"] for item in state["experiment_results"] if "evaluation" in item]
    supported = [item for item in evaluations if item["verdict"] == "SUPPORTED"]
    if not evaluations:
        status = "INCONCLUSIVE"
    elif supported and all(item["verdict"] != "REJECTED" for item in evaluations):
        status = "SUPPORTED"
    elif supported:
        status = "INCONCLUSIVE"
    else:
        status = "REJECTED"
    confidence = min(0.95, 0.35 + 0.1 * len(evaluations) + (0.15 if status == "SUPPORTED" else 0.0))
    test_confirmation = state.get("final_test", {})
    if status == "SUPPORTED" and test_confirmation:
        test_eval = test_confirmation.get("evaluation", {})
        if test_eval.get("verdict") != "SUPPORTED":
            status = "INCONCLUSIVE"
    return {
        "claim": "The selected configuration improves ETTm1 long-horizon forecasting under the executed bounded protocol",
        "evidence": [item.get("experiment_id") for item in state["experiment_results"]],
        "confidence": round(confidence, 4),
        "status": status,
        "reason": "Claims are downgraded when any executed round contradicts the proposed improvement.",
        "test_confirmation": test_confirmation,
    }
