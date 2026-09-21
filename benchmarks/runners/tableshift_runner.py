from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from benchmarks.baselines.tableshift import MLPBaseline, XGBoostBaseline
from benchmarks.problems.tableshift.diabetes_readmission import DiabetesReadmission
from benchmarks.problems.tableshift.evaluator import evaluate_tableshift


def _features(rows):
    fields = ("time_in_hospital", "num_lab_procedures", "num_procedures", "num_medications", "number_outpatient", "number_emergency", "number_inpatient")
    return np.asarray([[float(row[field]) if row[field].isdigit() else 0.0 for field in fields] for row in rows])


def run_tableshift(root="data/tableshift", results_root="results/tableshift", max_rows=None):
    benchmark = DiabetesReadmission(root)
    try:
        rows, targets, domains = benchmark.setup()
    except Exception as exc:
        result = {"benchmark": "TableShift", "task": benchmark.name, "status": "BLOCKED", "BLOCKED_REASON": str(exc)}
    else:
        if max_rows:
            rows, targets, domains = rows[:max_rows], targets[:max_rows], domains[:max_rows]
        x = _features(rows)
        y = np.asarray(targets, dtype=float)
        split = np.asarray([int(domain) if str(domain).isdigit() else 0 for domain in domains])
        train = split != 9
        ood = ~train
        if not ood.any():
            ood = np.arange(len(y)) >= max(1, int(len(y) * 0.2))
            train = ~ood
        result = {"benchmark": "TableShift", "task": benchmark.name, "status": "SUCCEEDED", "models": {}}
        for name, model in (("XGBoost", XGBoostBaseline()), ("MLP", MLPBaseline())):
            model.fit(x[train], y[train])
            id_scores = model.predict_proba(x[train])
            ood_scores = model.predict_proba(x[ood])
            result["models"][name] = {**evaluate_tableshift(id_scores, ood_scores, y[train], y[ood]), "implementation": model.implementation}
    output = Path(results_root)
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="data/tableshift")
    parser.add_argument("--results-root", default="results/tableshift")
    parser.add_argument("--max-rows", type=int)
    args = parser.parse_args()
    print(json.dumps(run_tableshift(**vars(args)), indent=2, default=str))
