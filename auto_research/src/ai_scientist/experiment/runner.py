"""Local, policy-checked, reproducible experiment execution."""
from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

from .models import ExperimentResult, ExperimentSpec
from .recovery import FailureRecoveryPolicy
from .sandbox import SandboxPolicy


class ExperimentRunner:
    """Run ExperimentSpec objects with policy checks and bounded recovery."""

    def __init__(
        self,
        sandbox_policy: SandboxPolicy | None = None,
        recovery_policy: FailureRecoveryPolicy | None = None,
    ):
        self.sandbox_policy = sandbox_policy or SandboxPolicy()
        self.recovery_policy = recovery_policy or FailureRecoveryPolicy()

    def run(self, spec: ExperimentSpec) -> ExperimentResult:
        self.sandbox_policy.validate(spec)
        workspace = Path(spec.workspace).resolve()
        started = datetime.utcnow().isoformat()
        t0 = time.monotonic()
        env = os.environ.copy()
        env.update(spec.env)
        env["AI_SCIENTIST_METRICS_FILE"] = spec.metrics_file
        env["AI_SCIENTIST_EXPERIMENT_ID"] = spec.id

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

    def run_with_recovery(self, spec: ExperimentSpec, max_retries: int = 1) -> list[ExperimentResult]:
        """Run an experiment with deterministic, bounded retry behavior."""
        results = []
        current = spec
        for attempt in range(max_retries + 1):
            result = self.run(current)
            results.append(result)
            if result.status == "SUCCEEDED" and result.error_type is None:
                break
            next_spec = self.recovery_policy.retry_spec(current, result, attempt)
            if next_spec is None:
                break
            current = next_spec
        return results
