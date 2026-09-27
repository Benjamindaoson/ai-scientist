from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from ai_scientist.research_store import (
    ArtifactStore,
    FrozenRecordError,
    ResearchRepository,
    SQLiteImporter,
    initialize_database,
)


DATABASE_URL = os.getenv(
    "RESEARCH_DATABASE_URL",
    "postgresql+psycopg://research:research@localhost:55432/research_os",
)


@pytest.fixture(scope="module")
def engine():
    candidate = create_engine(DATABASE_URL, pool_pre_ping=True)
    try:
        with candidate.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - failure message is the test contract
        pytest.fail(f"M1 integration tests require real PostgreSQL: {exc}")
    initialize_database(candidate)
    with candidate.begin() as connection:
        tables = inspect(connection).get_table_names(schema="research")
        for table in reversed(tables):
            connection.execute(text(f'TRUNCATE TABLE research."{table}" CASCADE'))
    yield candidate
    candidate.dispose()


def _scientific_chain(repo: ResearchRepository) -> dict[str, str]:
    project = repo.create_project("durable project", domain="ml", seed_question="why?")
    question = repo.create_research_question(project["project_id"], "Does A improve B?")
    hypothesis = repo.create_hypothesis(
        project["project_id"],
        claim="A improves B",
        rationale="mechanism",
        predicted_effect="score >= 0.8",
        falsification_conditions=["score < 0.8"],
    )
    protocol = repo.create_protocol_version(
        project["project_id"],
        question["research_question_id"],
        hypothesis["hypothesis_id"],
        design={"seed": 7},
        measurement_plan={"primary_metric": "score"},
        data_split_policy={"test": "held-out"},
        analysis_plan={"test": "mean"},
        stopping_rules={"runs": 1},
        exclusion_rules={},
        resource_budget={"minutes": 5},
    )
    frozen = repo.freeze_protocol(protocol["protocol_version_id"])
    spec = repo.create_experiment_spec(
        project_id=project["project_id"],
        protocol_version_id=frozen["protocol_version_id"],
        hypothesis_id=hypothesis["hypothesis_id"],
        objective="test A",
        command=["python", "run.py"],
        workspace="workspace",
        metrics_contract={"score": {"op": ">=", "value": 0.8}},
        controls={"baseline": True},
        resource_limits={"timeout_seconds": 30},
        execution_profile="local",
        code_revision="abc123",
        data_manifest_hash="data123",
        declared_seed=7,
    )
    run = repo.create_experiment_run(spec["experiment_spec_id"], attempt=1, status="SUCCEEDED", metrics={"score": 0.9})
    analysis = repo.create_analysis_run(
        project["project_id"],
        frozen["protocol_version_id"],
        [run["experiment_run_id"]],
        analysis_code_revision="analysis123",
        analysis_plan_hash="plan123",
        status="VALID",
        results={"score": 0.9},
    )
    evidence = repo.create_evidence_item(
        project["project_id"],
        evidence_type="ANALYSIS",
        source_ref={"analysis_run_id": analysis["analysis_run_id"]},
        content_summary="score was 0.9",
        validity_status="VALID",
    )
    claim = repo.create_claim(project["project_id"], "RESULT", "A improves B", scope={"dataset": "held-out"}, created_by_role="analyst")
    repo.link_claim_evidence(claim["claim_id"], evidence["evidence_id"], "SUPPORTS", "formal analysis", "analyst")
    return {
        "project_id": project["project_id"],
        "question_id": question["research_question_id"],
        "hypothesis_id": hypothesis["hypothesis_id"],
        "protocol_id": frozen["protocol_version_id"],
        "spec_id": spec["experiment_spec_id"],
        "run_id": run["experiment_run_id"],
        "analysis_id": analysis["analysis_run_id"],
        "evidence_id": evidence["evidence_id"],
        "claim_id": claim["claim_id"],
    }


def test_required_research_schema_exists(engine):
    expected = {
        "programs", "projects", "ideas", "idea_gate_evaluations", "research_questions",
        "hypotheses", "protocol_versions", "tasks", "agent_runs", "action_requests",
        "experiment_specs", "experiment_runs", "analysis_runs", "claims", "evidence_items",
        "claim_evidence_links", "objections", "review_findings", "decisions", "approvals",
        "artifacts", "manuscript_versions",
    }
    assert expected <= set(inspect(engine).get_table_names(schema="research"))


