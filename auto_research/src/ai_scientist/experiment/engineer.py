"""Generate and safely materialize experiment code/configuration."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.gateway import BaseGateway
from ..hypothesis import Hypothesis
from .models import ExperimentSpec
from .sandbox import WorkspaceSandbox


@dataclass
class ExperimentImplementation:
    files: list[dict[str, str]] = field(default_factory=list)
    command: list[str] = field(default_factory=list)
    metrics_file: str = "metrics.json"
    success_criteria: dict[str, dict[str, float | str]] = field(default_factory=dict)
    notes: str = ""


class ExperimentEngineer:
    """LLM-backed code/config generator with workspace path confinement."""

    def __init__(self, gateway: BaseGateway, sandbox: WorkspaceSandbox | None = None):
        self.gateway = gateway
        self.sandbox = sandbox or WorkspaceSandbox()

    def design(self, hypothesis: Hypothesis, objective: str, workspace: str) -> ExperimentImplementation:
        prompt = f"""Design a minimal reproducible Python experiment for this hypothesis.
Hypothesis: {hypothesis.claim}
Rationale: {hypothesis.rationale}
Objective: {objective}

Return ONLY JSON with:
{{
  "files": [{{"path":"relative/path.py","content":"..."}}],
  "command": ["python","relative/path.py"],
  "metrics_file": "metrics.json",
  "success_criteria": {{"metric_name": {{"op": ">=", "value": 0.0}}}},
  "notes": "..."
}}
The program MUST write the declared metrics_file as JSON.
Do not use shell commands or absolute paths."""
        data = json.loads(self.gateway.generate(prompt))
        return ExperimentImplementation(
            files=data.get("files", []),
            command=list(data.get("command", [])),
            metrics_file=data.get("metrics_file", "metrics.json"),
            success_criteria=data.get("success_criteria", {}),
            notes=data.get("notes", ""),
        )

    def materialize(self, implementation: ExperimentImplementation, workspace: str) -> None:
        for item in implementation.files:
            path = self.sandbox.safe_path(workspace, item["path"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(item.get("content", ""), encoding="utf-8")

    def create_spec(
        self,
        hypothesis: Hypothesis,
        objective: str,
        workspace: str,
        timeout_seconds: int = 1800,
    ) -> ExperimentSpec:
        implementation = self.design(hypothesis, objective, workspace)
        self.materialize(implementation, workspace)
        self.sandbox.validate_command(implementation.command)
        return ExperimentSpec(
            hypothesis_id=hypothesis.id,
            objective=objective,
            command=implementation.command,
            workspace=workspace,
            metrics_file=implementation.metrics_file,
            success_criteria=implementation.success_criteria,
            timeout_seconds=timeout_seconds,
            metadata={"engineering_notes": implementation.notes},
        )

    def repair(self, spec: ExperimentSpec, stderr: str) -> ExperimentSpec:
        workspace = Path(spec.workspace)
        prompt = f"""Repair a failed experiment without changing its scientific objective or metric definitions.
Objective: {spec.objective}
Command: {json.dumps(spec.command)}
Error:
{stderr[-8000:]}

Return ONLY JSON:
{{"files":[{{"path":"relative/path.py","content":"..."}}],"command":{json.dumps(spec.command)},"notes":"..."}}"""
        data = json.loads(self.gateway.generate(prompt))
        implementation = ExperimentImplementation(
            files=data.get("files", []),
            command=list(data.get("command", spec.command)),
            metrics_file=spec.metrics_file,
            success_criteria=spec.success_criteria,
            notes=data.get("notes", ""),
        )
        self.materialize(implementation, str(workspace))
        self.sandbox.validate_command(implementation.command)
        spec.command = implementation.command
        spec.metadata["last_repair_notes"] = implementation.notes
        return spec
