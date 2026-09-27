from __future__ import annotations

from typing import Any

from .repository import ResearchRepository


class PostgresObjectionRepository:
    """Compatibility adapter for the legacy ObjectionLedger over canonical PostgreSQL."""

    def __init__(self, repository: ResearchRepository):
        self.repository = repository

    @staticmethod
    def _legacy(row: dict[str, Any] | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {**row, "id": row["objection_id"], "raised_by": row["raised_by_role"]}

    def create_objection(self, data: dict[str, Any]) -> dict[str, Any]:
        row = self.repository.create_objection(
            data["project_id"], data["target_type"], data["target_id"], data["category"], data["severity"],
            data["title"], data["argument"], raised_by_role=data.get("raised_by", "legacy"),
            supporting_evidence_ids=data.get("supporting_evidence_ids", []), status=data.get("status", "OPEN"),
        )
        return self._legacy(row)  # type: ignore[return-value]

    def get_objection(self, objection_id: str) -> dict[str, Any] | None:
        return self._legacy(self.repository.get_objection(objection_id))

    def list_objections(self, project_id: str, status: str | None = None) -> list[dict[str, Any]]:
        return [self._legacy(row) for row in self.repository.list_objections(project_id, status=status)]  # type: ignore[misc]

    def get_open_objections(self, project_id: str, severity: str | None = None) -> list[dict[str, Any]]:
        rows = self.repository.list_objections(project_id, severity=severity)
        return [self._legacy(row) for row in rows if row["status"] in {"OPEN", "UNDER_REVIEW", "REQUIRES_HUMAN"}]  # type: ignore[misc]

    def get_fatal_objections(self, project_id: str) -> list[dict[str, Any]]:
        return self.get_open_objections(project_id, "FATAL")

    def update_objection_status(self, objection_id: str, **changes: Any) -> dict[str, Any]:
        return self._legacy(self.repository.update_objection(objection_id, **changes))  # type: ignore[return-value]
