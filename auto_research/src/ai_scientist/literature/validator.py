"""Evidence validator module.

Provides functionality for validating evidence and assessing quality.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class EvidenceType(str, Enum):
    EMPIRICAL = "EMPIRICAL"  # From experiments/data
    THEORETICAL = "THEORETICAL"  # From theory/logic
    ANECDOTAL = "ANECDOTAL"  # Case studies, examples
    SIMULATION = "SIMULATION"  # From simulations
    EXPERT = "EXPERT"  # Expert opinion


class EvidenceQuality(str, Enum):
    HIGH = "HIGH"  # Strong, well-supported
    MEDIUM = "MEDIUM"  # Moderate strength
    LOW = "LOW"  # Weak, preliminary


class ValidityThreat(str, Enum):
    CONFOUND = "CONFOUND"  # Confounding variables
    SELECTION = "SELECTION"  # Selection bias
    REVERSE_CAUSALITY = "REVERSE_CAUSALITY"  # Wrong direction
    OMISSION = "OMISSION"  # Missing variables
    MEASUREMENT = "MEASUREMENT"  # Measurement error
    GENERALIZATION = "GENERALIZATION"  # External validity
    REPLICATION = "REPLICATION"  # Not replicated


@dataclass
class EvidenceItem:
    """A piece of evidence."""
    id: str
    project_id: str
    content: str
    evidence_type: EvidenceType
    source: str = ""
    source_type: str = ""  # paper, experiment, expert, etc.
    source_paper_id: str = ""
    relevance: float = 0.5  # 0.0-1.0
    quality: EvidenceQuality = EvidenceQuality.MEDIUM
    citations: list[str] = field(default_factory=list)
    methodology_notes: str = ""
    context: str = ""
    extracted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ValidityAssessment:
    """Assessment of evidence validity."""
    threat_type: ValidityThreat
    description: str
    severity: str = "MEDIUM"  # HIGH, MEDIUM, LOW
    likelihood: float = 0.5  # 0.0-1.0
    mitigation: str = ""


@dataclass
class EvidenceValidationResult:
    """Result of evidence validation."""
    evidence_id: str
    overall_quality: EvidenceQuality
    quality_score: float  # 0.0-1.0

    # Breakdown
    relevance_score: float
    reliability_score: float
    validity_score: float

    # Threats identified
    threats: list[ValidityAssessment] = field(default_factory=list)

    # Recommendations
    improvements: list[str] = field(default_factory=list)
    supporting_evidence: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)

    # Confidence
    confidence: float = 0.5  # How confident are we in this assessment?


class EvidenceValidator:
    """Evidence validation and quality assessment system.

    Validates evidence against threats to validity and assesses quality.
    """

    def __init__(self, gateway=None):
        """Initialize evidence validator.

        Args:
            gateway: LLM gateway for analysis
        """
        self.gateway = gateway

    async def validate_evidence(
        self,
        evidence: EvidenceItem,
        context: dict | None = None,
    ) -> EvidenceValidationResult:
        """Validate a piece of evidence.

        Args:
            evidence: Evidence to validate
            context: Optional context (research question, hypothesis, etc.)

        Returns:
            Validation result with quality assessment
        """
        if self.gateway:
            return await self._llm_validate(evidence, context)
        return self._rule_based_validate(evidence, context)

    async def _llm_validate(
        self,
        evidence: EvidenceItem,
        context: dict | None,
    ) -> EvidenceValidationResult:
        """Use LLM for evidence validation."""
        context_str = ""
        if context:
            context_str = "\n\nContext:\n"
            for key, value in context.items():
                context_str += f"- {key}: {value}\n"

        prompt = f"""Evaluate the following evidence for research quality.

# Evidence
Type: {evidence.evidence_type.value}
Content: {evidence.content}
Source: {evidence.source}
Source Type: {evidence.source_type}
Context: {evidence.context}

{context_str}

Assess this evidence on:
1. RELEVANCE: How relevant is this to the research question?
2. RELIABILITY: Is the source trustworthy and method sound?
3. VALIDITY: Are there threats to internal/external validity?
4. THREATS: What threats to validity exist?
5. QUALITY: Overall quality assessment (HIGH/MEDIUM/LOW)
6. IMPROVEMENTS: What could improve this evidence?

