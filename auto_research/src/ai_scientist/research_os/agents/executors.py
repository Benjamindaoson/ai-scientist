from __future__ import annotations

import hashlib
import json
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable

from langgraph.types import interrupt

from .contracts import TaskResult, TaskSpec


class AgentExecutor(ABC):
    @abstractmethod
    def run(self, task: TaskSpec) -> TaskResult:
        raise NotImplementedError


class CodexExecutor(AgentExecutor):
    def __init__(self, executable: str = "codex", command_runner: Callable = subprocess.run, timeout_seconds: int = 900):
        self.executable = executable
        self.command_runner = command_runner
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _strict_output_schema() -> dict:
        schema = TaskResult.model_json_schema()

        def normalize(value):
            if isinstance(value, dict):
                if "properties" in value:
                    value["additionalProperties"] = False
                    value["required"] = list(value["properties"])
                for child in value.values():
                    normalize(child)
            elif isinstance(value, list):
                for child in value:
                    normalize(child)

        normalize(schema)
        return schema

    def run(self, task: TaskSpec) -> TaskResult:
        workspace = Path(task.workspace).resolve()
        if not workspace.is_dir():
            raise ValueError(f"task workspace does not exist: {workspace}")
        package = workspace / ".research-os" / "tasks" / task.task_id
        package.mkdir(parents=True, exist_ok=True)
        input_path = package / "input.json"
        schema_path = package / "task-result.schema.json"
        output_path = package / "output.json"
        execution_path = package / "execution.json"
        stdout_path = package / "stdout.log"
        stderr_path = package / "stderr.log"
        input_path.write_text(task.model_dump_json(indent=2), encoding="utf-8")
        schema_path.write_text(json.dumps(self._strict_output_schema(), indent=2), encoding="utf-8")
        prompt = (
            "Complete the bounded Research OS task in input.json. Do not broaden scope or change frozen scientific facts. "
            "Return one JSON object matching the supplied TaskResult schema. "
            f"Task package: {package}"
        )
        command = [
            self.executable, "--ask-for-approval", "never", "--sandbox", "workspace-write",
            "exec", "--ephemeral", "--skip-git-repo-check", "--cd", str(workspace), "--output-schema", str(schema_path),
            "--output-last-message", str(output_path), prompt,
        ]
        try:
            completed = self.command_runner(
                command, cwd=workspace, capture_output=True, text=True, check=False,
                shell=False, stdin=subprocess.DEVNULL, timeout=self.timeout_seconds,
                encoding="utf-8", errors="replace",
            )
        except subprocess.TimeoutExpired as exc:
            completed = subprocess.CompletedProcess(command, 124, stdout=exc.stdout or "", stderr=exc.stderr or "Codex CLI timed out")
        stdout_path.write_text((completed.stdout or "")[-200_000:], encoding="utf-8")
        stderr_path.write_text((completed.stderr or "")[-200_000:], encoding="utf-8")
        record = {
            "task_id": task.task_id,
            "executor": "codex_cli",
            "workspace": str(workspace),
            "argv": command[:-1],
            "return_code": completed.returncode,
            "stdout_sha256": hashlib.sha256((completed.stdout or "").encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256((completed.stderr or "").encode()).hexdigest(),
            "stdout_ref": str(stdout_path),
            "stderr_ref": str(stderr_path),
        }
        execution_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        if completed.returncode != 0:
            return TaskResult(task_id=task.task_id, role=task.role, status="FAILED", summary="Codex CLI task failed", execution_record_ref=str(execution_path), error_code="CODEX_EXEC_FAILED")
        result = TaskResult.model_validate_json(output_path.read_text(encoding="utf-8"))
        if result.task_id != task.task_id or result.role != task.role:
            raise ValueError("Codex result identity does not match task package")
        return result.model_copy(update={"execution_record_ref": str(execution_path)})


class HumanAssistedExecutor(AgentExecutor):
    def run(self, task: TaskSpec) -> TaskResult:
        workspace = Path(task.workspace).resolve()
        package = workspace / ".research-os" / "human-tasks" / task.task_id
        package.mkdir(parents=True, exist_ok=True)
        input_path = package / "input.json"
        input_path.write_text(task.model_dump_json(indent=2), encoding="utf-8")
        response = interrupt({"kind": "HUMAN_TASK", "task_id": task.task_id, "package_path": str(input_path), "result_schema": TaskResult.model_json_schema()})
        result = TaskResult.model_validate(response)
        if result.task_id != task.task_id or result.role != task.role:
            raise ValueError("human result identity does not match task package")
        return result


class PaidAPIExecutor(AgentExecutor):
    def __init__(self, enabled: bool = False, budget_approval_id: str | None = None):
        self.enabled = enabled
        self.budget_approval_id = budget_approval_id

    def run(self, task: TaskSpec) -> TaskResult:
        if not self.enabled or not self.budget_approval_id:
            raise PermissionError("paid LLM API execution is disabled without explicit budget approval")
        raise NotImplementedError("no paid API provider is configured")


class MockExecutor(AgentExecutor):
    def __init__(self):
        self.calls: list[TaskSpec] = []

    def run(self, task: TaskSpec) -> TaskResult:
        self.calls.append(task)
        return TaskResult(task_id=task.task_id, role=task.role, status="SUCCEEDED", summary=f"mock completed {task.capability.value}")
