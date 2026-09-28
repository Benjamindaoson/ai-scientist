from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from ai_scientist.literature_intelligence.production import classify_coverage, validate_known_prior_benchmark_v2
from ai_scientist.topic_discovery import CandidateIdea, DiscoveryLoop, GateEvidence, NoveltyJudge, ResearchProgram, TopicReadinessGate
from ai_scientist.topic_discovery.service import validate_dataset_preflight


def idea(index: int = 0) -> CandidateIdea:
    return CandidateIdea(
        idea_id=f"idea-{index}", title=f"Idea {index}", current_belief="belief", proposed_challenge="challenge",
        scientific_question=f"Does construct {index} predict outcome {index}?",
        falsifiable_claim=f"Construct {index} improves outcome {index} over baseline {index}.", why_now="FUTURE_CYCLE",
        origin_signal_ids=("signal-1",), expected_contribution_type="MEASUREMENT", possible_target_venues=("ICLR",),
        cheap_falsifier="pilot", main_risk="prior", generation_model="codex-cli",
        prompt_hash="a" * 64, input_signal_ids=("signal-1",), literature_context_ids=("paper-1",),
        reasoning_summary="Derived from a source-backed contradiction.", generation_timestamp="2026-09-28T00:00:00+00:00",
    )


def hardened_evidence(candidate: CandidateIdea | None = None) -> GateEvidence:
    candidate = candidate or idea()
    evidence = GateEvidence.complete()
    evidence.scientific_question = candidate.scientific_question
    evidence.falsifiable_claim = candidate.falsifiable_claim
    evidence.generation_provenance = {
        "generation_model": candidate.generation_model, "prompt_hash": candidate.prompt_hash,
        "input_signal_ids": list(candidate.input_signal_ids), "literature_context_ids": list(candidate.literature_context_ids),
        "reasoning_summary": candidate.reasoning_summary, "generation_timestamp": candidate.generation_timestamp,
    }
    evidence.deep_audit = [{
        "paper_version_id": "version-1", "full_text_status": "AVAILABLE", "source_chunk_ids": ["chunk-1"],
        "source_spans": [{"section": "method", "text": "independent evidence"}],
        "scientific_question_overlap": "FALSE", "claim_overlap": "FALSE", "assumption_overlap": "PARTIAL",
        "method_overlap": "PARTIAL", "measurement_overlap": "FALSE", "setting_overlap": "PARTIAL",
        "conclusion_overlap": "FALSE",
    }]
    evidence.significance = {
        name: {"pass": True, "reason": f"candidate-specific {name}", "evidence_refs": ["chunk-1"], "assessor": "reviewer"}
        for name in ("fundamental", "surprising", "broad", "actionable", "cheap_to_falsify", "hard_to_explain_away", "defensible_novelty", "value_over_cost")
    }
    evidence.critical_questions = [{
        "question": f"q{i}", "answer": f"answer {i}", "evidence_refs": ["chunk-1"],
        "counterarguments": [f"counter {i}"], "confidence_class": "MEDIUM", "unresolved": [],
        "status": "RESOLVED", "answer_model": "codex-cli", "prompt_hash": f"{i:064x}",
    } for i in range(15)]
    evidence.data = {
        "status": "DATA_READY", "target_variable": "failure outcome", "target_variable_available": True,
        "official_docs": ["https://example.test/docs"], "actual_size": "2GB debug subset",
        "download_method": "gsutil", "license": "documented", "schema": ["steps", "is_terminal"],
        "metadata_load": {"status": "SUCCEEDED", "command": "loader --debug", "artifact": "metadata.json"},
    }
    evidence.engineering = {"status": "READY", "command": "python smoke.py", "artifact": "smoke.json", "metric_computed": "AUROC"}
    evidence.compute = {"candidate_id": candidate.idea_id, "assumptions": ["200 samples"], "calculation": "200*2 passes / 50 samples/hour = 8 GPU hours", "best_case": {"gpu_hours": 4}, "expected": {"gpu_hours": 8}, "worst_reasonable": {"gpu_hours": 16}}
    evidence.time_estimate = {"candidate_id": candidate.idea_id, "assumptions": ["loader ready"], "calculation": "2+3+2 days", "best_days": 5, "expected_days": 7, "p90_days": 10}
    evidence.killer_experiment = {"candidate_id": candidate.idea_id, "data": "debug", "baseline": "baseline", "metric": "AUROC", "sample_size": 200, "kill_condition": "upper CI <= 0"}
    evidence.coherence = {"pass": True, "question_construct": "construct", "claim_construct": "construct", "primary_measurement": "construct", "outcome": "outcome", "baseline": "baseline"}
    return evidence


def test_hardcoded_lenses_are_not_production_generator():
    from ai_scientist.topic_discovery.service import ProductionTopicPipeline
    with pytest.raises(ValueError, match="executor-backed candidate generator"):
        ProductionTopicPipeline(None, None, None)


def test_first_passing_candidate_does_not_short_circuit_wave():
    class Pipeline:
        def __init__(self): self.screened = []; self.audited = []
        def sync(self): pass
        def signals(self): return []
        def candidates(self, minimum, strategy): return [idea(i) for i in range(minimum)]
        def cheap_screen(self, candidate): self.screened.append(candidate.idea_id); return True
        def rank_survivors(self, candidates): return list(reversed(candidates))
        def evaluate(self, candidate): self.audited.append(candidate.idea_id); return hardened_evidence(candidate)
        def select(self, ready): return ready[0]
    pipeline = Pipeline()
    result = DiscoveryLoop(pipeline, ResearchProgram.production_default(), max_waves=1).run_until_topic_ready()
    assert len(pipeline.screened) == 20
    assert len(pipeline.audited) >= 5
    assert result.selected_idea.idea_id == "idea-19"
    assert len(result.ready_candidates) >= 5


