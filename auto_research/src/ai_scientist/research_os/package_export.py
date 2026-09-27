from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from sqlalchemy import select

from ai_scientist.research_store import ArtifactStore, ResearchRepository
from ai_scientist.research_store import models
from ai_scientist.research_store.repository import canonical_hash


PROJECT_TABLES = (
    "projects", "research_questions", "hypotheses", "protocol_versions", "analysis_runs", "claims",
    "evidence_items", "objections", "review_findings", "decisions", "approvals", "manuscript_versions", "artifacts",
)


class ResearchPackageExporter:
    def __init__(self, repository: ResearchRepository, artifacts: ArtifactStore):
        self.repository = repository
        self.artifacts = artifacts

    @staticmethod
    def _git_refs(workspace: str | Path) -> dict[str, str | None]:
        def read(*args: str) -> str | None:
            try:
                result = subprocess.run(["git", *args], cwd=workspace, capture_output=True, text=True, check=False, shell=False)
            except OSError:
                return None
            return result.stdout.strip() if result.returncode == 0 else None
        return {"commit": read("rev-parse", "HEAD"), "branch": read("branch", "--show-current"), "remote": read("remote", "get-url", "origin")}

    def export(self, project_id: str, destination: str | Path, *, workspace: str | Path, retrieval_run_ids: list[str] | None = None, git_refs: dict[str, str | None] | None = None) -> Path:
        if not self.repository.get_project(project_id):
            raise KeyError(project_id)
        data = {name: self.repository.list_project_rows(name, project_id) for name in PROJECT_TABLES}
        specs = self.repository.list_project_rows("experiment_specs", project_id)
        data["experiment_specs"] = specs
        spec_ids = [item["experiment_spec_id"] for item in specs]
        with self.repository.engine.connect() as connection:
            data["experiment_runs"] = [dict(row._mapping) for row in connection.execute(select(models.experiment_runs).where(models.experiment_runs.c.experiment_spec_id.in_(spec_ids)))] if spec_ids else []
            claim_ids = [item["claim_id"] for item in data["claims"]]
            data["claim_evidence_links"] = [dict(row._mapping) for row in connection.execute(select(models.claim_evidence_links).where(models.claim_evidence_links.c.claim_id.in_(claim_ids)))] if claim_ids else []
        artifacts = data["artifacts"]
        integrity = [{"artifact_id": item["artifact_id"], "uri": item["uri"], "sha256": item["sha256"], "verified": self.artifacts.verify_hash(item["artifact_id"])} for item in artifacts]
        resolved_git_refs = git_refs or self._git_refs(workspace)
        if not resolved_git_refs.get("commit"):
            raise RuntimeError("research package requires a resolvable Git commit")
        manifest = {
            "format": "research-os-v2-package", "project_id": project_id, "database": data,
            "literature_retrieval_run_ids": retrieval_run_ids or [], "git": resolved_git_refs,
            "artifact_integrity": integrity,
        }
        manifest["manifest_hash"] = canonical_hash(manifest)
        destination = Path(destination).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        return destination

    def reconstruct(self, manifest_path: str | Path) -> dict[str, Any]:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        expected = manifest.pop("manifest_hash")
        if canonical_hash(manifest) != expected:
            raise ValueError("research package manifest hash mismatch")
        if not manifest.get("git", {}).get("commit"):
            raise ValueError("research package is missing its Git commit")
        for artifact in manifest["artifact_integrity"]:
            if not artifact["verified"] or not self.artifacts.verify_hash(artifact["artifact_id"]):
                raise ValueError(f"required artifact is missing or corrupt: {artifact['artifact_id']}")
        manifest["manifest_hash"] = expected
        return manifest
