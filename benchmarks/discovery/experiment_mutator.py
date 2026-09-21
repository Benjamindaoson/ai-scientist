from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Mutation:
    changed_files: list[str]
    reason: str
    hypothesis_id: str
    config: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "changed_files": self.changed_files,
            "reason": self.reason,
            "hypothesis_id": self.hypothesis_id,
            "config": self.config,
        }


class ExperimentMutator:
    def mutate(self, hypothesis: dict[str, Any]) -> Mutation:
        return Mutation(
            changed_files=["experiment_config.json"],
            reason=f"Test the mechanism proposed by {hypothesis['id']}: {hypothesis['claim']}",
            hypothesis_id=hypothesis["id"],
            config=dict(hypothesis.get("mutation", {})),
        )
