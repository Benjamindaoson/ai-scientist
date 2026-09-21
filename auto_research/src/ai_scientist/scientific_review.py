"""Peer review, rebuttal planning, and meta review."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from .core.gateway import BaseGateway
from .review_loop import ReviewActionRouter, ReviewIssue


@dataclass
class PeerReview:
    summary: str
    issues: list[ReviewIssue] = field(default_factory=list)
    recommendation: str = "REVISE"

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "issues": [i.to_dict() for i in self.issues],
            "recommendation": self.recommendation,
        }


class PeerReviewer:
    def __init__(self, gateway: BaseGateway | None = None):
        self.gateway = gateway

    def review(self, manuscript: dict, research_state: dict) -> PeerReview:
        if self.gateway:
            prompt = (
                "Act as a skeptical scientific reviewer. Return ONLY JSON: "
                "{summary, recommendation, issues:[{category,description,severity,evidence_ids}]}. "
                "Allowed categories: MISSING_EXPERIMENT, WEAK_BASELINE, INSUFFICIENT_ABLATION, "
                "NOVELTY_THREAT, STATISTICAL_WEAKNESS, CLAIM_EVIDENCE_MISMATCH, "
                "IMPLEMENTATION_CONCERN, WRITING_ONLY.\n"
                f"MANUSCRIPT={json.dumps(manuscript)}\nSTATE={json.dumps(research_state, default=str)}"
            )
            try:
                data = json.loads(self.gateway.generate(prompt))
                return PeerReview(
                    summary=data.get("summary", ""),
                    recommendation=data.get("recommendation", "REVISE"),
                    issues=[ReviewIssue(**x) for x in data.get("issues", [])],
                )
            except Exception:
                pass

        issues = []
        if not research_state.get("experiment_runs"):
            issues.append(ReviewIssue("MISSING_EXPERIMENT", "No executable experiment is recorded."))
        if not research_state.get("ablations"):
            issues.append(ReviewIssue("INSUFFICIENT_ABLATION", "No ablation evidence is recorded."))
        if not research_state.get("evidence"):
            issues.append(ReviewIssue("CLAIM_EVIDENCE_MISMATCH", "No evidence is linked to empirical claims."))
        recommendation = "REVISE" if issues else "ACCEPT"
        return PeerReview("Deterministic evidence-based review.", issues, recommendation)


class RebuttalPlanner:
    def __init__(self):
        self.router = ReviewActionRouter()

    def plan(self, review: PeerReview) -> list[dict]:
        return self.router.route(review.issues)


@dataclass
class MetaReview:
    decision: str
    unresolved_categories: list[str]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "unresolved_categories": self.unresolved_categories,
            "rationale": self.rationale,
        }


class MetaReviewer:
    """Require empirical issues to be resolved before acceptance."""

    EMPIRICAL_BLOCKERS = {
        "MISSING_EXPERIMENT", "WEAK_BASELINE", "INSUFFICIENT_ABLATION",
        "STATISTICAL_WEAKNESS", "CLAIM_EVIDENCE_MISMATCH", "IMPLEMENTATION_CONCERN",
    }

    def decide(self, review: PeerReview, resolved_categories: set[str] | None = None) -> MetaReview:
        resolved = resolved_categories or set()
        unresolved = [i.category for i in review.issues if i.category not in resolved]
        blocking = [c for c in unresolved if c in self.EMPIRICAL_BLOCKERS]
        decision = "ACCEPT" if not blocking else "REVISE"
        return MetaReview(
            decision=decision,
            unresolved_categories=unresolved,
            rationale="All empirical blockers resolved." if decision == "ACCEPT" else "Empirical review blockers remain unresolved.",
        )
