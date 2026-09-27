from __future__ import annotations

import os
from pathlib import Path

import pytest
from langgraph.types import Command
from sqlalchemy import create_engine

from ai_scientist.research_os.agents import ReviewFinding
from ai_scientist.research_os.config import ResearchOSConfig
from ai_scientist.research_os.graph import ResearchOSRuntime, build_research_graph, default_state, postgres_checkpointer
from ai_scientist.research_os.package_export import ResearchPackageExporter
from ai_scientist.research_os.paper_lifecycle import PaperLifecycleService
from ai_scientist.research_store import ArtifactStore, ResearchRepository, initialize_database
from ai_scientist.research_store.cli import main as cli_main


DATABASE_URL = os.getenv("RESEARCH_DATABASE_URL", "postgresql+psycopg://research:research@localhost:55432/research_os")


class TestPDFCompiler:
    def compile(self, source: Path) -> Path:
        assert "\\documentclass" in source.read_text(encoding="utf-8")
        pdf = source.with_suffix(".pdf")
        pdf.write_bytes(b"%PDF-1.4\n% Research OS integration artifact\n%%EOF\n")
        return pdf


@pytest.fixture
def lifecycle(tmp_path):
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    initialize_database(engine)
    repository = ResearchRepository(engine)
    project = repository.create_project("M5 lifecycle", domain="time-series")
    question = repository.create_research_question(project["project_id"], "Does the treatment improve score?")
    hypothesis = repository.create_hypothesis(project["project_id"], "Treatment improves score", predicted_effect="score >= 0.8")
    protocol = repository.freeze_protocol(repository.create_protocol_version(
        project["project_id"], question["research_question_id"], hypothesis["hypothesis_id"],
        design={"seed": 7}, measurement_plan={"primary_metric": "score"}, data_split_policy={"test": "held-out once"},
        analysis_plan={"method": "mean"}, stopping_rules={"runs": 1}, exclusion_rules={}, resource_budget={"minutes": 1},
    )["protocol_version_id"])
    spec = repository.create_experiment_spec(
        project_id=project["project_id"], protocol_version_id=protocol["protocol_version_id"], hypothesis_id=hypothesis["hypothesis_id"],
        objective="killer experiment", command=["python", "run.py"], workspace="workspace", metrics_contract={"score": {"op": ">=", "value": 0.8}},
        controls={}, resource_limits={}, execution_profile="local", code_revision="m5", data_manifest_hash="data", declared_seed=7,
    )
    run = repository.create_experiment_run(spec["experiment_spec_id"], attempt=1, status="SUCCEEDED", return_code=0, metrics={"score": 0.91})
    analysis = repository.create_analysis_run(
        project["project_id"], protocol["protocol_version_id"], [run["experiment_run_id"]],
        analysis_code_revision="analysis-v1", analysis_plan_hash="plan-v1", status="COMPLETE",
        results={"score": 0.91, "ci_low": 0.87}, uncertainty={"ci": [0.87, 0.95]}, limitations={"sample": "small"},
    )
    evidence = repository.create_evidence_item(
        project["project_id"], evidence_type="FORMAL_ANALYSIS",
        source_ref={"analysis_run_id": analysis["analysis_run_id"], "experiment_run_id": run["experiment_run_id"]},
        content_summary="Held-out score is 0.91", validity_status="VALID",
    )
    artifacts = ArtifactStore(tmp_path / "artifact-store", repository)
    service = PaperLifecycleService(repository, artifacts, tmp_path / "build", compiler=TestPDFCompiler())
    return repository, artifacts, service, project, protocol, spec, run, analysis, evidence


def _claim_and_manuscript(lifecycle):
    repository, _, service, project, protocol, _, _, analysis, evidence = lifecycle
    claim = service.freeze_claim(
        project["project_id"], "MAIN", "Treatment improves held-out score", scope={"dataset": "held-out"},
        protocol_version_id=protocol["protocol_version_id"], analysis_run_ids=[analysis["analysis_run_id"]], evidence_ids=[evidence["evidence_id"]],
    )
    manuscript = service.create_manuscript(
        project["project_id"], title="Traceable Result", claim_ids=[claim["claim_id"]],
        sections={
            "abstract": "We test a treatment.", "introduction": "The question is measurable.",
            "methods": "We follow the frozen protocol.", "results": "The formal result is reported below.",
            "limitations": "The sample is small.", "conclusion": "The scoped claim is supported.",
        },
        numeric_bindings={"held-out score": {"analysis_run_id": analysis["analysis_run_id"], "metric": "score", "expected": 0.91}},
        literature_trace=[{"paper_id": "paper-1", "paper_version_id": "version-1", "source_chunk_id": "chunk-1"}],
        anonymous=True, ai_disclosure="AI assistance will be disclosed according to venue policy.",
        supplement_refs=["artifact:supplement"], reproducibility_refs=["git:m5"],
    )
    return claim, manuscript


