import asyncio
import os
import shutil
import sys
from pathlib import Path

from ai_scientist import AIScientist, MockGateway
from ai_scientist.autonomous_loop import AutonomousResearchLoop
from ai_scientist.engine.final_research_court import (
    FinalResearchCourt,
    ObjectionGate,
    ScientificDecision,
)
from ai_scientist.engine.multi_agent_debate import DebateResult, DebateStatus
from ai_scientist.experiment import ExperimentResult, ExperimentRunner, ExperimentSpec, SandboxPolicy
from ai_scientist.hypothesis import Hypothesis
from ai_scientist.literature.reader import PaperReader
from ai_scientist.research_state import ResearchState


def _hypothesis() -> Hypothesis:
    return Hypothesis(
        claim="Method A improves accuracy",
        rationale="A should reduce estimation error",
        predicted_effect="accuracy >= 0.90",
        falsification_conditions=["accuracy <= 0.50"],
    )


class _ResultRunner:
    def __init__(self, status: str, metrics: dict, error_type: str | None = None):
        self.status = status
        self.metrics = metrics
        self.error_type = error_type
        self.calls = 0

    def run(self, spec: ExperimentSpec, repair_callback=None) -> ExperimentResult:
        self.calls += 1
        return ExperimentResult(
            experiment_id=spec.id,
            hypothesis_id=spec.hypothesis_id,
            status=self.status,
            return_code=0 if self.status == "SUCCEEDED" else 1,
            metrics=self.metrics,
            error_type=self.error_type,
        )


def _spec(tmp_path: Path, hypothesis: Hypothesis, **kwargs) -> ExperimentSpec:
    return ExperimentSpec(
        hypothesis_id=hypothesis.id,
        objective="Test Method A",
        command=[sys.executable, "run.py"],
        workspace=str(tmp_path),
        success_criteria={"accuracy": {"op": ">=", "value": 0.90}},
        **kwargs,
    )


def test_fatal_plus_human_is_kill():
    decision = FinalResearchCourt().make_decision(
        gates={
            "objection_gate": ObjectionGate(
                open_fatal_objections=[{"id": "fatal-1", "title": "Fatal flaw"}],
                requires_human_objections=[{"id": "human-1", "title": "Human judgment"}],
            )
        }
    )

    assert decision.decision == ScientificDecision.KILL
    assert decision.requires_human_review is True
    assert decision.human_review_reason


def test_kill_decision_never_executes_experiment(tmp_path, monkeypatch):
    runner = _ResultRunner("SUCCEEDED", {"accuracy": 1.0})
    scientist = AIScientist(db_path=":memory:", gateway=MockGateway())
    scientist.autonomous_loop = AutonomousResearchLoop(gateway=MockGateway(), runner=runner)
    hypothesis = _hypothesis()

    async def no_literature(*args, **kwargs):
        return []

    async def killed_debate(*args, **kwargs):
        return DebateResult(
            debate_id="debate-kill",
            direction_id="direction-kill",
            status=DebateStatus.REJECTED,
            rounds_completed=1,
            kill_votes=1,
            total_votes=1,
            kill_ratio=1.0,
            conclusion="Killed by the scientific court",
            metadata={"court_decision": {"decision": "KILL"}},
        )

    monkeypatch.setattr(scientist, "search_literature", no_literature)
    monkeypatch.setattr(scientist, "evaluate_direction", killed_debate)

    result = asyncio.run(
        scientist.run_full_research_pipeline(
            seed_question="Should this direction run?",
            hypothesis=hypothesis,
            experiment_spec=_spec(tmp_path, hypothesis),
            max_review_rounds=0,
        )
    )

    assert runner.calls == 0
    assert result["stages"]["autonomous_research"]["decision"] == "KILL"


def test_inconclusive_is_not_contradiction(tmp_path):
    hypothesis = _hypothesis()
    runner = _ResultRunner("SUCCEEDED", {"accuracy": 0.80})
    state = ResearchState(project_id="project", problem="Does Method A help?")
    output = AutonomousResearchLoop(runner=runner).run_experiment_cycle(
        state,
        hypothesis,
        _spec(tmp_path, hypothesis),
        evolve=False,
    )

    evidence_id = output["evidence"]["id"]
    claim_edges = [
        edge for edge in state.evidence_graph["edges"]
        if edge["source"] == evidence_id and edge["target"] == hypothesis.id
    ]
    assert output["evaluation"]["verdict"] == "INCONCLUSIVE"
    assert [edge["relation"] for edge in claim_edges] == ["INCONCLUSIVE"]
    assert evidence_id not in hypothesis.contradicting_evidence_ids


