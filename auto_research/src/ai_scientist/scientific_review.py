"""Peer review, rebuttal planning, and meta-review."""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .core.gateway import BaseGateway
from .research_state import ResearchState
from .review_loop import ReviewActionRouter, ReviewIssue


@dataclass
class PeerReview:
    issues: list[ReviewIssue] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {"issues": [i.to_dict() for i in self.issues], "summary": self.summary}


class ScientificReviewer:
    def __init__(self, gateway: BaseGateway | None = None):
        self.gateway = gateway

    def review(self, state: ResearchState, manuscript: str = "") -> PeerReview:
        if self.gateway:
            prompt = f"""Review this research package as a strict scientific reviewer.
Return ONLY JSON {{"summary":"...","issues":[{{"category":"MISSING_EXPERIMENT|WEAK_BASELINE|INSUFFICIENT_ABLATION|NOVELTY_THREAT|STATISTICAL_WEAKNESS|CLAIM_EVIDENCE_MISMATCH|IMPLEMENTATION_CONCERN|WRITING_ONLY","description":"...","severity":"MAJOR|MINOR"}}]}}.
Do not invent evidence.
STATE={json.dumps(state.to_dict(), default=str)[:30000]}
MANUSCRIPT={manuscript[:12000]}"""
            try:
                data = json.loads(self.gateway.generate(prompt))
                return PeerReview(
                    issues=[ReviewIssue(**i) for i in data.get("issues", [])],
                    summary=data.get("summary", ""),
                )
            except Exception:
                pass

        issues = []
        if not state.experiment_runs:
            issues.append(ReviewIssue("MISSING_EXPERIMENT", "No executed experiment supports the research claim."))
        if state.experiment_runs and not state.ablations:
            issues.append(ReviewIssue("INSUFFICIENT_ABLATION", "No ablation isolates the claimed mechanism."))
        if state.hypotheses and not state.evidence:
            issues.append(ReviewIssue("CLAIM_EVIDENCE_MISMATCH", "Hypotheses exist without linked evidence."))
        return PeerReview(issues=issues, summary="Structured review from recorded research state.")


class RebuttalPlanner:
    def __init__(self):
        self.router = ReviewActionRouter()

    def plan(self, review: PeerReview) -> list[dict]:
        return self.router.route(review.issues)


class MetaReviewer:
    def decide(self, review: PeerReview, integrity_report: dict | None = None) -> dict:
        blocking = [i for i in review.issues if i.severity == "MAJOR"]
        integrity_ok = True if integrity_report is None else integrity_report.get("passed", False)
        decision = "ACCEPT" if not blocking and integrity_ok else "REVISE"
        return {
            "decision": decision,
            "major_issues": len(blocking),
            "integrity_passed": integrity_ok,
            "reason": "No blocking scientific issues remain." if decision == "ACCEPT"
                      else "Blocking review or integrity issues remain.",
        }
