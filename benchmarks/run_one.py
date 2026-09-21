"""Execute one Benchmark v1 cell from the command line."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "auto_research" / "src"))

from ai_scientist.core.gateway import create_gateway
from benchmarks.core.harness import BenchmarkHarness
from benchmarks.core.variants import SystemVariant
from benchmarks.problems import RobustnessProblem, TableShiftProblem, TimeSeriesProblem


PROBLEMS = {
    "timeseries": TimeSeriesProblem,
    "robustness": RobustnessProblem,
    "tableshift": TableShiftProblem,
}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--problem", choices=PROBLEMS, required=True)
    p.add_argument("--variant", choices=[x.value for x in SystemVariant], required=True)
    p.add_argument("--workspace", required=True)
    p.add_argument("--baseline-json", required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--gateway", default="auto", choices=["auto","anthropic","relay","mock"])
    args=p.parse_args()

    baseline=json.loads(Path(args.baseline_json).read_text(encoding="utf-8"))
    problem=PROBLEMS[args.problem]()
    gateway=create_gateway(args.gateway)
    record,state=BenchmarkHarness(gateway=gateway).run_one(
        problem=problem, workspace=args.workspace, baseline_metrics=baseline,
        variant=args.variant, seed=args.seed,
        ablation_components={"component_a":True,"component_b":True} if args.variant!="single_shot" else None,
    )
    output=Path(args.output); output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({"record":record.to_dict(),"state":state.to_dict()},indent=2,default=str),encoding="utf-8")


if __name__=="__main__": main()
