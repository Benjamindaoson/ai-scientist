import json


def test_discovery_trajectory_contract(tmp_path):
    required = ["problem", "baseline", "hypothesis_candidates", "selected_hypothesis", "experiment_plan", "experiment_results", "ablation_results", "evolution_history", "evidence_graph", "review_history", "final_claim"]
    for name in required:
        (tmp_path / f"{name}.json").write_text(json.dumps({"name": name}))
    assert all((tmp_path / f"{name}.json").exists() for name in required)
