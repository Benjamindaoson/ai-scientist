from __future__ import annotations

from .contracts import ResearchRole, TaskResult, TaskSpec
from .executors import AgentExecutor
from .permissions import authorize


class AgentLab:
    def __init__(self, executors: dict[ResearchRole, AgentExecutor]):
        missing = set(ResearchRole) - set(executors)
        if missing:
            raise ValueError(f"missing role executors: {sorted(role.value for role in missing)}")
        self.executors = executors

    def run(self, task: TaskSpec) -> TaskResult:
        authorize(task)
        return self.executors[task.role].run(task)
