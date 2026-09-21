"""Multi-agent debate system for research direction evaluation.

This module implements the Scientific Deliberation Protocol where multiple
AI agents with distinct roles debate research directions to:
1. Identify weaknesses and risks
2. Kill (reject) non-viable directions
3. Extract researchable questions from surviving directions

V4 Integration:
- Historical objections loaded from ObjectionLedger before debate
- Red team split into review + discovery phases
- Objections tracked in persistent ledger
- Evidence-based decision support
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..db.repository import Repository
    from .objection_ledger import ObjectionLedger
    from .final_research_court import FinalResearchCourt


class AgentRole(str, Enum):
    PROPONENT = "PROPONENT"  # Defends the research direction
    SKEPTIC = "SKEPTIC"      # Challenges feasibility and validity
    NEUTRAL = "NEUTRAL"      # Provides balanced analysis
    DEVIL_ADVOCATE = "DEVIL_ADVOCATE"  # Tests robustness
    SYNTHESIZER = "SYNTHESIZER"  # Integrates perspectives


class DebateStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    RESEARCHABLE = "RESEARCHABLE"
    NEEDS_REVISION = "NEEDS_REVISION"
    REJECTED = "REJECTED"


class ObjectionSeverity(str, Enum):
    FATAL = "FATAL"  # Should kill the direction
    MAJOR = "MAJOR"   # Needs significant revision
    MINOR = "MINOR"   # Can be addressed


@dataclass
class Argument:
    """A single argument in a debate round."""
    agent_role: AgentRole
    content: str
    supporting_evidence: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Objection:
    """An objection raised against a position or argument."""
    objector_role: AgentRole
    target_role: AgentRole
    objection_text: str
    severity: ObjectionSeverity
    response_required: bool = True
    addressed: bool = False
    response_text: str = ""


@dataclass
class AgentVote:
    """Vote from an agent on whether to continue pursuing a direction."""
    agent_role: AgentRole
    kill_vote: bool  # True = vote to kill/reject direction
    confidence: float  # 0.0 to 1.0
    reasoning: str = ""


@dataclass
class DebateRound:
    """Complete information about one round of debate."""
    round_number: int
    agent_arguments: dict[AgentRole, Argument] = field(default_factory=dict)
    objections: list[Objection] = field(default_factory=list)
    agent_votes: dict[AgentRole, AgentVote] = field(default_factory=dict)
    is_final: bool = False


@dataclass
class DebateResult:
    """Final outcome of a multi-agent debate."""
    debate_id: str
    direction_id: str
    status: DebateStatus
    rounds_completed: int

    # Vote summary
    kill_votes: int
    total_votes: int
    kill_ratio: float

    # Synthesized conclusions
    conclusion: str
    key_objections: list[dict] = field(default_factory=list)
    researchable_questions: list[str] = field(default_factory=list)

    # Detailed round history
    rounds: list[DebateRound] = field(default_factory=list)

    # Recommendations
    recommendations: list[str] = field(default_factory=list)
    required_revisions: list[str] = field(default_factory=list)

    # V4: Additional metadata from ledger/court
    metadata: dict = field(default_factory=dict)

    def to_json_dict(self) -> dict:
        """Export debate result as JSON-serializable dict.

        V4: Includes metadata from ledger and court.
        """
        return {
            "debate_id": self.debate_id,
            "direction_id": self.direction_id,
            "status": self.status.value,
            "rounds_completed": self.rounds_completed,
            "vote_summary": {
                "kill_votes": self.kill_votes,
                "total_votes": self.total_votes,
                "kill_ratio": self.kill_ratio,
            },
            "conclusion": self.conclusion,
            "key_objections": self.key_objections,
            "researchable_questions": self.researchable_questions,
            "recommendations": self.recommendations,
            "required_revisions": self.required_revisions,
            "v4_metadata": self.metadata,
        }


class MultiAgentDebateSystem:
    """Multi-agent debate system for research direction evaluation.

    Implements the Scientific Deliberation Protocol:
    - 5 agents with distinct roles debate research directions
    - Kill votes are collected and consensus determined
    - Surviving directions yield researchable questions

    V4 Integration:
    - Historical objections loaded from ObjectionLedger
    - Red team split into review + discovery phases
    - Objections persist in ledger across debates
    - Supports evidence-based decision making
    """

    def __init__(
        self,
        db=None,
        gateway=None,
        max_rounds: int = 4,
        kill_threshold: float = 0.6,
        objection_ledger: "ObjectionLedger | None" = None,
        research_court: "FinalResearchCourt | None" = None,
    ):
        """Initialize debate system.

        Args:
            db: Database repository for persistence
            gateway: LLM gateway for agent reasoning
            max_rounds: Maximum debate rounds
            kill_threshold: Ratio of kill votes needed to reject (0.0-1.0)
            objection_ledger: Optional ObjectionLedger for persistent tracking
            research_court: Optional FinalResearchCourt for evidence-based decisions
        """
        self.db = db
        self.gateway = gateway
        self.max_rounds = max_rounds
        self.kill_threshold = kill_threshold
        self.ledger = objection_ledger
        self.court = research_court
        self.agents = {}
        self._initialize_agents()

    def _initialize_agents(self) -> None:
        """Initialize agent personas."""
        self.agents = {
            AgentRole.PROPONENT: {
                "name": "Proponent",
                "persona": """You are a passionate research advocate. Your role is to:
