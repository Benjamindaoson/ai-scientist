"""Evidence-driven autonomous research loop."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .ablation import AblationPlanner
from .experiment import ExperimentEvaluator, ExperimentRunner, ExperimentSpec
from .hypothesis import Hypothesis, HypothesisEvolver
from .research_state import ResearchState
from .review_loop import ReviewActionRouter, ReviewIssue


class AutonomousResearchLoop:
    """Connect scientific reasoning to executable experiments and revision."""

    def __init__(self, gateway=None, runner: ExperimentRunner | None = None):
        self.runner = runner or ExperimentRunner()
        self.evaluator = ExperimentEvaluator()
        self.evolver = HypothesisEvolver(gateway=gateway)
        self.ablation_planner = AblationPlanner()
        self.review_router = ReviewActionRouter()

    def run_experiment_cycle(
        self,
        state: ResearchState,
        hypothesis: Hypothesis,
        spec: ExperimentSpec,
        unresolved_objections: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Execute experiment -> evidence -> hypothesis evolution."""
        state.append("hypotheses", hypothesis.to_dict())
        state.append("experiment_specs", spec.to_dict())

        result = self.runner.run(spec)
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
        }
        state.append("evidence", evidence)

        hypothesis.experiment_ids.append(result.experiment_id)
        if evaluation["verdict"] == "SUPPORTED":
            hypothesis.status = "SUPPORTED"
            hypothesis.supporting_evidence_ids.append(evidence["id"])
        else:
            hypothesis.status = "INCONCLUSIVE"
            hypothesis.contradicting_evidence_ids.append(evidence["id"])

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

    def process_review(
        self,
        state: ResearchState,
        issues: list[ReviewIssue],
    ) -> list[dict]:
        review = {"issues": [i.to_dict() for i in issues]}
        state.append("reviews", review)
        actions = self.review_router.route(issues)
        review["actions"] = actions
        return actions

    def research_package(self, state: ResearchState) -> dict:
        """Return a traceable research package suitable for persistence/export."""
        return state.to_dict()
