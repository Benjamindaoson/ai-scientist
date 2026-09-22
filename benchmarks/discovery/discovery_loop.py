from __future__ import annotations

import json
import hashlib
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
        tried_mutations: set[str] = set()

        for round_index in range(1, max_rounds + 1):
            ranked = self.generator.generate(problem, previous)
            state.problem["hypothesis_source"] = self.generator.last_source
            state.candidate_history.append({"round": round_index, "candidates": ranked})
            for candidate in ranked:
                mutation_key = json.dumps(candidate.get("mutation", {}), sort_keys=True)
                candidate["selection_score"] = round(
                    float(candidate.get("rank_score", 0.0))
                    + (0.25 if mutation_key not in tried_mutations else 0.0), 6
                )
            selected = max(ranked, key=lambda item: item["selection_score"])
            selected = dict(selected)
            original_id = selected["id"]
            parent_id = state.selected_hypotheses[-1]["id"] if state.selected_hypotheses else None
            provenance = f"{selected['claim']}|{selected['mechanism']}|{json.dumps(selected['mutation'], sort_keys=True)}|{parent_id}"
            immutable_id = f"hyp_r{round_index:02d}_{hashlib.sha256(provenance.encode()).hexdigest()[:8]}"
            selected["id"] = immutable_id
            selected["original_candidate_id"] = original_id
            selected["parent_id"] = parent_id
            selected["generation"] = round_index
            selected["selection_reason"] = {
                "utility": selected["selection_score"],
                "formula": "rank_score + 0.25 information_gain for an untried mutation",
                "alternatives_considered": [item["id"] for item in ranked if item["id"] != original_id],
            }
            tried_mutations.add(json.dumps(selected.get("mutation", {}), sort_keys=True))
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
            control = dict(selected)
            control["id"] = f"ablation_r{round_index:02d}_control"
            control["claim"] = "Unchanged DLinear baseline control"
            control["mutation"] = {}
            control_spec = self.planner.plan(control, baseline, root / "workspaces" / f"round_{round_index:02d}_ablation", data_root, max_windows, evaluation_split="val")
            control_result = self.runner.run(control_spec).to_dict()
            control_evaluation = evaluate_experiment(baseline, control_result)
            state.ablation_results.append({
                "round": round_index,
                "ablation_id": f"ablation_{round_index:03d}",
                "status": "EXECUTED" if control_result["status"] == "SUCCEEDED" else "BLOCKED",
                "variant": "unchanged_baseline_protocol",
                "spec": control_spec.to_dict(),
                "result": control_result,
                "evaluation": control_evaluation,
            })
            state.evolution_history.append({
                "round": round_index,
                "from_hypothesis": selected["id"],
                "observation": evaluation,
                "next_action": "continue" if round_index < max_rounds else "finalize",
            })
            previous = result_dict if result.status == "SUCCEEDED" else baseline

        frozen = state.selected_hypotheses[-1]
        final_spec = self.planner.plan(
            frozen, baseline, root / "workspaces" / "final_test", data_root, max_windows, evaluation_split="test"
        )
        final_test_result = self.runner.run(final_spec).to_dict()
        final_test_baseline = dict(baseline)
        final_test_baseline["split"] = "test"
        # The test control is run once, after the final candidate is frozen.
        control_spec = self.planner.plan(
            {**frozen, "id": "final_test_control", "mutation": {}},
            baseline, root / "workspaces" / "final_test_control", data_root, max_windows, evaluation_split="test"
        )
        control_test_result = self.runner.run(control_spec).to_dict()
        state.final_test = {
            "candidate": final_test_result,
            "control": control_test_result,
            "evaluation": evaluate_experiment(
                {"metrics": control_test_result.get("metrics", {}).get("metrics", {})},
                final_test_result,
            ),
            "protocol": "test evaluated once after candidate freeze",
        }
        claim = final_claim({"experiment_results": state.experiment_results, "final_test": state.final_test})
        trajectory = Trajectory(root)
        for name, value in {
            "problem": state.problem,
            "baseline": state.baseline,
            "hypothesis_candidates": state.hypothesis_candidates,
            "candidate_history": state.candidate_history,
            "selected_hypothesis": state.selected_hypotheses,
            "experiment_plan": state.experiment_plans,
            "experiment_results": state.experiment_results,
            "ablation_results": state.ablation_results,
            "evolution_history": state.evolution_history,
            "evidence_graph": state.evidence_graph,
            "review_history": state.review_history,
            "final_claim": claim,
            "final_test": state.final_test,
        }.items():
            trajectory.write(name, value)
        return {"trajectory": str(root), "claim": claim, "state": state}