1. Identify and articulate the novelty and importance of the research direction
2. Find supporting evidence and theoretical grounding
3. Address objections constructively
4. Refine the direction to make it more viable
5. Extract specific, testable research questions from the direction

Be enthusiastic but intellectually honest. You want this research to succeed,
but you must also ensure it can withstand scrutiny.""",
                "focus_questions": [
                    "What is the novel contribution of this research?",
                    "What evidence supports this direction?",
                    "What are the strongest theoretical foundations?",
                    "What specific questions can we answer with this approach?",
                ],
            },
            AgentRole.SKEPTIC: {
                "name": "Skeptic",
                "persona": """You are a rigorous skeptic. Your role is to:
1. Challenge the feasibility of the proposed research
2. Identify methodological weaknesses
3. Question the validity of expected findings
4. Find alternative explanations that might subsume this work
5. Determine if this direction is worth pursuing at all

Be constructive but merciless. Find the fatal flaws. A good critique saves
months of wasted effort.""",
                "focus_questions": [
                    "Is this research actually feasible given current methods?",
                    "What are the most likely failure modes?",
                    "Are there confounds or alternative explanations?",
                    "What evidence would definitively refute this hypothesis?",
                ],
            },
            AgentRole.NEUTRAL: {
                "name": "Neutral Analyst",
                "persona": """You are a balanced analyst. Your role is to:
1. Provide objective assessment of strengths and weaknesses
2. Evaluate novelty relative to existing literature
3. Assess the potential impact if successful
4. Identify what would make this research impactful
5. Consider ethical implications and broader context

Be fair and thorough. Your job is to see both sides clearly.""",
                "focus_questions": [
                    "How does this compare to existing work in the field?",
                    "What would successful completion of this research achieve?",
                    "Are there any ethical concerns with this research?",
                    "What is the risk/reward ratio?",
                ],
            },
            AgentRole.DEVIL_ADVOCATE: {
                "name": "Devil's Advocate",
                "persona": """You are a devil's advocate who tests the robustness of arguments.
Your role is to:
1. Assume the worst-case scenario and explore it
2. Find edge cases and boundary condition failures
3. Question the assumptions underlying the research
4. Challenge whether the framing is correct
5. Test if the research question is well-posed

Be adversarial but intellectually useful. Your job is to break weak arguments
so strong ones can emerge.""",
                "focus_questions": [
                    "What happens at the boundaries of this theory?",
                    "What assumptions are we making that might be wrong?",
                    "Is the research question correctly framed?",
                    "What would make this entire research program fail?",
                ],
            },
            AgentRole.SYNTHESIZER: {
                "name": "Synthesizer",
                "persona": """You are an integrator who weaves together diverse perspectives.
