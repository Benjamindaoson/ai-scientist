from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from .repository import ResearchRepository


class SQLiteImporter:
    """Read-only, replay-safe importer for the legacy SQLite store."""

    def __init__(self, repository: ResearchRepository):
        self.repository = repository

    def import_database(self, source: str | Path) -> dict[str, int]:
        path = Path(source).resolve(strict=True)
        source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        counts = {"projects": 0, "objections": 0}
        try:
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "projects" in tables:
                for row in connection.execute("SELECT * FROM projects"):
                    source_id = str(row["id"])
                    if self.repository.legacy_row_imported(source_hash, "projects", source_id):
                        continue
                    project = self.repository.create_project(
                        row["name"], row["domain"] or "", row["seed_question"] or "", row["description"] or "", legacy_id=source_id,
                    )
                    self.repository.record_legacy_import(source_hash, "projects", source_id, "project", project["project_id"])
                    counts["projects"] += 1
            if "scientific_objections" in tables:
                for row in connection.execute("SELECT * FROM scientific_objections"):
                    source_id = str(row["id"])
                    if self.repository.legacy_row_imported(source_hash, "scientific_objections", source_id):
                        continue
                    project = self.repository.get_project_by_legacy_id(str(row["project_id"]))
                    if not project:
                        continue
                    target_id = project["project_id"]
                    objection = self.repository.create_objection(
                        project["project_id"], row["target_type"], target_id, row["category"], row["severity"],
                        row["title"], row["argument"], raised_by_role=row["raised_by"] or "legacy",
                        supporting_evidence_ids=[], status=row["status"] or "OPEN",
                    )
                    self.repository.record_legacy_import(source_hash, "scientific_objections", source_id, "objection", objection["objection_id"])
                    counts["objections"] += 1
        finally:
            connection.close()
        return counts
