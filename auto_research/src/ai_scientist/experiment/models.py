"""Typed experiment specifications and results."""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ExperimentSpec:
    hypothesis_id: str
    objective: str
    command: list[str]
    workspace: str
    metrics_file: str = "metrics.json"
    baseline: dict[str, Any] = field(default_factory=dict)
    controls: list[str] = field(default_factory=list)
    success_criteria: dict[str, dict[str, float | str]] = field(default_factory=dict)
    env: dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 1800
    id: str = field(default_factory=lambda: f"exp_{uuid.uuid4().hex[:10]}")
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ExperimentResult:
    experiment_id: str
    hypothesis_id: str
    status: str
    return_code: int
    metrics: dict[str, Any] = field(default_factory=dict)
    stdout: str = ""
    stderr: str = ""
    artifacts: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    error_type: str | None = None
    started_at: str = ""
    completed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