Your role is to:
1. Identify areas of agreement among agents
2. Find common ground between opposing views
3. Extract actionable insights from debate
4. Formulate specific research questions
5. Suggest how to address major objections

Be integrative and constructive. Your job is to create synthesis, not
to take sides. Transform conflict into clarity.""",
                "focus_questions": [
                    "What do all agents agree on?",
                    "What are the non-negotiable requirements for this research?",
                    "What specific questions emerged from the debate?",
                    "How can we address the major objections?",
                ],
            },
        }

    def _get_agent_prompt(
        self,
        role: AgentRole,
        direction: dict,
        context: dict | None = None,
        round_number: int = 1,
        historical_objections: list[dict] | None = None,
        target_type: str = "RESEARCH_DIRECTION",
        target_id: str = "",
    ) -> str:
        """Generate agent-specific prompt for a debate round.

        Args:
            role: Agent role
            direction: Research direction dict
            context: Previous debate context
            round_number: Current round number
            historical_objections: Objections from previous runs (V4)
            target_type: Type of target being debated
            target_id: ID of target being debated
        """
        agent = self.agents[role]
        direction_title = direction.get("title", "")
        direction_hypothesis = direction.get("hypothesis", "")
        direction_novelty = direction.get("novelty", "")
        direction_feasibility = direction.get("feasibility", 0.5)
        direction_importance = direction.get("importance", 0.5)

        # Build context from previous rounds
        context_str = ""
        if context:
            context_str = "\n\nPrevious debate context:\n"
            for key, value in context.items():
                context_str += f"- {key}: {value}\n"

        # V4: Include historical objections for review
        historical_obj_str = ""
        if historical_objections:
            historical_obj_str = "\n\n## Historical Objections (from previous runs - MUST REVIEW)\n"
            historical_obj_str += "These objections were raised in previous debates. You MUST:\n"
            historical_obj_str += "1. Review each objection\n"
            historical_obj_str += "2. Determine if it has been adequately addressed\n"
            historical_obj_str += "3. Re-raise it if it remains unresolved\n\n"

            for obj in historical_objections:
                status = obj.get("status", "OPEN")
                severity = obj.get("severity", "MAJOR")
                title = obj.get("title", "Unknown")
                argument = obj.get("argument", "")
                resolution = obj.get("resolution_reason", "")

                historical_obj_str += f"### [{severity}] {title}\n"
                historical_obj_str += f"- Status: {status}\n"
                historical_obj_str += f"- Argument: {argument}\n"
                if resolution:
                    historical_obj_str += f"- Resolution: {resolution}\n"
                historical_obj_str += "\n"

            historical_obj_str += "**Important**: If any OPEN FATAL objections exist, the research direction cannot proceed until they are addressed.\n"

        # V4: Add target info for objection tracking
        target_info = ""
        if target_id:
            target_info = f"\n**Debate Target**: {target_type}: {target_id}\n"

        prompt = f"""# Debate Round {round_number}
{target_info}
## Research Direction Under Discussion
- **Title**: {direction_title}
- **Hypothesis**: {direction_hypothesis}
- **Novelty Claim**: {direction_novelty}
- **Feasibility Score**: {direction_feasibility:.1f}/1.0
- **Importance Score**: {direction_importance:.1f}/1.0

{context_str}
{historical_obj_str}
## Your Role: {agent['name']}
{agent['persona']}

## Your Focus Questions
{chr(10).join(f"- {q}" for q in agent['focus_questions'])}

## Your Task
Analyze this research direction from your perspective. Provide:
1. Your position (argument, assessment, or critique)
2. Any objections to other perspectives (including historical objections)
3. Your vote: should this direction be KILLED (reject) or PURSUED (continue)?

**V4 Requirements**:
- If reviewing historical objections, explicitly state whether each has been addressed
- For unresolved FATAL objections, vote KILL with high confidence
- Cite evidence when possible to support your position

