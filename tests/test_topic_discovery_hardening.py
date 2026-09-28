from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import os
from types import SimpleNamespace
import uuid

import pytest
from sqlalchemy import create_engine

from ai_scientist.literature_intelligence.production import classify_coverage, validate_known_prior_benchmark_v2
from ai_scientist.literature_intelligence import HashingEmbeddingProvider, HybridSearch, LiteratureRepository, LiteratureService, initialize_literature_database
from ai_scientist.opportunity_intelligence import OpportunityRepository, initialize_opportunity_database
from ai_scientist.opportunity_intelligence import models as opportunity_models
from ai_scientist.topic_discovery import CandidateIdea, DiscoveryLoop, GateEvidence, NoveltyJudge, ResearchProgram, TopicReadinessGate
from ai_scientist.topic_discovery.service import TopicDiscoveryService, validate_dataset_preflight


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
        "metadata_load": {"status": "SUCCEEDED", "command": "loader --debug", "artifact": "metadata.json", "execution_receipt": "metadata-receipt.json"},
    }
    evidence.engineering = {"status": "READY", "command": "python smoke.py", "artifact": "smoke.json", "execution_receipt": "smoke-receipt.json", "metric_computed": "AUROC"}
    evidence.compute = {"candidate_id": candidate.idea_id, "assumptions": ["200 samples"], "calculation": "200*2 passes / 50 samples/hour = 8 GPU hours", "best_case": {"gpu_hours": 4}, "expected": {"gpu_hours": 8}, "worst_reasonable": {"gpu_hours": 16}}
    evidence.time_estimate = {"candidate_id": candidate.idea_id, "assumptions": ["loader ready"], "calculation": "2+3+2 days", "best_days": 5, "expected_days": 7, "p90_days": 10}
    evidence.killer_experiment = {"candidate_id": candidate.idea_id, "data": "debug", "baseline": "baseline", "metric": "AUROC", "sample_size": 200, "kill_condition": "upper CI <= 0"}
    evidence.coherence = {"pass": True, "question_construct": "construct", "claim_construct": "construct", "primary_measurement": "construct", "outcome": "outcome", "baseline": "baseline"}
    return evidence


def test_hardcoded_lenses_are_not_production_generator():
    from ai_scientist.topic_discovery.service import ProductionTopicPipeline
    with pytest.raises(ValueError, match="executor-backed candidate generator"):
        ProductionTopicPipeline(None, None, None)


def test_hardening_invalidates_previous_ready_run():
    engine = create_engine(os.getenv("RESEARCH_DATABASE_URL", "postgresql+psycopg://research:research@localhost:55432/research_os_test"), pool_pre_ping=True)
    initialize_opportunity_database(engine)
    repository = OpportunityRepository(engine)
    idea_id, topic_id, run_id = "stale-ready-idea", str(uuid.uuid4()), str(uuid.uuid4())
    with engine.begin() as connection:
        for table in (opportunity_models.feasibility_audits, opportunity_models.discovery_runs, opportunity_models.topic_dossiers, opportunity_models.topic_candidates, opportunity_models.idea_lineage):
            connection.execute(table.delete())
        connection.execute(opportunity_models.topic_candidates.insert().values(candidate_row_id=str(uuid.uuid4()), idea_id=idea_id, wave=1, strategy="test", payload={}, state="TOPIC_READY"))
        connection.execute(opportunity_models.idea_lineage.insert().values(idea_lineage_id=str(uuid.uuid4()), idea_id=idea_id, generation=0, origin_signal_ids=[], normalized_question="q", semantic_fingerprint="f", killing_papers=[], status="TOPIC_READY", material_change_refs=[]))
        connection.execute(opportunity_models.topic_dossiers.insert().values(topic_id=topic_id, idea_id=idea_id, status="NOVELTY_UNCERTAIN", dossier={}, content_hash="hash"))
        connection.execute(opportunity_models.discovery_runs.insert().values(discovery_run_id=run_id, program={}, status="TOPIC_READY", wave=1, counts={}, topic_id=topic_id))
    service = TopicDiscoveryService.__new__(TopicDiscoveryService)
    service.pipeline = SimpleNamespace(opportunity_repository=repository)
    service._invalidate_previous_readiness(idea_id)
    with engine.connect() as connection:
        row = connection.execute(opportunity_models.discovery_runs.select().where(opportunity_models.discovery_runs.c.discovery_run_id == run_id)).first()
    assert row.status == "INVALIDATED_BY_HARDENING"


