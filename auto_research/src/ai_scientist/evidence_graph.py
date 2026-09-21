"""Claim-evidence-experiment traceability graph."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvidenceGraph:
    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    edges: list[dict[str, str]] = field(default_factory=list)

    def add_node(self, node_id: str, node_type: str, **data: Any) -> None:
        self.nodes[node_id] = {"id": node_id, "type": node_type, **data}

    def add_edge(self, source: str, target: str, relation: str) -> None:
        if source not in self.nodes or target not in self.nodes:
            raise KeyError("Both edge endpoints must exist")
        edge = {"source": source, "target": target, "relation": relation}
        if edge not in self.edges:
            self.edges.append(edge)

    def add_claim(self, claim_id: str, text: str) -> None:
        self.add_node(claim_id, "CLAIM", text=text)

    def add_experiment(self, experiment_id: str, metrics: dict | None = None) -> None:
        self.add_node(experiment_id, "EXPERIMENT", metrics=metrics or {})

    def add_evidence(self, evidence_id: str, evidence_type: str = "EXPERIMENT") -> None:
        self.add_node(evidence_id, "EVIDENCE", evidence_type=evidence_type)

    def link_claim_evidence(self, claim_id: str, evidence_id: str, supports: bool = True) -> None:
        self.add_edge(evidence_id, claim_id, "SUPPORTS" if supports else "CONTRADICTS")

    def link_evidence_experiment(self, evidence_id: str, experiment_id: str) -> None:
        self.add_edge(experiment_id, evidence_id, "PRODUCES")

    def evidence_for_claim(self, claim_id: str) -> list[str]:
        return [e["source"] for e in self.edges if e["target"] == claim_id and e["relation"] in {"SUPPORTS", "CONTRADICTS"}]

    def to_dict(self) -> dict[str, Any]:
        return {"nodes": list(self.nodes.values()), "edges": self.edges}
