import json

from benchmarks.ablations.system import ABLATION_MODES, run_system_ablation
from benchmarks.problems.vision.cifar10c.evaluator import evaluate_cifar10c
from benchmarks.runners.cifar10c_runner import run_cifar10c
from benchmarks.evaluators.integrity_checks import audit_benchmark_record


def test_cifar10c_evaluator_reports_required_metrics():
    result = evaluate_cifar10c([0, 1], [0, 0], [0, 1])
    assert set(result) == {"clean_accuracy", "corruption_accuracy", "mce"}
    assert result["clean_accuracy"] == 1.0


def test_cifar10c_runner_records_blocked_dataset_without_fake_result(tmp_path):
    result = run_cifar10c(tmp_path / "missing", tmp_path / "results")
    assert result["status"] == "BLOCKED"
    assert "BLOCKED_REASON" in result
    assert json.loads((tmp_path / "results" / "summary.json").read_text())["status"] == "BLOCKED"


def test_system_ablation_runs_all_declared_modes():
    result = run_system_ablation(lambda mode: {"final_score": 1.0, "experiment_count": 1})
    assert [item["mode"] for item in result] == list(ABLATION_MODES)


def test_integrity_audit_detects_leakage_claim_and_metric_mismatch():
    result = audit_benchmark_record({
        "metrics": {},
        "declared_metrics": ["mse"],
        "train_test_overlap": True,
        "claim_status": "SUPPORTED",
    })
    assert result["passed"] is False
    assert result["leakage"] is True
    assert result["invalid_claim"] is True
    assert result["metric_mismatch"] == ["mse"]
