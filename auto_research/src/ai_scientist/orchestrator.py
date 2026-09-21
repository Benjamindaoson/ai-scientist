"""AI Scientist Main Orchestrator.

Coordinates all components for end-to-end research automation.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from ai_scientist.core.gateway import BaseGateway, create_gateway, MockGateway
from ai_scientist.core.models.domain import (
    ResearchPhenomenon, ResearchPuzzle, ResearchQuestion,
    PhenomenonType, PuzzleType, QuestionClarity, QuestionFeasibility,
)
from ai_scientist.db.repository import Database, Repository
from ai_scientist.engine.multi_agent_debate import MultiAgentDebateSystem, AgentRole
from ai_scientist.engine.objection_ledger import ObjectionLedger
from ai_scientist.engine.final_research_court import FinalResearchCourt
from ai_scientist.engine.theory_engine import TheoryEngine, TheoryComponentType
from ai_scientist.literature.search import LiteratureSearch, SearchQuery, SearchSource
from ai_scientist.literature.reader import PaperReader, PaperContent
from ai_scientist.literature.validator import EvidenceValidator, EvidenceItem, EvidenceType
from ai_scientist.autonomous_loop import AutonomousResearchLoop
from ai_scientist.experiment import ExperimentSpec
from ai_scientist.hypothesis import Hypothesis
from ai_scientist.research_state import ResearchState
from ai_scientist.review_loop import ReviewIssue


@dataclass
class ResearchSession:
    """A research session tracking all activities."""
    session_id: str
    project_id: str
    seed_question: str
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    stages_completed: list[str] = field(default_factory=list)
    current_stage: str = "initialized"
    artifacts: dict = field(default_factory=dict)


class AIScientist:
    """Main orchestrator for AI-driven scientific research.

    Coordinates:
    - Literature search and paper analysis
    - Research phenomenon identification
    - Puzzle formulation
    - Multi-agent debate for direction evaluation
    - Theory development
    - Research question generation
    """

    def __init__(
        self,
        db_path: str | Path = "ai_scientist.db",
        gateway: BaseGateway | None = None,
        max_literature_results: int = 20,
    ):
        """Initialize AI Scientist.

        Args:
            db_path: Path to SQLite database
            gateway: LLM gateway (auto-created if not provided)
            max_literature_results: Max papers to fetch per search
        """
        self.db_path = db_path
        self.gateway = gateway or create_gateway()

        # Initialize database
        self.db = Database(db_path)
        self.db.init_schema()
        self.repo = Repository(self.db)

        # Initialize components
        self.literature_search = LiteratureSearch(gateway=self.gateway)
        self.paper_reader = PaperReader(gateway=self.gateway)
        self.evidence_validator = EvidenceValidator()
        self.objection_ledger = ObjectionLedger(self.repo)
        self.research_court = FinalResearchCourt(self.objection_ledger)
        self.debate_system = MultiAgentDebateSystem(
            db=self.repo,
            gateway=self.gateway,
            objection_ledger=self.objection_ledger,
            research_court=self.research_court,
        )
        self.theory_engine = TheoryEngine(gateway=self.gateway)
        self.autonomous_loop = AutonomousResearchLoop(gateway=self.gateway)

        self.max_literature_results = max_literature_results
        self.current_session: ResearchSession | None = None

    async def start_research(
        self,
        seed_question: str,
        project_name: str = "AI Research Project",
        domain: str = "AI",
    ) -> ResearchSession:
        """Start a new research session.

        Args:
            seed_question: Initial research question or observation
            project_name: Name of the research project
            domain: Research domain

        Returns:
            ResearchSession with initial state
        """
        # Create project
        project = self.repo.create_project(
            name=project_name,
            seed_question=seed_question,
            domain=domain,
        )

        # Create session
        import uuid
        session = ResearchSession(
            session_id=f"session_{uuid.uuid4().hex[:8]}",
            project_id=project["id"],
            seed_question=seed_question,
        )
        self.current_session = session

        # Log event
        self.repo.create_event(
            project_id=project["id"],
            event_type="RESEARCH_SESSION_STARTED",
            content=f"Started research on: {seed_question}",
            metadata={"session_id": session.session_id},
        )

        return session

    async def search_literature(
        self,
        query: str,
        max_results: int | None = None,
    ) -> list[PaperContent]:
        """Search for relevant literature.

        Args:
            query: Search query
            max_results: Maximum number of results

        Returns:
            List of paper contents
        """
        max_results = max_results or self.max_literature_results

        search_query = SearchQuery(
            query_text=query,
            sources=[SearchSource.ARXIV],
            max_results=max_results,
        )

        results = await self.literature_search.search(search_query)

        # Load paper contents
        papers = []
        for result in results[:max_results]:
            paper = await self.paper_reader.read_paper(
                result.arxiv_id,
                project_id=self.current_session.project_id if self.current_session else "",
                fetch_full_text=False,
            )
            if paper:
                papers.append(paper)

        return papers

    async def identify_phenomenon(
        self,
        observation: str,
        domain: str = "AI",
    ) -> ResearchPhenomenon:
        """Identify a research phenomenon from observation.

        Args:
            observation: Raw observation or statement
            domain: Domain field

        Returns:
            Identified ResearchPhenomenon
        """
        phenomenon_id = self.repo.create_phenomenon(
            project_id=self.current_session.project_id,
            raw_description=observation,
            phenomenon_type="OBSERVATIONAL",
            domain=domain,
            scope="micro",
        )

        return ResearchPhenomenon(
            id=phenomenon_id["id"],
            project_id=self.current_session.project_id,
            raw_description=observation,
            phenomenon_type=PhenomenonType.OBSERVATIONAL,
            domain=domain,
            scope="micro",
            key_entities=[],
            key_behaviors=[],
            boundary_conditions=[],
        )

    async def formulate_puzzle(
        self,
        phenomenon: ResearchPhenomenon,
        puzzle_type: PuzzleType = PuzzleType.MECHANISTIC,
    ) -> ResearchPuzzle:
        """Formulate a research puzzle from a phenomenon.

        Args:
            phenomenon: The observed phenomenon
            puzzle_type: Type of puzzle

        Returns:
            Formulated ResearchPuzzle
        """
        # Default puzzle type if not specified
        from ai_scientist.core.models.domain import PuzzleType
        effective_puzzle_type = puzzle_type or PuzzleType.MECHANISTIC

        puzzle_id = self.repo.create_puzzle(
            phenomenon_id=phenomenon.id,
            project_id=self.current_session.project_id,
            puzzle_statement=f"Why does this happen: {phenomenon.raw_description}",
            puzzle_type=effective_puzzle_type.value,
            why_important="Understanding this is crucial for advancing the field",
        )

        return ResearchPuzzle(
            id=puzzle_id["id"],
            phenomenon_id=phenomenon.id,
            project_id=self.current_session.project_id,
            puzzle_type=effective_puzzle_type,
            puzzle_statement=f"Why does this happen: {phenomenon.raw_description}",
            why_important="Understanding this is crucial for advancing the field",
            current_explanations=[],
            gaps_in_explanations=[],
            difficulty="MEDIUM",
            tractability="MEDIUM",
        )

    async def evaluate_direction(
        self,
        direction: dict,
        max_rounds: int = 3,
    ) -> Any:
        """Evaluate a research direction using multi-agent debate.

        Args:
            direction: Research direction dictionary
            max_rounds: Maximum debate rounds

        Returns:
            DebateResult
        """
        self.debate_system.max_rounds = max_rounds

        # If direction has no valid id, skip database debate creation
        # by temporarily storing the real db reference
        direction_id = direction.get("id", "")
        if direction_id and not self.repo.get_direction(direction_id):
            # Direction ID is fake, create a real one first
            if "title" in direction and "hypothesis" in direction:
                real_direction = self.repo.create_direction(
                    project_id=self.current_session.project_id,
                    title=direction.get("title", "Unnamed Direction"),
                    hypothesis=direction.get("hypothesis", ""),
                )
                direction = dict(direction)
                direction["id"] = real_direction["id"]

        result = await self.debate_system.conduct_debate(
            direction=direction,
            project_id=self.current_session.project_id,
            target_type="RESEARCH_DIRECTION",
            target_id=direction.get("id"),
        )

        return result

    async def develop_theory(
        self,
        theory_name: str,
        core_claim: str,
    ) -> Any:
        """Start developing a theory.

        Args:
            theory_name: Name of the theory
            core_claim: Central claim

        Returns:
            TheoryDraft
        """
        return self.theory_engine.create_theory(theory_name, core_claim)

    async def generate_research_questions(
        self,
        phenomenon: ResearchPhenomenon,
        puzzle: ResearchPuzzle,
    ) -> list[ResearchQuestion]:
        """Generate research questions from phenomenon and puzzle.

        Args:
            phenomenon: The phenomenon
            puzzle: The puzzle

        Returns:
            List of generated research questions
        """
        questions = []

        # Use LLM to generate questions if available
        if self.gateway and not isinstance(self.gateway, MockGateway):
            prompt = f"""Based on this research puzzle:

