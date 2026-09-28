from __future__ import annotations

import csv
import json
import os
import subprocess

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from pydantic import ValidationError
from sqlalchemy import create_engine

from ai_scientist.research_os.actions import ActionBroker
from ai_scientist.research_os.agents import (
    ActionRequest,
    AgentLab,
    Capability,
    ClaimRecord,
    CodexExecutor,
    HumanAssistedExecutor,
    MockExecutor,
    PaidAPIExecutor,
    ResearchRole,
    ReviewFinding,
    TaskResult,
    TaskSpec,
)
from ai_scientist.research_os.architecture_ablation import run_architecture_ablation
from ai_scientist.research_os.graph import ResearchOSRuntime, build_research_graph, default_state, postgres_checkpointer
from ai_scientist.research_store import ResearchRepository, initialize_database
from benchmarks.discovery.discovery_loop import AutonomousDiscoveryLoop
from benchmarks.discovery.problem import ResearchProblem
from benchmarks.runners.baseline_runner import run_baseline


DATABASE_URL = os.getenv("RESEARCH_DATABASE_URL", "postgresql+psycopg://research:research@localhost:55432/research_os_test")


def _task(tmp_path, role=ResearchRole.SCOUT, capability=Capability.PRIOR_SEARCH, task_id="task-1"):
    return TaskSpec(
        task_id=task_id,
        role=role,
        capability=capability,
        objective="Produce one bounded evidence artifact.",
        workspace=str(tmp_path),
        input_refs=["project:test"],
        acceptance_criteria=["structured result"],
    )


def test_contracts_are_strict_and_blocking_findings_require_evidence(tmp_path):
    with pytest.raises(ValidationError):
        TaskSpec(**{**_task(tmp_path).model_dump(), "unexpected": True})
    with pytest.raises(ValidationError):
        ReviewFinding(
            finding_id="f1", category="STATISTICS", severity="BLOCKING", target="analysis:1",
            evidence_refs=[], impact="May reverse the conclusion", required_resolution="Recompute",
        )
    finding = ReviewFinding(
        finding_id="f1", category="STATISTICS", severity="BLOCKING", target="analysis:1",
        evidence_refs=["artifact:calculation"], impact="May reverse the conclusion", required_resolution="Recompute",
    )
    claim = ClaimRecord(
        claim_id="c1", text="Method improves score", scope="held-out test", protocol_version_id="p1",
        analysis_run_ids=["a1"], evidence_ids=["e1"], counterevidence_ids=[], status="SUPPORTED",
    )
    assert finding.severity == "BLOCKING"
    assert claim.status == "SUPPORTED"


def test_role_permissions_are_enforced_before_executor(tmp_path):
    executor = MockExecutor()
    lab = AgentLab({role: executor for role in ResearchRole})
    accepted = lab.run(_task(tmp_path))
    assert accepted.status == "SUCCEEDED"
    with pytest.raises(PermissionError):
        lab.run(_task(tmp_path, ResearchRole.EDITOR, Capability.MODIFY_SCIENTIFIC_NUMBERS, "forbidden"))
    with pytest.raises(PermissionError):
        lab.run(_task(tmp_path, ResearchRole.SCOUT, Capability.APPROVE_NOVELTY, "self-approve"))
    assert [call.task_id for call in executor.calls] == ["task-1"]


def test_codex_executor_builds_supported_structured_task_package(tmp_path):
    commands = []

    def fake_run(command, **kwargs):
        commands.append((command, kwargs))
        output_path = command[command.index("--output-last-message") + 1]
        result = TaskResult(task_id="codex-task", role=ResearchRole.ENGINEER, status="SUCCEEDED", summary="validated", output_refs=["artifact:1"])
        open(output_path, "w", encoding="utf-8").write(result.model_dump_json())
        return subprocess.CompletedProcess(command, 0, stdout="event", stderr="")

    task = _task(tmp_path, ResearchRole.ENGINEER, Capability.IMPLEMENT_EXPERIMENT, "codex-task")
    result = CodexExecutor(command_runner=fake_run).run(task)
    command, kwargs = commands[0]
    assert result.status == "SUCCEEDED"
    assert command[0] == "codex" and "exec" in command
    assert "--ephemeral" in command and "--output-schema" in command and "--output-last-message" in command
    assert command[command.index("--cd") + 1] == str(tmp_path.resolve())
    package = tmp_path / ".research-os" / "tasks" / "codex-task"
    assert (package / "input.json").exists() and (package / "execution.json").exists()
    assert "secret" not in (package / "execution.json").read_text(encoding="utf-8").lower()
    assert kwargs["shell"] is False
    assert kwargs["stdin"] is subprocess.DEVNULL


def test_human_assisted_executor_uses_resumable_langgraph_interrupt(tmp_path):
    executor = HumanAssistedExecutor()
    graph = StateGraph(dict)
    graph.add_node("human", lambda state: {"result": executor.run(_task(tmp_path, ResearchRole.PI, Capability.STUDY_DESIGN, "human-task")).model_dump()})
    graph.add_edge(START, "human")
    graph.add_edge("human", END)
    compiled = graph.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "human-task"}}
    paused = compiled.invoke({}, config)
    assert paused["__interrupt__"]
    package_path = paused["__interrupt__"][0].value["package_path"]
    assert os.path.exists(package_path)
    response = TaskResult(task_id="human-task", role=ResearchRole.PI, status="SUCCEEDED", summary="human result")
    resumed = compiled.invoke(Command(resume=response.model_dump(mode="json")), config)
    assert resumed["result"]["status"] == "SUCCEEDED"


