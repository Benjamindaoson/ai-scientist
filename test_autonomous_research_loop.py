"""Integration tests for the executable autonomous research loop."""
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).parent / "auto_research" / "src"))

from ai_scientist.autonomous_loop import AutonomousResearchLoop
from ai_scientist.experiment import ExperimentSpec
from ai_scientist.hypothesis import Hypothesis
from ai_scientist.research_state import ResearchState
from ai_scientist.review_loop import ReviewIssue


def test_experiment_to_evidence_to_hypothesis_evolution():
    with TemporaryDirectory() as td:
        workspace = Path(td)
        script = workspace / "run_exp.py"
        script.write_text(
            "import json\n"
            "json.dump({'accuracy': 0.91}, open('metrics.json','w'))\n",
            encoding="utf-8",
        )

        hypothesis = Hypothesis(
            claim="Method A improves accuracy",
            rationale="A should reduce estimation error",
            predicted_effect="accuracy >= 0.90",
            falsification_conditions=["accuracy < 0.90"],
        )
        spec = ExperimentSpec(
            hypothesis_id=hypothesis.id,
            objective="Test Method A",
            command=[sys.executable, "run_exp.py"],
            workspace=str(workspace),
            success_criteria={"accuracy": {"op": ">=", "value": 0.90}},
        )
        state = ResearchState(project_id="p1", problem="Does Method A help?")
        loop = AutonomousResearchLoop()

        output = loop.run_experiment_cycle(state, hypothesis, spec)

        assert output["result"]["status"] == "SUCCEEDED"
        assert output["evaluation"]["verdict"] == "SUPPORTED"
        assert len(state.experiment_runs) == 1
        assert len(state.evidence) == 1
        assert len(state.hypotheses) == 2
        assert state.hypotheses[-1]["parent_hypothesis_id"] == hypothesis.id


def test_ablation_and_review_are_actionable():
    state = ResearchState(project_id="p2", problem="Which component matters?")
    loop = AutonomousResearchLoop()

    plan = loop.plan_ablations(
        state,
        "hyp_1",
        {"retrieval": True, "reranker": True, "verifier": True},
    )
    assert {v["name"] for v in plan["variants"]} == {
        "without_retrieval", "without_reranker", "without_verifier"
    }

    actions = loop.process_review(
        state,
        [
            ReviewIssue("MISSING_EXPERIMENT", "Need an OOD benchmark"),
            ReviewIssue("INSUFFICIENT_ABLATION", "Isolate reranker contribution"),
            ReviewIssue("CLAIM_EVIDENCE_MISMATCH", "Claim exceeds measured evidence"),
        ],
    )
    assert [a["action"] for a in actions] == [
        "EXPERIMENT", "ABLATION", "EVIDENCE_VERIFICATION"
    ]


if __name__ == "__main__":
    test_experiment_to_evidence_to_hypothesis_evolution()
    test_ablation_and_review_are_actionable()
    print("autonomous research loop tests passed")
