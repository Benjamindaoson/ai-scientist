"""Integration tests for the evidence-driven autonomous research loop."""
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).parent / "auto_research" / "src"))

from ai_scientist.autonomous_loop import AutonomousResearchLoop
from ai_scientist.experiment import ExperimentRunner, ExperimentSpec, WorkspaceSandbox
from ai_scientist.hypothesis import Hypothesis
from ai_scientist.integrity import IntegrityAuditor
from ai_scientist.research_package import ResearchPackageWriter
from ai_scientist.research_state import ResearchState
from ai_scientist.review_loop import ReviewIssue


def make_hypothesis():
    return Hypothesis(
        claim="Method A improves accuracy",
        rationale="A should reduce estimation error",
        predicted_effect="accuracy >= 0.90",
        falsification_conditions=["accuracy < 0.90"],
    )


def test_sandbox_blocks_path_escape_and_secret_inheritance():
    sandbox = WorkspaceSandbox()
    with TemporaryDirectory() as td:
        try:
            sandbox.safe_path(td, "../escape.txt")
            raise AssertionError("path traversal should have been rejected")
        except ValueError:
            pass

        os.environ["AI_SCIENTIST_TEST_SECRET"] = "must-not-leak"
        script = Path(td) / "env_check.py"
        script.write_text(
            "import json, os\n"
            "json.dump({'secret_absent': int(os.getenv('AI_SCIENTIST_TEST_SECRET') is None)}, "
            "open('metrics.json','w'))\n",
            encoding="utf-8",
        )
        spec = ExperimentSpec(
            hypothesis_id="hyp_security",
            objective="verify environment isolation",
            command=[sys.executable, "env_check.py"],
            workspace=td,
            success_criteria={"secret_absent": {"op": "==", "value": 1}},
        )
        result = ExperimentRunner().run(spec)
        assert result.status == "SUCCEEDED"
        assert result.metrics["secret_absent"] == 1


def test_failure_recovery_retries_boundedly():
    with TemporaryDirectory() as td:
        script = Path(td) / "flaky.py"
        script.write_text(
            "from pathlib import Path\n"
            "import json, sys\n"
            "p=Path('attempt.marker')\n"
            "if not p.exists():\n"
            "    p.write_text('1')\n"
            "    sys.exit(1)\n"
            "json.dump({'accuracy': 0.91}, open('metrics.json','w'))\n",
            encoding="utf-8",
        )
        spec = ExperimentSpec(
            hypothesis_id="hyp_retry",
            objective="recover from transient failure",
            command=[sys.executable, "flaky.py"],
            workspace=td,
            success_criteria={"accuracy": {"op": ">=", "value": 0.90}},
            max_attempts=2,
        )
        result = ExperimentRunner().run(spec)
        assert result.status == "SUCCEEDED"
        assert result.attempts == 2
        assert result.recovery_history[0]["decision"].startswith("retry")


def test_experiment_to_evidence_to_hypothesis_evolution():
    with TemporaryDirectory() as td:
        workspace = Path(td)
        script = workspace / "run_exp.py"
        script.write_text(
            "import json\n"
            "json.dump({'accuracy': 0.91}, open('metrics.json','w'))\n",
            encoding="utf-8",
        )
        hypothesis = make_hypothesis()
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
        assert state.evidence_graph["edges"]


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


def test_complete_program_reaches_meta_review_and_exports_package():
    with TemporaryDirectory() as td:
        workspace = Path(td) / "workspace"
        workspace.mkdir()
        script = workspace / "run_exp.py"
        script.write_text(
            "import json, os\n"
            "score = 0.91\n"
            "json.dump({'accuracy': score}, open('metrics.json','w'))\n",
            encoding="utf-8",
        )
        hypothesis = make_hypothesis()
        spec = ExperimentSpec(
            hypothesis_id=hypothesis.id,
            objective="Test Method A",
            command=[sys.executable, "run_exp.py"],
            workspace=str(workspace),
            success_criteria={"accuracy": {"op": ">=", "value": 0.90}},
        )
        state = ResearchState(
            project_id="p3",
            problem="Does Method A help?",
            literature=[{"title": "Traceable Reference", "arxiv_id": "2601.00001"}],
        )
        loop = AutonomousResearchLoop()
        output = loop.run_program(
            state=state,
            hypothesis=hypothesis,
            spec=spec,
            components={"module_a": True, "module_b": True},
            max_review_rounds=2,
        )

        assert len(state.ablations) == 1
        assert len(state.ablations[0]["executions"]) == 2
        assert state.rebuttals
        assert output["review_cycle"]["integrity"]["passed"] is True
        assert output["review_cycle"]["meta_review"]["decision"] == "ACCEPT"
        assert "## References" in state.manuscript["content"]

        package_dir = Path(td) / "package"
        paths = ResearchPackageWriter().write(state, package_dir)
        for path in paths.values():
            assert Path(path).exists()

        specs = [ExperimentSpec(**x) for x in state.experiment_specs]
        results_by_id = {x["experiment_id"]: x for x in state.experiment_runs}
        expected = next(x for x in state.experiment_runs if x["experiment_id"] == spec.id)
        from ai_scientist.experiment import ExperimentResult
        reproduction = IntegrityAuditor().reproduce(
            specs[0],
            ExperimentResult(**expected),
            tolerance=0.0,
        )
        assert reproduction.passed is True


if __name__ == "__main__":
    test_sandbox_blocks_path_escape_and_secret_inheritance()
    test_failure_recovery_retries_boundedly()
    test_experiment_to_evidence_to_hypothesis_evolution()
    test_ablation_and_review_are_actionable()
    test_complete_program_reaches_meta_review_and_exports_package()
    print("autonomous research loop integration tests passed")