def test_all_declared_query_variants_are_actually_executed():
    engine = create_engine(os.getenv("RESEARCH_DATABASE_URL", "postgresql+psycopg://research:research@localhost:55432/research_os_test"), pool_pre_ping=True)
    initialize_literature_database(engine)
    repository, service = LiteratureRepository(engine), LiteratureService(LiteratureRepository(engine))
    native = f"hardening-{datetime.now(timezone.utc).timestamp()}"
    paper = service.ingest_record({
        "source": "hardening-test", "source_record_id": native, "title": "Runtime robot failure prediction",
        "abstract": "Action uncertainty detects robot failure and intervention need.", "publication_year": 2026,
        "version": {"version_label": "v1", "source_url": "https://example.test/paper"},
    })
    doc = service.ingest_full_text(paper["paper_version_id"], "Introduction\nRobot failure prediction.\nMethod\nAction uncertainty and intervention.", source_url="https://example.test/paper", license_name="test open access")
    provider = HashingEmbeddingProvider()
    service.embed_document(doc["document_id"], provider)
    variants = [f"robot failure query {i}" for i in range(7)]
    result = HybridSearch(repository, provider).search(variants[0], actor_role="scout", query_variants=variants, filters={"years": [2026, 2026]}, limit=5)
    assert result["executed_query_count"] == 7
    assert set(result["query_executions"]) == set(variants)
    assert all("keyword_result_count" in item and "dense_result_count" in item for item in result["query_executions"].values())
    assert all(item["metadata_filters_applied"] for item in result["query_executions"].values())


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


def test_uncertain_candidates_are_not_counted_as_killed():
    class Pipeline:
        def sync(self): pass
        def signals(self): return []
        def candidates(self, minimum, strategy): return [idea(i) for i in range(minimum)]
        def cheap_screen(self, candidate): return True
        def rank_survivors(self, candidates): return candidates
        def evaluate(self, candidate): return None
        def outcome(self, candidate): return "NOVELTY_UNCERTAIN"
    result = DiscoveryLoop(Pipeline(), ResearchProgram.production_default(), max_waves=1).run_until_topic_ready()
    assert result.ideas_killed == 0
    assert result.status == "NO_TOPIC_READY_WITHIN_LIMIT"


def test_nonready_gate_evidence_is_not_counted_as_killed_without_kill_outcome():
    class Pipeline:
        def sync(self): pass
        def signals(self): return []
        def candidates(self, minimum, strategy): return [idea(i) for i in range(minimum)]
        def cheap_screen(self, candidate): return True
        def rank_survivors(self, candidates): return candidates
        def evaluate(self, candidate): return GateEvidence()
        def outcome(self, candidate): return "FEASIBILITY_UNCERTAIN"
    result = DiscoveryLoop(Pipeline(), ResearchProgram.production_default(), max_waves=1).run_until_topic_ready()
    assert result.ideas_killed == 0


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


def test_conclusive_covering_prior_kills_even_when_another_prior_is_unavailable():
    unavailable = {
        "paper_id": "unknown", "full_text_status": "UNAVAILABLE", "source_spans": [],
        **{name: "UNKNOWN" for name in ("scientific_question_overlap", "claim_overlap", "assumption_overlap", "method_overlap", "measurement_overlap", "setting_overlap", "conclusion_overlap")},
    }
    covering = {
        "paper_id": "covering", "full_text_status": "AVAILABLE", "source_spans": [{"text": "source"}],
        "review_status": "REVIEWED", "review_evidence_refs": ["chunk"],
        "scientific_question_overlap": "TRUE", "claim_overlap": "TRUE", "assumption_overlap": "PARTIAL",
        "method_overlap": "PARTIAL", "measurement_overlap": "TRUE", "setting_overlap": "PARTIAL", "conclusion_overlap": "TRUE",
    }
    decision = NoveltyJudge().deep_decide(idea(), [unavailable, covering], search_complete=True)
    assert decision.decision.value == "KILLED_BY_PRIOR"
    assert decision.killing_paper_id == "covering"


def test_executor_backed_reviewer_resolves_structured_novelty_dimensions(tmp_path):
    import json
    from pathlib import Path
    from ai_scientist.research_os.agents import TaskResult
    from ai_scientist.topic_discovery.service import CodexScientificGateExecutor

    class Executor:
        def run(self, task):
            assert Path(task.workspace).resolve() != tmp_path.resolve()
            assert not (Path(task.workspace) / ".git").exists()
            output = Path(task.context["required_output_path"])
            output.write_text(json.dumps([{
                "paper_id": "prior", "scientific_question_overlap": "TRUE", "claim_overlap": "TRUE",
                "assumption_overlap": "PARTIAL", "method_overlap": "PARTIAL", "measurement_overlap": "TRUE",
                "setting_overlap": "PARTIAL", "conclusion_overlap": "TRUE", "evidence_refs": ["chunk"],
            }]), encoding="utf-8")
            return TaskResult(task_id=task.task_id, role=task.role, status="SUCCEEDED", summary="reviewed")

    audit = {"paper_id": "prior", "full_text_status": "AVAILABLE", "source_chunk_ids": ["chunk"], "source_spans": [{"chunk_id": "chunk", "text": "source"}]}
    reviewed = CodexScientificGateExecutor(Executor(), tmp_path).review_novelty(idea(), [audit])[0]
    assert reviewed["review_status"] == "REVIEWED"
    assert reviewed["scientific_question_overlap"] == "TRUE"


