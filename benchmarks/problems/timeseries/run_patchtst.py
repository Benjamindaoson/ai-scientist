"""Run the official PatchTST supervised benchmark and emit normalized metrics.json.

Expected workspace layout:
  <upstream>/PatchTST_supervised/run_longExp.py
  <upstream>/PatchTST_supervised/dataset/ETTm1.csv
  <upstream>/PatchTST_supervised/dataset/weather.csv
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


HORIZONS = (96, 192, 336, 720)
DATASETS = {
    "ETTm1": {"data": "ETTm1", "path": "ETTm1.csv", "enc_in": 7, "freq": "t"},
    "weather": {"data": "custom", "path": "weather.csv", "enc_in": 21, "freq": "h"},
}


def parse_last_result(result_file: Path) -> tuple[float, float]:
    text = result_file.read_text(encoding="utf-8", errors="ignore")
    matches = re.findall(r"mse:([0-9.eE+-]+),\s*mae:([0-9.eE+-]+)", text)
    if not matches:
        raise RuntimeError("PatchTST result.txt did not contain mse/mae")
    mse, mae = matches[-1]
    return float(mse), float(mae)


def run_one(root: Path, dataset: str, pred_len: int, seed: int, epochs: int, model: str) -> tuple[float, float]:
    cfg = DATASETS[dataset]
    supervised = root / "PatchTST_supervised"
    result_file = supervised / "result.txt"
    before = result_file.read_text(encoding="utf-8", errors="ignore") if result_file.exists() else ""
    cmd = [
        sys.executable, "run_longExp.py",
        "--random_seed", str(seed), "--is_training", "1",
        "--root_path", "./dataset/", "--data_path", cfg["path"],
        "--model_id", f"bench_{dataset}_336_{pred_len}",
        "--model", model, "--data", cfg["data"], "--features", "M",
        "--seq_len", "336", "--pred_len", str(pred_len),
        "--enc_in", str(cfg["enc_in"]), "--dec_in", str(cfg["enc_in"]), "--c_out", str(cfg["enc_in"]),
        "--e_layers", "3", "--n_heads", "16", "--d_model", "128", "--d_ff", "256",
        "--dropout", "0.2", "--fc_dropout", "0.2", "--head_dropout", "0",
        "--patch_len", "16", "--stride", "8", "--des", "BenchV1",
        "--train_epochs", str(epochs), "--patience", "10", "--lradj", "type3",
        "--itr", "1", "--batch_size", "128", "--learning_rate", "0.0001",
        "--freq", cfg["freq"],
    ]
    proc = subprocess.run(cmd, cwd=supervised, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"PatchTST failed for {dataset}/{pred_len}: {proc.stderr[-4000:]}")
    if not result_file.exists():
        raise RuntimeError("PatchTST did not create result.txt")
    after = result_file.read_text(encoding="utf-8", errors="ignore")
    if after == before:
        raise RuntimeError("PatchTST result.txt was not updated")
    return parse_last_result(result_file)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--upstream", required=True)
    p.add_argument("--seed", type=int, default=2021)
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--model", default="PatchTST")
    args = p.parse_args()
    root = Path(args.upstream).resolve()
    if not (root / "PatchTST_supervised" / "run_longExp.py").exists():
        raise SystemExit("Expected official PatchTST checkout at --upstream")

    rows = []
    for dataset in DATASETS:
        for horizon in HORIZONS:
            mse, mae = run_one(root, dataset, horizon, args.seed, args.epochs, args.model)
            rows.append({"dataset": dataset, "horizon": horizon, "mse": mse, "mae": mae})

    metrics = {
        "mse": sum(r["mse"] for r in rows) / len(rows),
        "mae": sum(r["mae"] for r in rows) / len(rows),
        "conditions": len(rows),
        "details": rows,
    }
    (root / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
