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
    """Check traceability, recovered execution validity, and claim support."""

    @staticmethod
    def _root_experiment_id(experiment_id: str) -> str:
        return experiment_id.split("_retry", 1)[0]

    def audit(self, state: ResearchState, graph: EvidenceGraph | None = None) -> IntegrityReport:
        findings = []
        runs = state.experiment_runs

        # Recovery-aware execution check: an experiment is valid when at least one
        # attempt in its retry lineage succeeds.
        status_by_root: dict[str, list[dict]] = {}
        for run in runs:
            root = self._root_experiment_id(str(run.get("experiment_id", "")))
            status_by_root.setdefault(root, []).append(run)
        unrecovered = [
            root for root, attempts in status_by_root.items()
            if not any(a.get("status") == "SUCCEEDED" for a in attempts)
        ]
        findings.append(AuditFinding(
            "experiment_execution",
            bool(status_by_root) and not unrecovered,
            f"Unrecovered experiments: {unrecovered}" if unrecovered else "Every experiment lineage has a successful execution.",
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

        successful_runs = [r for r in runs if r.get("status") == "SUCCEEDED"]
        findings.append(AuditFinding(
            "metrics_present",
            bool(successful_runs) and all(isinstance(r.get("metrics"), dict) and bool(r.get("metrics")) for r in successful_runs),
            "Every successful experiment must record non-empty metrics.",
        ))

        if graph is not None:
            claim_nodes = [n for n in graph.nodes.values() if n.get("type") == "CLAIM"]
            unsupported = [n["id"] for n in claim_nodes if not graph.evidence_for_claim(n["id"])]
            findings.append(AuditFinding(
                "claim_evidence_traceability",
                bool(claim_nodes) and not unsupported,
                f"Unsupported claims: {unsupported}" if unsupported else "All graph claims have linked evidence.",
            ))

        findings.append(AuditFinding(
            "manuscript_present",
            bool(state.manuscript.get("body")) if state.manuscript else False,
            "A final manuscript must be generated from structured state.",
        ))
        return IntegrityReport(findings)