def test_full_scientific_relation_survives_restart(engine):
    ids = _scientific_chain(ResearchRepository(engine))
    engine.dispose()
    restarted_engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    restarted = ResearchRepository(restarted_engine)
    chain = restarted.get_claim_provenance(ids["claim_id"])
    assert chain["claim"]["claim_id"] == ids["claim_id"]
    assert chain["evidence"][0]["evidence_id"] == ids["evidence_id"]
    assert chain["analyses"][0]["analysis_run_id"] == ids["analysis_id"]
    assert chain["experiment_runs"][0]["experiment_run_id"] == ids["run_id"]
    assert chain["experiment_specs"][0]["experiment_spec_id"] == ids["spec_id"]
    assert chain["protocols"][0]["protocol_version_id"] == ids["protocol_id"]
    restarted_engine.dispose()


def test_frozen_protocol_is_immutable_and_revision_retains_v1(engine):
    repo = ResearchRepository(engine)
    ids = _scientific_chain(repo)
    v1 = repo.get_protocol(ids["protocol_id"])
    with pytest.raises(FrozenRecordError):
        repo.update_protocol(ids["protocol_id"], measurement_plan={"primary_metric": "changed"})
    v2 = repo.revise_protocol(ids["protocol_id"], measurement_plan={"primary_metric": "score", "secondary": "latency"})
    assert v2["version"] == v1["version"] + 1
    assert v2["content_hash"] != v1["content_hash"]
    assert repo.get_protocol(ids["protocol_id"])["measurement_plan"] == {"primary_metric": "score"}


def test_approval_is_bound_to_exact_target_hash(engine):
    repo = ResearchRepository(engine)
    ids = _scientific_chain(repo)
    v1 = repo.get_protocol(ids["protocol_id"])
    approval = repo.create_approval(
        ids["project_id"], "PROTOCOL", "protocol_version", ids["protocol_id"], v1["content_hash"], status="APPROVED", approved_by="human"
    )
    v2 = repo.revise_protocol(ids["protocol_id"], design={"seed": 11})
    assert repo.approval_authorizes(approval["approval_id"], ids["protocol_id"], v1["content_hash"])
    assert not repo.approval_authorizes(approval["approval_id"], v2["protocol_version_id"], v2["content_hash"])


def test_objection_and_experiment_evidence_persist(engine):
    repo = ResearchRepository(engine)
    ids = _scientific_chain(repo)
    objection = repo.create_objection(
        ids["project_id"], "claim", ids["claim_id"], "VALIDITY", "MAJOR", "Check scope", "scope may be narrow", raised_by_role="reviewer"
    )
    restarted = ResearchRepository(create_engine(DATABASE_URL, pool_pre_ping=True))
    assert restarted.get_objection(objection["objection_id"])["title"] == "Check scope"
    assert restarted.get_experiment_run(ids["run_id"])["metrics"] == {"score": 0.9}
    assert restarted.get_claim_provenance(ids["claim_id"])["links"][0]["relation"] == "SUPPORTS"


def test_artifact_store_register_get_verify_and_project_listing(engine, tmp_path: Path):
    repo = ResearchRepository(engine)
    project = repo.create_project("artifact project")
    source = tmp_path / "result.txt"
    source.write_text("immutable result", encoding="utf-8")
    store = ArtifactStore(tmp_path / "artifacts", repo)
    artifact = store.register(source, "RESULT", project_id=project["project_id"], mime_type="text/plain")
    assert artifact["sha256"] == hashlib.sha256(b"immutable result").hexdigest()
    assert store.get(artifact["artifact_id"]).read_text(encoding="utf-8") == "immutable result"
    assert store.verify_hash(artifact["artifact_id"])
    assert [item["artifact_id"] for item in store.list_for_project(project["project_id"])] == [artifact["artifact_id"]]
    store.get(artifact["artifact_id"]).write_text("tampered", encoding="utf-8")
    assert not store.verify_hash(artifact["artifact_id"])


def test_sqlite_import_twice_is_idempotent_and_source_is_unchanged(engine, tmp_path: Path):
    source = tmp_path / "legacy.db"
    connection = sqlite3.connect(source)
    connection.execute("CREATE TABLE projects (id TEXT PRIMARY KEY, name TEXT, description TEXT, seed_question TEXT, domain TEXT)")
    connection.execute("INSERT INTO projects VALUES ('legacy-project', 'Legacy', 'desc', 'question', 'ml')")
    connection.commit()
    connection.close()
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    importer = SQLiteImporter(ResearchRepository(engine))
    first = importer.import_database(source)
    second = importer.import_database(source)
    assert first["projects"] == 1
    assert second["projects"] == 0
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    assert ResearchRepository(engine).get_project_by_legacy_id("legacy-project")["name"] == "Legacy"
