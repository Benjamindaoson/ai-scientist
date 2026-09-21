import csv

from benchmarks.problems.timeseries.ettm1.dataset import ETTm1Dataset
from benchmarks.problems.timeseries.ettm1.evaluator import evaluate_forecasts


def write_fixture(path):
    fields = ["date", "HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in range(20):
            writer.writerow({field: index if field != "date" else f"2016-01-01 00:{index:02d}:00" for field in fields})


def test_ettm1_dataset_splits_and_yields_windows(tmp_path):
    csv_path = tmp_path / "ETTm1.csv"
    write_fixture(csv_path)
    dataset = ETTm1Dataset(
        root=tmp_path,
        lookback=4,
        horizon=2,
        split_points=(10, 15),
        download=False,
    )

    assert dataset.split_lengths() == {"train": 10, "val": 5, "test": 5}
    window = next(dataset.windows("train"))
    assert len(window.inputs) == 4
    assert len(window.targets) == 2
    assert len(window.inputs[0]) == 7


def test_ettm1_evaluator_returns_mse_and_mae():
    metrics = evaluate_forecasts([[1.0, 3.0]], [[0.0, 1.0]])

    assert metrics == {"mse": 2.5, "mae": 1.5}
