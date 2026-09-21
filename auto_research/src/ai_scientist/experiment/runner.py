"""Sandboxed, reproducible experiment execution with bounded recovery."""
from __future__ import annotations

import json
import subprocess
import time
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from .models import ExperimentResult, ExperimentSpec
from .recovery import RecoveryPolicy
from .sandbox import DockerSandbox, WorkspaceSandbox


class ExperimentRunner:
    """Run an ExperimentSpec and capture metrics, logs, artifacts, and recovery history."""

    def __init__(self, local_sandbox: WorkspaceSandbox | None = None):
        self.local_sandbox = local_sandbox or WorkspaceSandbox()

    def _backend(self, spec: ExperimentSpec):
        if spec.sandbox_backend == "docker":
            return DockerSandbox(policy=self.local_sandbox.policy)
        if spec.sandbox_backend != "local":
            raise ValueError(f"Unknown sandbox backend: {spec.sandbox_backend}")
        return self.local_sandbox

    def _run_once(self, spec: ExperimentSpec) -> ExperimentResult:
        workspace = self.local_sandbox.resolve_workspace(spec.workspace)
        self.local_sandbox.safe_path(workspace, spec.metrics_file)
        started = datetime.utcnow().isoformat()
        t0 = time.monotonic()

        try:
            proc = self._backend(spec).run(
                spec.command,
                workspace=workspace,
                env=spec.env,
                timeout=spec.timeout_seconds,
            )
            status = "SUCCEEDED" if proc.returncode == 0 else "FAILED"
            error_type = None if proc.returncode == 0 else "NONZERO_EXIT"
            stdout, stderr, code = proc.stdout or "", proc.stderr or "", proc.returncode
        except subprocess.TimeoutExpired as exc:
            status, error_type, code = "FAILED", "TIMEOUT", -1
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        except Exception as exc:
            status, error_type, code = "FAILED", "SANDBOX_ERROR", -1
            stdout, stderr = "", str(exc)

        metrics = {}
        metrics_path = workspace / spec.metrics_file
        if metrics_path.exists():
            try:
                metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            except Exception:
                error_type = error_type or "INVALID_METRICS"
        elif status == "SUCCEEDED":
            error_type = "MISSING_METRICS"

        artifacts = [str(p.relative_to(workspace)) for p in workspace.rglob("*") if p.is_file()]
        if status == "SUCCEEDED" and error_type in {"MISSING_METRICS", "INVALID_METRICS"}:
            status = "FAILED"

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

    def run(self, spec: ExperimentSpec, repair_callback=None) -> ExperimentResult:
        policy = RecoveryPolicy(max_attempts=spec.max_attempts)
        current = spec
        history = []

        for attempt in range(1, spec.max_attempts + 1):
            result = self._run_once(current)
            result.attempts = attempt
            decision = policy.decide(current, result, attempt)
            history.append({
                "attempt": attempt,
                "status": result.status,
                "error_type": result.error_type,
                "decision": decision.reason,
            })
            if not decision.retry:
                result.recovery_history = history
                return result

            current = decision.updated_spec or current
            if repair_callback and "repair" in decision.reason:
                current = repair_callback(current, result)

        result.recovery_history = history
        return result
