from benchmarks.discovery.hypothesis_generator import HypothesisGenerator
from benchmarks.discovery.problem import ResearchProblem


def test_generator_returns_ranked_candidates():
    problem = ResearchProblem("t", "d", "ETTm1", ["DLinear"])
    candidates = HypothesisGenerator().generate(problem, {"metrics": {"mse": 1.0}})
    assert len(candidates) >= 5
    assert candidates[0]["rank_score"] >= candidates[-1]["rank_score"]
    assert all(item["mutation"] for item in candidates)
