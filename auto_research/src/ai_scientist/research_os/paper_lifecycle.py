from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from sqlalchemy import select

from ai_scientist.research_os.agents import ReviewFinding
from ai_scientist.research_store import ArtifactStore, ResearchRepository
from ai_scientist.research_store import models
from ai_scientist.research_store.repository import canonical_hash


REVIEW_ROUTES = {
    "WRITING": ["editor"],
    "STATISTICS": ["analyst"],
    "IMPLEMENTATION": ["engineer"],
    "MISSING_EXPERIMENT": ["pi", "engineer"],
    "NOVELTY": ["scout", "reviewer"],
    "CITATION": ["scout", "reviewer"],
    "CLAIM_EVIDENCE": ["pi", "analyst"],
    "PROTOCOL": ["pi", "reviewer"],
}


def _latex(value: Any) -> str:
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}"}
    return re.sub(r"[\\&%$#_{}]", lambda match: replacements[match.group(0)], str(value))


class LatexCompiler:
    def __init__(self, command: str | None = None):
        self.command = command or shutil.which("tectonic") or shutil.which("pdflatex")

    def compile(self, source: Path) -> Path:
        if not self.command:
            raise RuntimeError("No supported LaTeX compiler is installed")
        executable = Path(self.command).name.lower()
        command = [self.command, str(source)] if executable.startswith("tectonic") else [self.command, "-interaction=nonstopmode", "-halt-on-error", source.name]
        completed = subprocess.run(command, cwd=source.parent, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180, check=False, shell=False)
        if completed.returncode != 0:
            raise RuntimeError(f"LaTeX compilation failed: {completed.stderr[-2000:] or completed.stdout[-2000:]}")
        pdf = source.with_suffix(".pdf")
        if not pdf.is_file():
            raise RuntimeError("LaTeX compiler did not create a PDF")
        return pdf


