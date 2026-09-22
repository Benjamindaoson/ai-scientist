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
        dataset_kwargs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        root = Path(trajectory_root)
        state = DiscoveryState(problem=problem.to_dict(), baseline=baseline)
        state.hypothesis_candidates = []
        state.problem["hypothesis_source"] = self.generator.last_source
        previous = baseline
        tried_mutations: set[str] = set()
        test_accessed = False

        for round_index in range(1, max_rounds + 1):
            prior_context = {
                "previous_result": previous,
                "previous_hypothesis": state.selected_hypotheses[-1] if state.selected_hypotheses else None,
                "previous_review": state.review_history[-1] if state.review_history else None,
            }
            ranked = self.generator.generate(
                problem,
                previous,
                prior_context=prior_context,
                tested_mutations=[json.loads(item) for item in tried_mutations],
            )
            state.problem["hypothesis_source"] = self.generator.last_source
            for candidate in ranked:
                mutation_key = json.dumps(candidate.get("mutation", {}), sort_keys=True)
                candidate["selection_score"] = round(
                    float(candidate.get("rank_score", 0.0))
                    + (0.25 if mutation_key not in tried_mutations else 0.0), 6
                )
            parent_id = state.selected_hypotheses[-1]["id"] if state.selected_hypotheses else None
            for candidate_index, candidate in enumerate(ranked, start=1):
                provenance = f"{candidate['claim']}|{candidate['mechanism']}|{json.dumps(candidate['mutation'], sort_keys=True)}|{parent_id}|{round_index}"
                candidate["id"] = f"hyp_r{round_index:02d}_{candidate_index:03d}_{hashlib.sha256(provenance.encode()).hexdigest()[:6]}"
                candidate["round"] = round_index
                candidate["generation"] = round_index
                candidate["parent_hypothesis_id"] = parent_id
                candidate["mutation_fingerprint"] = hashlib.sha256(json.dumps(candidate["mutation"], sort_keys=True).encode()).hexdigest()[:12]
                candidate["source"] = self.generator.last_source
                candidate["model"] = getattr(self.generator.gateway, "model", "deterministic-fallback")
                candidate["prompt_hash"] = hashlib.sha256(json.dumps(prior_context, sort_keys=True, default=str).encode()).hexdigest()
            state.candidate_history.append({"round": round_index, "candidates": ranked})
            if not state.hypothesis_candidates:
                state.hypothesis_candidates = [dict(item) for item in ranked]
            eligible = [
                item for item in ranked
                if json.dumps(item.get("mutation", {}), sort_keys=True) not in tried_mutations
            ]
            if not eligible:
                eligible = ranked
            selected = dict(max(eligible, key=lambda item: item["selection_score"]))
            selected_id = selected["id"]
            selected["selection_reason"] = {
                "utility": selected["selection_score"],
                "formula": "rank_score + 0.25 information_gain for an untried mutation",
                "alternatives_considered": [item["id"] for item in ranked if item["id"] != selected_id],
                "rejected_duplicate_candidates": [item["id"] for item in ranked if json.dumps(item.get("mutation", {}), sort_keys=True) in tried_mutations],
                "eligible_candidates": [item["id"] for item in eligible],
            }
            tried_mutations.add(json.dumps(selected.get("mutation", {}), sort_keys=True))
            state.selected_hypotheses.append(selected)
            mutation = self.mutator.mutate(selected)
            workspace = root / "workspaces" / f"round_{round_index:02d}"
            spec = self.planner.plan(selected, baseline, workspace, data_root, max_windows, dataset_kwargs=dataset_kwargs)
            state.experiment_plans.append({"round": round_index, "spec": spec.to_dict(), "mutation": mutation.to_dict()})
            result = self.runner.run(spec)
            result_dict = result.to_dict()
            evaluation = evaluate_experiment(baseline, result_dict, selected.get("evaluation_contract"))
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
            control_spec = self.planner.plan(control, baseline, root / "workspaces" / f"round_{round_index:02d}_ablation", data_root, max_windows, evaluation_split="val", dataset_kwargs=dataset_kwargs)
            control_result = self.runner.run(control_spec).to_dict()
            control_evaluation = evaluate_experiment(baseline, control_result, {"primary_metric": "mse", "direction": "decrease", "minimum_effect": 0.005})
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
            previous = {
                "result": result_dict,
                "evaluation": evaluation,
                "critique": state.review_history[-1] if state.review_history else None,
            }

        frozen = state.selected_hypotheses[-1]
        final_spec = self.planner.plan(
            frozen, baseline, root / "workspaces" / "final_test", data_root, max_windows, evaluation_split="test", dataset_kwargs=dataset_kwargs
        )
        final_test_result = self.runner.run(final_spec).to_dict()
        final_test_baseline = dict(baseline)
        final_test_baseline["split"] = "test"
        # The test control is run once, after the final candidate is frozen.
        control_spec = self.planner.plan(
            {**frozen, "id": "final_test_control", "mutation": {}},
            baseline, root / "workspaces" / "final_test_control", data_root, max_windows, evaluation_split="test", dataset_kwargs=dataset_kwargs
        )
        control_test_result = self.runner.run(control_spec).to_dict()
        test_accessed = True
        final_validation = next(item for item in state.experiment_results if item["experiment_id"] == state.selected_hypotheses[-1]["id"] or item["result"]["hypothesis_id"] == frozen["id"])
        state.final_test = {
            "candidate": final_test_result,
            "control": control_test_result,
            "evaluation": evaluate_experiment(
                {"metrics": control_test_result.get("metrics", {}).get("metrics", {})},
                final_test_result,
                frozen.get("evaluation_contract"),
            ),
            "protocol": "test evaluated once after candidate freeze",
            "test_accessed_after_freeze": test_accessed,
        }
        state.final_test["candidate"]["metrics"] = state.final_test["candidate"].get("metrics", {}).get("metrics", {})
        state.final_test["control"]["metrics"] = state.final_test["control"].get("metrics", {}).get("metrics", {})
        state.final_test["evaluation"] = evaluate_experiment(
            {"metrics": state.final_test["control"]["metrics"]},
            {"status": state.final_test["candidate"]["status"], "metrics": state.final_test["candidate"]["metrics"]},
            frozen.get("evaluation_contract"),
        )
        state.final_test["evaluation"]["candidate_experiment_id"] = state.final_test["candidate"]["experiment_id"]
        claim = final_claim({
            "experiment_results": state.experiment_results,
            "final_hypothesis": frozen,
            "final_validation": final_validation["evaluation"] | {"experiment_id": final_validation["experiment_id"], "metrics": final_validation["result"]["metrics"]},
            "final_test": state.final_test,
            "baseline_validation_metrics": baseline.get("metrics", {}),
        })
        manifest = {
            "benchmark": problem.benchmark,
            "dataset": "ETTm1",
            "split_policy": {"search": "train->val", "final": "frozen candidate->test once"},
            "backend": baseline.get("backend", "numpy_fallback"),
            "seeds": [baseline.get("seed", 1)],
            "model": "DLinear",
            "training_budget": {"max_windows": max_windows},
            "effect_threshold": 0.005,
            "max_rounds": max_rounds,
            "test_access_policy": {"test_accessed_after_freeze": test_accessed, "evolution_after_test": False},
            "status": "FINALIZED",
        }
        trajectory = Trajectory(root)
        for name, value in {
            "problem": state.problem,
            "baseline": state.baseline,
            "hypothesis_candidates": state.hypothesis_candidates,
            "candidate_history": state.candidate_history,
            "candidate_generation_history": state.candidate_history,
            "selected_hypothesis": state.selected_hypotheses,
            "experiment_plan": state.experiment_plans,
            "experiment_results": state.experiment_results,
            "ablation_results": state.ablation_results,
            "control_or_ablation_results": state.ablation_results,
            "evolution_history": state.evolution_history,
            "evidence_graph": state.evidence_graph,
            "review_history": state.review_history,
            "final_claim": claim,
            "final_test": state.final_test,
            "final_hypothesis": frozen,
            "final_verification": state.final_test,
            "protocol_manifest": manifest,
        }.items():
            trajectory.write(name, value)
        return {"trajectory": str(root), "claim": claim, "state": state}
