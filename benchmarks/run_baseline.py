"""Generate a frozen baseline metrics JSON for one benchmark problem/seed."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/"auto_research"/"src"))

from ai_scientist.experiment import ExperimentRunner
from benchmarks.problems import RobustnessProblem,TableShiftProblem,TimeSeriesProblem

PROBLEMS={"timeseries":TimeSeriesProblem,"robustness":RobustnessProblem,"tableshift":TableShiftProblem}

def main():
    p=argparse.ArgumentParser(); p.add_argument("--problem",choices=PROBLEMS,required=True)
    p.add_argument("--workspace",required=True); p.add_argument("--seed",type=int,required=True); p.add_argument("--output",required=True)
    args=p.parse_args(); problem=PROBLEMS[args.problem](); spec=problem.make_baseline_spec(args.workspace,args.seed)
    result=ExperimentRunner().run(spec)
    if result.status!="SUCCEEDED": raise SystemExit(f"baseline failed: {result.error_type}\n{result.stderr[-4000:]}")
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(result.metrics,indent=2),encoding="utf-8")
    print(json.dumps(result.metrics,indent=2))

if __name__=="__main__": main()
