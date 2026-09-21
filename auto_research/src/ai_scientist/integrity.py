"""Scientific integrity audits for autonomous research artifacts."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .evidence_graph import EvidenceGraph
from .experiment.models import ExperimentResult, ExperimentSpec
from .experiment.sandbox import WorkspaceSandbox


@dataclass
class AuditCheck:
    name: str
    passed: bool
    details: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "details": self.details}


@dataclass
class IntegrityReport:
    checks: list[AuditCheck] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def to_dict(self) -> dict:
        return {"passed": self.passed, "checks": [c.to_dict() for c in self.checks]}


class IntegrityAuditor:
    def __init__(self, sandbox: WorkspaceSandbox | None = None):
        self.sandbox = sandbox or WorkspaceSandbox()

    def audit(
        self,
        graph: EvidenceGraph,
        specs: list[ExperimentSpec],
        results: list[ExperimentResult],
        literature: list[dict] | None = None,
    ) -> IntegrityReport:
        checks = []
        unsupported = graph.unsupported_claims()
        checks.append(AuditCheck(
            "claim_evidence_coverage",
            not unsupported,
            "All claims have evidence." if not unsupported else f"Unsupported claims: {unsupported}",
        ))

        result_ids = {r.experiment_id for r in results}
        missing_results = [s.id for s in specs if s.id not in result_ids]
        checks.append(AuditCheck(
            "experiment_result_alignment",
            not missing_results,
            "Every experiment spec has a result." if not missing_results else f"Missing: {missing_results}",
        ))

        violations = []
        for spec in specs:
            try:
                self.sandbox.resolve_workspace(spec.workspace)
                self.sandbox.validate_command(spec.command)
                self.sandbox.safe_path(spec.workspace, spec.metrics_file)
            except Exception as exc:
                violations.append(f"{spec.id}: {exc}")
        checks.append(AuditCheck(
            "specification_compliance",
            not violations,
            "Experiment specifications obey workspace/command policy." if not violations else "; ".join(violations),
        ))

        malformed_refs = [
            p for p in (literature or [])
            if not p.get("title") or not (p.get("arxiv_id") or p.get("doi") or p.get("url") or p.get("id"))
        ]
        checks.append(AuditCheck(
            "reference_metadata",
            not malformed_refs,
            "References have traceable identifiers." if not malformed_refs else f"Malformed references: {len(malformed_refs)}",
        ))

        missing_artifacts = []
        specs_by_id = {s.id: s for s in specs}
        for result in results:
            spec = specs_by_id.get(result.experiment_id)
            if not spec:
                continue
            root = Path(spec.workspace)
            for artifact in result.artifacts:
                if not (root / artifact).exists():
                    missing_artifacts.append(f"{result.experiment_id}:{artifact}")
        checks.append(AuditCheck(
            "artifact_traceability",
            not missing_artifacts,
            "Recorded artifacts exist." if not missing_artifacts else f"Missing artifacts: {missing_artifacts[:10]}",
        ))

        return IntegrityReport(checks)
