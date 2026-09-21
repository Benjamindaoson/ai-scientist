"""Traceable Claim-Evidence-Experiment graph."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EvidenceGraph:
    nodes: dict[str, dict] = field(default_factory=dict)
    edges: list[dict] = field(default_factory=list)

    def add_node(self, node_id: str, node_type: str, **data) -> None:
        self.nodes[node_id] = {"id": node_id, "type": node_type, **data}

    def add_edge(self, source: str, target: str, relation: str) -> None:
        edge = {"source": source, "target": target, "relation": relation}
        if edge not in self.edges:
            self.edges.append(edge)

    def link_experiment_evidence(
        self,
        claim_id: str,
        evidence_id: str,
        experiment_id: str,
        metrics: dict,
        artifact_paths: list[str] | None = None,
        relation: str = "SUPPORTS",
    ) -> None:
        self.add_node(claim_id, "CLAIM")
        self.add_node(evidence_id, "EVIDENCE", metrics=metrics)
        self.add_node(experiment_id, "EXPERIMENT")
        self.add_edge(evidence_id, claim_id, relation)
        self.add_edge(experiment_id, evidence_id, "PRODUCES")
        for path in artifact_paths or []:
            artifact_id = f"artifact:{experiment_id}:{path}"
            self.add_node(artifact_id, "ARTIFACT", path=path)
            self.add_edge(artifact_id, experiment_id, "OUTPUT_OF")

    def challenge(self, objection_id: str, claim_id: str, **data) -> None:
        self.add_node(objection_id, "OBJECTION", **data)
        self.add_node(claim_id, "CLAIM")
        self.add_edge(objection_id, claim_id, "CHALLENGES")

    def evidence_for_claim(self, claim_id: str) -> list[dict]:
        ids = [e["source"] for e in self.edges if e["target"] == claim_id and e["relation"] == "SUPPORTS"]
        return [self.nodes[i] for i in ids if i in self.nodes]

    def unsupported_claims(self) -> list[str]:
        claims = [n for n, v in self.nodes.items() if v.get("type") == "CLAIM"]
        return [claim for claim in claims if not self.evidence_for_claim(claim)]

    def to_dict(self) -> dict:
        return {"nodes": list(self.nodes.values()), "edges": self.edges}
