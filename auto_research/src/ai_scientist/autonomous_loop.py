"""Evidence-driven autonomous research loop."""
from __future__ import annotations

from typing import Any

from .ablation import AblationPlanner
from .ablation_executor import AblationExecutor
from .engineering import CodeEngineeringAgent, EngineeringPlan, WorkspaceEditor
from .evidence_graph import EvidenceGraph
from .experiment import ExperimentEvaluator, ExperimentRunner, ExperimentSpec
from .hypothesis import Hypothesis, HypothesisEvolver
from .integrity import IntegrityAuditor
from .manuscript import ManuscriptWriter
from .research_state import ResearchState
from .review_loop import ReviewActionRouter, ReviewIssue
from .scientific_review import MetaReviewer, PeerReview, PeerReviewer, RebuttalPlanner


class AutonomousResearchLoop:
    """Connect scientific reasoning, execution, evidence, review, and revision."""

    def __init__(self, gateway=None, runner: ExperimentRunner | None = None):
        self.gateway = gateway
        self.runner = runner or ExperimentRunner()
        self.evaluator = ExperimentEvaluator()
        self.evolver = HypothesisEvolver(gateway=gateway)
        self.ablation_planner = AblationPlanner()
        self.ablation_executor = AblationExecutor(self.runner)
        self.review_router = ReviewActionRouter()
        self.engineer = CodeEngineeringAgent(gateway=gateway)
        self.writer = ManuscriptWriter(gateway=gateway)
        self.peer_reviewer = PeerReviewer(gateway=gateway)
        self.rebuttal_planner = RebuttalPlanner()
        self.meta_reviewer = MetaReviewer()
        self.auditor = IntegrityAuditor()
        self.graph = EvidenceGraph()

    def apply_engineering_plan(self, workspace: str, plan: EngineeringPlan) -> list[str]:
        """Apply structured code changes inside a bounded workspace."""
        return WorkspaceEditor(workspace).apply(plan)

    def run_experiment_cycle(
        self,
        state: ResearchState,
        hypothesis: Hypothesis,
        spec: ExperimentSpec,
        unresolved_objections: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Execute experiment -> evidence -> hypothesis update -> evolution."""
        state.append("experiment_specs", spec.to_dict())
        attempts = self.runner.run_with_recovery(spec)
        for attempt in attempts:
            state.append("experiment_runs", attempt.to_dict())
        result = attempts[-1]

        evaluation = self.evaluator.evaluate(spec, result)
        evidence_id = f"evidence_{result.experiment_id}"
        claim_id = f"claim_{hypothesis.id}"
        evidence = {
            "id": evidence_id,
            "type": "EXPERIMENT",
            "hypothesis_id": hypothesis.id,
            "experiment_id": result.experiment_id,
            "evaluation": evaluation,
            "metrics": result.metrics,
        }
        state.append("evidence", evidence)

        hypothesis.experiment_ids.append(result.experiment_id)
        if evaluation["verdict"] == "SUPPORTED":
            hypothesis.status = "SUPPORTED"
            hypothesis.supporting_evidence_ids.append(evidence_id)
        else:
            hypothesis.status = "INCONCLUSIVE"
            hypothesis.contradicting_evidence_ids.append(evidence_id)
        state.append("hypotheses", hypothesis.to_dict())
        state.append("claims", {"id": claim_id, "text": hypothesis.claim, "hypothesis_id": hypothesis.id})

        self.graph.add_claim(claim_id, hypothesis.claim)
        self.graph.add_experiment(result.experiment_id, result.metrics)
        self.graph.add_evidence(evidence_id)
        self.graph.link_evidence_experiment(evidence_id, result.experiment_id)
        self.graph.link_claim_evidence(claim_id, evidence_id, supports=evaluation["verdict"] == "SUPPORTED")
        state.evidence_graph = self.graph.to_dict()
        state.touch()

        evolved = self.evolver.evolve(
            current=hypothesis,
            experiment=result.to_dict(),
            objections=unresolved_objections or [],
        )
        state.append("hypotheses", evolved.to_dict())

        return {
            "attempts": [a.to_dict() for a in attempts],
            "result": result.to_dict(),
            "evaluation": evaluation,
            "evidence": evidence,
            "evolved_hypothesis": evolved.to_dict(),
        }

    def plan_ablations(
        self,
        state: ResearchState,
        hypothesis_id: str,
        components: dict[str, object],
    ) -> dict:
        plan = self.ablation_planner.plan(hypothesis_id, components).to_dict()
        state.append("ablations", plan)
        return plan

    def execute_ablations(
        self,
        state: ResearchState,
        base_spec: ExperimentSpec,
        plan: dict,
    ) -> list[dict]:
        outputs = self.ablation_executor.execute(base_spec, plan)
        for output in outputs:
            state.append("experiment_specs", output["spec"])
            for attempt in output["attempts"]:
                state.append("experiment_runs", attempt)
            ev_id = f"evidence_{output['result']['experiment_id']}"
            evidence = {
                "id": ev_id,
                "type": "ABLATION",
                "hypothesis_id": base_spec.hypothesis_id,
                "experiment_id": output["result"]["experiment_id"],
                "variant": output["variant"],
                "evaluation": output["evaluation"],
                "metrics": output["result"].get("metrics", {}),
            }
            state.append("evidence", evidence)
            self.graph.add_experiment(output["result"]["experiment_id"], output["result"].get("metrics", {}))
            self.graph.add_evidence(ev_id, evidence_type="ABLATION")
            self.graph.link_evidence_experiment(ev_id, output["result"]["experiment_id"])
        state.evidence_graph = self.graph.to_dict()
        state.touch()
        return outputs

    def process_review(self, state: ResearchState, issues: list[ReviewIssue]) -> list[dict]:
        review = {"issues": [i.to_dict() for i in issues]}
        actions = self.review_router.route(issues)
        review["actions"] = actions
        state.append("reviews", review)
        return actions

    def draft_manuscript(self, state: ResearchState, title: str = "Autonomous Research Report") -> dict:
        manuscript = self.writer.draft(state, title=title)
        state.manuscript = manuscript
        state.touch()
        return manuscript

    def peer_review(self, state: ResearchState) -> PeerReview:
        if not state.manuscript:
            self.draft_manuscript(state)
        review = self.peer_reviewer.review(state.manuscript, state.to_dict())
        state.append("reviews", {"type": "PEER_REVIEW", **review.to_dict()})
        return review

    def rebuttal(
        self,
        state: ResearchState,
        review: PeerReview,
        supplementary_specs: dict[str, ExperimentSpec] | None = None,
    ) -> dict:
        """Turn review issues into actions and execute supplied supplementary experiments."""
        actions = self.rebuttal_planner.plan(review)
        supplementary_specs = supplementary_specs or {}
        executed = []
        resolved = set()

        for action in actions:
            category = action["category"]
            spec = supplementary_specs.get(category)
            if spec is None:
                continue
            attempts = self.runner.run_with_recovery(spec)
            final = attempts[-1]
            evaluation = self.evaluator.evaluate(spec, final)
            for attempt in attempts:
                state.append("experiment_runs", attempt.to_dict())
            state.append("experiment_specs", spec.to_dict())
            evidence = {
                "id": f"evidence_{final.experiment_id}",
                "type": "REBUTTAL_EXPERIMENT",
                "hypothesis_id": spec.hypothesis_id,
                "experiment_id": final.experiment_id,
                "review_category": category,
                "metrics": final.metrics,
                "evaluation": evaluation,
            }
            state.append("evidence", evidence)
            executed.append({"category": category, "result": final.to_dict(), "evaluation": evaluation})
            if final.status == "SUCCEEDED" and final.metrics:
                resolved.add(category)

        rebuttal = {"actions": actions, "executed": executed, "resolved_categories": sorted(resolved)}
        state.append("rebuttals", rebuttal)
        if executed:
            # Revision is evidence-driven: regenerate manuscript after supplementary evidence.
            self.draft_manuscript(state, title=state.manuscript.get("title", "Autonomous Research Report"))
        return rebuttal

    def meta_review(self, state: ResearchState, review: PeerReview, resolved_categories: set[str] | None = None) -> dict:
        meta = self.meta_reviewer.decide(review, resolved_categories).to_dict()
        state.append("meta_reviews", meta)
        state.append("decisions", {"stage": "META_REVIEW", **meta})
        return meta

    def integrity_audit(self, state: ResearchState) -> dict:
        report = self.auditor.audit(state, self.graph).to_dict()
        state.integrity_report = report
        state.touch()
        return report

    def finalize(
        self,
        state: ResearchState,
        title: str = "Autonomous Research Report",
        supplementary_specs: dict[str, ExperimentSpec] | None = None,
    ) -> dict:
        """Draft -> peer review -> rebuttal experiments -> revision -> meta review -> audit."""
        manuscript = self.draft_manuscript(state, title)
        review = self.peer_review(state)
        rebuttal = self.rebuttal(state, review, supplementary_specs=supplementary_specs)
        meta = self.meta_review(state, review, set(rebuttal["resolved_categories"]))
        audit = self.integrity_audit(state)
        final_decision = "READY" if meta["decision"] == "ACCEPT" and audit["passed"] else "REVISE"
        state.append("decisions", {
            "stage": "FINAL",
            "decision": final_decision,
            "meta_review": meta["decision"],
            "integrity_passed": audit["passed"],
        })
        return {
            "manuscript": manuscript,
            "peer_review": review.to_dict(),
            "rebuttal": rebuttal,
            "meta_review": meta,
            "integrity_report": audit,
            "final_decision": final_decision,
            "research_package": state.to_dict(),
        }

    def research_package(self, state: ResearchState) -> dict:
        return state.to_dict()
