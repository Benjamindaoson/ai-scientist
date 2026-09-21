"""Theory Engine for AI Scientist.

Provides functionality for theory development, mechanism analysis, and construct refinement.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TheoryComponentType(str, Enum):
    """Types of theory components."""
    CONSTRUCT = "CONSTRUCT"
    MECHANISM = "MECHANISM"
    PROPOSITION = "PROPOSITION"
    BOUNDARY_CONDITION = "BOUNDARY_CONDITION"
    ALTERNATIVE_EXPLANATION = "ALTERNATIVE_EXPLANATION"


class TheoryStatus(str, Enum):
    """Theory development status."""
    EMBRYONIC = "EMBRYONIC"
    FORMULATING = "FORMULATING"
    TESTABLE = "TESTABLE"
    TESTED = "TESTED"
    REVISED = "REVISED"
    ESTABLISHED = "ESTABLISHED"


@dataclass
class TheoryComponent:
    """A component within a theory."""
    component_type: TheoryComponentType
    name: str
    description: str
    evidence_support: list[str] = field(default_factory=list)
    confidence: float = 0.5
    contradictions: list[str] = field(default_factory=list)


@dataclass
class TheoryLink:
    """A causal or logical link between components."""
    source: str
    target: str
    link_type: str  # "causal", "enables", "constrains", "correlates"
    description: str
    evidence: str = ""
    strength: float = 0.5


@dataclass
class MechanismPathway:
    """A pathway through which a mechanism operates."""
    pathway_name: str
    steps: list[str]
    input_conditions: list[str]
    output_predictions: list[str]
    intermediate_constructs: list[str] = field(default_factory=list)
    testable_predictions: list[str] = field(default_factory=list)


@dataclass
class TheoryEvaluation:
    """Evaluation of a theory."""
    coherence: float = 0.0
    testability: float = 0.0
    parsimony: float = 0.0
    explanatory_power: float = 0.0
    predictive_power: float = 0.0
    falsifiability: float = 0.0
    overall_score: float = 0.0
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)


@dataclass
class TheoryDraft:
    """A draft theory under development."""
    theory_id: str
    theory_name: str
    status: TheoryStatus
    core_claim: str
    components: list[TheoryComponent] = field(default_factory=list)
    links: list[TheoryLink] = field(default_factory=list)
    mechanisms: list[MechanismPathway] = field(default_factory=list)
    evaluation: TheoryEvaluation = field(default_factory=TheoryEvaluation)
    alternative_explanations: list[str] = field(default_factory=list)
    boundary_conditions: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)


class TheoryEngine:
    """Engine for theory development and analysis.

    Helps researchers develop, evaluate, and refine theories through:
    - Component identification and linking
    - Mechanism pathway analysis
    - Alternative explanation consideration
    - Theory evaluation against criteria
    """

    def __init__(self, gateway=None):
        """Initialize theory engine.

        Args:
            gateway: Optional LLM gateway for advanced analysis
        """
        self.gateway = gateway
        self.theories: dict[str, TheoryDraft] = {}

    def create_theory(
        self,
        theory_name: str,
        core_claim: str,
    ) -> TheoryDraft:
        """Create a new theory draft.

        Args:
            theory_name: Name of the theory
            core_claim: Central claim or thesis

        Returns:
            New TheoryDraft
        """
        theory_id = f"theory_{uuid.uuid4().hex[:8]}"
        theory = TheoryDraft(
            theory_id=theory_id,
            theory_name=theory_name,
            status=TheoryStatus.EMBRYONIC,
            core_claim=core_claim,
        )
        self.theories[theory_id] = theory
        return theory

    def add_component(
        self,
        theory_id: str,
        component_type: TheoryComponentType,
        name: str,
        description: str,
    ) -> TheoryComponent | None:
        """Add a component to a theory.

        Args:
            theory_id: ID of the theory
            component_type: Type of component
            name: Component name
            description: Component description

        Returns:
            Created component or None if theory not found
        """
        if theory_id not in self.theories:
            return None

        component = TheoryComponent(
            component_type=component_type,
            name=name,
            description=description,
        )
        self.theories[theory_id].components.append(component)
        self._update_status(theory_id)
        return component

    def add_link(
        self,
        theory_id: str,
        source: str,
        target: str,
        link_type: str,
        description: str,
        evidence: str = "",
    ) -> TheoryLink | None:
        """Add a link between theory components.

        Args:
            theory_id: ID of the theory
            source: Source component name
            target: Target component name
            link_type: Type of link
            description: Link description
            evidence: Supporting evidence

        Returns:
            Created link or None
        """
        if theory_id not in self.theories:
            return None

        link = TheoryLink(
            source=source,
            target=target,
            link_type=link_type,
            description=description,
            evidence=evidence,
        )
        self.theories[theory_id].links.append(link)
        return link

    def add_mechanism_pathway(
        self,
        theory_id: str,
        pathway_name: str,
        steps: list[str],
        input_conditions: list[str],
        output_predictions: list[str],
    ) -> MechanismPathway | None:
        """Add a mechanism pathway to a theory.

        Args:
            theory_id: ID of the theory
            pathway_name: Name of the pathway
            steps: Ordered steps in the mechanism
            input_conditions: Required input conditions
            output_predictions: Predicted outputs

        Returns:
            Created pathway or None
        """
        if theory_id not in self.theories:
            return None

        pathway = MechanismPathway(
            pathway_name=pathway_name,
            steps=steps,
            input_conditions=input_conditions,
            output_predictions=output_predictions,
        )
        self.theories[theory_id].mechanisms.append(pathway)
        self._update_status(theory_id)
        return pathway

    def evaluate_theory(self, theory_id: str) -> TheoryEvaluation | None:
        """Evaluate a theory against standard criteria.

        Args:
            theory_id: ID of the theory

        Returns:
            Theory evaluation or None if theory not found
        """
        if theory_id not in self.theories:
            return None

        theory = self.theories[theory_id]
        eval_result = TheoryEvaluation()

        # Coherence: Are components logically consistent?
        eval_result.coherence = self._evaluate_coherence(theory)

        # Testability: Can the theory be empirically tested?
        eval_result.testability = self._evaluate_testability(theory)

        # Parsimony: Is the theory as simple as possible?
        eval_result.parsimony = self._evaluate_parsimony(theory)

        # Explanatory power: How much does it explain?
        eval_result.explanatory_power = self._evaluate_explanatory_power(theory)

        # Predictive power: Does it generate testable predictions?
        eval_result.predictive_power = self._evaluate_predictive_power(theory)

        # Falsifiability: Can it be proven wrong?
        eval_result.falsifiability = self._evaluate_falsifiability(theory)

        # Overall score
        eval_result.overall_score = (
            eval_result.coherence * 0.15 +
            eval_result.testability * 0.20 +
            eval_result.parsimony * 0.10 +
            eval_result.explanatory_power * 0.25 +
            eval_result.predictive_power * 0.15 +
            eval_result.falsifiability * 0.15
        )

        # Identify strengths and weaknesses
        eval_result.strengths = self._identify_strengths(eval_result)
        eval_result.weaknesses = self._identify_weaknesses(eval_result)
        eval_result.gaps = self._identify_gaps(theory)

        theory.evaluation = eval_result
        return eval_result

    def _evaluate_coherence(self, theory: TheoryDraft) -> float:
        """Evaluate theory coherence."""
        if not theory.components:
            return 0.0

        # Check if all linked components exist
        component_names = {c.name for c in theory.components}
        links_valid = all(
            link.source in component_names and link.target in component_names
            for link in theory.links
        )

        if not links_valid:
            return 0.3

        # Check for contradictions
        has_contradictions = any(c.contradictions for c in theory.components)

        score = 0.8 if links_valid else 0.4
        score -= 0.2 if has_contradictions else 0.0

        return max(0.0, min(1.0, score))

    def _evaluate_testability(self, theory: TheoryDraft) -> float:
        """Evaluate theory testability."""
        if not theory.mechanisms:
            return 0.3

        pathways_with_predictions = sum(
            1 for m in theory.mechanisms if m.testable_predictions
        )

        score = pathways_with_predictions / len(theory.mechanisms)

        # Bonus for clear output predictions
        if any(m.output_predictions for m in theory.mechanisms):
            score += 0.2

        return max(0.0, min(1.0, score))

    def _evaluate_parsimony(self, theory: TheoryDraft) -> float:
        """Evaluate theory parsimony."""
        num_components = len(theory.components)
        num_links = len(theory.links)

        # Ideal ratio is around 1 link per component
        if num_components == 0:
            return 1.0

        link_ratio = num_links / num_components

        if link_ratio < 0.5:
            return 0.6  # Too few links, may be incomplete
        elif link_ratio <= 2.0:
            return 0.9  # Good ratio
        else:
            return max(0.4, 1.0 - (link_ratio - 2.0) * 0.1)

    def _evaluate_explanatory_power(self, theory: TheoryDraft) -> float:
        """Evaluate theory explanatory power."""
        if not theory.core_claim:
            return 0.0

        # More mechanisms = more explanatory power
        mechanism_score = min(1.0, len(theory.mechanisms) * 0.3)

        # Evidence support helps
        evidence_count = sum(
            len(c.evidence_support) for c in theory.components
        )
        evidence_score = min(0.3, evidence_count * 0.1)

        # Alternative explanations considered = better
        alt_score = min(0.2, len(theory.alternative_explanations) * 0.1)

        return mechanism_score + evidence_score + alt_score

    def _evaluate_predictive_power(self, theory: TheoryDraft) -> float:
        """Evaluate theory predictive power."""
        total_predictions = sum(
            len(m.testable_predictions) + len(m.output_predictions)
            for m in theory.mechanisms
        )

        if not theory.mechanisms:
            return 0.0

        avg_predictions = total_predictions / len(theory.mechanisms)

        if avg_predictions >= 3:
            return 1.0
        elif avg_predictions >= 2:
            return 0.8
        elif avg_predictions >= 1:
            return 0.6
        else:
            return 0.3

    def _evaluate_falsifiability(self, theory: TheoryDraft) -> float:
        """Evaluate theory falsifiability."""
        if not theory.boundary_conditions:
            return 0.3

        # Clear boundary conditions help falsifiability
        boundary_score = min(1.0, len(theory.boundary_conditions) * 0.2)

        # Predictions that could be wrong
        has_predictions = any(
            m.testable_predictions or m.output_predictions
            for m in theory.mechanisms
        )

        return boundary_score if has_predictions else 0.2

    def _identify_strengths(self, eval_result: TheoryEvaluation) -> list[str]:
        """Identify theory strengths."""
        strengths = []

        if eval_result.coherence >= 0.8:
            strengths.append("High logical coherence between components")
        if eval_result.testability >= 0.8:
            strengths.append("Strong testability with clear predictions")
        if eval_result.explanatory_power >= 0.7:
            strengths.append("Strong explanatory power for observed phenomena")
        if eval_result.predictive_power >= 0.8:
            strengths.append("Generates specific, testable predictions")
        if eval_result.parsimony >= 0.8:
            strengths.append("Good balance of complexity and simplicity")

        return strengths

    def _identify_weaknesses(self, eval_result: TheoryEvaluation) -> list[str]:
        """Identify theory weaknesses."""
        weaknesses = []

        if eval_result.coherence < 0.5:
            weaknesses.append("Components may not be logically connected")
        if eval_result.testability < 0.5:
            weaknesses.append("Difficult to empirically test")
        if eval_result.explanatory_power < 0.5:
            weaknesses.append("Limited explanatory power for phenomena")
        if eval_result.predictive_power < 0.5:
            weaknesses.append("Few testable predictions")
        if eval_result.parsimony < 0.5:
            weaknesses.append("May be overly complex")
        if eval_result.falsifiability < 0.5:
            weaknesses.append("Hard to disprove or falsify")

        return weaknesses

    def _identify_gaps(self, theory: TheoryDraft) -> list[str]:
        """Identify gaps in the theory."""
        gaps = []

        if not theory.mechanisms:
            gaps.append("No mechanism pathways specified")
        if not theory.links:
            gaps.append("No causal/logical links between components")
        if not theory.alternative_explanations:
            gaps.append("Alternative explanations not considered")
        if not theory.boundary_conditions:
            gaps.append("Boundary conditions not specified")
        if not theory.open_questions:
            gaps.append("No explicit open questions identified")

        return gaps

    def _update_status(self, theory_id: str) -> None:
        """Update theory status based on development."""
        theory = self.theories[theory_id]

        if len(theory.components) >= 3 and len(theory.links) >= 2:
            theory.status = TheoryStatus.FORMULATING

        if theory.mechanisms and any(
            m.testable_predictions for m in theory.mechanisms
        ):
            theory.status = TheoryStatus.TESTABLE

    def generate_revision_suggestions(
        self,
        theory_id: str,
    ) -> list[str] | None:
        """Generate suggestions for theory revision.

        Args:
            theory_id: ID of the theory

        Returns:
            List of revision suggestions or None
        """
        if theory_id not in self.theories:
            return None

        theory = self.theories[theory_id]
        suggestions = []

        eval_result = self.evaluate_theory(theory_id)
        if not eval_result:
            return None

        # Based on weaknesses
        for weakness in eval_result.weaknesses:
            if "logically connected" in weakness:
                suggestions.append(
                    "Add explicit links between components to improve coherence"
                )
            if "empirically test" in weakness:
                suggestions.append(
                    "Develop mechanism pathways with specific, measurable predictions"
                )
            if "explanatory power" in weakness:
                suggestions.append(
                    "Consider additional mechanisms or construct relationships"
                )
            if "alternative explanations" in weakness.lower():
                suggestions.append(
                    "Explicitly consider and address alternative explanations"
                )
            if "boundary conditions" in weakness:
                suggestions.append(
                    "Specify clear boundary conditions for theory applicability"
                )

        # Based on gaps
        for gap in eval_result.gaps:
            if "mechanism" in gap.lower():
                suggestions.append(
                    "Define one or more mechanism pathways explaining how the theory works"
                )
            if "links" in gap.lower():
                suggestions.append(
                    "Specify causal or logical relationships between components"
                )
            if "alternative" in gap.lower():
                suggestions.append(
                    "Identify and address the main alternative explanations"
                )

        return suggestions

    def get_theory(self, theory_id: str) -> TheoryDraft | None:
        """Get a theory by ID."""
        return self.theories.get(theory_id)

    def list_theories(self) -> list[TheoryDraft]:
        """List all theories."""
        return list(self.theories.values())

    def to_dict(self, theory_id: str) -> dict | None:
        """Export theory as dictionary."""
        theory = self.theories.get(theory_id)
        if not theory:
            return None

        return {
            "theory_id": theory.theory_id,
            "theory_name": theory.theory_name,
            "status": theory.status.value,
            "core_claim": theory.core_claim,
            "components": [
                {
                    "type": c.component_type.value,
                    "name": c.name,
                    "description": c.description,
                    "evidence": c.evidence_support,
                    "confidence": c.confidence,
                }
                for c in theory.components
            ],
            "links": [
                {
                    "source": l.source,
                    "target": l.target,
                    "type": l.link_type,
                    "description": l.description,
                }
                for l in theory.links
            ],
            "mechanisms": [
                {
                    "name": m.pathway_name,
                    "steps": m.steps,
                    "inputs": m.input_conditions,
                    "outputs": m.output_predictions,
                    "predictions": m.testable_predictions,
                }
                for m in theory.mechanisms
            ],
            "evaluation": {
                "coherence": theory.evaluation.coherence,
                "testability": theory.evaluation.testability,
                "parsimony": theory.evaluation.parsimony,
                "explanatory_power": theory.evaluation.explanatory_power,
                "predictive_power": theory.evaluation.predictive_power,
                "falsifiability": theory.evaluation.falsifiability,
                "overall": theory.evaluation.overall_score,
            } if theory.evaluation else None,
            "alternatives": theory.alternative_explanations,
            "boundaries": theory.boundary_conditions,
            "open_questions": theory.open_questions,
        }
