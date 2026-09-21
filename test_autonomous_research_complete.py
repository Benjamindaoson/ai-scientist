"""End-to-end tests for the complete autonomous research system."""
import asyncio
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).parent / "auto_research" / "src"))

from ai_scientist.autonomous_loop import AutonomousResearchLoop
from ai_scientist.core.gateway import MockGateway
from ai_scientist.engineering import EngineeringPlan, FileChange, WorkspaceEditor
from ai_scientist.experiment import ExperimentRunner, ExperimentSpec
from ai_scientist.hypothesis import Hypothesis
from ai_scientist.orchestrator import AIScientist
from ai_scientist.research_state import ResearchState


def _write_metric_script(workspace: Path, name: str = "experiment.py") -> Path:
    script = workspace / name
    script.write_text(
        "import json, os\n"
        "metrics_file = os.environ.get('AI_SCIENTIST_METRICS_FILE', 'metrics.json')\n"
        "cfg = json.loads(os.environ.get('AI_SCIENTIST_ABLATION', '{}'))\n"
        "penalty = sum(0.02 for v in cfg.values() if v is False)\n"
        "json.dump({'accuracy': 0.92 - penalty}, open(metrics_file, 'w'))\n",
        encoding="utf-8",
    )
    return script


def test_complete_ready_cycle():
    with TemporaryDirectory() as td:
        workspace = Path(td)
        _write_metric_script(workspace)

        scientist = AIScientist(
            db_path=workspace / "scientist.db",
            gateway=MockGateway(default_response="not-json"),
        )
        asyncio.run(scientist.start_research("Does componentized Method A improve accuracy?"))

        hypothesis = Hypothesis(
            claim="Method A improves predictive accuracy",
            rationale="The components address complementary error sources.",
            predicted_effect="accuracy >= 0.85",
            falsification_conditions=["accuracy < 0.85"],
        )
        spec = ExperimentSpec(
            hypothesis_id=hypothesis.id,
            objective="Evaluate Method A",
            command=[sys.executable, "experiment.py"],
            workspace=str(workspace),
            success_criteria={"accuracy": {"op": ">=", "value": 0.85}},
        )

        output = scientist.run_complete_autonomous_cycle(
            hypothesis=hypothesis,
            experiment_spec=spec,
            ablation_components={"retrieval": True, "reranker": True, "verifier": True},
            manuscript_title="Method A Evaluation",
        )

        assert output["experiment_cycle"]["evaluation"]["verdict"] == "SUPPORTED"
        assert len(output["ablation_results"]) == 3
        assert output["meta_review"]["decision"] == "ACCEPT"
        assert output["integrity_report"]["passed"] is True
        assert output["final_decision"] == "READY"
        package = output["research_package"]
        assert package["evidence_graph"]["nodes"]
        assert package["manuscript"]["body"]
        assert package["decisions"][-1]["decision"] == "READY"


def test_failure_recovery_succeeds_on_second_attempt():
    with TemporaryDirectory() as td:
        workspace = Path(td)
        script = workspace / "flaky.py"
        script.write_text(
            "import json, os, pathlib, sys\n"
            "marker = pathlib.Path('attempt.marker')\n"
            "if not marker.exists():\n"
            "    marker.write_text('1')\n"
            "    print('temporary failure', file=sys.stderr)\n"
            "    raise SystemExit(2)\n"
            "json.dump({'score': 1.0}, open(os.environ['AI_SCIENTIST_METRICS_FILE'], 'w'))\n",
            encoding="utf-8",
        )
        spec = ExperimentSpec(
            hypothesis_id="hyp_recovery",
            objective="Test recovery",
            command=[sys.executable, "flaky.py"],
            workspace=str(workspace),
            success_criteria={"score": {"op": ">=", "value": 1.0}},
        )
        results = ExperimentRunner().run_with_recovery(spec)
        assert len(results) == 2
        assert results[0].status == "FAILED"
        assert results[-1].status == "SUCCEEDED"
        assert results[-1].metrics["score"] == 1.0


def test_review_to_supplementary_experiment_to_meta_review():
    with TemporaryDirectory() as td:
        workspace = Path(td)
        _write_metric_script(workspace)
        loop = AutonomousResearchLoop(gateway=MockGateway(default_response="not-json"))
        state = ResearchState(project_id="p_review", problem="Does Method A work?")
        hypothesis = Hypothesis(
            claim="Method A improves accuracy",
            rationale="Test",
            predicted_effect="accuracy >= 0.85",
            falsification_conditions=["accuracy < 0.85"],
        )
        base = ExperimentSpec(
            hypothesis_id=hypothesis.id,
            objective="Base experiment",
            command=[sys.executable, "experiment.py"],
            workspace=str(workspace),
            success_criteria={"accuracy": {"op": ">=", "value": 0.85}},
        )
        loop.run_experiment_cycle(state, hypothesis, base)
        loop.draft_manuscript(state)
        review = loop.peer_review(state)
        categories = {i.category for i in review.issues}
        assert "INSUFFICIENT_ABLATION" in categories

        supplementary = ExperimentSpec(
            hypothesis_id=hypothesis.id,
            objective="Reviewer-requested component isolation",
            command=[sys.executable, "experiment.py"],
            workspace=str(workspace),
            metrics_file="review_metrics.json",
            env={"AI_SCIENTIST_ABLATION": json.dumps({"reranker": False})},
            success_criteria={"accuracy": {"op": ">=", "value": 0.80}},
        )
        rebuttal = loop.rebuttal(
            state,
            review,
            supplementary_specs={"INSUFFICIENT_ABLATION": supplementary},
        )
        assert "INSUFFICIENT_ABLATION" in rebuttal["resolved_categories"]
        meta = loop.meta_review(state, review, set(rebuttal["resolved_categories"]))
        assert meta["decision"] == "ACCEPT"


def test_workspace_editor_rejects_escape():
    with TemporaryDirectory() as td:
        editor = WorkspaceEditor(td)
        good = EngineeringPlan("write safe file", [FileChange("src/demo.py", "x = 1\n")])
        assert editor.apply(good) == ["src/demo.py"]
        assert (Path(td) / "src" / "demo.py").exists()

        bad = EngineeringPlan("escape", [FileChange("../outside.py", "bad = True\n")])
        try:
            editor.apply(bad)
        except ValueError:
            pass
        else:
            raise AssertionError("WorkspaceEditor allowed path escape")


def test_sandbox_rejects_shell_by_default():
    with TemporaryDirectory() as td:
        spec = ExperimentSpec(
            hypothesis_id="h",
            objective="shell should be denied",
            command=["sh", "-c", "echo unsafe"],
            workspace=td,
        )
        try:
            ExperimentRunner().run(spec)
        except ValueError as exc:
            assert "Shell execution is disabled" in str(exc)
        else:
            raise AssertionError("Sandbox allowed shell execution")


if __name__ == "__main__":
    test_complete_ready_cycle()
    test_failure_recovery_succeeds_on_second_attempt()
    test_review_to_supplementary_experiment_to_meta_review()
    test_workspace_editor_rejects_escape()
    test_sandbox_rejects_shell_by_default()
    print("complete autonomous research tests passed")
