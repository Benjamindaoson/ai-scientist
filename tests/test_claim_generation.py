from benchmarks.discovery.evaluator import final_claim


def test_claim_is_not_promoted_when_evidence_is_mixed():
    claim = final_claim({"experiment_results": [
        {"experiment_id": "a", "evaluation": {"verdict": "SUPPORTED"}},
        {"experiment_id": "b", "evaluation": {"verdict": "REJECTED"}},
    ]})
    assert claim["status"] == "INCONCLUSIVE"
