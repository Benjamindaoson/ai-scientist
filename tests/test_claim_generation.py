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


def test_early_rejection_does_not_refute_frozen_final_hypothesis():
    from benchmarks.discovery.evaluator import final_claim

    claim = final_claim({
        "experiment_results": [
            {"experiment_id": "old", "evaluation": {"verdict": "REJECTED"}},
            {"experiment_id": "final", "evaluation": {"verdict": "SUPPORTED"}},
        ],
        "final_hypothesis": {"id": "hyp_r02_001", "mutation": {"moving_avg": 13}},
        "final_validation": {"experiment_id": "final", "verdict": "SUPPORTED", "metrics": {"mse": 0.9}},
        "final_test": {"candidate": {"experiment_id": "test", "metrics": {"mse": 0.8}}, "evaluation": {"verdict": "SUPPORTED"}},
        "baseline_validation_metrics": {"mse": 1.0},
    })
    assert claim["status"] == "SUPPORTED"
    assert claim["final_hypothesis_id"] == "hyp_r02_001"
