from __future__ import annotations


def audit_benchmark_record(record: dict) -> dict:
    metrics = record.get("metrics", {})
    declared = record.get("declared_metrics", list(metrics))
    mismatches = [name for name in declared if name not in metrics]
    leakage = record.get("train_test_overlap", False)
    invalid_claim = record.get("claim_status") == "SUPPORTED" and not metrics
    return {
        "passed": not mismatches and not leakage and not invalid_claim,
        "leakage": bool(leakage),
        "invalid_claim": bool(invalid_claim),
        "metric_mismatch": mismatches,
    }