Puzzle: {puzzle.puzzle_statement}
Phenomenon: {phenomenon.raw_description}

Generate 3 specific, testable research questions that would help resolve this puzzle.
Format each as: [QUESTION] <question text>"""

            try:
                response = self.gateway.generate(prompt)
                for line in response.split("\n"):
                    if "[QUESTION]" in line:
                        question_text = line.split("[QUESTION]")[1].strip()
                        rq_id = self.repo.create_research_question(
                            project_id=self.current_session.project_id,
                            question_text=question_text,
                            direction_id=None,
                        )
                        questions.append(ResearchQuestion(
                            id=rq_id["id"],
                            project_id=self.current_session.project_id,
                            direction_id=None,
                            question_text=question_text,
                            clarity=QuestionClarity.SPECIFIC,
                            is_conditional=False,
                            feasibility=QuestionFeasibility.EMPIRICALLY_TESTABLE,
                            data_availability="NEEDS_ASSESSMENT",
                            method_availability="NEEDS_ASSESSMENT",
                        ))
            except Exception:
                pass

        # Fallback: generate basic question
        if not questions:
            question_text = f"How does {phenomenon.raw_description[:50]}...?"
            rq_id = self.repo.create_research_question(
                project_id=self.current_session.project_id,
                question_text=question_text,
                direction_id=None,  # No direction yet
            )
            questions.append(ResearchQuestion(
                id=rq_id["id"],
                project_id=self.current_session.project_id,
                direction_id=None,
                question_text=question_text,
                clarity=QuestionClarity.SPECIFIC,
                is_conditional=False,
                feasibility=QuestionFeasibility.EMPIRICALLY_TESTABLE,
                data_availability="NEEDS_ASSESSMENT",
                method_availability="NEEDS_ASSESSMENT",
            ))

        return questions

    async def validate_evidence(
        self,
        evidence_content: str,
        evidence_type: EvidenceType = EvidenceType.EMPIRICAL,
    ) -> Any:
        """Validate a piece of evidence.

        Args:
            evidence_content: Content of the evidence
            evidence_type: Type of evidence

        Returns:
            EvidenceValidationResult
        """
        import uuid
        evidence_item = EvidenceItem(
            id=f"ev_{uuid.uuid4().hex[:8]}",
            project_id=self.current_session.project_id if self.current_session else "",
            content=evidence_content,
            evidence_type=evidence_type,
        )
        return await self.evidence_validator.validate_evidence(evidence_item)

    async def run_full_research_pipeline(
        self,
        seed_question: str,
        project_name: str = "Auto-Research Project",
        max_literature: int = 10,
        hypothesis: Hypothesis | None = None,
        experiment_spec: ExperimentSpec | None = None,
        experiment_workspace: str | None = None,
        ablation_components: dict[str, object] | None = None,
        output_dir: str | None = None,
        max_review_rounds: int = 2,
    ) -> dict:
        """Run scientific reasoning and, when executable inputs are available, the full experiment loop."""
        results = {
            "project_name": project_name,
            "seed_question": seed_question,
            "stages": {},
            "errors": [],
        }

        try:
            self.current_stage = "initializing"
            session = await self.start_research(seed_question, project_name)
            results["stages"]["initialization"] = {
                "session_id": session.session_id,
                "project_id": session.project_id,
            }

            self.current_stage = "literature_search"
            papers = await self.search_literature(seed_question, max_literature)
            literature = [
                {
                    "id": p.paper_id,
                    "arxiv_id": p.arxiv_id,
                    "title": p.title,
                    "authors": p.authors,
                }
                for p in papers
            ]
            results["stages"]["literature_search"] = {
                "papers_found": len(papers),
                "sample_titles": [p.title for p in papers[:5]],
            }

            self.current_stage = "phenomenon_identification"
            phenomenon = await self.identify_phenomenon(seed_question)
            results["stages"]["phenomenon"] = {
                "phenomenon_id": phenomenon.id,
                "description": phenomenon.raw_description,
            }

            self.current_stage = "puzzle_formulation"
            puzzle = await self.formulate_puzzle(phenomenon)
            results["stages"]["puzzle"] = {
                "puzzle_id": puzzle.id,
                "statement": puzzle.puzzle_statement,
            }

            self.current_stage = "question_generation"
            questions = await self.generate_research_questions(phenomenon, puzzle)
            results["stages"]["questions"] = {
                "questions": [q.question_text for q in questions],
            }

            self.current_stage = "theory_development"
            theory = await self.develop_theory(
                f"Theory of {project_name}",
                f"Understanding {phenomenon.raw_description[:100]}...",
            )
            results["stages"]["theory"] = {
                "theory_id": theory.theory_id,
                "theory_name": theory.theory_name,
            }

            if hypothesis is None:
                hypothesis = Hypothesis(
                    claim=questions[0].question_text if questions else seed_question,
                    rationale=f"Derived from the research puzzle: {puzzle.puzzle_statement}",
                    predicted_effect="A measurable effect relative to an explicit baseline",
                    falsification_conditions=["No measurable effect under the declared evaluation criteria"],
                )

            self.current_stage = "scientific_debate"
            direction_record = self.repo.create_direction(
                project_id=session.project_id,
                title=f"Direction: {project_name}",
                hypothesis=hypothesis.claim,
            )
            debate = await self.evaluate_direction(
                {
                    "id": direction_record["id"],
                    "title": f"Direction: {project_name}",
                    "hypothesis": hypothesis.claim,
                }
            )
            results["stages"]["scientific_debate"] = debate.to_json_dict()

            if experiment_spec is None and experiment_workspace and self.autonomous_loop.engineer:
                experiment_spec = self.autonomous_loop.engineer.create_spec(
                    hypothesis=hypothesis,
                    objective=f"Empirically test: {hypothesis.claim}",
                    workspace=experiment_workspace,
                )

            if experiment_spec is not None:
                self.current_stage = "autonomous_experiment_loop"
                program = self.run_autonomous_research_program(
                    hypothesis=hypothesis,
                    experiment_spec=experiment_spec,
                    ablation_components=ablation_components,
                    unresolved_objections=self.objection_ledger.get_open_objections(),
                    max_review_rounds=max_review_rounds,
                    literature=literature,
                    output_dir=output_dir,
                )
                results["stages"]["autonomous_research"] = program
            else:
                results["stages"]["autonomous_research"] = {
                    "status": "READY_FOR_EXPERIMENT",
                    "reason": "Provide experiment_spec or a workspace with a real LLM gateway for code generation.",
                    "hypothesis": hypothesis.to_dict(),
                }

            self.current_stage = "completed"
            self.current_session.current_stage = "completed"
            self.current_session.completed_at = datetime.utcnow()
            results["success"] = True

        except Exception as e:
            results["success"] = False
            results["errors"].append(str(e))
            self.current_stage = "failed"
            if self.current_session:
                self.current_session.current_stage = "failed"

        return results

    def run_experiment_research_cycle(
        self,
        hypothesis: Hypothesis,
        experiment_spec: ExperimentSpec,
        unresolved_objections: list[dict] | None = None,
        ablation_components: dict[str, object] | None = None,
        review_issues: list[ReviewIssue] | None = None,
    ) -> dict:
        """Run one executable scientific cycle using the current research session."""
        if not self.current_session:
            raise RuntimeError("start_research() must be called before running an experiment cycle")

        state = ResearchState(
            project_id=self.current_session.project_id,
            problem=self.current_session.seed_question,
        )
        cycle = self.autonomous_loop.run_experiment_cycle(
            state=state,
            hypothesis=hypothesis,
            spec=experiment_spec,
            unresolved_objections=unresolved_objections or [],
        )

        if ablation_components:
            cycle["ablation_executions"] = self.autonomous_loop.execute_ablations(
                state, hypothesis, experiment_spec, ablation_components
            )

        if review_issues:
            cycle["review_actions"] = self.autonomous_loop.process_review(state, review_issues)

        cycle["research_state"] = self.autonomous_loop.research_package(state)
        return cycle

    def run_autonomous_research_program(
        self,
        hypothesis: Hypothesis,
        experiment_spec: ExperimentSpec,
        ablation_components: dict[str, object] | None = None,
        unresolved_objections: list[dict] | None = None,
        max_review_rounds: int = 2,
        literature: list[dict] | None = None,
        output_dir: str | None = None,
    ) -> dict:
        """Run hypothesis -> experiment -> evidence -> ablation -> review -> rebuttal -> meta-review."""
        if not self.current_session:
            raise RuntimeError("start_research() must be called before running an autonomous program")

        state = ResearchState(
            project_id=self.current_session.project_id,
            problem=self.current_session.seed_question,
            literature=literature or [],
            metadata={"title": f"Research Report: {self.current_session.seed_question[:80]}"},
        )
        return self.autonomous_loop.run_program(
            state=state,
            hypothesis=hypothesis,
            spec=experiment_spec,
            components=ablation_components,
            unresolved_objections=unresolved_objections or [],
            max_review_rounds=max_review_rounds,
            output_dir=output_dir,
        )

    def design_and_run_autonomous_research(
        self,
        hypothesis: Hypothesis,
        objective: str,
        workspace: str,
        ablation_components: dict[str, object] | None = None,
        max_review_rounds: int = 2,
        output_dir: str | None = None,
    ) -> dict:
        """Let the experiment engineer generate code/config and run the complete research loop."""
        if not self.current_session:
            raise RuntimeError("start_research() must be called first")
        if not self.autonomous_loop.engineer:
            raise RuntimeError("A real LLM gateway is required for autonomous experiment code generation")

        spec = self.autonomous_loop.engineer.create_spec(
            hypothesis=hypothesis,
            objective=objective,
            workspace=workspace,
        )
        return self.run_autonomous_research_program(
            hypothesis=hypothesis,
            experiment_spec=spec,
            ablation_components=ablation_components,
            max_review_rounds=max_review_rounds,
            output_dir=output_dir,
        )

    def get_session_status(self) -> dict | None:
        """Get current session status."""
        if not self.current_session:
            return None

        return {
            "session_id": self.current_session.session_id,
            "project_id": self.current_session.project_id,
            "seed_question": self.current_session.seed_question,
            "current_stage": self.current_session.current_stage,
            "stages_completed": self.current_session.stages_completed,
        }

    def export_project(self, project_id: str, output_path: str | Path) -> bool:
        """Export project data to JSON.

        Args:
            project_id: Project to export
            output_path: Output file path

        Returns:
            True if successful
        """
        try:
            project = self.repo.get_project(project_id)
            if not project:
                return False

            # Gather all project data
            data = {
                "project": project,
                "papers": self.repo.list_papers(project_id),
                "directions": self.repo.list_directions(project_id),
                "phenomena": self.repo.list_phenomena(project_id),
                "puzzles": self.repo.list_puzzles(project_id),
                "events": self.repo.list_events(project_id),
            }

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

            return True
        except Exception:
            return False
