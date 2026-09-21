"""Final Research Court - Evidence-Based Decision Making (v4).

This module implements the hard-constraint rules for final research decisions:
1. OPEN FATAL objections ALWAYS block CONTINUE
2. GateEvaluation is SEPARATE from ScientificDecision
3. Kill Ratio is DEMOTED to auxiliary diagnostic
4. Final decisions are evidence-based with structured JSON output
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class GateResult(str, Enum):
    """Gate evaluation results - separate from decision."""
    PASS = "PASS"           # Passed all gates
    BLOCKED = "BLOCKED"     # Blocked by objections
    INCONCLUSIVE = "INCONCLUSIVE"  # Cannot determine


class ScientificDecision(str, Enum):
    """Final scientific decision - applies hard constraints to gate result."""
    CONTINUE = "CONTINUE"    # Proceed with research
    REVISE = "REVISE"        # Revise and resubmit
    PIVOT = "PIVOT"          # Change direction
    KILL = "KILL"           # Terminate research


class EvidenceQuality(str, Enum):
    """Quality of evidence supporting a decision."""
    STRONG = "STRONG"        # Multiple independent sources
    MODERATE = "MODERATE"    # Some supporting evidence
    WEAK = "WEAK"            # Limited evidence
    ABSENT = "ABSENT"        # No evidence provided


@dataclass
class GateEvaluation:
    """Gate evaluation - separate from final decision.

    This evaluates whether the research has passed various gates
    without making the final decision.
    """
    gate_name: str
    result: GateResult
    evidence_ids: list[str] = field(default_factory=list)
    reasoning: str = ""
    objection_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "gate_name": self.gate_name,
            "result": self.result.value,
            "evidence_ids": self.evidence_ids,
            "reasoning": self.reasoning,
            "objection_ids": self.objection_ids,
        }


@dataclass
class ObjectionGate:
    """The core gate: check for blocking objections."""
    # Open FATAL objections - primary blocker
    open_fatal_objections: list[dict] = field(default_factory=list)

    # Objections requiring human review
    requires_human_objections: list[dict] = field(default_factory=list)

    def evaluate(self) -> GateEvaluation:
        """Evaluate the objection gate.

        Returns:
            GateEvaluation with PASS if no blockers, BLOCKED otherwise
        """
        blockers = []

        # Open FATAL objections always block
        if self.open_fatal_objections:
            blockers.extend([
                f"FATAL: {obj.get('title', 'Unknown')}"
                for obj in self.open_fatal_objections
            ])

        # Objections requiring human also block
        if self.requires_human_objections:
            blockers.extend([
                f"REQUIRES_HUMAN: {obj.get('title', 'Unknown')}"
                for obj in self.requires_human_objections
            ])

        if blockers:
            return GateEvaluation(
                gate_name="OBJECTION_GATE",
                result=GateResult.BLOCKED,
                reasoning="Open FATAL objections or human review required",
                objection_ids=[obj.get("id") for obj in self.open_fatal_objections],
            )

        return GateEvaluation(
            gate_name="OBJECTION_GATE",
            result=GateResult.PASS,
            reasoning="No blocking objections",
        )

    def to_dict(self) -> dict:
        ev = self.evaluate()
        return {
            "open_fatal_count": len(self.open_fatal_objections),
            "requires_human_count": len(self.requires_human_objections),
            "evaluation": ev.to_dict(),
        }


@dataclass
class NoveltyGate:
    """Gate: Is the research actually novel?"""
    has_novel_claim: bool = False
    evidence_ids: list[str] = field(default_factory=list)
    novelty_threats: list[str] = field(default_factory=list)
    nearest_neighbors_identified: bool = False

    def evaluate(self) -> GateEvaluation:
        """Evaluate novelty gate.

        Returns INCONCLUSIVE if cannot determine novelty.
        """
        if not self.has_novel_claim:
            return GateEvaluation(
                gate_name="NOVELTY_GATE",
                result=GateResult.BLOCKED,
                reasoning="No novel claim identified",
            )

        if self.novelty_threats and not self.evidence_ids:
            return GateEvaluation(
                gate_name="NOVELTY_GATE",
                result=GateResult.INCONCLUSIVE,
                reasoning=f"Novelty threats identified but unresolved: {len(self.novelty_threats)} threats",
                objection_ids=self.novelty_threats,
            )

        return GateEvaluation(
            gate_name="NOVELTY_GATE",
            result=GateResult.PASS,
            evidence_ids=self.evidence_ids,
            reasoning="Novel claim with supporting evidence",
        )

    def to_dict(self) -> dict:
        ev = self.evaluate()
        return {
            "has_novel_claim": self.has_novel_claim,
            "novelty_threats": self.novelty_threats,
            "nearest_neighbors_identified": self.nearest_neighbors_identified,
            "evaluation": ev.to_dict(),
        }


@dataclass
class FeasibilityGate:
    """Gate: Can the research be conducted?"""
    has_method: bool = False
    has_data: bool = False
    has_measurements: bool = False
    feasibility_objections: list[dict] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)

    def evaluate(self) -> GateEvaluation:
        """Evaluate feasibility gate."""
        blockers = []

        if not self.has_method:
            blockers.append("No research method proposed")

        if not self.has_data:
            blockers.append("No data source identified")

        if self.feasibility_objections:
            blockers.extend([
                f"Feasibility concern: {obj.get('title', 'Unknown')}"
                for obj in self.feasibility_objections
            ])

        if blockers:
            return GateEvaluation(
                gate_name="FEASIBILITY_GATE",
                result=GateResult.BLOCKED if len(blockers) >= 2 else GateResult.INCONCLUSIVE,
                reasoning="; ".join(blockers),
                evidence_ids=self.evidence_ids,
                objection_ids=[obj.get("id") for obj in self.feasibility_objections],
            )

        return GateEvaluation(
            gate_name="FEASIBILITY_GATE",
            result=GateResult.PASS,
            evidence_ids=self.evidence_ids,
            reasoning="Method, data, and measurements identified",
        )

    def to_dict(self) -> dict:
        ev = self.evaluate()
        return {
            "has_method": self.has_method,
            "has_data": self.has_data,
            "has_measurements": self.has_measurements,
            "feasibility_objections_count": len(self.feasibility_objections),
            "evaluation": ev.to_dict(),
        }


@dataclass
class DecisionReason:
    """A single reason contributing to the decision."""
    type: str  # BLOCKING, SUPPORTING, DIAGNOSTIC
    category: str  # OBJECTION, NOVELTY, FEASIBILITY, DEBATE, OTHER
    evidence_ids: list[str] = field(default_factory=list)
    text: str = ""

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "category": self.category,
            "evidence_ids": self.evidence_ids,
            "text": self.text,
        }


@dataclass
class FinalDecision:
    """Final research decision with evidence-based reasoning.

    This is the structured output of FinalResearchCourt.
    """
    decision: ScientificDecision
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # Gate evaluations
    gates: dict[str, GateEvaluation] = field(default_factory=dict)

    # Decision reasoning
    reasons: list[DecisionReason] = field(default_factory=list)

    # Evidence supporting decision
    supporting_evidence_ids: list[str] = field(default_factory=list)
    contradicting_evidence_ids: list[str] = field(default_factory=list)

    # Objection status at decision time
    open_objections_summary: dict = field(default_factory=dict)

    # Auxiliary diagnostics (NOT decision factors)
    kill_ratio: float | None = None
    debate_status: str | None = None

    # Additional metadata
    requires_human_review: bool = False
    human_review_reason: str = ""

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "timestamp": self.timestamp,
            "gates": {
                name: gate.to_dict()
                for name, gate in self.gates.items()
            },
            "reasons": [r.to_dict() for r in self.reasons],
            "supporting_evidence_ids": self.supporting_evidence_ids,
            "contradicting_evidence_ids": self.contradicting_evidence_ids,
            "open_objections_summary": self.open_objections_summary,
            "diagnostics": {
                "kill_ratio": self.kill_ratio,
                "debate_status": self.debate_status,
            },
            "requires_human_review": self.requires_human_review,
            "human_review_reason": self.human_review_reason,
        }

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


class FinalResearchCourt:
    """Evidence-based research decision court.

    This court makes the FINAL decision on research directions using:
    1. Hard-constraint rules: OPEN FATAL always blocks CONTINUE
    2. Gate evaluation: SEPARATE from final decision
    3. Evidence-based reasoning: decisions require evidence
    4. Kill Ratio demoted: auxiliary diagnostic, not decision factor

    Hard-Constraint Rules:
    ------------------------
    IF open_fatal_objections EXISTS:
        IF status == OPEN OR UNDER_REVIEW OR REQUIRES_HUMAN:
            decision = KILL (cannot continue with unresolved fatal objections)
        ELSE IF status == ACCEPTED_RISK:
            decision = REVISE (may continue with explicit risk acceptance)
    ELSE IF requires_human_objections EXISTS:
        decision = REVISE (requires human to review before continuing)
    ELSE IF novelty_gate == BLOCKED:
        decision = REVISE (must establish novelty first)
    ELSE IF feasibility_gate == BLOCKED:
        decision = REVISE (must establish feasibility first)
    ELSE:
        decision = CONTINUE (passed all gates)

    Kill Ratio (demoted):
    ---------------------
    - NOT a primary decision factor
    - USED as auxiliary diagnostic to explain debate dynamics
    - Reported in diagnostics section
    - May trigger REVISE (not KILL) if kill_ratio > 0.5 without clear blockers
    """

    def __init__(self, objection_ledger=None):
        """Initialize the court.

        Args:
            objection_ledger: ObjectionLedger instance for objection checking
        """
        self.ledger = objection_ledger

    def make_decision(
        self,
        gates: dict[str, Any],
        kill_ratio: float | None = None,
        debate_status: str | None = None,
        supporting_evidence_ids: list[str] | None = None,
        contradicting_evidence_ids: list[str] | None = None,
    ) -> FinalDecision:
        """Make final research decision.

        Args:
            gates: Dictionary of gate evaluations:
                   - 'objection_gate': ObjectionGate
                   - 'novelty_gate': NoveltyGate
                   - 'feasibility_gate': FeasibilityGate
            kill_ratio: Auxiliary diagnostic from debate
            debate_status: Auxiliary diagnostic from debate
            supporting_evidence_ids: Evidence supporting CONTINUE
            contradicting_evidence_ids: Evidence against CONTINUE

        Returns:
            FinalDecision with structured decision and reasoning
        """
        decision = FinalDecision(
            gates={},
            supporting_evidence_ids=supporting_evidence_ids or [],
            contradicting_evidence_ids=contradicting_evidence_ids or [],
            kill_ratio=kill_ratio,
            debate_status=debate_status,
        )

        # Evaluate all gates
        objection_gate = gates.get("objection_gate")
        novelty_gate = gates.get("novelty_gate")
        feasibility_gate = gates.get("feasibility_gate")

        # Gate 1: Objection Gate (PRIMARY - hard constraint)
        if isinstance(objection_gate, ObjectionGate):
            gate_result = objection_gate.evaluate()
            decision.gates["objection_gate"] = gate_result

            if gate_result.result == GateResult.BLOCKED:
                # Check if it's FATAL or requires human
                fatal_objs = objection_gate.open_fatal_objections
                human_objs = objection_gate.requires_human_objections

                if fatal_objs:
                    # HARD CONSTRAINT: Open FATAL blocks CONTINUE
                    decision.decision = ScientificDecision.KILL
                    decision.reasons.append(DecisionReason(
                        type="BLOCKING",
                        category="OBJECTION",
                        evidence_ids=gate_result.objection_ids,
                        text=f"Open FATAL objections block continuation: {len(fatal_objs)} objections",
                    ))

                    for obj in fatal_objs:
                        decision.reasons.append(DecisionReason(
                            type="BLOCKING",
                            category="OBJECTION",
                            evidence_ids=obj.get("supporting_evidence_ids", []),
                            text=f"  FATAL: {obj.get('title', 'Unknown')}",
                        ))

                if human_objs:
                    decision.requires_human_review = True
                    decision.human_review_reason = f"{len(human_objs)} objections require human review"
                    decision.decision = ScientificDecision.REVISE
                    decision.reasons.append(DecisionReason(
                        type="BLOCKING",
                        category="OBJECTION",
                        evidence_ids=[obj.get("id") for obj in human_objs],
                        text=decision.human_review_reason,
                    ))

        # Gate 2: Novelty Gate
        if isinstance(novelty_gate, NoveltyGate):
            gate_result = novelty_gate.evaluate()
            decision.gates["novelty_gate"] = gate_result

            if gate_result.result == GateResult.BLOCKED:
                if decision.decision != ScientificDecision.KILL:
                    decision.decision = ScientificDecision.REVISE
                decision.reasons.append(DecisionReason(
                    type="BLOCKING",
                    category="NOVELTY",
                    evidence_ids=gate_result.evidence_ids,
                    text="Must establish novelty before proceeding",
                ))

        # Gate 3: Feasibility Gate
        if isinstance(feasibility_gate, FeasibilityGate):
            gate_result = feasibility_gate.evaluate()
            decision.gates["feasibility_gate"] = gate_result

            if gate_result.result == GateResult.BLOCKED:
                if decision.decision != ScientificDecision.KILL:
                    decision.decision = ScientificDecision.REVISE
                decision.reasons.append(DecisionReason(
                    type="BLOCKING",
                    category="FEASIBILITY",
                    evidence_ids=gate_result.evidence_ids,
                    text="Must establish feasibility before proceeding",
                ))

        # Add objection summary
        if self.ledger:
            decision.open_objections_summary = self.ledger.get_summary().to_dict()

        # Check if we should recommend PIVOT
        if decision.decision == ScientificDecision.REVISE:
            # If no clear path to fix, suggest pivot
            revision_count = len([
                r for r in decision.reasons
                if r.type == "BLOCKING"
            ])
            if revision_count > 3:
                decision.reasons.append(DecisionReason(
                    type="SUPPORTING",
                    category="OTHER",
                    text="Consider PIVOT to a more viable direction",
                ))

        # Add supporting reasons if decision is CONTINUE
        if decision.decision == ScientificDecision.CONTINUE:
            for name, gate in decision.gates.items():
                if gate.result == GateResult.PASS:
                    decision.reasons.append(DecisionReason(
                        type="SUPPORTING",
                        category=name.upper().replace("_GATE", ""),
                        evidence_ids=gate.evidence_ids,
                        text=f"{gate.gate_name} passed",
                    ))

        return decision

    def make_decision_from_ledger(
        self,
        novelty_gate: NoveltyGate | None = None,
        feasibility_gate: FeasibilityGate | None = None,
        kill_ratio: float | None = None,
        debate_status: str | None = None,
    ) -> FinalDecision:
        """Make decision using only the objection ledger.

        Convenience method when only objection data is available.

        Args:
            novelty_gate: Optional novelty gate
            feasibility_gate: Optional feasibility gate
            kill_ratio: Auxiliary diagnostic
            debate_status: Auxiliary diagnostic

        Returns:
            FinalDecision
        """
        gates = {
            "objection_gate": ObjectionGate(
                open_fatal_objections=self.ledger.get_fatal_objections() if self.ledger else [],
                requires_human_objections=self.ledger.get_requires_human_objections() if self.ledger else [],
            ),
        }

        if novelty_gate:
            gates["novelty_gate"] = novelty_gate
        if feasibility_gate:
            gates["feasibility_gate"] = feasibility_gate

        return self.make_decision(
            gates=gates,
            kill_ratio=kill_ratio,
            debate_status=debate_status,
        )

    def validate_decision(self, decision: FinalDecision) -> tuple[bool, list[str]]:
        """Validate that a decision follows hard-constraint rules.

        Args:
            decision: FinalDecision to validate

        Returns:
            Tuple of (is_valid, list of violations)
        """
        violations = []

        # Rule 1: OPEN FATAL cannot coexist with CONTINUE
        objection_gate = decision.gates.get("objection_gate")
        if objection_gate:
            if objection_gate.result == GateResult.BLOCKED:
                if decision.decision == ScientificDecision.CONTINUE:
                    violations.append(
                        "HARD CONSTRAINT VIOLATION: OPEN FATAL objections cannot coexist with CONTINUE decision"
                    )

        # Rule 2: KILL decision requires FATAL objections
        if decision.decision == ScientificDecision.KILL:
            if not decision.reasons or not any(
                r.type == "BLOCKING" and r.category == "OBJECTION"
                for r in decision.reasons
            ):
                violations.append(
                    "KILL decision requires at least one blocking objection as reason"
                )

        # Rule 3: REVISE requires at least one blocking reason
        if decision.decision == ScientificDecision.REVISE:
            blocking_reasons = [r for r in decision.reasons if r.type == "BLOCKING"]
            if not blocking_reasons:
                violations.append(
                    "REVISE decision requires at least one blocking reason"
                )

        return len(violations) == 0, violations


# ──────────────────────────────────────────────
# Decision Reason Graph
# ──────────────────────────────────────────────

@dataclass
class DecisionGraph:
    """Graph representing decision reasoning."""
    nodes: list[dict] = field(default_factory=list)
    edges: list[dict] = field(default_factory=list)

    def add_node(
        self,
        node_id: str,
        node_type: str,
        label: str,
        data: dict | None = None,
    ) -> None:
        """Add a node to the graph."""
        self.nodes.append({
            "id": node_id,
            "type": node_type,
            "label": label,
            "data": data or {},
        })

    def add_edge(
        self,
        from_id: str,
        to_id: str,
        edge_type: str,
        label: str = "",
    ) -> None:
        """Add an edge to the graph."""
        self.edges.append({
            "from": from_id,
            "to": to_id,
            "type": edge_type,
            "label": label,
        })

    def from_decision(self, decision: FinalDecision) -> "DecisionGraph":
        """Build graph from a FinalDecision.

        Args:
            decision: FinalDecision to visualize

        Returns:
            DecisionGraph
        """
        graph = DecisionGraph()

        # Add decision node
        graph.add_node(
            node_id="final_decision",
            node_type="DECISION",
            label=decision.decision.value,
        )

        # Add gate nodes
        for gate_name, gate in decision.gates.items():
            gate_node_id = f"gate_{gate_name}"
            graph.add_node(
                node_id=gate_node_id,
                node_type="GATE",
                label=f"{gate.gate_name}: {gate.result.value}",
            )
            graph.add_edge(
                from_id=gate_node_id,
                to_id="final_decision",
                edge_type="DETERMINES",
            )

        # Add reason nodes
        for i, reason in enumerate(decision.reasons):
            reason_node_id = f"reason_{i}"
            graph.add_node(
                node_id=reason_node_id,
                node_type=f"REASON_{reason.type}",
                label=reason.text[:100],
                data=reason.to_dict(),
            )
            graph.add_edge(
                from_id=reason_node_id,
                to_id="final_decision",
                edge_type="SUPPORTS" if reason.type == "SUPPORTING" else "BLOCKS",
            )

            # Connect to evidence
            for ev_id in reason.evidence_ids:
                ev_node_id = f"evidence_{ev_id}"
                graph.add_node(
                    node_id=ev_node_id,
                    node_type="EVIDENCE",
                    label=f"Evidence: {ev_id[:20]}...",
                )
                graph.add_edge(
                    from_id=ev_node_id,
                    to_id=reason_node_id,
                    edge_type="SUPPORTS",
                )

        # Add objection nodes if present
        if decision.open_objections_summary:
            summary = decision.open_objections_summary
            if summary.get("open_fatal", 0) > 0:
                graph.add_node(
                    node_id="blocking_objections",
                    node_type="OBJECTION_GROUP",
                    label=f"Open FATAL: {summary['open_fatal']}",
                )
                graph.add_edge(
                    from_id="blocking_objections",
                    to_id="final_decision",
                    edge_type="BLOCKS",
                )

        return graph

    def to_dict(self) -> dict:
        return {
            "nodes": self.nodes,
            "edges": self.edges,
        }