def test_failed_execution_is_invalid_evidence(tmp_path):
    hypothesis = _hypothesis()
    runner = _ResultRunner("FAILED", {}, error_type="NONZERO_EXIT")
    state = ResearchState(project_id="project", problem="Does Method A help?")
    output = AutonomousResearchLoop(runner=runner).run_experiment_cycle(
        state,
        hypothesis,
        _spec(tmp_path, hypothesis),
        evolve=False,
    )

    evidence_id = output["evidence"]["id"]
    claim_edges = [
        edge for edge in state.evidence_graph["edges"]
        if edge["source"] == evidence_id and edge["target"] == hypothesis.id
    ]
    assert output["evaluation"]["verdict"] == "INVALID"
    assert [edge["relation"] for edge in claim_edges] == ["INVALID"]
    assert evidence_id not in hypothesis.supporting_evidence_ids
    assert evidence_id not in hypothesis.contradicting_evidence_ids


def test_invalid_metrics_are_invalid_evidence(tmp_path):
    hypothesis = _hypothesis()
    (tmp_path / "run.py").write_text(
        "import json\njson.dump(['not', 'a', 'metric', 'mapping'], open('metrics.json', 'w'))\n",
        encoding="utf-8",
    )
    state = ResearchState(project_id="project", problem="Does Method A help?")

    output = AutonomousResearchLoop(runner=ExperimentRunner()).run_experiment_cycle(
        state,
        hypothesis,
        _spec(tmp_path, hypothesis, max_attempts=1),
        evolve=False,
    )

    assert output["result"]["status"] == "FAILED"
    assert output["result"]["error_type"] == "INVALID_METRICS"
    assert output["evaluation"]["verdict"] == "INVALID"
    assert hypothesis.supporting_evidence_ids == []
    assert hypothesis.contradicting_evidence_ids == []


def test_sandbox_rejects_untrusted_same_basename_executable(tmp_path, monkeypatch):
    policy = SandboxPolicy()
    untrusted = tmp_path / "untrusted" / Path(sys.executable).name

    assert policy.executable_allowed(str(untrusted)) is False
    assert policy.executable_allowed(sys.executable) is True

    interpreter_dir = str(Path(sys.executable).parent)
    monkeypatch.setenv("PATH", interpreter_dir + os.pathsep + os.environ.get("PATH", ""))
    for command in ("python", "python3", "pytest"):
        if shutil.which(command):
            assert policy.executable_allowed(command) is True


def test_arxiv_parser_preserves_authors_categories():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom"
          xmlns:arxiv="http://arxiv.org/schemas/atom">
      <entry>
        <id>http://arxiv.org/abs/2601.00001v1</id>
        <title>Metadata Preservation</title>
        <summary>A fixed offline fixture.</summary>
        <published>2026-01-01T00:00:00Z</published>
        <author><name>Ada Researcher</name></author>
        <author><name>Grace Scientist</name></author>
        <category term="cs.AI" scheme="http://arxiv.org/schemas/atom" />
        <category term="cs.LG" scheme="http://arxiv.org/schemas/atom" />
        <link title="pdf" href="https://arxiv.org/pdf/2601.00001" />
      </entry>
    </feed>
    """

    paper = PaperReader()._parse_arxiv_response(xml, "2601.00001")

    assert paper is not None
    assert paper.authors == ["Ada Researcher", "Grace Scientist"]
    assert paper.categories == ["cs.AI", "cs.LG"]


def test_explicit_contradiction_is_contradicted(tmp_path):
    hypothesis = _hypothesis()
    runner = _ResultRunner("SUCCEEDED", {"accuracy": 0.40})
    state = ResearchState(project_id="project", problem="Does Method A help?")
    spec = _spec(
        tmp_path,
        hypothesis,
        contradiction_criteria={"accuracy": {"op": "<=", "value": 0.50}},
    )

    output = AutonomousResearchLoop(runner=runner).run_experiment_cycle(
        state, hypothesis, spec, evolve=False
    )

    assert output["evaluation"]["verdict"] == "CONTRADICTED"
    assert output["evidence"]["id"] in hypothesis.contradicting_evidence_ids


def test_ablation_inconclusive_is_not_contradiction(tmp_path):
    hypothesis = _hypothesis()
    runner = _ResultRunner("SUCCEEDED", {"accuracy": 0.80})
    state = ResearchState(project_id="project", problem="Which component matters?")
    AutonomousResearchLoop(runner=runner).execute_ablations(
        state,
        hypothesis,
        _spec(tmp_path, hypothesis),
        {"component": True},
    )

    claim_relations = [
        edge["relation"] for edge in state.evidence_graph["edges"]
        if edge["target"] == hypothesis.id
    ]
    assert claim_relations == ["INCONCLUSIVE"]
