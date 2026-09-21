from __future__ import annotations


def scientific_improvement(baseline_score: float, final_score: float, higher_is_better: bool = True) -> float:
    return final_score - baseline_score if higher_is_better else baseline_score - final_score


def hypothesis_evolution_gain(hypotheses: list[dict]) -> int:
    return max(0, sum(1 for item in hypotheses if item.get("status") == "EVOLVED"))


def research_efficiency(final_score: float, experiment_count: int, cost: float = 0.0) -> float:
    denominator = max(1.0, experiment_count + cost)
    return final_score / denominator


def review_resolution_rate(reviews: list[dict]) -> float:
    issues = sum(len(item.get("issues", [])) for item in reviews)
    resolved = sum(1 for item in reviews for issue in item.get("issues", []) if issue.get("status") in {"RESOLVED", "FIXED"})
    return resolved / issues if issues else 1.0


def integrity_score(audits: list[dict]) -> float:
    return sum(bool(audit.get("passed")) for audit in audits) / len(audits) if audits else 0.0


def trajectory_completeness(trajectory: dict) -> float:
    required = ("problem", "baseline", "hypothesis_history", "experiment_history", "evidence_graph", "reviews", "final_decision")
    return sum(name in trajectory and trajectory[name] is not None for name in required) / len(required)
