"""Generate the fixed Benchmark v1 experiment matrix."""
from __future__ import annotations

import json
from benchmarks.core.variants import SystemVariant
from benchmarks.problems import ROBUSTNESS_PROBLEM, TABLESHIFT_PROBLEM, TIME_SERIES_PROBLEM


PROBLEMS=(TIME_SERIES_PROBLEM,ROBUSTNESS_PROBLEM,TABLESHIFT_PROBLEM)


def build_matrix():
    return [
        {"problem_id":p.problem_id,"variant":v.value,"seed":seed}
        for p in PROBLEMS for v in SystemVariant for seed in p.seeds
    ]


if __name__=="__main__":
    matrix=build_matrix(); print(json.dumps({"runs":len(matrix),"matrix":matrix},indent=2))
