"""Integrity audit for autonomous research artifacts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .evidence_graph import EvidenceGraph
from .research_state import ResearchState


@dataclass
class AuditFinding:
    check: str
    passed: bool
    details: str

    def to_dict(self) -> dict[str, Any]:
        return {"check": self.check, "passed": self.passed, "details": self.details}


@dataclass
class IntegrityReport:
    findings: list[AuditFinding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(f.passed for f in self.findings)

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "findings": [f.to_dict() for f in self.findings]}


class IntegrityAuditor:
    """Check traceability, execution validity, and claim support."""

    def audit(self, state: ResearchState, graph: EvidenceGraph | None = None) -> IntegrityReport:
        findings = []
        runs = state.experiment_runs
        findings.append(AuditFinding(
            "experiment_execution",
            bool(runs) and all(r.get("status") == "SUCCEEDED" for r in runs),
            "All recorded experiments must execute successfully.",
        ))

        evidence_ids = {e.get("id") for e in state.evidence}
        referenced = set()
        for h in state.hypotheses:
            referenced.update(h.get("supporting_evidence_ids", []))
            referenced.update(h.get("contradicting_evidence_ids", []))
        findings.append(AuditFinding(
            "evidence_references",
            referenced.issubset(evidence_ids),
            "All hypothesis evidence references must resolve to stored evidence.",
        ))

        findings.append(AuditFinding(
            "metrics_present",
            bool(runs) and all(isinstance(r.get("metrics"), dict) and r.get("metrics") for r in runs),
            "Every successful experiment must record non-empty metrics.",
        ))

        if graph is not None:
            claim_nodes = [n for n in graph.nodes.values() if n.get("type") == "CLAIM"]
            unsupported = [n["id"] for n in claim_nodes if not graph.evidence_for_claim(n["id"])]
            findings.append(AuditFinding(
                "claim_evidence_traceability",
                not unsupported,
                f"Unsupported claims: {unsupported}" if unsupported else "All graph claims have linked evidence.",
            ))

        findings.append(AuditFinding(
            "manuscript_present",
            bool(state.manuscript.get("body")) if state.manuscript else False,
            "A final manuscript must be generated from structured state.",
        ))
        return IntegrityReport(findings)
