from benchmarks.discovery.evaluator import final_claim


def test_claim_is_not_promoted_when_evidence_is_mixed():
    claim = final_claim({"experiment_results": [
        {"experiment_id": "a", "evaluation": {"verdict": "SUPPORTED"}},
        {"experiment_id": "b", "evaluation": {"verdict": "REJECTED"}},
    ]})
    assert claim["status"] == "INCONCLUSIVE"


def test_numerical_noise_is_not_an_improvement():
    from benchmarks.discovery.evaluator import evaluate_experiment

    evaluation = evaluate_experiment(
        {"metrics": {"mse": 1.0}},
        {"status": "SUCCEEDED", "metrics": {"metrics": {"mse": 1.0 - 1e-15}}},
    )
    assert evaluation["verdict"] == "REJECTED"
