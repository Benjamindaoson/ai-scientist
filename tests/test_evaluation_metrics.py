from benchmarks.evaluators.research_metrics import (
    hypothesis_evolution_gain,
    integrity_score,
    research_efficiency,
    scientific_improvement,
    trajectory_completeness,
)
import pytest


def test_research_metrics_are_defined_and_bounded():
    assert scientific_improvement(0.5, 0.7) == pytest.approx(0.2)
    assert hypothesis_evolution_gain([{"status": "EVOLVED"}, {"status": "PROPOSED"}]) == 1
    assert research_efficiency(0.8, 2) == 0.4
    assert integrity_score([{"passed": True}, {"passed": False}]) == 0.5
    assert trajectory_completeness({name: {} for name in ("problem", "baseline", "hypothesis_history", "experiment_history", "evidence_graph", "reviews", "final_decision")}) == 1.0