def test_claim_to_protocol_chain_and_manuscript_numbers_are_traceable(lifecycle):
    repository, artifacts, service, _, protocol, spec, run, analysis, evidence = lifecycle
    claim, manuscript = _claim_and_manuscript(lifecycle)
    provenance = repository.get_claim_provenance(claim["claim_id"])
    assert provenance["evidence"][0]["evidence_id"] == evidence["evidence_id"]
    assert provenance["analyses"][0]["analysis_run_id"] == analysis["analysis_run_id"]
    assert provenance["experiment_runs"][0]["experiment_run_id"] == run["experiment_run_id"]
    assert provenance["experiment_specs"][0]["experiment_spec_id"] == spec["experiment_spec_id"]
    assert provenance["protocols"][0]["protocol_version_id"] == protocol["protocol_version_id"]
    assert manuscript["numeric_trace"]["held-out score"] == {"analysis_run_id": analysis["analysis_run_id"], "metric": "score", "value": 0.91}
    assert artifacts.verify_hash(manuscript["source_artifact_id"])
    assert artifacts.verify_hash(manuscript["pdf_artifact_id"])


def test_analysis_correction_invalidates_claim_and_manuscript(lifecycle):
    repository, _, service, _, _, _, _, analysis, _ = lifecycle
    claim, manuscript = _claim_and_manuscript(lifecycle)
    result = service.correct_analysis(analysis["analysis_run_id"], results={"score": 0.72}, reason="corrected aggregation")
    assert repository.get_analysis_run(analysis["analysis_run_id"])["status"] == "SUPERSEDED"
    assert result["corrected_analysis"]["status"] == "COMPLETE"
    assert repository.get_claim(claim["claim_id"])["status"] == "STALE"
    assert repository.get_manuscript_version(manuscript["manuscript_version_id"])["status"] == "STALE"


def test_unknown_or_invented_metric_value_is_rejected(lifecycle):
    repository, _, service, project, protocol, _, _, analysis, evidence = lifecycle
    claim = service.freeze_claim(
        project["project_id"], "MAIN", "Scoped", scope={}, protocol_version_id=protocol["protocol_version_id"],
        analysis_run_ids=[analysis["analysis_run_id"]], evidence_ids=[evidence["evidence_id"]],
    )
    base = dict(
        project_id=project["project_id"], title="Bad number", claim_ids=[claim["claim_id"]],
        sections={key: key for key in ("abstract", "introduction", "methods", "results", "limitations", "conclusion")},
        literature_trace=[], anonymous=True, ai_disclosure="disclosed", supplement_refs=[], reproducibility_refs=["git:x"],
    )
    with pytest.raises(ValueError, match="unknown formal analysis metric"):
        service.create_manuscript(**base, numeric_bindings={"made up": {"analysis_run_id": analysis["analysis_run_id"], "metric": "unknown"}})
    with pytest.raises(ValueError, match="invented or stale"):
        service.create_manuscript(**base, numeric_bindings={"wrong": {"analysis_run_id": analysis["analysis_run_id"], "metric": "score", "expected": 9.9}})


