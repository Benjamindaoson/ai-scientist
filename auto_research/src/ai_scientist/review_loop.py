"""Route scientific review findings into executable follow-up actions."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ReviewIssue:
    category: str
    description: str
    severity: str = "MAJOR"
    evidence_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "description": self.description,
            "severity": self.severity,
            "evidence_ids": self.evidence_ids,
        }


class ReviewActionRouter:
    ROUTES = {
        "MISSING_EXPERIMENT": "EXPERIMENT",
        "WEAK_BASELINE": "BASELINE_EXPERIMENT",
        "INSUFFICIENT_ABLATION": "ABLATION",
        "NOVELTY_THREAT": "LITERATURE_SEARCH",
        "STATISTICAL_WEAKNESS": "EXPERIMENT",
        "CLAIM_EVIDENCE_MISMATCH": "EVIDENCE_VERIFICATION",
        "IMPLEMENTATION_CONCERN": "ENGINEERING_REPAIR",
        "WRITING_ONLY": "MANUSCRIPT_REVISION",
    }

    def route(self, issues: list[ReviewIssue]) -> list[dict]:
        return [
            {
                "category": issue.category,
                "action": self.ROUTES.get(issue.category, "HUMAN_REVIEW"),
                "description": issue.description,
                "severity": issue.severity,
                "evidence_ids": issue.evidence_ids,
            }
            for issue in issues
        ]
