"""Local, reproducible experiment execution."""
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

from .models import ExperimentResult, ExperimentSpec


class ExperimentRunner:
    """Run an ExperimentSpec and capture metrics, logs, and artifacts."""

    def run(self, spec: ExperimentSpec) -> ExperimentResult:
        workspace = Path(spec.workspace).resolve()
        if not workspace.exists() or not workspace.is_dir():
            raise ValueError(f"Experiment workspace does not exist: {workspace}")
        if not spec.command:
            raise ValueError("Experiment command cannot be empty")

        started = datetime.utcnow().isoformat()
        t0 = time.monotonic()
        env = os.environ.copy()
        env.update(spec.env)

        try:
            proc = subprocess.run(
                spec.command,
                cwd=workspace,
                env=env,
                capture_output=True,
                text=True,
                timeout=spec.timeout_seconds,
                check=False,
            )
            status = "SUCCEEDED" if proc.returncode == 0 else "FAILED"
            error_type = None if proc.returncode == 0 else "NONZERO_EXIT"
            stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as exc:
            status, error_type, code = "FAILED", "TIMEOUT", -1
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")

        metrics = {}
        metrics_path = workspace / spec.metrics_file
        if metrics_path.exists():
            try:
                metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            except Exception:
                error_type = error_type or "INVALID_METRICS"

        artifacts = [str(p.relative_to(workspace)) for p in workspace.rglob("*") if p.is_file()]
        return ExperimentResult(
            experiment_id=spec.id,
            hypothesis_id=spec.hypothesis_id,
            status=status,
            return_code=code,
            metrics=metrics,
            stdout=stdout,
            stderr=stderr,
            artifacts=artifacts,
            duration_seconds=time.monotonic() - t0,
            error_type=error_type,
            started_at=started,
            completed_at=datetime.utcnow().isoformat(),
        )