Be specific, cite evidence where possible, and justify your reasoning.

Format your response as:
```
POSITION: [Your main argument]
HISTORICAL_OBJECTION_REVIEW: [For each historical objection: ADDRESSED/NOT_ADDRESSED with reasoning]
OBJECTIONS: [Any new objections to other views, or "None"]
VOTE: KILL / PURSUE
CONFIDENCE: [0.0-1.0]
```
"""
        return prompt

    def _parse_agent_response(
        self, response: str
    ) -> tuple[str, list[str], str, float]:
        """Parse agent response into components."""
        lines = response.strip().split("\n")

        position = ""
        objections = []
        vote = "PURSUE"
        confidence = 0.5

        for line in lines:
            line = line.strip()
            if line.startswith("POSITION:"):
                position = line.replace("POSITION:", "").strip()
            elif line.startswith("OBJECTIONS:"):
                obj_text = line.replace("OBJECTIONS:", "").strip()
                if obj_text.lower() != "none":
                    objections = [o.strip() for o in obj_text.split(";") if o.strip()]
            elif line.startswith("VOTE:"):
                vote_str = line.replace("VOTE:", "").strip().upper()
                vote = "KILL" if "KILL" in vote_str else "PURSUE"
            elif line.startswith("CONFIDENCE:"):
                try:
                    confidence = float(line.replace("CONFIDENCE:", "").strip())
                    confidence = max(0.0, min(1.0, confidence))
                except ValueError:
                    confidence = 0.5

        return position, objections, vote, confidence

    def _call_agent(
        self,
        role: AgentRole,
        prompt: str,
    ) -> str:
        """Call LLM for agent reasoning."""
        if self.gateway:
            return self.gateway.generate(prompt)

        # Fallback: Generate response with role-based heuristics
        return self._generate_mock_response(role, prompt)

    def _generate_mock_response(self, role: AgentRole, prompt: str) -> str:
        """Generate a mock response for testing without LLM."""
        direction = "this research direction"

        if role == AgentRole.PROPONENT:
            return f"""POSITION: This research direction addresses a critical gap in the literature.
The proposed approach is novel and has strong theoretical grounding. Preliminary evidence
suggests the hypothesis is testable with current methods.

OBJECTIONS: The skeptic raises valid concerns about feasibility, but these can be addressed
through careful experimental design.

VOTE: PURSUE
CONFIDENCE: 0.75"""

        elif role == AgentRole.SKEPTIC:
            return f"""POSITION: While the research question is interesting, there are significant
methodological concerns. The proposed methods may not adequately control for confounds,
and alternative explanations are not sufficiently addressed.

OBJECTIONS: The proponent's optimism about feasibility may be premature.

VOTE: PURSUE (with revisions)
CONFIDENCE: 0.60"""

        elif role == AgentRole.NEUTRAL:
            return f"""POSITION: The research direction has moderate novelty and potential impact.
Feasibility is acceptable but not guaranteed. The risk/reward ratio is favorable
conditional on addressing methodological concerns.

OBJECTIONS: Need more detail on identification strategy.

VOTE: PURSUE
CONFIDENCE: 0.65"""

        elif role == AgentRole.DEVIL_ADVOCATE:
            return f"""POSITION: Testing the boundary conditions reveals potential failure modes.
What happens if the core assumption is violated? The research question may need
reframing to be more precise.

OBJECTIONS: The proponent assumes too much without sufficient justification.

VOTE: PURSUE (needs reframing)
CONFIDENCE: 0.55"""

        else:  # SYNTHESIZER
            return f"""POSITION: Synthesis of all perspectives shows general agreement that
this direction is worth pursuing, with several key objections that must be addressed.
The research questions can be refined based on the debate.

OBJECTIONS: None that haven't been addressed.

