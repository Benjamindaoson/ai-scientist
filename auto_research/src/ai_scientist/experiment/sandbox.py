"""Policy checks for experiment execution."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .models import ExperimentSpec


@dataclass
class SandboxPolicy:
    """Lightweight process policy for local research execution.

    This is not an OS/container isolation boundary. It prevents accidental use of
    shells, absolute executables outside an allow-list, workspace escape, and
    unbounded runtime in the built-in runner.
    """
    allowed_executables: set[str] = field(default_factory=lambda: {
        "python", "python3", "pytest", "bash", "sh"
    })
    allow_shells: bool = False
    max_timeout_seconds: int = 7200

    def validate(self, spec: ExperimentSpec) -> None:
        workspace = Path(spec.workspace).resolve()
        if not workspace.exists() or not workspace.is_dir():
            raise ValueError(f"Workspace does not exist: {workspace}")
        if not spec.command:
            raise ValueError("Experiment command cannot be empty")
        executable = Path(spec.command[0]).name
        if executable in {"bash", "sh"} and not self.allow_shells:
            raise ValueError("Shell execution is disabled by sandbox policy")
        if executable not in self.allowed_executables and not executable.startswith("python"):
            raise ValueError(f"Executable not allowed: {executable}")
        if spec.timeout_seconds <= 0 or spec.timeout_seconds > self.max_timeout_seconds:
            raise ValueError("Experiment timeout violates sandbox policy")
