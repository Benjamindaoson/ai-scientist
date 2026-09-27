from __future__ import annotations

from typing import Any, Callable

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from ai_scientist.research_os.policy import audit_route, decision_value, idea_route, killer_route, progress_route, protocol_route

from .runtime import ResearchOSRuntime
from .state import ResearchExecutionState


NODE_NAMES = (
    "bootstrap_project", "discover_candidates", "scout_prior_search", "reviewer_novelty_search", "evaluate_10_10_gate", "human_start_approval",
    "formalize_question", "design_study", "design_measurement", "review_protocol", "protocol_gate", "freeze_protocol",
    "engineering_preflight", "implement_killer_experiment", "submit_killer_experiment", "wait_for_experiment", "analyze_killer_experiment", "interpret_killer_result", "killer_gate",
    "plan_next_research_action", "implement_experiment", "submit_experiment", "wait_for_experiment_result", "analyze_experiment", "update_scientific_model", "research_progress_gate",
    "freeze_confirmatory_protocol", "run_confirmation", "formal_analysis", "independent_result_audit", "claim_freeze", "draft_manuscript", "independent_paper_review",
    "revision_router", "submission_preflight", "human_release_approval", "archive_project", "seed_followup_candidates",
)


def _stage(runtime: ResearchOSRuntime, name: str, role: str | None = None, capability: str | None = None) -> Callable[[ResearchExecutionState], dict[str, Any]]:
    def node(state: ResearchExecutionState) -> dict[str, Any]:
        update = runtime.dispatch_task(name, role, capability, state) if role and capability else {}
        return {"current_stage": name.upper(), "active_role": role, **update, **runtime.run_stage(name, state)}
    return node


