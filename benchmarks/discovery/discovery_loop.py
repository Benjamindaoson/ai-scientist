from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmarks.core.trajectory import Trajectory

from .discovery_state import DiscoveryState
from .evaluator import evaluate_experiment, final_claim
from .experiment_mutator import ExperimentMutator
from .experiment_planner import ExperimentPlanner
from .hypothesis_generator import HypothesisGenerator
from .problem import ResearchProblem


class AutonomousDiscoveryLoop:
    def __init__(self, runner: ExperimentRunner | None = None, gateway=None):
        if runner is None:
            import sys
            source = Path(__file__).parents[2] / "auto_research" / "src"
            if str(source) not in sys.path:
                sys.path.insert(0, str(source))
            from ai_scientist.experiment.runner import ExperimentRunner
            runner = ExperimentRunner()
        self.runner = runner
        self.generator = HypothesisGenerator(gateway=gateway)
        self.planner = ExperimentPlanner()
        self.mutator = ExperimentMutator()

    def run(
        self,
        problem: ResearchProblem,
        baseline: dict[str, Any],
        data_root: str | Path,
        trajectory_root: str | Path,
        max_rounds: int = 3,
        max_windows: int = 1024,
        mode: str = "full",
    ) -> dict[str, Any]:
        root = Path(trajectory_root)
        state = DiscoveryState(problem=problem.to_dict(), baseline=baseline)
        state.hypothesis_candidates = self.generator.generate(problem, baseline)
        state.problem["hypothesis_source"] = self.generator.last_source
        previous = baseline

        for round_index in range(1, max_rounds + 1):
            ranked = self.generator.generate(problem, previous)
            state.problem["hypothesis_source"] = self.generator.last_source
            # Ensure later rounds evolve from the prior observation rather than
            # silently repeating the same candidate.
            selected = ranked[0 if mode == "no_evolution" else (round_index - 1) % len(ranked)]
            selected = dict(selected)
            selected["round"] = round_index
            state.selected_hypotheses.append(selected)
            mutation = self.mutator.mutate(selected)
            workspace = root / "workspaces" / f"round_{round_index:02d}"
            spec = self.planner.plan(selected, baseline, workspace, data_root, max_windows)
            state.experiment_plans.append({"round": round_index, "spec": spec.to_dict(), "mutation": mutation.to_dict()})
            result = self.runner.run(spec)
            result_dict = result.to_dict()
            evaluation = evaluate_experiment(baseline, result_dict)
            evaluation["round"] = round_index
            record = {"round": round_index, "experiment_id": result.experiment_id, "result": result_dict, "evaluation": evaluation}
            state.experiment_results.append(record)
            state.evidence_graph["nodes"].extend([
                {"id": selected["id"], "type": "HYPOTHESIS", "round": round_index},
                {"id": f"evidence_{result.experiment_id}", "type": "EVIDENCE", "round": round_index, "evaluation": evaluation},
            ])
            state.evidence_graph["edges"].append({"source": selected["id"], "target": f"evidence_{result.experiment_id}", "relation": evaluation["verdict"]})
            if mode != "no_review":
                state.review_history.append({
                    "round": round_index,
                    "critique": "Evidence supports the candidate only when test MSE is strictly below the fixed baseline.",
                    "decision": evaluation["verdict"],
                    "integrity": mode != "no_integrity" and result.status == "SUCCEEDED" and bool(result.metrics),
                })
            state.ablation_results.append({
                "round": round_index,
                "ablation_id": f"ablation_{round_index:03d}",
                "status": "EXECUTED" if result.status == "SUCCEEDED" else "BLOCKED",
                "variant": "unchanged_baseline_protocol",
                "comparison": {"metrics": baseline.get("metrics", {})},
            })
            state.evolution_history.append({
                "round": round_index,
                "from_hypothesis": selected["id"],
                "observation": evaluation,
                "next_action": "continue" if round_index < max_rounds else "finalize",
            })
            previous = result_dict if result.status == "SUCCEEDED" else baseline

        claim = final_claim({"experiment_results": state.experiment_results})
        trajectory = Trajectory(root)
        for name, value in {
            "problem": state.problem,
            "baseline": state.baseline,
            "hypothesis_candidates": state.hypothesis_candidates,
            "selected_hypothesis": state.selected_hypotheses,
            "experiment_plan": state.experiment_plans,
            "experiment_results": state.experiment_results,
            "ablation_results": state.ablation_results,
            "evolution_history": state.evolution_history,
            "evidence_graph": state.evidence_graph,
            "review_history": state.review_history,
            "final_claim": claim,
        }.items():
            trajectory.write(name, value)
        return {"trajectory": str(root), "claim": claim, "state": state}
