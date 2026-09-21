"""Controlled code generation and workspace editing for research experiments."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .core.gateway import BaseGateway


@dataclass
class FileChange:
    path: str
    content: str
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "content": self.content, "reason": self.reason}


@dataclass
class EngineeringPlan:
    objective: str
    changes: list[FileChange] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"objective": self.objective, "changes": [c.to_dict() for c in self.changes]}


class CodeEngineeringAgent:
    """Generate structured file changes, never free-form shell commands."""

    def __init__(self, gateway: BaseGateway | None = None):
        self.gateway = gateway

    def plan(self, objective: str, context: dict[str, Any] | None = None) -> EngineeringPlan:
        if not self.gateway:
            return EngineeringPlan(objective=objective)
        prompt = (
            "Create a minimal research-code modification plan. Return ONLY JSON with "
            "{objective: string, changes: [{path: relative path, content: full file content, reason: string}]}. "
            "Do not include shell commands or absolute paths.\n"
            f"OBJECTIVE={objective}\nCONTEXT={json.dumps(context or {}, default=str)}"
        )
        try:
            data = json.loads(self.gateway.generate(prompt))
            return EngineeringPlan(
                objective=data.get("objective", objective),
                changes=[FileChange(**c) for c in data.get("changes", [])],
            )
        except Exception:
            return EngineeringPlan(objective=objective)


class WorkspaceEditor:
    """Apply generated file changes strictly inside a declared workspace."""

    def __init__(self, workspace: str | Path):
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, relative_path: str) -> Path:
        candidate = (self.workspace / relative_path).resolve()
        if self.workspace != candidate and self.workspace not in candidate.parents:
            raise ValueError(f"Path escapes workspace: {relative_path}")
        return candidate

    def apply(self, plan: EngineeringPlan) -> list[str]:
        changed = []
        for change in plan.changes:
            path = self._safe_path(change.path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(change.content, encoding="utf-8")
            changed.append(str(path.relative_to(self.workspace)))
        return changed