def test_first_candidate_can_be_killed_and_loop_continues():
    class Pipeline:
        def sync(self): pass
        def signals(self): return []
        def candidates(self, minimum, strategy): return [idea(i) for i in range(minimum)]
        def cheap_screen(self, candidate): return True
        def rank_survivors(self, candidates): return candidates
        def evaluate(self, candidate): return None if candidate.idea_id == "idea-0" else hardened_evidence(candidate)
        def select(self, ready): return ready[0]
    result = DiscoveryLoop(Pipeline(), ResearchProgram.production_default(), max_waves=1).run_until_topic_ready()
    assert result.status == "TOPIC_READY"
    assert result.selected_idea.idea_id != "idea-0"


def test_all_wave_killed_changes_strategy():
    class Pipeline:
        def __init__(self): self.strategies = []
        def sync(self): pass
        def signals(self): return []
        def candidates(self, minimum, strategy): self.strategies.append(strategy); return [idea(len(self.strategies)*100+i) for i in range(minimum)]
        def cheap_screen(self, candidate): return len(self.strategies) > 1
        def rank_survivors(self, candidates): return candidates
        def evaluate(self, candidate): return hardened_evidence(candidate)
        def select(self, ready): return ready[0]
    pipeline = Pipeline()
    result = DiscoveryLoop(pipeline, ResearchProgram.production_default(), max_waves=2).run_until_topic_ready()
    assert result.waves_run == 2
    assert pipeline.strategies == ["CFP_THEMES", "WORKSHOP_OPEN_QUESTIONS"]


def test_abstract_only_prior_cannot_claim_full_text_audit():
    candidate = idea()
    decision = NoveltyJudge().deep_decide(candidate, [{
        "paper_id": "p", "paper_version_id": "v", "full_text_status": "UNAVAILABLE", "source_chunk_ids": ["abstract"],
        "scientific_question_overlap": "UNKNOWN", "claim_overlap": "UNKNOWN", "assumption_overlap": "UNKNOWN",
        "method_overlap": "UNKNOWN", "measurement_overlap": "UNKNOWN", "setting_overlap": "UNKNOWN", "conclusion_overlap": "UNKNOWN",
    }], search_complete=True)
    assert decision.decision.value == "NOVELTY_UNCERTAIN"


def test_self_retrieval_benchmark_rejected():
    rows = [{"question": "Does SAFE multitask failure detection work?", "target_title": "SAFE multitask failure detection", "target_abstract": "SAFE multitask failure detection works", "dangerous_prior_ids": ["p1"]}]
    with pytest.raises(ValueError, match="self-retrieval"):
        validate_known_prior_benchmark_v2(rows)


def test_partial_venue_corpus_cannot_claim_complete():
    assert classify_coverage(expected=1000, ingested=120) == "PARTIAL"
    assert classify_coverage(expected=1000, ingested=1000) == "COMPLETE"
    assert classify_coverage(expected=None, ingested=0) == "UNAVAILABLE"


def test_critical_answers_cannot_all_be_static_defaults():
    evidence = hardened_evidence()
    evidence.critical_questions = [{"question": str(i), "answer": "resolved", "evidence_refs": ["e"], "unresolved": []} for i in range(15)]
    verdict = TopicReadinessGate().evaluate(evidence)
    assert "critical_questions" in verdict.missing


def test_hard_coded_significance_passes_rejected():
    evidence = hardened_evidence()
    evidence.significance = {name: True for name in ("fundamental", "surprising", "broad", "actionable")}
    assert "significance" in TopicReadinessGate().evaluate(evidence).missing


def test_homepage_http_200_does_not_imply_data_ready():
    result = validate_dataset_preflight({"http_status": 200, "homepage_reachable": True})
    assert result["status"] != "DATA_READY"


def test_missing_target_label_blocks_topic():
    evidence = hardened_evidence()
    evidence.data["target_variable_available"] = False
    evidence.data["status"] = "DATA_LABEL_GAP"
    assert "data" in TopicReadinessGate().evaluate(evidence).missing


def test_question_claim_incoherence_blocks_topic():
    evidence = hardened_evidence()
    evidence.coherence = {"pass": False, "reason": "question says prediction error; claim says uncertainty"}
    assert "coherence" in TopicReadinessGate().evaluate(evidence).missing


def test_candidate_specific_feasibility_required():
    evidence = hardened_evidence()
    evidence.engineering = {"status": "READY", "preflight": "standard sklearn metrics"}
    assert "engineering" in TopicReadinessGate().evaluate(evidence).missing


def test_candidate_specific_compute_estimate_required():
    evidence = hardened_evidence()
    evidence.compute.pop("candidate_id")
    assert "compute" in TopicReadinessGate().evaluate(evidence).missing


def test_scout_reviewer_independent_retrieval_required():
    evidence = hardened_evidence()
    evidence.reviewer_retrieval_run_id = evidence.scout_retrieval_run_id
    assert "independent_retrieval_runs" in TopicReadinessGate().evaluate(evidence).missing


def test_known_vla_failure_priors_enter_dangerous_set():
    from ai_scientist.topic_discovery.service import KNOWN_DANGEROUS_VLA_PRIORS
    titles = " ".join(row["title"] for row in KNOWN_DANGEROUS_VLA_PRIORS)
    assert "Failure Prediction at Runtime" in titles
    assert "SAFE: Multitask Failure Detection" in titles
    assert "Ask Before You Act" in titles


def test_historical_signal_is_not_called_current_cfp():
    candidate = idea()
    assert "current CFP" not in candidate.why_now