VOTE: PURSUE
CONFIDENCE: 0.70"""

    async def conduct_debate(
        self,
        direction: dict,
        project_id: str,
        debate_id: str | None = None,
        target_type: str = "RESEARCH_DIRECTION",
        target_id: str = "",
    ) -> DebateResult:
        """Conduct a multi-agent debate on a research direction.

        V4 Features:
        - Loads historical objections from ObjectionLedger
        - Reviews historical objections with red team
        - Adds new objections to ledger
        - Integrates with FinalResearchCourt for evidence-based decisions

        Args:
            direction: Research direction dictionary
            project_id: Project ID for logging
            debate_id: Optional existing debate ID to continue
            target_type: Type of target being debated
            target_id: ID of target being debated

        Returns:
            DebateResult with outcome and extracted questions
        """
        # V4: Load historical objections from ledger
        historical_objections = []
        if self.ledger:
            self.ledger.load_project(project_id, current_run=0)  # Load all
            historical_objections = self.ledger.get_open_objections()

            # Filter to relevant objections
            if target_id:
                relevant = [
                    o for o in historical_objections
                    if o.get("target_id") == target_id
                ]
                if relevant:
                    historical_objections = relevant

        # Create debate record first if we have a database
        if self.db and debate_id is None:
            direction_id = direction.get("id")  # None if not present
            debate_record = self.db.create_debate(
                project_id=project_id,
                direction_id=direction_id,
                max_rounds=self.max_rounds,
                kill_threshold=self.kill_threshold,
            )
            debate_id = debate_record["id"]
        elif debate_id is None:
            debate_id = f"debate_{uuid.uuid4().hex[:8]}"

        rounds_completed = 0
        all_rounds: list[DebateRound] = []
        all_votes: list[AgentVote] = []
        all_objections_from_debate: list[dict] = []  # V4: Track objections

        # Collect context from previous debate rounds if continuing
        context = {}
        if self.db:
            prev_rounds = self.db.list_debate_rounds(debate_id)
            if prev_rounds:
                context["previous_rounds"] = f"{len(prev_rounds)} rounds already completed"

        # V4: Add historical objection context
        if historical_objections:
            fatal_count = len([o for o in historical_objections if o.get("severity") == "FATAL"])
            context["historical_objections"] = f"{len(historical_objections)} open objections ({fatal_count} FATAL)"

        # Conduct debate rounds
        for round_num in range(1, self.max_rounds + 1):
            round_obj = DebateRound(round_number=round_num)
            round_context = dict(context)
            round_context["current_round"] = round_num

            # Each agent provides their perspective
            for role in AgentRole:
                prompt = self._get_agent_prompt(
                    role, direction, round_context, round_num,
                    historical_objections=historical_objections if round_num == 1 else None,
                    target_type=target_type,
                    target_id=target_id,
                )
                response = await self._call_agent_async(role, prompt)

                position, objections, vote, confidence = self._parse_agent_response(response)

                # Create argument
                argument = Argument(
                    agent_role=role,
                    content=position,
                )
                round_obj.agent_arguments[role] = argument

                # Create vote
                agent_vote = AgentVote(
                    agent_role=role,
                    kill_vote=(vote == "KILL"),
                    confidence=confidence,
                    reasoning=position,
                )
                round_obj.agent_votes[role] = agent_vote
                all_votes.append(agent_vote)

                # Create objections from agent responses
                for obj_text in objections:
                    severity = ObjectionSeverity.FATAL if "fatal" in obj_text.lower() else \
                               ObjectionSeverity.MAJOR if "major" in obj_text.lower() else \
                               ObjectionSeverity.MINOR
                    round_obj.objections.append(Objection(
                        objector_role=role,
                        target_role=AgentRole.PROPONENT,  # Usually target proponent
                        objection_text=obj_text,
                        severity=severity,
                    ))

                    # V4: Add to ledger if we have one
                    if self.ledger and target_id:
                        obj_data = {
                            "title": f"Objection from {role.value}",
                            "argument": obj_text,
                            "severity": severity.value,
                            "target_type": target_type,
                            "target_id": target_id,
                        }
                        new_obj = self.ledger.add_objection(**obj_data)
                        all_objections_from_debate.append(new_obj)

            # Check for early termination (unanimous kill or pursue)
            kill_votes = sum(1 for v in round_obj.agent_votes.values() if v.kill_vote)
            total_votes = len(round_obj.agent_votes)

            if kill_votes == total_votes:  # Unanimous kill
                round_obj.is_final = True
                all_rounds.append(round_obj)
                rounds_completed = round_num
                break

            # Check if we should continue
            if round_num < self.max_rounds:
                all_rounds.append(round_obj)
                rounds_completed = round_num

                # Update context for next round
                context[f"round_{round_num}"] = {
                    "kill_ratio": kill_votes / total_votes,
                    "positions": {
                        r.value: a.content[:100] for r, a in round_obj.agent_arguments.items()
                    }
                }
            else:
                round_obj.is_final = True
                all_rounds.append(round_obj)
                rounds_completed = round_num

        # Calculate final vote tally
        kill_count = sum(1 for v in all_votes if v.kill_vote)
        total_count = len(all_votes)
        kill_ratio = kill_count / total_count if total_count > 0 else 0

        # V4: Use FinalResearchCourt for evidence-based decision
        if self.court and self.ledger:
            # Get updated objection status from ledger
            court_result = self.court.make_decision_from_ledger(
                kill_ratio=kill_ratio,
                debate_status=status.value if status else None,
            )

            # Update status based on court decision
            final_decision = court_result.decision
            if final_decision.value == "KILL":
                status = DebateStatus.REJECTED
                conclusion = f"Direction rejected by FinalResearchCourt: {final_decision.value}"
            elif final_decision.value == "REVISE":
                status = DebateStatus.NEEDS_REVISION
                conclusion = f"Direction needs revision: {final_decision.value}"
            else:
                conclusion = court_result.to_dict().get("reasons", [{}])[0].get("text", "")

            # Store court decision in result metadata
            court_decision = court_result
        else:
            # V1-style decision based on kill ratio
            if kill_ratio >= self.kill_threshold:
                status = DebateStatus.REJECTED
                conclusion = f"Direction rejected with {kill_ratio:.1%} kill vote (threshold: {self.kill_threshold:.1%})"
            else:
                status = DebateStatus.RESEARCHABLE
                conclusion = f"Direction accepted with {kill_ratio:.1%} kill vote (threshold: {self.kill_threshold:.1%})"
            court_decision = None

        # Extract researchable questions
        questions = self._extract_research_questions(all_rounds, direction)

        # Build result
        result = DebateResult(
            debate_id=debate_id,
            direction_id=direction.get("id", ""),
            status=status,
            rounds_completed=rounds_completed,
            kill_votes=kill_count,
            total_votes=total_count,
            kill_ratio=kill_ratio,
            conclusion=conclusion,
            key_objections=[
                {
                    "text": o.objection_text,
                    "severity": o.severity.value,
                    "objector": o.objector_role.value,
                }
                for o in all_rounds[-1].objections if o.severity == ObjectionSeverity.FATAL
            ] if all_rounds else [],
            researchable_questions=questions,
            rounds=all_rounds,
            recommendations=self._generate_recommendations(all_rounds, status),
            required_revisions=[
                o.objection_text
                for o in (all_rounds[-1].objections if all_rounds else [])
                if o.severity in (ObjectionSeverity.FATAL, ObjectionSeverity.MAJOR)
            ],
        )

        # V4: Add objection ledger info to result
        if self.ledger:
            result.metadata = {
                "court_decision": court_decision.to_dict() if court_decision else None,
                "ledger_summary": self.ledger.get_summary().to_dict(),
                "objections_added": len(all_objections_from_debate),
                "historical_objections_reviewed": len(historical_objections),
            }

        # Persist to database
        if self.db:
            await self._persist_debate(result, project_id)

        return result

    async def _call_agent_async(
        self,
        role: AgentRole,
        prompt: str,
    ) -> str:
        """Async wrapper for agent calls."""
        return self._call_agent(role, prompt)

    def _extract_research_questions(
        self,
        rounds: list[DebateRound],
        direction: dict,
    ) -> list[str]:
        """Extract researchable questions from debate."""
        questions = []

        # Extract from synthesizer's final position if available
        if rounds and AgentRole.SYNTHESIZER in rounds[-1].agent_arguments:
            syn_position = rounds[-1].agent_arguments[AgentRole.SYNTHESIZER].content
            # Look for question patterns
            for line in syn_position.split("\n"):
                if "?" in line and len(line) > 20:
                    questions.append(line.strip())

        # Extract from proponent's questions
        for round_obj in rounds:
            if AgentRole.PROPONENT in round_obj.agent_arguments:
                prop_position = round_obj.agent_arguments[AgentRole.PROPONENT].content
                for line in prop_position.split("\n"):
                    if "?" in line and len(line) > 20:
                        questions.append(line.strip())

        # Deduplicate and limit
        seen = set()
        unique_questions = []
        for q in questions:
            q_normalized = q.lower().strip()
            if q_normalized not in seen and len(unique_questions) < 5:
                seen.add(q_normalized)
                unique_questions.append(q)

        # If no questions extracted, generate from direction
        if not unique_questions:
            direction_title = direction.get("title", "")
            if direction_title:
                unique_questions.append(
                    f"How can we investigate {direction_title} empirically?"
                )

        return unique_questions

    def _generate_recommendations(
        self,
        rounds: list[DebateRound],
        status: DebateStatus,
    ) -> list[str]:
        """Generate recommendations based on debate."""
        recommendations = []

        if status == DebateStatus.REJECTED:
            recommendations.append("Revise the research direction to address fatal objections")
            recommendations.append("Consider alternative theoretical frameworks")
            recommendations.append("Re-submit for debate after major revisions")
        else:
            recommendations.append("Proceed with research question formulation")
            recommendations.append("Develop detailed methodology addressing objections")
            recommendations.append("Conduct literature survey for nearest neighbors")

        # Add specific recommendations from objections
        fatal_objections = []
        for round_obj in rounds:
            fatal_objections.extend([
                o for o in round_obj.objections
                if o.severity == ObjectionSeverity.FATAL
            ])

        if fatal_objections:
            recommendations.append(
                f"Address {len(fatal_objections)} fatal objections before proceeding"
            )

        return recommendations

    async def _persist_debate(
        self,
        result: DebateResult,
        project_id: str,
    ) -> None:
        """Persist debate results to database."""
        if not self.db:
            return

        # Update debate record
        self.db.update_debate(
            result.debate_id,
            status="COMPLETED",
            final_status=result.status.value,
            conclusion=result.conclusion,
        )

        # Persist rounds
        for round_obj in result.rounds:
            self.db.create_debate_round(
                debate_id=result.debate_id,
                round_number=round_obj.round_number,
                agent_role=list(round_obj.agent_arguments.keys())[0].value if round_obj.agent_arguments else "",
                agent_position=list(round_obj.agent_arguments.values())[0].content[:500] if round_obj.agent_arguments else "",
                arguments=[
                    {"role": a.agent_role.value, "content": a.content}
                    for a in round_obj.agent_arguments.values()
                ],
                objections=[
                    {
                        "text": o.objection_text,
                        "severity": o.severity.value,
                        "objector": o.objector_role.value,
                    }
                    for o in round_obj.objections
                ],
                votes={
                    v.agent_role.value: {"kill": v.kill_vote, "confidence": v.confidence}
                    for v in round_obj.agent_votes.values()
                },
            )

        # Create event
        self.db.create_event(
            project_id=project_id,
            event_type="DEBATE_COMPLETED",
            content=result.conclusion,
            metadata={
                "debate_id": result.debate_id,
                "status": result.status.value,
                "kill_ratio": result.kill_ratio,
                "questions_found": len(result.researchable_questions),
            },
        )