def test_latex_manuscript_supports_figures_appendix_and_references(lifecycle, tmp_path):
    repository, artifacts, service, project, protocol, _, _, analysis, evidence = lifecycle
    figure = tmp_path / "effect.png"
    figure.write_bytes(__import__("base64").b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="))
    figure_artifact = artifacts.register(figure, "FIGURE", project_id=project["project_id"], mime_type="image/png", metadata={"caption": "Held-out effect"})
    claim = service.freeze_claim(
        project["project_id"], "MAIN", "Scoped", scope={}, protocol_version_id=protocol["protocol_version_id"],
        analysis_run_ids=[analysis["analysis_run_id"]], evidence_ids=[evidence["evidence_id"]],
    )
    manuscript = service.create_manuscript(
        project["project_id"], title="Complete LaTeX", claim_ids=[claim["claim_id"]],
        sections={key: key for key in ("abstract", "introduction", "methods", "results", "limitations", "conclusion")},
        numeric_bindings={"score": {"analysis_run_id": analysis["analysis_run_id"], "metric": "score"}}, literature_trace=[],
        anonymous=True, ai_disclosure="disclosed", supplement_refs=[], reproducibility_refs=["git:HEAD"],
        figure_artifact_ids=[figure_artifact["artifact_id"]], references=[{"key": "prior-2026", "authors": "A. Author", "title": "Prior Work", "year": "2026"}],
        appendix="Reproducibility details.",
    )
    source = artifacts.get(manuscript["source_artifact_id"]).read_text(encoding="utf-8")
    assert "\\includegraphics" in source and "\\appendix" in source and "\\bibitem{prior-2026}" in source


def test_review_router_assigns_expertise_and_novelty_retrieval(lifecycle):
    _, _, service, project, _, _, _, _, _ = lifecycle
    target = project["project_id"]
    calls = []
    statistical = service.route_finding(project["project_id"], ReviewFinding(
        finding_id="stat", category="STATISTICS", severity="MAJOR", target=f"project:{target}",
        evidence_refs=["analysis:a"], impact="uncertainty changes", required_resolution="recompute uncertainty",
    ))
    implementation = service.route_finding(project["project_id"], ReviewFinding(
        finding_id="impl", category="IMPLEMENTATION", severity="MAJOR", target=f"project:{target}",
        evidence_refs=["code:c"], impact="result may differ", required_resolution="repair implementation",
    ))
    novelty = service.route_finding(project["project_id"], ReviewFinding(
        finding_id="novel", category="NOVELTY", severity="MAJOR", target=f"project:{target}",
        evidence_refs=["paper:p"], impact="claim may not be novel", required_resolution="independent search",
    ), novelty_callback=lambda finding: calls.append(finding.finding_id) or {"retrieval_run_id": "independent-1"})
    assert statistical["assigned_roles"] == ["analyst"]
    assert implementation["assigned_roles"] == ["engineer"]
    assert novelty["assigned_roles"] == ["scout", "reviewer"] and calls == ["novel"]
    with pytest.raises(ValueError, match="independent retrieval"):
        service.route_finding(project["project_id"], ReviewFinding(
            finding_id="novel-without-search", category="NOVELTY", severity="MAJOR", target=f"project:{target}",
            evidence_refs=["paper:p"], impact="claim may not be novel", required_resolution="independent search",
        ))


def test_preflight_and_human_release_approval_are_mandatory(lifecycle):
    repository, _, service, _, _, _, _, _, _ = lifecycle
    _, manuscript = _claim_and_manuscript(lifecycle)
    policy = {"version": "2026.1", "required_sections": ["abstract", "methods", "results", "limitations"], "anonymous_required": True, "supplement_required": True}
    preflight = service.preflight(manuscript["manuscript_version_id"], venue_policy=policy)
    assert preflight["passed"] and all(preflight["checks"].values())
    approval = service.request_release_approval(manuscript["manuscript_version_id"])
    with pytest.raises(PermissionError):
        service.authorize_release(manuscript["manuscript_version_id"], approval["approval_id"])
    repository.update_approval(approval["approval_id"], status="APPROVED", approved_by="human-lab-director")
    assert service.authorize_release(manuscript["manuscript_version_id"], approval["approval_id"])["status"] == "RELEASE_READY"


def test_deleted_artifact_fails_preflight_and_package_reconstruction(lifecycle, tmp_path):
    repository, artifacts, service, project, _, _, _, _, _ = lifecycle
    _, manuscript = _claim_and_manuscript(lifecycle)
    manifest = ResearchPackageExporter(repository, artifacts).export(project["project_id"], tmp_path / "package.json", workspace=Path.cwd())
    artifacts.get(manuscript["pdf_artifact_id"]).unlink()
    assert not service.preflight(manuscript["manuscript_version_id"], venue_policy={"version": "x"})["passed"]
    with pytest.raises(ValueError, match="missing or corrupt"):
        ResearchPackageExporter(repository, artifacts).reconstruct(manifest)


def test_research_package_reconstructs_from_database_artifacts_and_git(lifecycle, tmp_path):
    repository, artifacts, service, project, _, _, _, _, _ = lifecycle
    _claim_and_manuscript(lifecycle)
    exporter = ResearchPackageExporter(repository, artifacts)
    manifest_path = exporter.export(project["project_id"], tmp_path / "package.json", workspace=Path.cwd(), retrieval_run_ids=["retrieval:1"])
    package = exporter.reconstruct(manifest_path)
    assert package["project_id"] == project["project_id"]
    assert package["database"]["experiment_runs"]
    assert package["database"]["manuscript_versions"]
    assert package["literature_retrieval_run_ids"] == ["retrieval:1"]
    assert package["git"]["commit"] and package["git"]["branch"] == "research-os-v2"


def test_rebuttal_followups_and_central_config(lifecycle, monkeypatch):
    _, artifacts, service, project, _, _, _, _, _ = lifecycle
    rebuttal = service.create_rebuttal(project["project_id"], ["finding:1"], {"finding:1": "Resolved by scoped revision."}, reviewer_verified=True)
    assert artifacts.verify_hash(rebuttal["artifact_id"])
    followups = service.seed_followups(limitations=["larger sample"], negative_results=["no gain on B"], unresolved_questions=[], review_findings=["audit other domain"])
    assert len(followups) == 3 and all(item["status"] == "PENDING_NOVELTY_GATE" and not item["auto_publication"] for item in followups)
    monkeypatch.setenv("RESEARCH_DATABASE_URL", DATABASE_URL)
    monkeypatch.setenv("RESEARCH_CONFERENCE_YEARS", "2024,2025")
    monkeypatch.setenv("RESEARCH_RESOURCE_BUDGET_JSON", '{"max_experiment_minutes":5,"max_agent_tasks":7}')
    config = ResearchOSConfig.from_env()
    assert config.database_url == DATABASE_URL and config.embedding_model == "BAAI/bge-m3" and config.paid_api_enabled is False
    assert config.conference_years == (2024, 2025) and config.resource_budget["max_agent_tasks"] == 7


def test_research_cli_create_and_status_are_runnable(monkeypatch, capsys):
    monkeypatch.setenv("RESEARCH_DATABASE_URL", DATABASE_URL)
    assert cli_main(["research", "create", "--name", "CLI lifecycle", "--seed-question", "Can it run?"]) == 0
    project = __import__("json").loads(capsys.readouterr().out)
    assert cli_main(["research", "status", project["project_id"]]) == 0
    status = __import__("json").loads(capsys.readouterr().out)
    assert status["project"]["name"] == "CLI lifecycle"


def test_langgraph_runs_paper_lifecycle_and_requires_hash_bound_release_after_restart(lifecycle):
    repository, _, service, project, protocol, spec, _, analysis, evidence = lifecycle
    for kind, decision in (("IDEA_GATE", "CONTINUE"), ("PROTOCOL_GATE", "CONTINUE"), ("KILLER_GATE", "CONTINUE"), ("PROGRESS_GATE", "READY_TO_CONFIRM"), ("AUDIT_GATE", "PASS")):
        repository.create_decision(project["project_id"], kind, decision, policy_version="research-os-v2")
    created = {}

    def freeze_claim(_):
        created["claim"] = service.freeze_claim(
            project["project_id"], "MAIN", "Treatment improves held-out score", scope={"dataset": "held-out"},
            protocol_version_id=protocol["protocol_version_id"], analysis_run_ids=[analysis["analysis_run_id"]], evidence_ids=[evidence["evidence_id"]],
        )
        return {"artifact_refs": [f"claim:{created['claim']['claim_id']}"]}

    def draft(_):
        created["manuscript"] = service.create_manuscript(
            project["project_id"], title="Graph-routed paper", claim_ids=[created["claim"]["claim_id"]],
            sections={key: key for key in ("abstract", "introduction", "methods", "results", "limitations", "conclusion")},
            numeric_bindings={"score": {"analysis_run_id": analysis["analysis_run_id"], "metric": "score"}}, literature_trace=[],
            anonymous=True, ai_disclosure="AI assistance disclosed.", supplement_refs=["artifact:supplement"], reproducibility_refs=["git:HEAD"],
        )
        return {"manuscript_version_id": created["manuscript"]["manuscript_version_id"]}

    def preflight(_):
        assert service.preflight(created["manuscript"]["manuscript_version_id"], venue_policy={"version": "test", "required_sections": ["abstract", "methods", "results", "limitations"]})["passed"]
        created["approval"] = service.request_release_approval(created["manuscript"]["manuscript_version_id"])
        return {"pending_approval_id": created["approval"]["approval_id"]}

    runtime = ResearchOSRuntime(
        repository, experiment_runner=object(),
        stage_handlers={"claim_freeze": freeze_claim, "draft_manuscript": draft, "submission_preflight": preflight},
    )
    thread = f"m5-paper-{project['project_id']}"
    config = {"configurable": {"thread_id": thread}}
    initial = default_state(project["project_id"], protocol_version_id=protocol["protocol_version_id"], experiment_spec_id=spec["experiment_spec_id"])
    with postgres_checkpointer(DATABASE_URL) as first:
        paused = build_research_graph(runtime, first).invoke(initial, config)
        assert paused["__interrupt__"]
    assert repository.get_manuscript_version(created["manuscript"]["manuscript_version_id"])["status"] == "PREFLIGHT_PASSED"
    repository.update_approval(created["approval"]["approval_id"], status="APPROVED", approved_by="human-lab-director")
    with postgres_checkpointer(DATABASE_URL) as restarted:
        result = build_research_graph(runtime, restarted).invoke(Command(resume={"approval_id": created["approval"]["approval_id"]}), config)
    assert result["current_stage"] == "ARCHIVED"
    assert result["pending_approval_id"] == created["approval"]["approval_id"]
    assert repository.get_manuscript_version(created["manuscript"]["manuscript_version_id"])["status"] == "RELEASE_READY"