def test_paid_api_is_disabled_by_default(tmp_path):
    with pytest.raises(PermissionError):
        PaidAPIExecutor().run(_task(tmp_path))


def test_action_broker_priority_idempotency_and_risk_policy(tmp_path):
    calls = []

    def handler(channel):
        return lambda request, session: calls.append(channel) or {"channel": channel, "artifact_refs": []}

    broker = ActionBroker(
        tmp_path / "actions", handlers={"api_cli": handler("api_cli"), "http": handler("http"), "playwright": handler("playwright")},
        allowed_domains={"example.org"},
    )
    request = ActionRequest(
        action_id="a1", operation="fetch", target="https://example.org/data", domain="example.org",
        allowed_channels=["playwright", "http", "api_cli"], idempotency_key="fetch:1", risk="LOW",
    )
    first = broker.execute(request)
    second = broker.execute(request)
    assert first == second and calls == ["api_cli"]
    with pytest.raises(PermissionError):
        broker.execute(request.model_copy(update={"action_id": "a2", "domain": "evil.example", "idempotency_key": "fetch:2"}))
    with pytest.raises(PermissionError):
        broker.execute(request.model_copy(update={"action_id": "a3", "risk": "HIGH", "idempotency_key": "fetch:3"}))
    session = broker.browser_session("a4")
    assert session["profile_dir"].startswith(str((tmp_path / "actions").resolve()))
    assert {"trace", "screenshot", "downloads", "metadata"} <= set(session)


def test_frozen_architecture_ablation_reports_all_variants_and_metrics():
    result = run_architecture_ablation("benchmarks/agent_architecture/frozen_tasks_v1.json")
    assert set(result) == {"six_role", "pi_engineer_merged", "analyst_reviewer_merged", "self_review"}
    required = {"valid_error_detection", "false_blocking", "protocol_violation", "human_repair_time", "execution_cost_usage"}
    assert all(required == set(metrics) for metrics in result.values())


def test_langgraph_role_nodes_dispatch_bounded_agent_tasks(tmp_path):
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    initialize_database(engine)
    repository = ResearchRepository(engine)
    project = repository.create_project("M4 dispatch")
    decision = repository.create_decision(project["project_id"], "IDEA_GATE", "KILL", policy_version="research-os-v2")
    executor = MockExecutor()
    lab = AgentLab({role: executor for role in ResearchRole})
    runtime = ResearchOSRuntime(repository, experiment_runner=MockExecutor(), agent_lab=lab, task_workspace=str(tmp_path))
    with postgres_checkpointer(DATABASE_URL) as checkpointer:
        result = build_research_graph(runtime, checkpointer).invoke(
            default_state(project["project_id"], decision_id=decision["decision_id"]),
            {"configurable": {"thread_id": f"m4-dispatch-{project['project_id']}"}},
        )
    assert result["current_stage"] == "ARCHIVED"
    assert [(call.role, call.capability) for call in executor.calls] == [
        (ResearchRole.SCOUT, Capability.DISCOVER_CANDIDATES),
        (ResearchRole.SCOUT, Capability.PRIOR_SEARCH),
        (ResearchRole.REVIEWER, Capability.INDEPENDENT_NOVELTY_AUDIT),
        (ResearchRole.SCOUT, Capability.DISCOVER_CANDIDATES),
    ]


def test_mini_e2e_uses_existing_autonomous_discovery_benchmark(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    fields = ["date", "HUFL", "HULL", "MUFL", "MULL", "LUFL", "LULL", "OT"]
    with (data / "ETTm1.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for i in range(40):
            writer.writerow({field: i + (j * 0.1) for j, field in enumerate(fields)})
    baseline = run_baseline("ettm1", "dlinear", data_root=data, max_windows=4, persist=False, lookback=4, horizon=2, split_points=(20, 30))
    discovery = AutonomousDiscoveryLoop().run(
        ResearchProblem("m4", "six role mini e2e", "ETTm1", ["DLinear"]), baseline, data, tmp_path / "trajectory",
        max_rounds=1, max_windows=4, dataset_kwargs={"lookback": 4, "horizon": 2, "split_points": (20, 30)},
    )
    executor = MockExecutor()
    lab = AgentLab({role: executor for role in ResearchRole})
    stages = [
        (ResearchRole.SCOUT, Capability.DISCOVER_CANDIDATES),
        (ResearchRole.REVIEWER, Capability.INDEPENDENT_NOVELTY_AUDIT),
        (ResearchRole.PI, Capability.STUDY_DESIGN),
        (ResearchRole.ENGINEER, Capability.IMPLEMENT_EXPERIMENT),
        (ResearchRole.ANALYST, Capability.FORMAL_ANALYSIS),
        (ResearchRole.REVIEWER, Capability.INDEPENDENT_RESULT_AUDIT),
    ]
    results = [lab.run(_task(tmp_path, role, capability, f"e2e-{index}")) for index, (role, capability) in enumerate(stages)]
    assert discovery["state"].experiment_results
    assert discovery["state"].final_test["protocol"] == "test evaluated once after candidate freeze"
    assert len(results) == 6 and all(result.status == "SUCCEEDED" for result in results)