def build_research_graph(runtime: ResearchOSRuntime, checkpointer):
    graph = StateGraph(ResearchExecutionState)
    roles = {
        "discover_candidates": "scout", "scout_prior_search": "scout", "reviewer_novelty_search": "reviewer",
        "formalize_question": "pi", "design_study": "pi", "design_measurement": "analyst", "review_protocol": "reviewer",
        "engineering_preflight": "engineer", "implement_killer_experiment": "engineer", "analyze_killer_experiment": "analyst",
        "interpret_killer_result": "pi", "plan_next_research_action": "pi", "implement_experiment": "engineer",
        "analyze_experiment": "analyst", "update_scientific_model": "pi", "run_confirmation": "engineer",
        "formal_analysis": "analyst", "independent_result_audit": "reviewer", "draft_manuscript": "editor",
        "independent_paper_review": "reviewer", "submission_preflight": "editor", "seed_followup_candidates": "scout",
    }
    capabilities = {
        "discover_candidates": "discover_candidates", "scout_prior_search": "prior_search", "reviewer_novelty_search": "independent_novelty_audit",
        "formalize_question": "formalize_question", "design_study": "study_design", "design_measurement": "design_measurement", "review_protocol": "protocol_audit",
        "engineering_preflight": "test_code", "implement_killer_experiment": "implement_experiment", "analyze_killer_experiment": "formal_analysis",
        "interpret_killer_result": "interpretation", "plan_next_research_action": "next_research_action", "implement_experiment": "implement_experiment",
        "analyze_experiment": "formal_analysis", "update_scientific_model": "interpretation", "run_confirmation": "implement_experiment",
        "formal_analysis": "formal_analysis", "independent_result_audit": "independent_result_audit", "draft_manuscript": "draft_paper",
        "independent_paper_review": "paper_review", "submission_preflight": "submission_package", "seed_followup_candidates": "discover_candidates",
    }
    special = {
        "evaluate_10_10_gate", "human_start_approval", "protocol_gate", "submit_killer_experiment",
        "submit_experiment", "wait_for_experiment", "wait_for_experiment_result", "killer_gate",
        "research_progress_gate", "independent_result_audit", "human_release_approval", "archive_project",
        "seed_followup_candidates",
    }
    for name in NODE_NAMES:
        if name not in special:
            graph.add_node(name, _stage(runtime, name, roles.get(name), capabilities.get(name)))

    def evaluate(state: ResearchExecutionState) -> dict[str, Any]:
        decision = runtime.decision(state["project_id"], "IDEA_GATE", state.get("last_decision_id"))
        value = decision_value(decision)
        count = state.get("reframe_count", 0) + (1 if value == "REFRAME" else 0)
        return {
            "current_stage": "IDEA_GATE", "last_decision_id": decision["decision_id"] if decision else None,
            "reframe_count": count, "error_code": "REFRAME_LIMIT_REACHED" if value == "REFRAME" and count > runtime.max_reframes else None,
        }

    def gate(state: ResearchExecutionState, kind: str, stage: str) -> dict[str, Any]:
        decision = runtime.decision(state["project_id"], kind, state.get("last_decision_id"))
        return {"current_stage": stage, "last_decision_id": decision["decision_id"] if decision else None}

    def human_start(state: ResearchExecutionState) -> dict[str, Any]:
        response = interrupt({"kind": "START_APPROVAL", "project_id": state["project_id"]})
        return {"current_stage": "HUMAN_START_APPROVED" if response else "WAIT_FOR_HUMAN"}

    def submit(state: ResearchExecutionState) -> dict[str, Any]:
        spec_id = state.get("active_experiment_spec_id")
        if not spec_id:
            return {"error_code": "MISSING_EXPERIMENT_SPEC", "current_stage": "BLOCKED"}
        run = runtime.submit_experiment(spec_id)
        return {"active_experiment_run_id": run["experiment_run_id"], "current_stage": "EXPERIMENT_SUBMITTED"}

    def wait_for_run(state: ResearchExecutionState) -> dict[str, Any]:
        run_id = state.get("active_experiment_run_id")
        run = runtime.repository.get_experiment_run(run_id) if run_id else None
        if run and run["status"] in {"PENDING", "RUNNING", "SUBMITTED"}:
            interrupt({"kind": "EXPERIMENT", "experiment_run_id": run_id})
            run = runtime.repository.get_experiment_run(run_id)
        return {"current_stage": "EXPERIMENT_COMPLETE" if run and run["status"] not in {"PENDING", "RUNNING", "SUBMITTED"} else "WAIT_FOR_EXPERIMENT"}

    def release(state: ResearchExecutionState) -> dict[str, Any]:
        response = interrupt({"kind": "FINAL_RELEASE", "project_id": state["project_id"], "approval_id": state.get("pending_approval_id")})
        approval_id = response.get("approval_id") if isinstance(response, dict) else None
        manuscript_id = state.get("manuscript_version_id")
        if not approval_id or not manuscript_id or not runtime.release_authorized(approval_id, manuscript_id):
            raise PermissionError("explicit hash-bound human release approval is required")
        runtime.repository.update_manuscript_version(manuscript_id, status="RELEASE_READY")
        return {"current_stage": "RELEASE_APPROVED", "pending_approval_id": approval_id}

    graph.add_node("evaluate_10_10_gate", evaluate)
    graph.add_node("human_start_approval", human_start)
    graph.add_node("protocol_gate", lambda state: gate(state, "PROTOCOL_GATE", "PROTOCOL_GATE"))
    graph.add_node("submit_killer_experiment", submit)
    graph.add_node("submit_experiment", submit)
    graph.add_node("wait_for_experiment", wait_for_run)
    graph.add_node("wait_for_experiment_result", wait_for_run)
    graph.add_node("killer_gate", lambda state: gate(state, "KILLER_GATE", "KILLER_GATE"))
    graph.add_node("research_progress_gate", lambda state: gate(state, "PROGRESS_GATE", "PROGRESS_GATE"))
    def independent_audit(state: ResearchExecutionState) -> dict[str, Any]:
        return {**gate(state, "AUDIT_GATE", "RESULT_AUDIT"), **runtime.dispatch_task("independent_result_audit", "reviewer", "independent_result_audit", state)}

    graph.add_node("independent_result_audit", independent_audit)
    graph.add_node("human_release_approval", release)
    graph.add_node("archive_project", lambda _: {"current_stage": "ARCHIVED", "active_role": None})
    graph.add_node("seed_followup_candidates", lambda state: {"current_stage": "ARCHIVED", "active_role": "scout", **runtime.dispatch_task("seed_followup_candidates", "scout", "discover_candidates", state)})

    graph.add_edge(START, "bootstrap_project")
    for left, right in zip(("bootstrap_project", "discover_candidates", "scout_prior_search", "reviewer_novelty_search"), ("discover_candidates", "scout_prior_search", "reviewer_novelty_search", "evaluate_10_10_gate")):
        graph.add_edge(left, right)
    graph.add_conditional_edges("evaluate_10_10_gate", lambda s: idea_route(decision_value(runtime.decision(s["project_id"], "IDEA_GATE", s.get("last_decision_id"))), s.get("reframe_count", 0), runtime.max_reframes), {"continue": "formalize_question", "reframe": "discover_candidates", "human": "human_start_approval", "archive": "archive_project"})
    graph.add_edge("human_start_approval", "formalize_question")
    for left, right in zip(("formalize_question", "design_study", "design_measurement", "review_protocol"), ("design_study", "design_measurement", "review_protocol", "protocol_gate")):
        graph.add_edge(left, right)
    graph.add_conditional_edges("protocol_gate", lambda s: protocol_route(decision_value(runtime.decision(s["project_id"], "PROTOCOL_GATE", s.get("last_decision_id")))), {"pass": "freeze_protocol", "science": "design_study", "measurement": "design_measurement", "review": "review_protocol", "archive": "archive_project"})
    for left, right in zip(("freeze_protocol", "engineering_preflight", "implement_killer_experiment", "submit_killer_experiment", "wait_for_experiment", "analyze_killer_experiment", "interpret_killer_result"), ("engineering_preflight", "implement_killer_experiment", "submit_killer_experiment", "wait_for_experiment", "analyze_killer_experiment", "interpret_killer_result", "killer_gate")):
        graph.add_edge(left, right)
    graph.add_conditional_edges("killer_gate", lambda s: killer_route(decision_value(runtime.decision(s["project_id"], "KILLER_GATE", s.get("last_decision_id")))), {"continue": "plan_next_research_action", "reframe": "formalize_question", "human": "human_start_approval", "archive": "archive_project"})
    for left, right in zip(("plan_next_research_action", "implement_experiment", "submit_experiment", "wait_for_experiment_result", "analyze_experiment", "update_scientific_model"), ("implement_experiment", "submit_experiment", "wait_for_experiment_result", "analyze_experiment", "update_scientific_model", "research_progress_gate")):
        graph.add_edge(left, right)
    graph.add_conditional_edges("research_progress_gate", lambda s: progress_route(decision_value(runtime.decision(s["project_id"], "PROGRESS_GATE", s.get("last_decision_id")))), {"more": "plan_next_research_action", "confirm": "freeze_confirmatory_protocol", "reframe": "formalize_question", "human": "human_start_approval", "archive": "archive_project"})
    for left, right in zip(("freeze_confirmatory_protocol", "run_confirmation", "formal_analysis"), ("run_confirmation", "formal_analysis", "independent_result_audit")):
        graph.add_edge(left, right)
    graph.add_conditional_edges("independent_result_audit", lambda s: audit_route(decision_value(runtime.decision(s["project_id"], "AUDIT_GATE", s.get("last_decision_id")))), {"pass": "claim_freeze", "engineering": "implement_experiment", "analysis": "formal_analysis", "science": "update_scientific_model", "novelty": "reviewer_novelty_search", "archive": "archive_project"})
    for left, right in zip(("claim_freeze", "draft_manuscript", "independent_paper_review", "revision_router", "submission_preflight", "human_release_approval", "archive_project", "seed_followup_candidates"), ("draft_manuscript", "independent_paper_review", "revision_router", "submission_preflight", "human_release_approval", "archive_project", "seed_followup_candidates", END)):
        graph.add_edge(left, right)
    return graph.compile(checkpointer=checkpointer)
