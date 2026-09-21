import csv
import json

from benchmarks.runners.baseline_runner import run_baseline


def test_baseline_runner_writes_uniform_summary(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    fields = ["date", "HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"]
    with (data_dir / "ETTm1.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(40):
            writer.writerow({field: index if field != "date" else str(index) for field in fields})

    output = run_baseline(
        benchmark_name="ettm1",
        model_name="dlinear",
        data_root=data_dir,
        results_root=tmp_path / "results",
        lookback=4,
        horizon=2,
        split_points=(20, 30),
        max_windows=4,
    )

    summary_path = tmp_path / "results" / "ettm1" / "baseline" / "summary.json"
    assert output["benchmark"] == "ETTm1"
    assert set(output["metrics"]) == {"mse", "mae"}
    assert json.loads(summary_path.read_text())["model"] == "DLinear"
