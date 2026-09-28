from __future__ import annotations

import os

import pytest
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command
from sqlalchemy import create_engine, text

from ai_scientist.research_os.graph import NODE_NAMES, ResearchOSRuntime, build_research_graph, default_state, postgres_checkpointer
from ai_scientist.research_store import ResearchRepository, initialize_database
from ai_scientist import AIScientist


DATABASE_URL = os.getenv("RESEARCH_DATABASE_URL", "postgresql+psycopg://research:research@localhost:55432/research_os_test")


class RecordingRunner:
    def __init__(self):
        self.calls = 0

    def run(self, spec):
        self.calls += 1
        return {"status": "SUCCEEDED", "return_code": 0, "metrics": {"score": 0.9}}


class PendingRunner(RecordingRunner):
    def run(self, spec):
        self.calls += 1
        return {"status": "RUNNING", "metrics": {}}


@pytest.fixture
def repo():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    initialize_database(engine)
    return ResearchRepository(engine)


def _project(repo: ResearchRepository):
    project = repo.create_project("M2 project")
    question = repo.create_research_question(project["project_id"], "Does A work?")
    hypothesis = repo.create_hypothesis(project["project_id"], "A works", predicted_effect="score >= 0.8")
    protocol = repo.freeze_protocol(repo.create_protocol_version(
        project["project_id"], question["research_question_id"], hypothesis["hypothesis_id"],
        design={"seed": 1}, measurement_plan={"primary_metric": "score"}, data_split_policy={"test": "held-out"},
        analysis_plan={"test": "mean"}, stopping_rules={"runs": 1}, exclusion_rules={}, resource_budget={"minutes": 1},
    )["protocol_version_id"])
    spec = repo.create_experiment_spec(
        project_id=project["project_id"], protocol_version_id=protocol["protocol_version_id"], hypothesis_id=hypothesis["hypothesis_id"],
        objective="test", command=["python", "run.py"], workspace="workspace", metrics_contract={"score": {"op": ">=", "value": 0.8}},
        controls={}, resource_limits={}, execution_profile="local", code_revision="m2", data_manifest_hash="data", declared_seed=1,
    )
    return project, hypothesis, protocol, spec


def _decision(repo, project_id, decision_type, decision):
    return repo.create_decision(project_id, decision_type, decision, policy_version="research-os-v2")


def test_complete_node_catalogue_is_present():
    assert len(NODE_NAMES) == 38
    assert {"bootstrap_project", "submit_killer_experiment", "human_release_approval", "seed_followup_candidates"} <= set(NODE_NAMES)


def test_kill_path_never_calls_experiment_runner(repo):
    project, hypothesis, protocol, spec = _project(repo)
    decision = _decision(repo, project["project_id"], "IDEA_GATE", "KILL")
    runner = RecordingRunner()
    runtime = ResearchOSRuntime(repo, runner)
    with postgres_checkpointer(DATABASE_URL) as checkpointer:
        graph = build_research_graph(runtime, checkpointer)
        result = graph.invoke(default_state(project["project_id"], hypothesis["hypothesis_id"], protocol["protocol_version_id"], spec["experiment_spec_id"], decision["decision_id"]), {"configurable": {"thread_id": f"kill-{project['project_id']}"}})
    assert runner.calls == 0
    assert result["current_stage"] == "ARCHIVED"


def test_wait_for_human_survives_graph_restart(repo):
    project, hypothesis, protocol, spec = _project(repo)
    decision = _decision(repo, project["project_id"], "IDEA_GATE", "WAIT_FOR_HUMAN")
    thread = f"human-{project['project_id']}"
    state = default_state(project["project_id"], hypothesis["hypothesis_id"], protocol["protocol_version_id"], spec["experiment_spec_id"], decision["decision_id"])
    with postgres_checkpointer(DATABASE_URL) as first:
        graph = build_research_graph(ResearchOSRuntime(repo, RecordingRunner()), first)
        paused = graph.invoke(state, {"configurable": {"thread_id": thread}})
        assert paused["__interrupt__"]
    with postgres_checkpointer(DATABASE_URL) as restarted:
        graph = build_research_graph(ResearchOSRuntime(repo, RecordingRunner()), restarted)
        snapshot = graph.get_state({"configurable": {"thread_id": thread}})
        assert snapshot.values["project_id"] == project["project_id"]
        assert snapshot.next == ("human_start_approval",)


def test_stale_approval_is_rejected(repo):
    project, _, protocol, _ = _project(repo)
    approval = repo.create_approval(project["project_id"], "PROTOCOL", "protocol_version", protocol["protocol_version_id"], protocol["content_hash"], status="APPROVED", approved_by="human")
    v2 = repo.revise_protocol(protocol["protocol_version_id"], design={"seed": 2})
    assert not repo.approval_authorizes(approval["approval_id"], v2["protocol_version_id"], v2["content_hash"])


