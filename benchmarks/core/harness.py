"""System-ablation harness for AI Scientist Benchmark v1."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from ai_scientist.autonomous_loop import AutonomousResearchLoop
from ai_scientist.research_state import ResearchState
from benchmarks.core.metrics import research_efficiency
from benchmarks.core.schema import BenchmarkRecord
from benchmarks.core.variants import SystemVariant, config_for
from benchmarks.problems.base import BenchmarkProblem
from benchmarks.problems.protocol import verify_locked_runner


class BenchmarkHarness:
    """Run predeclared system variants and score only a locked final evaluator."""

    def __init__(self, gateway=None):
        self.gateway = gateway

    @staticmethod
    def _review_stats(state: ResearchState) -> tuple[int, int, float | None]:
        issue_count=sum(len(r.get("issues",[])) for r in state.reviews)
        outcomes=[]
        for rebuttal in state.rebuttals: outcomes.extend(rebuttal.get("results",[]))
        action_count=len(outcomes)
        if issue_count==0: return issue_count,action_count,1.0
        resolved=0
        for outcome in outcomes:
            cycle=outcome.get("cycle",{})
            if cycle.get("result",{}).get("status")=="SUCCEEDED": resolved+=1; continue
            executions=outcome.get("executions",[])
            if executions and all(x.get("result",{}).get("status")=="SUCCEEDED" for x in executions): resolved+=1; continue
            if outcome.get("revised") or outcome.get("integrity",{}).get("passed"): resolved+=1
        return issue_count,action_count,min(resolved/issue_count,1.0)

    def run_one(
        self,
        problem: BenchmarkProblem,
        workspace: str | Path,
        baseline_metrics: dict[str,float],
        variant: SystemVariant | str,
        seed: int,
        ablation_components: dict[str,object] | None=None,
        literature: list[dict] | None=None,
    ) -> tuple[BenchmarkRecord,ResearchState]:
        variant=SystemVariant(variant); cfg=config_for(variant); loop=AutonomousResearchLoop(gateway=self.gateway)
        hypothesis=problem.make_hypothesis(); spec=problem.make_experiment_spec(workspace,seed); spec.hypothesis_id=hypothesis.id
        components=problem.ablation_components() if ablation_components is None else ablation_components
        state=ResearchState(
            project_id=f"benchmark_{problem.spec.problem_id}_{variant.value}_{seed}",
            problem=problem.spec.research_question,literature=literature or [],
            metadata={"benchmark_problem":problem.spec.problem_id,"benchmark_variant":variant.value,"seed":seed},
        )

        initial=loop.run_experiment_cycle(state,hypothesis,spec,unresolved_objections=[],evolve=cfg.evolve_hypothesis)
        initial_metrics=initial["result"].get("metrics",{})

        if cfg.execute_ablations and components:
            loop.execute_ablations(state,hypothesis,spec,components)

        if cfg.run_review and cfg.execute_review_actions:
            loop.run_review_revision_loop(state,hypothesis,spec,components=components,max_rounds=2)
        elif cfg.run_review:
            manuscript=loop.manuscript_builder.build(state); state.manuscript={"format":"markdown","content":manuscript}
            review=loop.reviewer.review(state,manuscript); state.append("reviews",{"round":1,**review.to_dict()})

        expected_hash=str(spec.metadata.get("locked_evaluator_sha256",""))
        protocol_ok=bool(expected_hash) and verify_locked_runner(spec.workspace,expected_hash)
        protocol_violations=[]
        final_metrics=initial_metrics
        if protocol_ok:
            final_spec=deepcopy(spec)
            final_spec.id=f"{spec.id}_locked_final"
            final_spec.objective=f"LOCKED FINAL EVALUATION: {problem.spec.research_question}"
            final_cycle=loop.run_experiment_cycle(state,hypothesis,final_spec,unresolved_objections=[],evolve=False)
            final_metrics=final_cycle["result"].get("metrics",{})
        else:
            protocol_violations.append("locked evaluator hash mismatch")

        manuscript=loop.manuscript_builder.build(state); state.manuscript={"format":"markdown","content":manuscript}
        integrity=loop.integrity_report(state) if cfg.run_integrity else None
        meta=None
        if cfg.run_review:
            final_review=loop.reviewer.review(state,manuscript)
            state.append("reviews",{"round":"final_locked",**final_review.to_dict()})
            meta=loop.meta_reviewer.decide(final_review,integrity)
            state.append("decisions",{"type":"META_REVIEW","benchmark_final":True,**meta})

        improvement=problem.score(baseline_metrics,final_metrics)
        valid,violations=problem.valid_discovery(baseline_metrics,final_metrics)
        violations.extend(protocol_violations)
        if protocol_violations: valid=False
        if integrity is not None and not integrity.get("passed",False):
            valid=False; violations.append("integrity audit failed")

        gpu_count=float(spec.metadata.get("gpu_count",0) or 0)
        wall_hours=sum(float(r.get("duration_seconds",0.0)) for r in state.experiment_runs)/3600.0
        compute_hours=wall_hours*gpu_count if gpu_count>0 else wall_hours
        issue_count,action_count,resolution_rate=self._review_stats(state)
        evolution_gain=None
        if cfg.evolve_hypothesis and initial_metrics and final_metrics:
            evolution_gain=improvement-problem.score(baseline_metrics,initial_metrics)

        record=BenchmarkRecord(
            problem_id=problem.spec.problem_id,variant=variant.value,seed=seed,
            baseline_metrics=baseline_metrics,final_metrics=final_metrics,
            task_improvement=improvement,valid_discovery=valid,constraint_violations=violations,
            experiment_count=len(state.experiment_runs),compute_hours=compute_hours,
            research_efficiency=research_efficiency(improvement,compute_hours,len(state.experiment_runs)),
            hypothesis_evolution_gain=evolution_gain,review_issue_count=issue_count,
            review_action_count=action_count,review_resolution_rate=resolution_rate,
            integrity_passed=None if integrity is None else bool(integrity.get("passed")),
            meta_review_decision=None if meta is None else meta.get("decision"),
            metadata={"initial_metrics":initial_metrics,"locked_protocol_ok":protocol_ok},
        )
        return record,state