def test_executor_review_without_source_linked_refs_stays_unreviewed(tmp_path):
    import json
    from pathlib import Path
    from ai_scientist.research_os.agents import TaskResult
    from ai_scientist.topic_discovery.service import CodexScientificGateExecutor

    class Executor:
        def run(self, task):
            output = Path(task.context["required_output_path"])
            output.write_text(json.dumps([{
                "paper_id": "prior", "scientific_question_overlap": "TRUE", "claim_overlap": "TRUE",
                "assumption_overlap": "TRUE", "method_overlap": "TRUE", "measurement_overlap": "TRUE",
                "setting_overlap": "TRUE", "conclusion_overlap": "TRUE", "evidence_refs": [],
            }]), encoding="utf-8")
            return TaskResult(task_id=task.task_id, role=task.role, status="SUCCEEDED", summary="reviewed")

    audit = {"paper_id": "prior", "full_text_status": "AVAILABLE", "source_chunk_ids": ["chunk"], "source_spans": [{"chunk_id": "chunk", "text": "source"}]}
    reviewed = CodexScientificGateExecutor(Executor(), tmp_path).review_novelty(idea(), [audit])[0]
    assert "review_status" not in reviewed


def test_frozen_benchmark_metadata_triggers_legal_full_text_hydration(monkeypatch):
    from ai_scientist.topic_discovery.service import ProductionTopicPipeline
    engine = create_engine(os.getenv("RESEARCH_DATABASE_URL", "postgresql+psycopg://research:research@localhost:55432/research_os_test"), pool_pre_ping=True)
    initialize_literature_database(engine)
    repository, service = LiteratureRepository(engine), LiteratureService(LiteratureRepository(engine))
    record_id = f"hydrate-{uuid.uuid4()}"
    paper = service.ingest_record({
        "source": "arxiv", "source_record_id": record_id, "title": "Hydration prior",
        "abstract": "metadata only", "publication_year": 2026, "identifiers": {"arxiv": record_id},
        "version": {"version_label": "v1", "source_url": f"https://arxiv.org/abs/{record_id}"},
    })
    service.ingest_full_text(paper["paper_version_id"], "Abstract\nmetadata only", source_url=f"https://arxiv.org/abs/{record_id}", license_name="frozen benchmark metadata")

    class Response:
        text = "<h1>Introduction</h1><p>" + ("source backed method evidence " * 300) + "</p>"
        def raise_for_status(self): pass

    monkeypatch.setattr("ai_scientist.topic_discovery.service.httpx.get", lambda *args, **kwargs: Response())
    pipeline = ProductionTopicPipeline.__new__(ProductionTopicPipeline)
    pipeline.literature_repository, pipeline.literature = repository, service
    pipeline.gate_executor = None
    audit = pipeline._structured_deep_audit(idea(), [{"paper_id": paper["paper_id"], "title": "Hydration prior"}])[0]
    assert audit["full_text_status"] == "AVAILABLE"
    assert audit["source_spans"]


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


def test_candidate_without_declared_dataset_is_blocked_before_network_preflight():
    from ai_scientist.topic_discovery.service import ProductionTopicPipeline
    result = ProductionTopicPipeline._data_preflight(ProductionTopicPipeline.__new__(ProductionTopicPipeline), idea())
    assert result["status"] == "DATA_BLOCKED"
    assert result["candidate_id"] == idea().idea_id


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


def test_all_external_sources_normalize_into_ingestable_records():
    from ai_scientist.topic_discovery.service import ExternalPriorExpander
    payloads = {
        "crossref": [{"DOI": "10.1/x", "title": ["Crossref work"], "published": {"date-parts": [[2025]]}}],
        "openalex": [{"id": "https://openalex.org/W1", "title": "OpenAlex work", "publication_year": 2025}],
        "semantic_scholar": [{"paperId": "S1", "title": "S2 work", "year": 2025}],
        "arxiv": "<feed xmlns='http://www.w3.org/2005/Atom'><entry><id>https://arxiv.org/abs/2501.00001v1</id><title>arXiv work</title><summary>abstract</summary><published>2025-01-01T00:00:00Z</published></entry></feed>",
        "openreview": [{"id": "OR1", "content": {"title": {"value": "OpenReview work"}, "abstract": {"value": "abstract"}}}],
    }
    records = ExternalPriorExpander._normalize_external_records(payloads)
    assert {record["source"] for record in records} == {"crossref", "openalex", "semantic_scholar", "arxiv", "openreview"}


def test_historical_signal_is_not_called_current_cfp():
    candidate = idea()
    assert "current CFP" not in candidate.why_now


def test_adversarial_solved_candidates_are_killed_but_uncertain_is_not():
    judge = NoveltyJudge(minimum_candidates=1, kill_threshold=0.60)
    killed = 0
    for index in range(10):
        candidate = idea(index)
        prior = {"paper_id": f"prior-{index}", "title": candidate.title,
                 "abstract": f"{candidate.scientific_question} {candidate.falsifiable_claim}", "source_chunk_ids": [f"chunk-{index}"]}
        killed += judge.decide(candidate, [prior], search_complete=False).decision.value == "KILLED_BY_PRIOR"
    uncertain = judge.decide(idea(99), [{"paper_id": "other", "title": "Unrelated theorem", "abstract": "orthogonal result", "source_chunk_ids": ["c"]}], search_complete=False)
    assert killed >= 8
    assert uncertain.decision.value == "NOVELTY_UNCERTAIN"
