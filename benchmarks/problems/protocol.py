"""Helpers for materializing and verifying locked benchmark evaluators."""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path


LOCKED_RUNNER_NAME = "_benchmark_locked_runner.py"


def sha256_file(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def materialize_locked_runner(source: str | Path, workspace: str | Path) -> tuple[str, str]:
    workspace = Path(workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    target = workspace / LOCKED_RUNNER_NAME
    shutil.copyfile(Path(source).resolve(), target)
    return LOCKED_RUNNER_NAME, sha256_file(target)


def verify_locked_runner(workspace: str | Path, expected_sha256: str) -> bool:
    target = Path(workspace).resolve() / LOCKED_RUNNER_NAME
    return target.exists() and sha256_file(target) == expected_sha256
