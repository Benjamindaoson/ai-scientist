from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

from .repository import ResearchRepository


class ArtifactStore:
    def __init__(self, root: str | Path, repository: ResearchRepository):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.repository = repository

    def _path(self, uri: str) -> Path:
        candidate = (self.root / uri).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("artifact path escapes configured root")
        return candidate

    def register(
        self, source: str | Path, artifact_type: str, *, project_id: str | None = None,
        mime_type: str | None = None, metadata: dict[str, Any] | None = None,
        created_by_task_id: str | None = None,
    ) -> dict[str, Any]:
        source_path = Path(source).resolve(strict=True)
        digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
        relative = Path(project_id or "global") / digest[:2] / f"{digest}{source_path.suffix}"
        destination = self._path(relative.as_posix())
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
            raise ValueError("immutable artifact destination contains different content")
        if not destination.exists():
            shutil.copyfile(source_path, destination)
        return self.repository.register_artifact(
            artifact_type=artifact_type, uri=relative.as_posix(), sha256=digest,
            size_bytes=source_path.stat().st_size, project_id=project_id, mime_type=mime_type,
            metadata=metadata, created_by_task_id=created_by_task_id,
        )

    def get(self, artifact_id: str) -> Path:
        artifact = self.repository.get_artifact(artifact_id)
        if not artifact:
            raise KeyError(artifact_id)
        return self._path(artifact["uri"])

    def verify_hash(self, artifact_id: str) -> bool:
        artifact = self.repository.get_artifact(artifact_id)
        if not artifact:
            raise KeyError(artifact_id)
        path = self._path(artifact["uri"])
        return path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]

    def list_for_project(self, project_id: str) -> list[dict[str, Any]]:
        return self.repository.list_artifacts_for_project(project_id)
