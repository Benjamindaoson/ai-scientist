"""Workspace-scoped experiment sandbox and execution policy."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SandboxPolicy:
    """Guardrails for running model-authored experiment code.

    The local backend is a guarded subprocess, not a VM security boundary.
    Use DockerSandbox with network disabled when strong isolation is required.
    """
    allowed_executables: tuple[str, ...] = ("python", "python3", "pytest")
    inherited_env: tuple[str, ...] = (
        "PATH", "PYTHONPATH", "HOME", "USERPROFILE", "TMPDIR", "TEMP", "TMP", "SYSTEMROOT"
    )
    allow_network: bool = False
    max_output_chars: int = 200_000

    def executable_allowed(self, executable: str) -> bool:
        name = Path(executable).name.lower()
        current = Path(sys.executable).name.lower()
        return name in {x.lower() for x in self.allowed_executables} or name == current


class WorkspaceSandbox:
    """Execute list-form commands inside an approved workspace."""

    def __init__(self, policy: SandboxPolicy | None = None):
        self.policy = policy or SandboxPolicy()

    def resolve_workspace(self, workspace: str | Path) -> Path:
        root = Path(workspace).resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError(f"Experiment workspace does not exist: {root}")
        return root

    def safe_path(self, workspace: str | Path, relative_path: str | Path) -> Path:
        root = self.resolve_workspace(workspace)
        candidate = (root / relative_path).resolve()
        if candidate != root and root not in candidate.parents:
            raise ValueError(f"Path escapes experiment workspace: {relative_path}")
        return candidate

    def validate_command(self, command: list[str]) -> None:
        if not command:
            raise ValueError("Experiment command cannot be empty")
        if not self.policy.executable_allowed(command[0]):
            raise PermissionError(f"Executable is not allowed by sandbox policy: {command[0]}")

    def build_env(self, extra_env: dict[str, str] | None = None) -> dict[str, str]:
        env = {k: os.environ[k] for k in self.policy.inherited_env if k in os.environ}
        for key, value in (extra_env or {}).items():
            env[str(key)] = str(value)
        return env

    def run(self, command: list[str], workspace: str | Path, env: dict[str, str], timeout: int):
        root = self.resolve_workspace(workspace)
        self.validate_command(command)
        proc = subprocess.run(
            command,
            cwd=root,
            env=self.build_env(env),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
        )
        proc.stdout = (proc.stdout or "")[-self.policy.max_output_chars:]
        proc.stderr = (proc.stderr or "")[-self.policy.max_output_chars:]
        return proc


class DockerSandbox:
    """Optional stronger isolation using Docker with networking disabled by default."""

    def __init__(self, image: str = "python:3.11-slim", policy: SandboxPolicy | None = None):
        self.image = image
        self.policy = policy or SandboxPolicy()

    @property
    def available(self) -> bool:
        return shutil.which("docker") is not None

    def run(self, command: list[str], workspace: str | Path, env: dict[str, str], timeout: int):
        if not self.available:
            raise RuntimeError("Docker is not available")
        root = Path(workspace).resolve()
        args = ["docker", "run", "--rm", "-v", f"{root}:/workspace", "-w", "/workspace"]
        if not self.policy.allow_network:
            args += ["--network", "none"]
        for key, value in env.items():
            args += ["-e", f"{key}={value}"]
        args += [self.image, *command]
        return subprocess.run(
            args, capture_output=True, text=True, timeout=timeout, check=False, shell=False
        )
