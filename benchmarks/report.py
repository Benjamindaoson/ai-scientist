"""Aggregate Benchmark v1 JSON run records."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from benchmarks.core.metrics import aggregate_records
from benchmarks.core.schema import BenchmarkRecord


def main():
    p=argparse.ArgumentParser(); p.add_argument("results_dir"); p.add_argument("--output",default="benchmark_summary.json"); args=p.parse_args()
    records=[]
    for path in sorted(Path(args.results_dir).glob("*.json")):
        data=json.loads(path.read_text(encoding="utf-8")); row=data.get("record",data)
        records.append(BenchmarkRecord(**row))
    summary=aggregate_records(records)
    Path(args.output).write_text(json.dumps(summary,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))


if __name__=="__main__": main()
