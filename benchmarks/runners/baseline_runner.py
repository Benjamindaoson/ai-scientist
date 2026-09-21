from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np

from benchmarks.baselines.timeseries.dlinear import DLinear, DLinearConfig
from benchmarks.baselines.timeseries.patchtst import PatchTST, PatchTSTConfig
from benchmarks.core.result import BenchmarkResult
from benchmarks.problems.timeseries.ettm1.dataset import ETTm1Dataset


def _windows(dataset: ETTm1Dataset, split: str, max_windows: int | None):
    values = list(dataset.windows(split))
    if max_windows is not None:
        values = values[:max_windows]
    inputs = np.asarray([window.inputs for window in values], dtype=float)
    targets = np.asarray([window.targets for window in values], dtype=float)
    return inputs, targets


def run_baseline(
    benchmark_name: str,
    model_name: str,
    data_root: str | Path = "data/ettm1",
    results_root: str | Path = "results",
    seed: int = 1,
    max_windows: int | None = None,
    persist: bool = True,
    model_kwargs: dict | None = None,
    **dataset_kwargs,
) -> dict:
    if benchmark_name.lower() != "ettm1":
        raise ValueError(f"unsupported benchmark: {benchmark_name}")
    random.seed(seed)
    np.random.seed(seed)
    dataset = ETTm1Dataset(root=data_root, **dataset_kwargs)
    train_x, train_y = _windows(dataset, "train", max_windows)
    test_x, test_y = _windows(dataset, "test", max_windows)
    config = {"seq_len": dataset.lookback, "pred_len": dataset.horizon, "channels": len(train_x[0][0])}
    model_key = model_name.lower()
    model_kwargs = model_kwargs or {}
    if model_key == "dlinear":
        dlinear_config = dict(config)
        dlinear_config.update(model_kwargs)
        model = DLinear(DLinearConfig(**dlinear_config)).fit(train_x, train_y)
        display_name = "DLinear"
    elif model_key == "patchtst":
        patch_config = dict(config)
        patch_config.update(model_kwargs)
        model = PatchTST(PatchTSTConfig(**patch_config)).fit(train_x, train_y)
        display_name = "PatchTST"
    else:
        raise ValueError(f"unsupported model: {model_name}")
    predictions = model.predict(test_x)
    errors = predictions - test_y
    summary = BenchmarkResult(
        benchmark="ETTm1",
        model=display_name,
        seed=seed,
        metrics={"mse": float(np.mean(errors**2)), "mae": float(np.mean(np.abs(errors)))},
    ).to_dict()
    summary["split"] = "test"
    summary["lookback"] = dataset.lookback
    summary["horizon"] = dataset.horizon
    summary["train_windows"] = len(train_x)
    summary["test_windows"] = len(test_x)
    summary["model_config"] = model_kwargs
    if persist:
        output_dir = Path(results_root) / "ettm1" / "baseline"
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(summary, indent=2) + "\n"
        (output_dir / "summary.json").write_text(payload, encoding="utf-8")
        (output_dir / f"summary_{model_key}.json").write_text(payload, encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", required=True)
    parser.add_argument("--model", required=True, choices=("dlinear", "patchtst"))
    parser.add_argument("--data-root", default="data/ettm1")
    parser.add_argument("--results-root", default="results")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--max-windows", type=int)
    args = parser.parse_args()
    print(json.dumps(run_baseline(
        benchmark_name=args.benchmark,
        model_name=args.model,
        data_root=args.data_root,
        results_root=args.results_root,
        seed=args.seed,
        max_windows=args.max_windows,
    ), indent=2))


if __name__ == "__main__":
    main()
