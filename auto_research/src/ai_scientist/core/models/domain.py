"""Core domain models for scientific research.

These models implement the typed schemas for:
- Research Phenomenon & Puzzle
- Paper & Paper Analysis
- Theory, Construct, Mechanism
- Research Question
- Method, Data Source, Measurement
- State Snapshot & Contract Version
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Literal


# ──────────────────────────────────────────────
# Research Phenomenon & Puzzle
# ──────────────────────────────────────────────


class PhenomenonType(str, Enum):
    OBSERVATIONAL = "OBSERVATIONAL"      # From empirical observation
    THEORETICAL = "THEORETICAL"         # From theory derivation
    COMPUTATIONAL = "COMPUTATIONAL"      # From simulation/AI behavior
    SOCIAL = "SOCIAL"                    # From human behavior
    NATURAL = "NATURAL"                 # From natural world


@dataclass
class ResearchPhenomenon:
    """A research phenomenon - observed pattern or regularity.

    The starting point of scientific inquiry.
    """
    id: str
    project_id: str
    raw_description: str          # Original observation description
    phenomenon_type: PhenomenonType
    domain: str                  # e.g., "AI", "Economics", "Biology"
    scope: str                    # "micro", "meso", "macro"
    key_entities: list[str] = field(default_factory=list)
    key_behaviors: list[str] = field(default_factory=list)
    boundary_conditions: list[str] = field(default_factory=list)
    anomalies_noted: list[str] = field(default_factory=list)  # Puzzles within phenomenon
    confidence: str = "MEDIUM"
    status: str = "ACTIVE"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "raw_description": self.raw_description,
            "phenomenon_type": self.phenomenon_type.value,
            "domain": self.domain,
            "scope": self.scope,
            "key_entities": self.key_entities,
            "key_behaviors": self.key_behaviors,
            "boundary_conditions": self.boundary_conditions,
            "anomalies_noted": self.anomalies_noted,
            "confidence": self.confidence,
            "status": self.status,
        }


class PuzzleType(str, Enum):
    EXISTENTIAL = "EXISTENTIAL"        # Why does X happen?
    MECHANISTIC = "MECHANISTIC"       # How does X work?
    CAUSAL = "CAUSAL"                 # What causes X?
    COMPARATIVE = "COMPARATIVE"        # What is different about X vs Y?
    PREDICTIVE = "PREDICTIVE"          # What will happen to X under conditions Y?
    NORMATIVE = "NORMATIVE"            # Should X do Y?


@dataclass
class ResearchPuzzle:
    """A research puzzle - specific question arising from phenomenon.

    The gap between observation and explanation.
    """
    id: str
    phenomenon_id: str
    project_id: str
    puzzle_type: PuzzleType
    puzzle_statement: str
    why_important: str = ""            # Why does this puzzle matter?
    current_explanations: list[str] = field(default_factory=list)
    gaps_in_explanations: list[str] = field(default_factory=list)
    related_constructs: list[str] = field(default_factory=list)  # Construct IDs
    difficulty: str = "MEDIUM"         # How hard is this to solve?
    tractability: str = "MEDIUM"       # How tractable is research on this?
    status: str = "ACTIVE"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "phenomenon_id": self.phenomenon_id,
            "project_id": self.project_id,
            "puzzle_type": self.puzzle_type.value,
            "puzzle_statement": self.puzzle_statement,
            "why_important": self.why_important,
            "current_explanations": self.current_explanations,
            "gaps_in_explanations": self.gaps_in_explanations,
            "related_constructs": self.related_constructs,
            "difficulty": self.difficulty,
            "tractability": self.tractability,
            "status": self.status,
        }


# ──────────────────────────────────────────────
# Paper & Paper Analysis
# ──────────────────────────────────────────────


class PaperType(str, Enum):
    EMPIRICAL = "EMPIRICAL"
    THEORETICAL = "THEORETICAL"
    METHODOLOGICAL = "METHODOLOGICAL"
    REVIEW = "REVIEW"
    META_ANALYSIS = "META_ANALYSIS"
    WORKING_PAPER = "WORKING_PAPER"


class NearestNeighborType(str, Enum):
    DIRECT_COMPETITOR = "DIRECT_COMPETITOR"    # Same research question
    ADJACENT_DOMAIN = "ADJACENT_DOMAIN"         # Different domain, similar phenomenon
    METHODOLOGICAL = "METHODOLOGICAL"           # Similar method
    THEORETICAL = "THEORETICAL"                 # Same theory
    PARTIAL_OVERLAP = "PARTIAL_OVERLAP"         # Some overlap


@dataclass
class PaperAnalysis:
    """Deep analysis of a paper.

    Captures structured understanding of research papers.
    """
    id: str
    paper_id: str
    project_id: str

    # Research Question Analysis
    primary_research_question: str = ""
    secondary_questions: list[str] = field(default_factory=list)

    # Novelty Analysis
    novelty_claimed: str = ""
    novelty_gaps_identified: list[str] = field(default_factory=list)
    contribution_type: str = ""  # THEORY, METHOD, EMPIRICAL, APPLICATION

    # Theoretical Analysis
    theories_used: list[str] = field(default_factory=list)  # Theory IDs
    constructs_examined: list[str] = field(default_factory=list)  # Construct IDs
    mechanisms_proposed: list[str] = field(default_factory=list)  # Mechanism IDs
    alternative_explanations_discussed: list[str] = field(default_factory=list)
    boundary_conditions: list[str] = field(default_factory=list)

    # Method Analysis
    research_method: str = ""
    data_sources: list[str] = field(default_factory=list)
    sample_size: str = ""
    measurement_approaches: list[str] = field(default_factory=list)
    identification_strategy: str = ""

    # Evidence Analysis
    key_findings: list[str] = field(default_factory=list)
    evidence_quality: str = "MEDIUM"
    limitations: list[str] = field(default_factory=list)

    # Citation Analysis
    cited_by_papers: list[str] = field(default_factory=list)  # Paper IDs
    references_to_papers: list[str] = field(default_factory=list)  # Paper IDs

    # Original Text Evidence
    original_evidence_passages: list[dict] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "paper_id": self.paper_id,
            "project_id": self.project_id,
            "primary_research_question": self.primary_research_question,
            "secondary_questions": self.secondary_questions,
            "novelty_claimed": self.novelty_claimed,
            "novelty_gaps_identified": self.novelty_gaps_identified,
            "contribution_type": self.contribution_type,
            "theories_used": self.theories_used,
            "constructs_examined": self.constructs_examined,
            "mechanisms_proposed": self.mechanisms_proposed,
            "alternative_explanations_discussed": self.alternative_explanations_discussed,
            "boundary_conditions": self.boundary_conditions,
            "research_method": self.research_method,
            "data_sources": self.data_sources,
            "sample_size": self.sample_size,
            "measurement_approaches": self.measurement_approaches,
            "identification_strategy": self.identification_strategy,
            "key_findings": self.key_findings,
            "evidence_quality": self.evidence_quality,
            "limitations": self.limitations,
            "cited_by_papers": self.cited_by_papers,
            "references_to_papers": self.references_to_papers,
            "original_evidence_passages": self.original_evidence_passages,
        }


@dataclass
class NearestNeighborPaper:
    """Identifies and characterizes a nearest neighbor paper.

    Critical for novelty assessment.
    """
    id: str
    paper_id: str  # Link to actual Paper
    project_id: str
    research_question_id: str | None = None  # Which RQ this is neighbor to

    neighbor_type: NearestNeighborType = NearestNeighborType.DIRECT_COMPETITOR
    relationship_description: str = ""

    # Comparison dimensions
    similar_phenomenon: bool = False
    similar_research_question: bool = False
    similar_method: bool = False
    similar_theory: bool = False

    # Key differences
    key_differences: list[str] = field(default_factory=list)
    opportunities_from_difference: list[str] = field(default_factory=list)

    # Threat assessment
    novelty_threat_level: str = "MEDIUM"  # HIGH, MEDIUM, LOW
    novelty_threat_explanation: str = ""

    # Status
    status: str = "ACTIVE"
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "paper_id": self.paper_id,
            "project_id": self.project_id,
            "research_question_id": self.research_question_id,
            "neighbor_type": self.neighbor_type.value,
            "relationship_description": self.relationship_description,
            "similar_phenomenon": self.similar_phenomenon,
            "similar_research_question": self.similar_research_question,
            "similar_method": self.similar_method,
            "similar_theory": self.similar_theory,
            "key_differences": self.key_differences,
            "opportunities_from_difference": self.opportunities_from_difference,
            "novelty_threat_level": self.novelty_threat_level,
            "novelty_threat_explanation": self.novelty_threat_explanation,
            "status": self.status,
        }


# ──────────────────────────────────────────────
# Theory, Construct, Mechanism
# ──────────────────────────────────────────────


class TheoryLevel(str, Enum):
    MICRO = "MICRO"          # Individual level
    MESO = "MESO"            # Organizational/group level
    MACRO = "MACRO"          # System level


@dataclass
class Theory:
    """A theoretical framework.

    Captures the theoretical foundation of research.
    """
    id: str
    project_id: str
    theory_name: str
    origin_domain: str         # Where did this theory come from?
    theory_level: TheoryLevel

    # Core elements
    core_constructs: list[str] = field(default_factory=list)  # Construct IDs
    core_propositions: list[str] = field(default_factory=list)
    assumed_relationships: list[dict] = field(default_factory=list)  # {from, to, type}

    # Boundary conditions
    scope_conditions: list[str] = field(default_factory=list)
    excluded_contexts: list[str] = field(default_factory=list)

    # Application to current research
    applicability_to_research: str = ""
    adaptations_needed: list[str] = field(default_factory=list)

    # Source
    source_paper_id: str | None = None
    source_authors: list[str] = field(default_factory=list)

    # Status
    status: str = "ACTIVE"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "theory_name": self.theory_name,
            "origin_domain": self.origin_domain,
            "theory_level": self.theory_level.value,
            "core_constructs": self.core_constructs,
            "core_propositions": self.core_propositions,
            "assumed_relationships": self.assumed_relationships,
            "scope_conditions": self.scope_conditions,
            "excluded_contexts": self.excluded_contexts,
            "applicability_to_research": self.applicability_to_research,
            "adaptations_needed": self.adaptations_needed,
            "source_paper_id": self.source_paper_id,
            "source_authors": self.source_authors,
            "status": self.status,
        }


@dataclass
class Construct:
    """A theoretical construct - abstract concept in theory.

    Key building block for mechanisms.
    """
    id: str
    theory_id: str | None     # Which theory this belongs to
    project_id: str
    construct_name: str
    construct_definition: str  # How is this construct defined?

    # Characteristics
    is_latent: bool = True     # Is this latent (measured indirectly)?
    is_multi_dimensional: bool = False
    dimensions: list[str] = field(default_factory=list)  # If multi-dimensional

    # Operationalization
    operationalization_status: str = "PROPOSED"  # PROPOSED, PARTIAL, FULL
    proposed_measurements: list[str] = field(default_factory=list)

    # Relationships
    antecedent_constructs: list[str] = field(default_factory=list)  # Construct IDs
    consequent_constructs: list[str] = field(default_factory=list)  # Construct IDs

    # Application
    role_in_research: str = ""  # IV, DV, Mediator, Moderator, Control

    status: str = "ACTIVE"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "theory_id": self.theory_id,
            "project_id": self.project_id,
            "construct_name": self.construct_name,
            "construct_definition": self.construct_definition,
            "is_latent": self.is_latent,
            "is_multi_dimensional": self.is_multi_dimensional,
            "dimensions": self.dimensions,
            "operationalization_status": self.operationalization_status,
            "proposed_measurements": self.proposed_measurements,
            "antecedent_constructs": self.antecedent_constructs,
            "consequent_constructs": self.consequent_constructs,
            "role_in_research": self.role_in_research,
            "status": self.status,
        }


class MechanismType(str, Enum):
    CAUSAL = "CAUSAL"                # X causes Y
    MEDIATING = "MEDIATING"          # X -> M -> Y
    MODERATING = "MODERATING"        # X * W -> Y
    FEEDBACK = "FEEDBACK"            # X -> Y -> X
    EMERGENT = "EMERGENT"           # Complex interaction produces Y
    ADAPTIVE = "ADAPTIVE"            # System adapts based on feedback


@dataclass
class Mechanism:
    """A causal mechanism - how X leads to Y.

    Central to theory-building.
    """
    id: str
    project_id: str
    mechanism_name: str

    mechanism_type: MechanismType

    # Core description
    causal_logic: str               # Why does X lead to Y through this mechanism?
    necessary_conditions: list[str] = field(default_factory=list)
    sufficient_conditions: list[str] = field(default_factory=list)

    # Linked constructs
    input_constructs: list[str] = field(default_factory=list)  # What enters
    output_constructs: list[str] = field(default_factory=list)  # What emerges

    # Process description
    intermediate_steps: list[str] = field(default_factory=list)  # Step 1, Step 2...

    # Theoretical grounding
    theory_id: str | None = None
    theoretical_rationale: str = ""

    # Alternative mechanisms
    alternative_mechanisms: list[str] = field(default_factory=list)  # Other ways X->Y
    why_this_mechanism: str = ""  # Why prefer this over alternatives?

    # Boundary conditions
    scope_conditions: list[str] = field(default_factory=list)
    failure_conditions: list[str] = field(default_factory=list)

    # Testability
    testable_predictions: list[str] = field(default_factory=list)
    required_evidence: list[str] = field(default_factory=list)

    status: str = "ACTIVE"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "mechanism_name": self.mechanism_name,
            "mechanism_type": self.mechanism_type.value,
            "causal_logic": self.causal_logic,
            "necessary_conditions": self.necessary_conditions,
            "sufficient_conditions": self.sufficient_conditions,
            "input_constructs": self.input_constructs,
            "output_constructs": self.output_constructs,
            "intermediate_steps": self.intermediate_steps,
            "theory_id": self.theory_id,
            "theoretical_rationale": self.theoretical_rationale,
            "alternative_mechanisms": self.alternative_mechanisms,
            "why_this_mechanism": self.why_this_mechanism,
            "scope_conditions": self.scope_conditions,
            "failure_conditions": self.failure_conditions,
            "testable_predictions": self.testable_predictions,
            "required_evidence": self.required_evidence,
            "status": self.status,
        }


@dataclass
class AlternativeExplanation:
    """An alternative explanation for observed phenomenon.

    Critical for rigorous research.
    """
    id: str
    project_id: str
    explanation_name: str
    description: str

    # What it explains
    target_puzzle_id: str | None = None
    target_phenomenon_id: str | None = None

    # Key differences from focal explanation
    key_differentiators: list[str] = field(default_factory=list)

    # Evidence for this explanation
    supporting_evidence: list[str] = field(default_factory=list)
    supporting_papers: list[str] = field(default_factory=list)

    # Evidence against
    contradicting_evidence: list[str] = field(default_factory=list)

    # Assessment
    plausibility: str = "MEDIUM"  # HIGH, MEDIUM, LOW
    testability: str = "MEDIUM"
    threat_level: str = "MEDIUM"   # How much does this threaten focal explanation?

    # How to distinguish
    distinguishing_tests: list[str] = field(default_factory=list)

    status: str = "ACTIVE"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "explanation_name": self.explanation_name,
            "description": self.description,
            "target_puzzle_id": self.target_puzzle_id,
            "target_phenomenon_id": self.target_phenomenon_id,
            "key_differentiators": self.key_differentiators,
            "supporting_evidence": self.supporting_evidence,
            "supporting_papers": self.supporting_papers,
            "contradicting_evidence": self.contradicting_evidence,
            "plausibility": self.plausibility,
            "testability": self.testability,
            "threat_level": self.threat_level,
            "distinguishing_tests": self.distinguishing_tests,
            "status": self.status,
        }


# ──────────────────────────────────────────────
# Research Question
# ──────────────────────────────────────────────


class QuestionClarity(str, Enum):
    VAGUE = "VAGUE"              # Needs significant refinement
    BROAD = "BROAD"              # Direction clear, scope unclear
    SPECIFIC = "SPECIFIC"         # Well-specified question
    OPERATIONALIZED = "OPERATIONALIZED"  # Directly testable


class QuestionFeasibility(str, Enum):
    THEORETICAL = "THEORETICAL"  # Can be addressed theoretically
    EMPIRICALLY_TESTABLE = "EMPIRICALLY_TESTABLE"
    FULLY_FEASIBLE = "FULLY_FEASIBLE"  # Theory + data + method available


@dataclass
class ResearchQuestion:
    """A specific, testable research question.

    Formed from direction after debate and refinement.
    """
    id: str
    project_id: str
    question_text: str

    # Optional fields with defaults
    direction_id: str | None = None

    # Specificity
    clarity: QuestionClarity = QuestionClarity.BROAD

    # Structure
    is_conditional: bool = False  # If X, then Y?
    condition_text: str = ""
    antecedent: str = ""         # X in "If X, then Y"
    consequent: str = ""          # Y in "If X, then Y"

    # Components
    phenomenon_referenced: str = ""  # What phenomenon is this about?
    mechanism_proposed: str = ""     # What mechanism is proposed?
    conditions_specified: str = ""   # Under what conditions?
    outcome_specified: str = ""      # What outcome?

    # Feasibility
    feasibility: QuestionFeasibility = QuestionFeasibility.THEORETICAL
    data_availability: str = "UNKNOWN"
    method_availability: str = "UNKNOWN"

    # Theoretical grounding
    theories_applicable: list[str] = field(default_factory=list)
    mechanisms_proposed: list[str] = field(default_factory=list)
    alternative_explanations: list[str] = field(default_factory=list)

    # Research design hints
    suggested_method: str = ""
    suggested_data_source: str = ""
    suggested_measurements: list[str] = field(default_factory=list)

    # Novelty assessment
    novelty_score: float = 0.5
    novelty_basis: str = ""
    relationship_to_existing: str = ""  # How does this differ from prior work?

    # Status
    status: str = "PROPOSED"  # PROPOSED, REFINED, VALIDATED, APPROVED, REJECTED
    rejection_reason: str = ""

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "direction_id": self.direction_id,
            "question_text": self.question_text,
            "clarity": self.clarity.value,
            "is_conditional": self.is_conditional,
            "condition_text": self.condition_text,
            "antecedent": self.antecedent,
            "consequent": self.consequent,
            "phenomenon_referenced": self.phenomenon_referenced,
            "mechanism_proposed": self.mechanism_proposed,
            "conditions_specified": self.conditions_specified,
            "outcome_specified": self.outcome_specified,
            "feasibility": self.feasibility.value,
            "data_availability": self.data_availability,
            "method_availability": self.method_availability,
            "theories_applicable": self.theories_applicable,
            "mechanisms_proposed": self.mechanisms_proposed,
            "alternative_explanations": self.alternative_explanations,
            "suggested_method": self.suggested_method,
            "suggested_data_source": self.suggested_data_source,
            "suggested_measurements": self.suggested_measurements,
            "novelty_score": self.novelty_score,
            "novelty_basis": self.novelty_basis,
            "relationship_to_existing": self.relationship_to_existing,
            "status": self.status,
            "rejection_reason": self.rejection_reason,
        }


# ──────────────────────────────────────────────
# Method, Data, Measurement
# ──────────────────────────────────────────────


class MethodType(str, Enum):
    EXPERIMENTAL = "EXPERIMENTAL"
    QUASI_EXPERIMENTAL = "QUASI_EXPERIMENTAL"
    SURVEY = "SURVEY"
    ARCHIVAL = "ARCHIVAL"
    CASE_STUDY = "CASE_STUDY"
    MIXED_METHODS = "MIXED_METHODS"
    SIMULATION = "SIMULATION"
    THEORETICAL = "THEORETICAL"


@dataclass
class ResearchMethod:
    """A research method proposed for testing RQ.
    """
    id: str
    research_question_id: str
    project_id: str

    method_type: MethodType
    method_name: str
    method_description: str

    # Design details
    key_design_features: list[str] = field(default_factory=list)
    required_conditions: list[str] = field(default_factory=list)

    # Validity considerations
    internal_validity_concerns: list[str] = field(default_factory=list)
    external_validity_concerns: list[str] = field(default_factory=list)

    # Identification
    identification_strategy: str = ""
    identification_strength: str = "MEDIUM"  # HIGH, MEDIUM, LOW

    # Alternative methods
    alternative_methods: list[str] = field(default_factory=list)
    why_this_method: str = ""

    # Feasibility
    feasibility_assessment: str = "MEDIUM"
    resource_requirements: list[str] = field(default_factory=list)
    estimated_time: str = ""

    status: str = "PROPOSED"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "research_question_id": self.research_question_id,
            "project_id": self.project_id,
            "method_type": self.method_type.value,
            "method_name": self.method_name,
            "method_description": self.method_description,
            "key_design_features": self.key_design_features,
            "required_conditions": self.required_conditions,
            "internal_validity_concerns": self.internal_validity_concerns,
            "external_validity_concerns": self.external_validity_concerns,
            "identification_strategy": self.identification_strategy,
            "identification_strength": self.identification_strength,
            "alternative_methods": self.alternative_methods,
            "why_this_method": self.why_this_method,
            "feasibility_assessment": self.feasibility_assessment,
            "resource_requirements": self.resource_requirements,
            "estimated_time": self.estimated_time,
            "status": self.status,
        }


@dataclass
class DataSource:
    """A data source for research.
    """
    id: str
    project_id: str
    source_name: str
    source_type: str = ""  # PRIMARY, SECONDARY, SIMULATED, SYNTHETIC

    # Optional foreign key
    research_method_id: str | None = None

    # Availability
    access_requirements: list[str] = field(default_factory=list)
    cost_estimate: str = ""
    availability_timeline: str = ""

    # Characteristics
    sample_size: str = ""
    time_span: str = ""
    coverage: str = ""

    # Quality
    data_quality_assessment: str = "MEDIUM"
    known_issues: list[str] = field(default_factory=list)
    cleaning_required: bool = False

    # Variables available
    variables_available: list[str] = field(default_factory=list)
    key_variables: list[str] = field(default_factory=list)

    # Fit for research question
    fit_assessment: str = "MEDIUM"
    fit_rationale: str = ""

    status: str = "IDENTIFIED"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "research_method_id": self.research_method_id,
            "project_id": self.project_id,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "access_requirements": self.access_requirements,
            "cost_estimate": self.cost_estimate,
            "availability_timeline": self.availability_timeline,
            "sample_size": self.sample_size,
            "time_span": self.time_span,
            "coverage": self.coverage,
            "data_quality_assessment": self.data_quality_assessment,
            "known_issues": self.known_issues,
            "cleaning_required": self.cleaning_required,
            "variables_available": self.variables_available,
            "key_variables": self.key_variables,
            "fit_assessment": self.fit_assessment,
            "fit_rationale": self.fit_rationale,
            "status": self.status,
        }


@dataclass
class Measurement:
    """How constructs are measured.
    """
    id: str
    project_id: str
    measurement_name: str
    measurement_type: str = ""  # SELF_REPORT, BEHAVIORAL, ARCHIVAL, PHYSIOLOGICAL, etc.
    measurement_description: str = ""

    # Optional foreign key
    construct_id: str | None = None
    measurement_items: list[str] = field(default_factory=list)

    # Validity
    validity_evidence: list[str] = field(default_factory=list)
    reliability_evidence: list[str] = field(default_factory=list)

    # Issues
    known_limitations: list[str] = field(default_factory=list)
    construct_validity_concerns: list[str] = field(default_factory=list)

    # Alternatives
    alternative_measurements: list[str] = field(default_factory=list)

    status: str = "PROPOSED"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "construct_id": self.construct_id,
            "project_id": self.project_id,
            "measurement_name": self.measurement_name,
            "measurement_type": self.measurement_type,
            "measurement_description": self.measurement_description,
            "measurement_items": self.measurement_items,
            "validity_evidence": self.validity_evidence,
            "reliability_evidence": self.reliability_evidence,
            "known_limitations": self.known_limitations,
            "construct_validity_concerns": self.construct_validity_concerns,
            "alternative_measurements": self.alternative_measurements,
            "status": self.status,
        }


@dataclass
class IdentificationStrategy:
    """How causal identification is achieved.
    """
    id: str
    research_method_id: str
    project_id: str

    strategy_name: str
    strategy_type: str  # EXPERIMENTAL_MANIPULATION, INSTRUMENTAL_VARIABLE, etc.

    # Description
    identification_logic: str
    key_assumptions: list[str] = field(default_factory=list)

    # Threats
    threats_to_identification: list[str] = field(default_factory=list)
    how_addressed: list[str] = field(default_factory=list)

    # Strength
    identification_strength: str = "MEDIUM"  # HIGH, MEDIUM, LOW
    robustness_checks: list[str] = field(default_factory=list)

    status: str = "PROPOSED"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "research_method_id": self.research_method_id,
            "project_id": self.project_id,
            "strategy_name": self.strategy_name,
            "strategy_type": self.strategy_type,
            "identification_logic": self.identification_logic,
            "key_assumptions": self.key_assumptions,
            "threats_to_identification": self.threats_to_identification,
            "how_addressed": self.how_addressed,
            "identification_strength": self.identification_strength,
            "robustness_checks": self.robustness_checks,
            "status": self.status,
        }


# ──────────────────────────────────────────────
# State Snapshot & Contract Version
# ──────────────────────────────────────────────


@dataclass
class StateSnapshot:
    """A point-in-time snapshot of research state.

    Captures complete research state for rollback/branching.
    """
    id: str
    project_id: str
    snapshot_name: str
    snapshot_type: str  # MILESTONE, DECISION_POINT, MANUAL, PRE_DEBATE, POST_DEBATE

    # What was captured
    research_phenomena: list[dict] = field(default_factory=list)
    research_puzzles: list[dict] = field(default_factory=list)
    research_directions: list[dict] = field(default_factory=list)
    research_questions: list[dict] = field(default_factory=list)
    theories: list[dict] = field(default_factory=list)
    constructs: list[dict] = field(default_factory=list)
    mechanisms: list[dict] = field(default_factory=list)
    methods: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    papers: list[dict] = field(default_factory=list)

    # Decision made at this point
    decision_made: str = ""
    decision_rationale: str = ""

    # Relationships
    parent_snapshot_id: str | None = None
    branch_name: str | None = None

    # Metadata
    stage: str = ""  # What stage was research at?
    key_insights: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)

    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "snapshot_name": self.snapshot_name,
            "snapshot_type": self.snapshot_type,
            "research_phenomena": self.research_phenomena,
            "research_puzzles": self.research_puzzles,
            "research_directions": self.research_directions,
            "research_questions": self.research_questions,
            "theories": self.theories,
            "constructs": self.constructs,
            "mechanisms": self.mechanisms,
            "methods": self.methods,
            "evidence": self.evidence,
            "papers": self.papers,
            "decision_made": self.decision_made,
            "decision_rationale": self.decision_rationale,
            "parent_snapshot_id": self.parent_snapshot_id,
            "branch_name": self.branch_name,
            "stage": self.stage,
            "key_insights": self.key_insights,
            "open_questions": self.open_questions,
        }


@dataclass
class ContractVersion:
    """A version of the research contract.

    Tracks evolution of research plan.
    """
    id: str
    research_question_id: str
    project_id: str

    version_number: int
    version_status: str  # DRAFT, REVIEWED, APPROVED, REJECTED, SUPERSEDED

    # Content
    research_question: str = ""
    theoretical_grounding: str = ""
    proposed_mechanism: str = ""
    alternative_explanations: list[str] = field(default_factory=list)
    proposed_method: str = ""
    data_source: str = ""
    measurement_plan: str = ""
    expected_contribution: str = ""

    # Review
    reviewer_notes: str = ""
    revision_requests: list[str] = field(default_factory=list)
    approved_by: str = ""

    # Changes from previous
    changes_from_previous: list[str] = field(default_factory=list)
    previous_version_id: str | None = None

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "research_question_id": self.research_question_id,
            "project_id": self.project_id,
            "version_number": self.version_number,
            "version_status": self.version_status,
            "research_question": self.research_question,
            "theoretical_grounding": self.theoretical_grounding,
            "proposed_mechanism": self.proposed_mechanism,
            "alternative_explanations": self.alternative_explanations,
            "proposed_method": self.proposed_method,
            "data_source": self.data_source,
            "measurement_plan": self.measurement_plan,
            "expected_contribution": self.expected_contribution,
            "reviewer_notes": self.reviewer_notes,
            "revision_requests": self.revision_requests,
            "approved_by": self.approved_by,
            "changes_from_previous": self.changes_from_previous,
            "previous_version_id": self.previous_version_id,
        }


# ──────────────────────────────────────────────
# Persistent Objection Ledger (v4)
# ──────────────────────────────────────────────


class ObjectionSeverity(str, Enum):
    """Severity level of a scientific objection.

    FATAL: Research cannot proceed without resolution
    MAJOR: Significant concern that must be addressed
    MINOR: Minor concern worth noting but not blocking
    """
    FATAL = "FATAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"


class ObjectionStatus(str, Enum):
    """Status of a scientific objection through its lifecycle.

    OPEN: Identified but not yet reviewed
    UNDER_REVIEW: Currently being evaluated
    RESOLVED: Addressed with evidence
    INVALIDATED: Found to be based on incorrect premises
    ACCEPTED_RISK: Acknowledged but research proceeds with explicit justification
    REQUIRES_HUMAN: Requires human judgment to resolve
    """
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    INVALIDATED = "INVALIDATED"
    ACCEPTED_RISK = "ACCEPTED_RISK"
    REQUIRES_HUMAN = "REQUIRES_HUMAN"


class ObjectionCategory(str, Enum):
    """Category of scientific objection.

    Used to classify objections for pattern analysis and resolution strategy.
    """
    INTERNAL_CONSISTENCY = "INTERNAL_CONSISTENCY"      # Contradicts other claims
    EVIDENCE_QUALITY = "EVIDENCE_QUALITY"              # Evidence insufficient/weak
    LOGICAL_FALLACY = "LOGICAL_FALLACY"                # Reasoning error
    EMPIRICAL_FEASIBILITY = "EMPIRICAL_FEASIBILITY"    # Cannot be tested empirically
    THEORETICAL_COHERENCE = "THEORETICAL_COHERENCE"    # Contradicts established theory
    NOVELTY_THREAT = "NOVELTY_THREAT"                  # Not novel enough
    METHODOLOGICAL = "METHODOLOGICAL"                  # Methodological flaws
    CYCLICAL_REASONING = "CYCLICAL_REASONING"          # Circular argument
    SCOPE_BOUNDARY = "SCOPE_BOUNDARY"                  # Vague boundary conditions
    OTHER = "OTHER"


class ResolutionType(str, Enum):
    """How an objection was resolved.

    ADDRESSED: Evidence provided resolves the objection
    DISMISSED: Objection based on incorrect premises
    ACCEPTED: Risk explicitly accepted with justification
    RETRACTED: Red team withdrew objection
    PIVOTED_AROUND: Research direction changed to avoid
    UNRESOLVED: No resolution reached
    """
    ADDRESSED = "ADDRESSED"
    DISMISSED = "DISMISSED"
    ACCEPTED = "ACCEPTED"
    RETRACTED = "RETRACTED"
    PIVOTED_AROUND = "PIVOTED_AROUND"
    UNRESOLVED = "UNRESOLVED"


@dataclass
class ScientificObjection:
    """A persistent scientific objection that must be tracked across research runs.

    This is the core model for the v4 Persistent Objection Ledger.
    Historical objections are inherited across runs to prevent "silent disappearance."
    """
    id: str
    project_id: str
    target_type: str              # RESEARCH_QUESTION, DIRECTION, THEORY, MECHANISM, etc.
    target_id: str                # ID of the target entity

    category: ObjectionCategory
    severity: ObjectionSeverity
    title: str                    # Short summary of the objection
    argument: str                 # Full argument/proof of the objection

    # Evidence references
    supporting_evidence_ids: list[str] = field(default_factory=list)
    contradictory_evidence_ids: list[str] = field(default_factory=list)

    # Lifecycle tracking
    introduced_in_run: int = 0    # Which run first raised this objection
    last_reviewed_in_run: int = 0 # Last run where this was reviewed
    status: ObjectionStatus = ObjectionStatus.OPEN

    # Resolution
    resolution_type: ResolutionType | None = None
    resolution_reason: str = ""
    resolved_by_evidence_ids: list[str] = field(default_factory=list)

    # Metadata
    raised_by: str = "RED_TEAM"   # Who raised this: RED_TEAM, DEBATE, HUMAN, etc.
    review_notes: list[str] = field(default_factory=list)  # History of review notes

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "argument": self.argument,
            "supporting_evidence_ids": self.supporting_evidence_ids,
            "contradictory_evidence_ids": self.contradictory_evidence_ids,
            "introduced_in_run": self.introduced_in_run,
            "last_reviewed_in_run": self.last_reviewed_in_run,
            "status": self.status.value,
            "resolution_type": self.resolution_type.value if self.resolution_type else None,
            "resolution_reason": self.resolution_reason,
            "resolved_by_evidence_ids": self.resolved_by_evidence_ids,
            "raised_by": self.raised_by,
            "review_notes": self.review_notes,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScientificObjection":
        """Create a ScientificObjection from a dictionary."""
        # Handle datetime conversion
        created_at = data.get("created_at", datetime.utcnow())
        updated_at = data.get("updated_at", datetime.utcnow())
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)

        return cls(
            id=data["id"],
            project_id=data["project_id"],
            target_type=data["target_type"],
            target_id=data["target_id"],
            category=ObjectionCategory(data["category"]),
            severity=ObjectionSeverity(data["severity"]),
            title=data["title"],
            argument=data["argument"],
            supporting_evidence_ids=data.get("supporting_evidence_ids", []),
            contradictory_evidence_ids=data.get("contradictory_evidence_ids", []),
            introduced_in_run=data.get("introduced_in_run", 0),
            last_reviewed_in_run=data.get("last_reviewed_in_run", 0),
            status=ObjectionStatus(data.get("status", "OPEN")),
            resolution_type=ResolutionType(data["resolution_type"]) if data.get("resolution_type") else None,
            resolution_reason=data.get("resolution_reason", ""),
            resolved_by_evidence_ids=data.get("resolved_by_evidence_ids", []),
            raised_by=data.get("raised_by", "RED_TEAM"),
            review_notes=data.get("review_notes", []),
            created_at=created_at,
            updated_at=updated_at,
        )

    def is_blocking(self) -> bool:
        """Returns True if this objection blocks research continuation.

        FATAL objections always block; others depend on status.
        """
        if self.severity == ObjectionSeverity.FATAL:
            return self.status in [
                ObjectionStatus.OPEN,
                ObjectionStatus.UNDER_REVIEW,
                ObjectionStatus.REQUIRES_HUMAN,
            ]
        return False

    def requires_review(self, current_run: int) -> bool:
        """Returns True if this objection needs review in the current run."""
        if self.status in [
            ObjectionStatus.RESOLVED,
            ObjectionStatus.INVALIDATED,
        ]:
            return False
        return self.last_reviewed_in_run < current_run