Format your response as:
RELEVANCE: [0.0-1.0]
RELIABILITY: [0.0-1.0]
VALIDITY: [0.0-1.0]
QUALITY: [HIGH/MEDIUM/LOW]
THREATS: [List any validity threats]
IMPROVEMENTS: [List recommendations]
SUPPORTING: [Any supporting evidence needed]
CONTRADICTING: [Any contradicting evidence to consider]"""

        try:
            response = self.gateway.generate(prompt)
            return self._parse_validation_response(evidence.id, response)
        except Exception:
            return self._rule_based_validate(evidence, context)

    def _rule_based_validate(
        self,
        evidence: EvidenceItem,
        context: dict | None,
    ) -> EvidenceValidationResult:
        """Rule-based evidence validation."""
        # Base scores
        relevance = evidence.relevance

        # Reliability based on source type
        source_scores = {
            "paper": 0.8,
            "experiment": 0.9,
            "dataset": 0.85,
            "expert": 0.6,
            "anecdotal": 0.3,
        }
        reliability = source_scores.get(evidence.source_type.lower(), 0.5)

        # Quality based on evidence type
        type_scores = {
            EvidenceType.EMPIRICAL: 0.8,
            EvidenceType.SIMULATION: 0.7,
            EvidenceType.THEORETICAL: 0.6,
            EvidenceType.EXPERT: 0.5,
            EvidenceType.ANECDOTAL: 0.3,
        }
        base_quality = type_scores.get(evidence.evidence_type, EvidenceQuality.MEDIUM)

        # Calculate overall
        validity = (relevance + reliability) / 2
        quality_score = (relevance * 0.3 + reliability * 0.3 + validity * 0.4)

        # Identify threats
        threats = self._identify_threats(evidence, context)

        # Determine quality enum
        if quality_score >= 0.75:
            quality = EvidenceQuality.HIGH
        elif quality_score >= 0.5:
            quality = EvidenceQuality.MEDIUM
        else:
            quality = EvidenceQuality.LOW

        # Generate improvements
        improvements = self._suggest_improvements(evidence, threats)

        return EvidenceValidationResult(
            evidence_id=evidence.id,
            overall_quality=quality,
            quality_score=quality_score,
            relevance_score=relevance,
            reliability_score=reliability,
            validity_score=validity,
            threats=threats,
            improvements=improvements,
            confidence=0.6,  # Lower confidence for rule-based
        )

    def _identify_threats(
        self,
        evidence: EvidenceItem,
        context: dict | None,
    ) -> list[ValidityAssessment]:
        """Identify threats to validity."""
        threats = []

        content_lower = evidence.content.lower()

        # Check for confounding indicators
        if any(word in content_lower for word in ["correlation", "association", "related to"]):
            threats.append(ValidityAssessment(
                threat_type=ValidityThreat.CONFOUND,
                description="Correlation may not imply causation",
                severity="MEDIUM",
                likelihood=0.6,
                mitigation="Consider experimental design or control variables",
            ))

        # Check for sample issues
        if evidence.source_type.lower() in ["anecdotal", "case study"]:
            threats.append(ValidityAssessment(
                threat_type=ValidityThreat.SELECTION,
                description="Evidence from non-representative sample",
                severity="MEDIUM",
                likelihood=0.7,
                mitigation="Generalize cautiously, seek replication",
            ))

        # Check for measurement issues
        if any(word in content_lower for word in ["self-reported", "subjective", "survey"]):
            threats.append(ValidityAssessment(
                threat_type=ValidityThreat.MEASUREMENT,
                description="Subjective measurement may introduce bias",
                severity="LOW",
                likelihood=0.5,
                mitigation="Use multiple measurement approaches",
            ))

        # Check for external validity
        if context and "generalization" in str(context).lower():
            threats.append(ValidityAssessment(
                threat_type=ValidityThreat.GENERALIZATION,
                description="Results may not generalize to other contexts",
                severity="MEDIUM",
                likelihood=0.5,
                mitigation="Specify boundary conditions clearly",
            ))

        return threats

    def _suggest_improvements(
        self,
        evidence: EvidenceItem,
        threats: list[ValidityAssessment],
    ) -> list[str]:
        """Suggest improvements for evidence."""
        improvements = []

        # Based on evidence type
        if evidence.evidence_type == EvidenceType.ANECDOTAL:
            improvements.append("Seek empirical evidence from controlled studies")
            improvements.append("Look for replications or larger samples")

        if evidence.evidence_type == EvidenceType.THEORETICAL:
            improvements.append("Consider empirical validation of theoretical claims")
            improvements.append("Look for experimental evidence supporting theory")

        # Based on threats
        for threat in threats:
            if threat.threat_type == ValidityThreat.CONFOUND:
                improvements.append("Consider experimental designs that control for confounds")
            if threat.threat_type == ValidityThreat.MEASUREMENT:
                improvements.append("Use validated measurement instruments")
            if threat.threat_type == ValidityThreat.SELECTION:
                improvements.append("Use larger, more representative samples")

        # General improvements
        if not evidence.citations:
            improvements.append("Add citations to support claims")
        if not evidence.methodology_notes:
            improvements.append("Document methodology used to obtain this evidence")

        return improvements

    def _parse_validation_response(
        self,
        evidence_id: str,
        response: str,
    ) -> EvidenceValidationResult:
        """Parse LLM validation response."""
        lines = response.strip().split("\n")

        relevance = 0.5
        reliability = 0.5
        validity = 0.5
        quality = EvidenceQuality.MEDIUM
        threats: list[ValidityAssessment] = []
        improvements: list[str] = []

        for line in lines:
            line = line.strip()
            if line.startswith("RELEVANCE:"):
                try:
                    relevance = float(line.split(":")[1].strip())
                except ValueError:
                    pass
            elif line.startswith("RELIABILITY:"):
                try:
                    reliability = float(line.split(":")[1].strip())
                except ValueError:
                    pass
            elif line.startswith("VALIDITY:"):
                try:
                    validity = float(line.split(":")[1].strip())
                except ValueError:
                    pass
            elif line.startswith("QUALITY:"):
                quality_str = line.split(":")[1].strip().upper()
                if "HIGH" in quality_str:
                    quality = EvidenceQuality.HIGH
                elif "LOW" in quality_str:
                    quality = EvidenceQuality.LOW
                else:
                    quality = EvidenceQuality.MEDIUM
            elif line.startswith("THREATS:"):
                threat_text = line.split(":")[1].strip()
                if threat_text and threat_text != "None":
                    threats.append(ValidityAssessment(
                        threat_type=ValidityThreat.CONFOUND,
                        description=threat_text,
                        severity="MEDIUM",
                        likelihood=0.5,
                    ))
            elif line.startswith("IMPROVEMENTS:"):
                imp_text = line.split(":")[1].strip()
                if imp_text and imp_text != "None":
                    improvements = [i.strip() for i in imp_text.split(",")]

        quality_score = (relevance + reliability + validity) / 3

        return EvidenceValidationResult(
            evidence_id=evidence_id,
            overall_quality=quality,
            quality_score=quality_score,
            relevance_score=relevance,
            reliability_score=reliability,
            validity_score=validity,
            threats=threats,
            improvements=improvements,
            confidence=0.8,
        )

    async def compare_evidence(
        self,
        evidence_a: EvidenceItem,
        evidence_b: EvidenceItem,
    ) -> dict[str, Any]:
        """Compare two pieces of evidence.

        Returns:
            Comparison result with relative assessments
        """
        val_a = await self.validate_evidence(evidence_a)
        val_b = await self.validate_evidence(evidence_b)

        comparison = {
            "evidence_a_id": evidence_a.id,
            "evidence_b_id": evidence_b.id,
            "quality_comparison": {
                "a_better": val_a.quality_score > val_b.quality_score,
                "difference": abs(val_a.quality_score - val_b.quality_score),
            },
            "relevance_comparison": {
                "a_better": val_a.relevance_score > val_b.relevance_score,
                "difference": abs(val_a.relevance_score - val_b.relevance_score),
            },
            "threats_a": [t.threat_type.value for t in val_a.threats],
            "threats_b": [t.threat_type.value for t in val_b.threats],
            "recommendation": "",
        }

        if val_a.quality_score > val_b.quality_score + 0.2:
            comparison["recommendation"] = "Evidence A is substantially stronger"
        elif val_b.quality_score > val_a.quality_score + 0.2:
            comparison["recommendation"] = "Evidence B is substantially stronger"
        else:
            comparison["recommendation"] = "Evidence quality is comparable, use both"

        return comparison
