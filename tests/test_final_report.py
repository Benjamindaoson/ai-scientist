import json

from benchmark_report.final_report import generate_final_report


def test_final_report_contains_all_benchmarks(tmp_path):
    for path, value in {
        "results/ettm1/baseline/summary_dlinear.json": {"metrics": {"mse": 0.4, "mae": 0.5}},
        "results/tableshift/summary.json": {"status": "SUCCEEDED", "models": {"XGBoost": {"ood_auroc": 0.6}}},
        "results/cifar10c/summary.json": {"status": "BLOCKED", "BLOCKED_REASON": "missing"},
    }.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value))

    report = generate_final_report(tmp_path)

    text = report.read_text()
    assert "ETTm1" in text
    assert "CIFAR-10-C" in text
    assert "TableShift" in text
    assert "Does an evidence-driven autonomous research loop improve ML discovery?" in text
