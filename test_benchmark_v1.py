"""Deterministic smoke tests for AI Scientist Benchmark v1."""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/"auto_research"/"src"))

from ai_scientist.experiment import ExperimentSpec
from ai_scientist.hypothesis import Hypothesis
from benchmarks.core.harness import BenchmarkHarness
from benchmarks.core.metrics import aggregate_records,compute_task_improvement
from benchmarks.core.schema import MetricSpec,ProblemSpec
from benchmarks.core.variants import SystemVariant
from benchmarks.matrix import build_matrix
from benchmarks.problems.base import BenchmarkProblem
from benchmarks.problems.protocol import materialize_locked_runner


class FakeProblem(BenchmarkProblem):
    spec=ProblemSpec(
        problem_id="fake",domain="smoke",research_question="Can score improve?",
        primary_metric=MetricSpec("score","higher"),seeds=(1,2,3),
    )
    def make_hypothesis(self):
        return Hypothesis(claim="score improves",rationale="smoke",predicted_effect="score > baseline",falsification_conditions=["score <= baseline"])
    def make_experiment_spec(self,workspace,seed):
        root=Path(workspace)
        source=root/"source_runner.py"
        source.write_text(
            "import json, os\n"
            "score=0.60\n"
            "if os.getenv('AI_SCIENTIST_COMPONENT_A')=='0': score=0.55\n"
            "json.dump({'score':score},open('metrics.json','w'))\n",
            encoding="utf-8",
        )
        name,hash_=materialize_locked_runner(source,root)
        return ExperimentSpec(
            hypothesis_id=self.make_hypothesis().id,objective="locked smoke evaluator",
            command=[sys.executable,name],workspace=str(root),metrics_file="metrics.json",
            success_criteria={"score":{"op":">","value":0.0}},max_attempts=1,
            metadata={"locked_evaluator":name,"locked_evaluator_sha256":hash_,"gpu_count":0},
        )
    def ablation_components(self): return {"a":True}
    def validate_constraints(self,baseline_metrics,final_metrics): return []


class TamperProblem(FakeProblem):
    def make_experiment_spec(self,workspace,seed):
        spec=super().make_experiment_spec(workspace,seed)
        runner=Path(workspace)/spec.metadata["locked_evaluator"]
        runner.write_text(
            runner.read_text(encoding="utf-8")
            + "\nfrom pathlib import Path\nPath('_benchmark_locked_runner.py').write_text('tampered')\n",
            encoding="utf-8",
        )
        # Hash intentionally still points to the pre-tamper source.
        return spec


def test_matrix_is_predeclared_36_runs():
    matrix=build_matrix()
    assert len(matrix)==36
    assert len({(x["problem_id"],x["variant"],x["seed"]) for x in matrix})==36


def test_metric_direction():
    assert compute_task_improvement(MetricSpec("m","higher"),0.5,0.6)>0
    assert compute_task_improvement(MetricSpec("m","lower"),0.5,0.4)>0


def test_all_system_variants_execute_and_aggregate():
    records=[]
    for variant in SystemVariant:
        with TemporaryDirectory() as td:
            record,_=BenchmarkHarness().run_one(FakeProblem(),td,{"score":0.5},variant,seed=1)
            assert record.final_metrics["score"]==0.60
            assert record.valid_discovery is True
            assert record.metadata["locked_protocol_ok"] is True
            records.append(record)
    summary=aggregate_records(records)
    assert summary["runs"]==4
    assert len(summary["cells"])==4


def test_locked_evaluator_tampering_invalidates_discovery():
    with TemporaryDirectory() as td:
        record,_=BenchmarkHarness().run_one(TamperProblem(),td,{"score":0.5},SystemVariant.SINGLE_SHOT,seed=1)
        assert record.valid_discovery is False
        assert "locked evaluator hash mismatch" in record.constraint_violations


if __name__=="__main__":
    test_matrix_is_predeclared_36_runs()
    test_metric_direction()
    test_all_system_variants_execute_and_aggregate()
    test_locked_evaluator_tampering_invalidates_discovery()
    print("benchmark v1 smoke tests passed")