def test_graph_replay_does_not_duplicate_experiment(repo):
    project, hypothesis, protocol, spec = _project(repo)
    idea = _decision(repo, project["project_id"], "IDEA_GATE", "CONTINUE")
    _decision(repo, project["project_id"], "PROTOCOL_GATE", "CONTINUE")
    _decision(repo, project["project_id"], "KILLER_GATE", "KILL")
    runner = RecordingRunner()
    runtime = ResearchOSRuntime(repo, runner)
    state = default_state(project["project_id"], hypothesis["hypothesis_id"], protocol["protocol_version_id"], spec["experiment_spec_id"], idea["decision_id"])
    with postgres_checkpointer(DATABASE_URL) as checkpointer:
        graph = build_research_graph(runtime, checkpointer)
        graph.invoke(state, {"configurable": {"thread_id": f"replay-a-{project['project_id']}"}})
        graph.invoke(state, {"configurable": {"thread_id": f"replay-b-{project['project_id']}"}})
    assert runner.calls == 1
    assert len(repo.list_experiment_runs(spec["experiment_spec_id"])) == 1


def test_experiment_completion_after_restart_resumes_analysis(repo):
    project, hypothesis, protocol, spec = _project(repo)
    idea = _decision(repo, project["project_id"], "IDEA_GATE", "CONTINUE")
    _decision(repo, project["project_id"], "PROTOCOL_GATE", "CONTINUE")
    _decision(repo, project["project_id"], "KILLER_GATE", "KILL")
    runner = PendingRunner()
    thread = f"experiment-restart-{project['project_id']}"
    config = {"configurable": {"thread_id": thread}}
    with postgres_checkpointer(DATABASE_URL) as first:
        graph = build_research_graph(ResearchOSRuntime(repo, runner), first)
        paused = graph.invoke(default_state(project["project_id"], hypothesis["hypothesis_id"], protocol["protocol_version_id"], spec["experiment_spec_id"], idea["decision_id"]), config)
        assert paused["__interrupt__"]
        run_id = graph.get_state(config).values["active_experiment_run_id"]
    repo.update_experiment_run(run_id, status="SUCCEEDED", return_code=0, metrics={"score": 0.9})
    with postgres_checkpointer(DATABASE_URL) as restarted:
        graph = build_research_graph(ResearchOSRuntime(repo, runner), restarted)
        result = graph.invoke(Command(resume={"experiment_run_id": run_id}), config)
    assert result["current_stage"] == "ARCHIVED"
    assert runner.calls == 1


def test_reframe_routes_back_to_discovery_without_experiment(repo):
    project, hypothesis, protocol, spec = _project(repo)
    decision = _decision(repo, project["project_id"], "IDEA_GATE", "REFRAME")
    runner = RecordingRunner()
    runtime = ResearchOSRuntime(repo, runner, max_reframes=1)
    with postgres_checkpointer(DATABASE_URL) as checkpointer:
        result = build_research_graph(runtime, checkpointer).invoke(
            default_state(project["project_id"], hypothesis["hypothesis_id"], protocol["protocol_version_id"], spec["experiment_spec_id"], decision["decision_id"]),
            {"configurable": {"thread_id": f"reframe-{project['project_id']}"}},
        )
    assert runner.calls == 0
    assert result["current_stage"] == "ARCHIVED"
    assert "REFRAME_LIMIT_REACHED" == result["error_code"]


def test_fatal_progress_decision_prevents_confirmation_and_manuscript(repo):
    project, hypothesis, protocol, spec = _project(repo)
    idea = _decision(repo, project["project_id"], "IDEA_GATE", "CONTINUE")
    _decision(repo, project["project_id"], "PROTOCOL_GATE", "CONTINUE")
    _decision(repo, project["project_id"], "KILLER_GATE", "CONTINUE")
    _decision(repo, project["project_id"], "PROGRESS_GATE", "KILL")
    runtime = ResearchOSRuntime(repo, RecordingRunner())
    with postgres_checkpointer(DATABASE_URL) as checkpointer:
        graph = build_research_graph(runtime, checkpointer)
        result = graph.invoke(default_state(project["project_id"], hypothesis["hypothesis_id"], protocol["protocol_version_id"], spec["experiment_spec_id"], idea["decision_id"]), {"configurable": {"thread_id": f"fatal-{project['project_id']}"}})
        history = [snapshot.values.get("current_stage") for snapshot in graph.get_state_history({"configurable": {"thread_id": f"fatal-{project['project_id']}"}})]
    assert result["current_stage"] == "ARCHIVED"
    assert "CONFIRMATION" not in history
    assert "MANUSCRIPT" not in history


def test_legacy_ai_scientist_facade_runs_research_os(repo, tmp_path):
    project, hypothesis, protocol, spec = _project(repo)
    decision = _decision(repo, project["project_id"], "IDEA_GATE", "KILL")
    runner = RecordingRunner()
    scientist = AIScientist(db_path=tmp_path / "legacy.db", research_database_url=DATABASE_URL)
    result = scientist.run_research_os(
        default_state(project["project_id"], hypothesis["hypothesis_id"], protocol["protocol_version_id"], spec["experiment_spec_id"], decision["decision_id"]),
        runner,
        thread_id=f"facade-{project['project_id']}",
    )
    assert result["current_stage"] == "ARCHIVED"
    assert runner.calls == 0
