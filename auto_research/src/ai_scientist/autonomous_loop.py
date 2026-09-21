"""Evidence-driven autonomous research loop."""
from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any

from .ablation import AblationExecutor, AblationPlanner
from .evidence_graph import EvidenceGraph
from .experiment import ExperimentEvaluator, ExperimentResult, ExperimentRunner, ExperimentSpec
from .experiment.engineer import ExperimentEngineer
from .hypothesis import Hypothesis, HypothesisEvolver
from .integrity import IntegrityAuditor
from .manuscript import ManuscriptBuilder
from .research_state import ResearchState
from .review_loop import ReviewActionRouter, ReviewIssue
from .scientific_review import MetaReviewer, RebuttalPlanner, ScientificReviewer


class AutonomousResearchLoop:
    """Connect reasoning, experiments, evidence, review, rebuttal, and revision."""

    def __init__(self, gateway=None, runner: ExperimentRunner | None = None):
        self.gateway = gateway
        self.runner = runner or ExperimentRunner()
        self.evaluator = ExperimentEvaluator()
        self.evolver = HypothesisEvolver(gateway=gateway)
        self.ablation_planner = AblationPlanner()
        self.ablation_executor = AblationExecutor(self.runner)
        self.review_router = ReviewActionRouter()
        self.manuscript_builder = ManuscriptBuilder()
        usable_gateway = gateway is not None and gateway.__class__.__name__ != "MockGateway"
        self.engineer = ExperimentEngineer(gateway) if usable_gateway else None
        self.reviewer = ScientificReviewer(gateway if usable_gateway else None)
        self.rebuttal_planner = RebuttalPlanner()
        self.meta_reviewer = MetaReviewer()
        self.integrity_auditor = IntegrityAuditor()

    def _graph(self, state: ResearchState) -> EvidenceGraph:
        data = state.evidence_graph or {}
        nodes = {n["id"]: n for n in data.get("nodes", []) if "id" in n}
        return EvidenceGraph(nodes=nodes, edges=list(data.get("edges", [])))

    def _save_graph(self, state: ResearchState, graph: EvidenceGraph) -> None:
        state.evidence_graph = graph.to_dict()

    def _repair_callback(self):
        if not self.engineer:
            return None

        def repair(spec: ExperimentSpec, result: ExperimentResult) -> ExperimentSpec:
            return self.engineer.repair(spec, result.stderr)

        return repair

    def run_experiment_cycle(
        self,
        state: ResearchState,
        hypothesis: Hypothesis,
        spec: ExperimentSpec,
        unresolved_objections: list[dict] | None = None,
        evolve: bool = True,
    ) -> dict[str, Any]:
        """Execute experiment -> evidence -> optional hypothesis evolution."""
        if not any(h.get("id") == hypothesis.id for h in state.hypotheses):
            state.append("hypotheses", hypothesis.to_dict())
        state.append("experiment_specs", spec.to_dict())

        result = self.runner.run(spec, repair_callback=self._repair_callback())
        result_dict = result.to_dict()
        state.append("experiment_runs", result_dict)

        evaluation = self.evaluator.evaluate(spec, result)
        evidence = {
            "id": f"evidence_{result.experiment_id}",
            "type": "EXPERIMENT",
            "hypothesis_id": hypothesis.id,
            "experiment_id": result.experiment_id,
            "evaluation": evaluation,
            "metrics": result.metrics,
            "artifacts": result.artifacts,
        }
        state.append("evidence", evidence)

        relation = "SUPPORTS" if evaluation["verdict"] == "SUPPORTED" else "CONTRADICTS"
        graph = self._graph(state)
        graph.link_experiment_evidence(
            claim_id=hypothesis.id,
            evidence_id=evidence["id"],
            experiment_id=result.experiment_id,
            metrics=result.metrics,
            artifact_paths=result.artifacts,
            relation=relation,
        )
        for objection in unresolved_objections or []:
            objection_id = objection.get("id", f"objection_{uuid.uuid4().hex[:8]}")
            graph.challenge(objection_id, hypothesis.id, **objection)
        self._save_graph(state, graph)

        hypothesis.experiment_ids.append(result.experiment_id)
        if evaluation["verdict"] == "SUPPORTED":
            hypothesis.status = "SUPPORTED"
            hypothesis.supporting_evidence_ids.append(evidence["id"])
        else:
            hypothesis.status = "INCONCLUSIVE"
            hypothesis.contradicting_evidence_ids.append(evidence["id"])

        evolved = None
        if evolve:
            evolved = self.evolver.evolve(
                current=hypothesis,
                experiment=result_dict,
                objections=unresolved_objections or [],
            )
            state.append("hypotheses", evolved.to_dict())

        return {
            "result": result_dict,
            "evaluation": evaluation,
            "evidence": evidence,
            "evolved_hypothesis": evolved.to_dict() if evolved else None,
        }

    def plan_ablations(
        self,
        state: ResearchState,
        hypothesis_id: str,
        components: dict[str, object],
    ) -> dict:
        plan = self.ablation_planner.plan(hypothesis_id, components)
        state.append("ablations", plan.to_dict())
        return plan.to_dict()

    def execute_ablations(
        self,
        state: ResearchState,
        hypothesis: Hypothesis,
        base_spec: ExperimentSpec,
        components: dict[str, object],
    ) -> list[dict]:
        """Plan and execute leave-one-component-out ablations."""
        plan = self.ablation_planner.plan(hypothesis.id, components)
        record = plan.to_dict()
        outputs = self.ablation_executor.execute(
            plan,
            base_spec,
            repair_callback=self._repair_callback(),
        )
        record["executions"] = outputs
        state.append("ablations", record)

        graph = self._graph(state)
        for output in outputs:
            spec_dict = output["spec"]
            result_dict = output["result"]
            state.append("experiment_specs", spec_dict)
            state.append("experiment_runs", result_dict)
            spec = ExperimentSpec(**spec_dict)
            result = ExperimentResult(**result_dict)
            evaluation = self.evaluator.evaluate(spec, result)
            evidence = {
                "id": f"evidence_{result.experiment_id}",
                "type": "ABLATION",
                "hypothesis_id": hypothesis.id,
                "experiment_id": result.experiment_id,
                "variant": output["variant"]["name"],
                "evaluation": evaluation,
                "metrics": result.metrics,
                "artifacts": result.artifacts,
            }
            state.append("evidence", evidence)
            graph.link_experiment_evidence(
                claim_id=hypothesis.id,
                evidence_id=evidence["id"],
                experiment_id=result.experiment_id,
                metrics=result.metrics,
                artifact_paths=result.artifacts,
                relation="SUPPORTS" if evaluation["verdict"] == "SUPPORTED" else "CONTRADICTS",
            )
        self._save_graph(state, graph)
        return outputs

    def process_review(
        self,
        state: ResearchState,
        issues: list[ReviewIssue],
    ) -> list[dict]:
        review = {"issues": [i.to_dict() for i in issues]}
        actions = self.review_router.route(issues)
        review["actions"] = actions
        state.append("reviews", review)
        return actions

    def _followup_spec(
        self,
        hypothesis: Hypothesis,
        base_spec: ExperimentSpec,
        action: dict,
    ) -> ExperimentSpec:
        objective = f"{base_spec.objective}; address review: {action['description']}"
        if self.engineer:
            try:
                return self.engineer.create_spec(
                    hypothesis=hypothesis,
                    objective=objective,
                    workspace=base_spec.workspace,
                    timeout_seconds=base_spec.timeout_seconds,
                )
            except Exception:
                pass
        spec = deepcopy(base_spec)
        spec.id = f"exp_{uuid.uuid4().hex[:10]}"
        spec.objective = objective
        spec.metadata = dict(spec.metadata)
        spec.metadata["review_action"] = action["category"]
        spec.env = dict(spec.env)
        spec.env["AI_SCIENTIST_REVIEW_FOLLOWUP"] = "1"
        return spec

    def integrity_report(self, state: ResearchState) -> dict:
        graph = self._graph(state)
        specs = [ExperimentSpec(**x) for x in state.experiment_specs]
        results = [ExperimentResult(**x) for x in state.experiment_runs]
        report = self.integrity_auditor.audit(
            graph=graph,
            specs=specs,
            results=results,
            literature=state.literature,
        ).to_dict()
        state.append("integrity_audits", report)
        return report

    def run_review_revision_loop(
        self,
        state: ResearchState,
        hypothesis: Hypothesis,
        base_spec: ExperimentSpec,
        components: dict[str, object] | None = None,
        max_rounds: int = 2,
    ) -> dict:
        """Run peer review -> rebuttal actions -> new evidence -> revision."""
        latest_review = None
        actions_taken = []

        for round_index in range(1, max_rounds + 1):
            manuscript = self.manuscript_builder.build(state)
            state.manuscript = {"format": "markdown", "content": manuscript}
            latest_review = self.reviewer.review(state, manuscript)
            review_record = latest_review.to_dict()
            review_record["round"] = round_index
            state.append("reviews", review_record)

            if not latest_review.issues:
                break

            actions = self.rebuttal_planner.plan(latest_review)
            rebuttal = {"round": round_index, "actions": actions, "results": []}

            for action in actions:
                action_type = action["action"]
                outcome = {"action": action}

                if action_type == "ABLATION" and components:
                    outcome["executions"] = self.execute_ablations(
                        state, hypothesis, base_spec, components
                    )
                elif action_type in {"EXPERIMENT", "BASELINE_EXPERIMENT", "ENGINEERING_REPAIR"}:
                    followup = self._followup_spec(hypothesis, base_spec, action)
                    outcome["cycle"] = self.run_experiment_cycle(
                        state, hypothesis, followup, evolve=False
                    )
                elif action_type == "EVIDENCE_VERIFICATION":
                    outcome["integrity"] = self.integrity_report(state)
                elif action_type == "MANUSCRIPT_REVISION":
                    revised = self.manuscript_builder.build(state)
                    state.manuscript = {"format": "markdown", "content": revised}
                    outcome["revised"] = True
                else:
                    outcome["status"] = "PENDING_EXTERNAL_HANDLER"

                rebuttal["results"].append(outcome)
                actions_taken.append(outcome)

            state.append("rebuttals", rebuttal)

        manuscript = self.manuscript_builder.build(state)
        state.manuscript = {"format": "markdown", "content": manuscript}
        final_review = self.reviewer.review(state, manuscript)
        integrity = self.integrity_report(state)
        meta = self.meta_reviewer.decide(final_review, integrity)
        state.append("decisions", {"type": "META_REVIEW", **meta})

        return {
            "final_review": final_review.to_dict(),
            "integrity": integrity,
            "meta_review": meta,
            "actions_taken": actions_taken,
        }

    def run_program(
        self,
        state: ResearchState,
        hypothesis: Hypothesis,
        spec: ExperimentSpec,
        components: dict[str, object] | None = None,
        unresolved_objections: list[dict] | None = None,
        max_review_rounds: int = 2,
    ) -> dict:
        """Run a complete executable research program from hypothesis to meta-review."""
        initial = self.run_experiment_cycle(
            state,
            hypothesis,
            spec,
            unresolved_objections=unresolved_objections or [],
        )
        review = self.run_review_revision_loop(
            state,
            hypothesis,
            spec,
            components=components,
            max_rounds=max_review_rounds,
        )
        return {
            "initial_cycle": initial,
            "review_cycle": review,
            "research_package": state.to_dict(),
        }

    def research_package(self, state: ResearchState) -> dict:
        return state.to_dict()