class PaperLifecycleService:
    def __init__(self, repository: ResearchRepository, artifacts: ArtifactStore, build_root: str | Path, compiler: Any | None = None):
        self.repository = repository
        self.artifacts = artifacts
        self.build_root = Path(build_root).resolve()
        self.build_root.mkdir(parents=True, exist_ok=True)
        self.compiler = compiler or LatexCompiler()

    def freeze_claim(
        self, project_id: str, claim_type: str, claim_text: str, *, scope: dict,
        protocol_version_id: str, analysis_run_ids: list[str], evidence_ids: list[str],
        counterevidence_ids: list[str] | None = None, parent_claim_id: str | None = None,
    ) -> dict[str, Any]:
        protocol = self.repository.get_protocol(protocol_version_id)
        if not protocol or protocol["status"] != "FROZEN":
            raise ValueError("claim requires a frozen protocol")
        analyses = [self.repository.get_analysis_run(item) for item in analysis_run_ids]
        if not analyses or any(not item or item["project_id"] != project_id or item["protocol_version_id"] != protocol_version_id or item["status"] != "COMPLETE" for item in analyses):
            raise ValueError("claim analyses must be complete and bound to the same frozen protocol")
        evidence = [self.repository.get_evidence_item(item) for item in evidence_ids]
        if not evidence or any(not item or item["validity_status"] == "INVALID" or item["source_ref"].get("analysis_run_id") not in analysis_run_ids for item in evidence):
            raise ValueError("claim evidence must be valid and analysis-bound")
        parent = self.repository.get_claim(parent_claim_id) if parent_claim_id else None
        version = (parent["version"] + 1) if parent else 1
        content_hash = canonical_hash({
            "text": claim_text, "scope": scope, "protocol": protocol_version_id,
            "analyses": analysis_run_ids, "evidence": evidence_ids, "counterevidence": counterevidence_ids or [],
        })
        claim = self.repository.create_claim(
            project_id, claim_type, claim_text, scope=scope, created_by_role="pi", status="FROZEN",
            version=version, parent_claim_id=parent_claim_id, content_hash=content_hash,
        )
        counter = set(counterevidence_ids or [])
        for evidence_id in evidence_ids:
            self.repository.link_claim_evidence(
                claim["claim_id"], evidence_id, "CONTRADICTS" if evidence_id in counter else "SUPPORTS",
                "Frozen claim evidence binding", "pi", review_status="VERIFIED",
            )
        return claim

    def correct_analysis(self, analysis_run_id: str, *, results: dict, uncertainty: dict | None = None, reason: str) -> dict[str, Any]:
        old = self.repository.get_analysis_run(analysis_run_id)
        if not old:
            raise KeyError(analysis_run_id)
        corrected = self.repository.create_analysis_run(
            old["project_id"], old["protocol_version_id"], list(old["input_experiment_run_ids"]),
            analysis_code_revision=f"{old['analysis_code_revision']}:correction",
            analysis_plan_hash=old["analysis_plan_hash"], status="COMPLETE", results=results,
            uncertainty=uncertainty or old["uncertainty"], limitations=old["limitations"], artifact_refs=old["artifact_refs"],
        )
        self.repository.update_analysis_run(analysis_run_id, status="SUPERSEDED")
        now = datetime.now(timezone.utc)
        with self.repository.engine.connect() as connection:
            claim_rows = connection.execute(
                select(models.claims.c.claim_id)
                .join(models.claim_evidence_links, models.claim_evidence_links.c.claim_id == models.claims.c.claim_id)
                .join(models.evidence_items, models.evidence_items.c.evidence_id == models.claim_evidence_links.c.evidence_id)
                .where(models.evidence_items.c.source_ref["analysis_run_id"].astext == analysis_run_id)
            ).all()
        claim_ids = list({row.claim_id for row in claim_rows})
        for claim_id in claim_ids:
            self.repository.update_claim(claim_id, status="STALE", invalidated_at=now, invalidation_reason=reason)
        manuscript_ids: list[str] = []
        if claim_ids:
            with self.repository.engine.connect() as connection:
                manuscripts = connection.execute(
                    select(models.manuscript_versions.c.manuscript_version_id, models.manuscript_versions.c.claim_ids)
                    .where(models.manuscript_versions.c.project_id == old["project_id"])
                ).all()
            manuscript_ids = [row.manuscript_version_id for row in manuscripts if set(row.claim_ids) & set(claim_ids)]
            for manuscript_id in manuscript_ids:
                self.repository.update_manuscript_version(manuscript_id, status="STALE", invalidated_at=now, invalidation_reason=reason)
        return {"corrected_analysis": corrected, "invalidated_claim_ids": claim_ids, "invalidated_manuscript_ids": manuscript_ids}

    def create_manuscript(
        self, project_id: str, *, title: str, sections: dict[str, str], claim_ids: list[str],
        numeric_bindings: dict[str, dict[str, Any]], literature_trace: list[dict[str, str]],
        anonymous: bool, ai_disclosure: str, supplement_refs: list[str], reproducibility_refs: list[str],
        figure_artifact_ids: list[str] | None = None, references: list[dict[str, str]] | None = None,
        appendix: str | None = None,
    ) -> dict[str, Any]:
        required = {"abstract", "introduction", "methods", "results", "limitations", "conclusion"}
        if required - set(sections):
            raise ValueError(f"missing manuscript sections: {sorted(required - set(sections))}")
        claims = [self.repository.get_claim(item) for item in claim_ids]
        if not claims or any(not claim or claim["status"] != "FROZEN" for claim in claims):
            raise ValueError("manuscript may reference only frozen, current claims")
        for claim_id in claim_ids:
            provenance = self.repository.get_claim_provenance(claim_id)
            if not provenance["evidence"] or not provenance["analyses"] or not provenance["experiment_runs"] or not provenance["experiment_specs"] or not all(protocol["status"] == "FROZEN" for protocol in provenance["protocols"]):
                raise ValueError(f"claim provenance is incomplete: {claim_id}")
        numeric_trace = {}
        for label, binding in numeric_bindings.items():
            analysis = self.repository.get_analysis_run(binding["analysis_run_id"])
            metric = binding["metric"]
            if not analysis or analysis["status"] != "COMPLETE" or metric not in analysis["results"]:
                raise ValueError(f"unknown formal analysis metric: {label}")
            value = analysis["results"][metric]
            if "expected" in binding and binding["expected"] != value:
                raise ValueError(f"invented or stale manuscript number: {label}")
            numeric_trace[label] = {"analysis_run_id": analysis["analysis_run_id"], "metric": metric, "value": value}
        work = self.build_root / project_id / f"manuscript-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        work.mkdir(parents=True, exist_ok=True)
        figure_blocks = []
        for index, artifact_id in enumerate(figure_artifact_ids or [], start=1):
            artifact = self.repository.get_artifact(artifact_id)
            if not artifact or artifact["project_id"] != project_id or not self.artifacts.verify_hash(artifact_id):
                raise ValueError(f"missing or invalid manuscript figure: {artifact_id}")
            source_figure = self.artifacts.get(artifact_id)
            figure_name = f"figure-{index}{source_figure.suffix.lower()}"
            shutil.copy2(source_figure, work / figure_name)
            caption = artifact.get("metadata", {}).get("caption", f"Figure {index}")
            figure_blocks.append(
                f"\\begin{{figure}}[ht]\\centering\\includegraphics[width=0.8\\linewidth]{{{figure_name}}}"
                f"\\caption{{{_latex(caption)}}}\\end{{figure}}"
            )
        rows = "\n".join(f"{_latex(label)} & {_latex(trace['value'])} \\\\" for label, trace in numeric_trace.items())
        body = "\n".join(f"\\section{{{_latex(name.title())}}}\n{_latex(content)}" for name, content in sections.items())
        bibliography = ""
        if references:
            items = []
            for index, reference in enumerate(references, start=1):
                key = re.sub(r"[^A-Za-z0-9:-]", "-", reference.get("key", f"ref-{index}"))
                citation = ". ".join(value for field in ("authors", "title", "venue", "year") if (value := reference.get(field)))
                items.append(f"\\bibitem{{{key}}} {_latex(citation)}")
            bibliography = "\\begin{thebibliography}{99}\n" + "\n".join(items) + "\n\\end{thebibliography}\n"
        appendix_text = f"\\appendix\n\\section{{Appendix}}\n{_latex(appendix)}\n" if appendix else ""
        figures = "\n".join(figure_blocks)
        tex = (
            "\\documentclass{article}\n\\usepackage{booktabs}\n\\usepackage{graphicx}\n\\begin{document}\n"
            f"\\title{{{_latex(title)}}}\n\\author{{{'Anonymous' if anonymous else 'Research OS Lab'}}}\n\\maketitle\n"
            f"{body}\n{figures}\n\\section{{Formal Results}}\n\\begin{{tabular}}{{ll}}\\toprule Metric & Value \\\\ \\midrule\n{rows}\n\\bottomrule\\end{{tabular}}\n"
            f"{appendix_text}{bibliography}\\section{{AI Disclosure}}\n{_latex(ai_disclosure)}\n\\end{{document}}\n"
        )
        source = work / "manuscript.tex"
        source.write_text(tex, encoding="utf-8")
        pdf = self.compiler.compile(source)
        metadata = {
            "sections": sorted(sections), "anonymous": anonymous, "ai_disclosure": bool(ai_disclosure),
            "supplement_refs": supplement_refs, "reproducibility_refs": reproducibility_refs,
            "figure_artifact_ids": figure_artifact_ids or [], "reference_keys": [item.get("key") for item in references or []],
            "appendix": bool(appendix),
        }
        source_artifact = self.artifacts.register(source, "MANUSCRIPT_SOURCE", project_id=project_id, mime_type="application/x-tex", metadata=metadata)
        pdf_artifact = self.artifacts.register(pdf, "MANUSCRIPT_PDF", project_id=project_id, mime_type="application/pdf", metadata=metadata)
        return self.repository.create_manuscript_version(
            project_id, source_artifact_id=source_artifact["artifact_id"], pdf_artifact_id=pdf_artifact["artifact_id"],
            claim_ids=claim_ids, status="DRAFT", content_hash=hashlib.sha256(source.read_bytes()).hexdigest(),
            numeric_trace=numeric_trace, literature_trace=literature_trace, validation={},
        )

    def route_finding(self, project_id: str, finding: ReviewFinding, novelty_callback: Callable[[ReviewFinding], Any] | None = None) -> dict[str, Any]:
        roles = REVIEW_ROUTES[finding.category]
        if finding.category in {"NOVELTY", "CITATION"} and novelty_callback is None:
            raise ValueError("novelty and citation findings require independent retrieval")
        saved = self.repository.create_review_finding(
            project_id, review_stage="PAPER", category=finding.category, severity=finding.severity,
            target_type=finding.target.split(":", 1)[0], target_id=finding.target.split(":", 1)[-1],
            finding=finding.required_resolution, evidence_refs=finding.evidence_refs, impact=finding.impact,
            required_resolution=finding.required_resolution, assigned_roles=roles,
        )
        retrieval = novelty_callback(finding) if finding.category in {"NOVELTY", "CITATION"} and novelty_callback else None
        return {"finding": saved, "assigned_roles": roles, "independent_retrieval": retrieval}

    def create_rebuttal(self, project_id: str, finding_ids: list[str], responses: dict[str, str], *, reviewer_verified: bool) -> dict[str, Any]:
        payload = {
            "project_id": project_id, "finding_ids": finding_ids, "responses": responses,
            "responsibility": {"science": "pi", "numbers": "analyst", "implementation": "engineer", "expression": "editor", "verification": "reviewer"},
            "reviewer_verified": reviewer_verified,
        }
        path = self.build_root / project_id / f"rebuttal-{canonical_hash(payload)[:12]}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.artifacts.register(path, "REBUTTAL", project_id=project_id, mime_type="application/json")

    def preflight(self, manuscript_version_id: str, *, venue_policy: dict[str, Any]) -> dict[str, Any]:
        manuscript = self.repository.get_manuscript_version(manuscript_version_id)
        if not manuscript:
            raise KeyError(manuscript_version_id)
        source_artifact = self.repository.get_artifact(manuscript["source_artifact_id"])
        checks = {
            "compiled_pdf_exists": bool(manuscript["pdf_artifact_id"] and self.artifacts.verify_hash(manuscript["pdf_artifact_id"])),
            "source_integrity": self.artifacts.verify_hash(manuscript["source_artifact_id"]),
            "no_blocking_findings": not any(item["severity"] == "BLOCKING" for item in self.repository.list_review_findings(manuscript["project_id"], "OPEN")),
            "claims_current": all((self.repository.get_claim(item) or {}).get("status") == "FROZEN" for item in manuscript["claim_ids"]),
            "numbers_match_analysis": all(
                (analysis := self.repository.get_analysis_run(trace["analysis_run_id"])) is not None
                and analysis["status"] == "COMPLETE" and analysis["results"].get(trace["metric"]) == trace["value"]
                for trace in manuscript["numeric_trace"].values()
            ),
            "required_sections": set(venue_policy.get("required_sections", [])) <= set((source_artifact or {}).get("metadata", {}).get("sections", [])),
            "anonymity": not venue_policy.get("anonymous_required") or bool((source_artifact or {}).get("metadata", {}).get("anonymous")),
            "ai_disclosure": bool((source_artifact or {}).get("metadata", {}).get("ai_disclosure")),
            "supplement": not venue_policy.get("supplement_required") or bool((source_artifact or {}).get("metadata", {}).get("supplement_refs")),
            "reproducibility": bool((source_artifact or {}).get("metadata", {}).get("reproducibility_refs")),
        }
        if source_artifact and checks["source_integrity"]:
            source_text = self.artifacts.get(source_artifact["artifact_id"]).read_text(encoding="utf-8")
            checks["no_missing_refs"] = "??" not in source_text
            checks["no_secrets"] = not re.search(r"(?i)(api[_-]?key|secret|password)\s*[:=]\s*[^\s{}]+", source_text)
        else:
            checks["no_missing_refs"] = checks["no_secrets"] = False
        passed = all(checks.values())
        self.repository.update_manuscript_version(manuscript_version_id, status="PREFLIGHT_PASSED" if passed else "PREFLIGHT_FAILED", validation={"passed": passed, "checks": checks, "venue_policy_version": venue_policy.get("version")})
        return {"passed": passed, "checks": checks}

    def request_release_approval(self, manuscript_version_id: str) -> dict[str, Any]:
        manuscript = self.repository.get_manuscript_version(manuscript_version_id)
        if not manuscript or manuscript["status"] != "PREFLIGHT_PASSED":
            raise PermissionError("release approval requires a passing submission preflight")
        return self.repository.create_approval(
            manuscript["project_id"], "FINAL_RELEASE", "manuscript_version",
            manuscript_version_id, manuscript["content_hash"], status="PENDING",
        )

    def authorize_release(self, manuscript_version_id: str, approval_id: str) -> dict[str, Any]:
        manuscript = self.repository.get_manuscript_version(manuscript_version_id)
        if not manuscript or manuscript["status"] != "PREFLIGHT_PASSED" or not self.repository.approval_authorizes(approval_id, manuscript_version_id, manuscript["content_hash"]):
            raise PermissionError("explicit hash-bound human release approval is required")
        return self.repository.update_manuscript_version(manuscript_version_id, status="RELEASE_READY")

    @staticmethod
    def seed_followups(*, limitations: list[str], negative_results: list[str], unresolved_questions: list[str], review_findings: list[str]) -> list[dict[str, Any]]:
        return [
            {"title": value, "source": source, "status": "PENDING_NOVELTY_GATE", "auto_publication": False}
            for source, values in (("limitation", limitations), ("negative_result", negative_results), ("unresolved_question", unresolved_questions), ("review_finding", review_findings))
            for value in values
        ]
