"""AI Scientist - Autonomous Research System.

A comprehensive system for automated scientific research using multi-agent debate,
literature analysis, and theory development.
"""

from .core.gateway import (
    BaseGateway,
    ClaudeGateway,
    ClaudeRelayGateway,
    MockGateway,
    create_gateway,
)
from .core.models.domain import (
    ResearchPhenomenon,
    ResearchPuzzle,
    ResearchQuestion,
    ResearchMethod,
    Theory,
    Construct,
    Mechanism,
    AlternativeExplanation,
    PhenomenonType,
    PuzzleType,
    MechanismType,
    QuestionClarity,
    QuestionFeasibility,
    MethodType,
    TheoryLevel,
)
from .db.repository import Database, Repository
from .engine.multi_agent_debate import (
    MultiAgentDebateSystem,
    AgentRole,
    DebateStatus,
    DebateResult,
)
from .engine.theory_engine import (
    TheoryEngine,
    TheoryDraft,
    TheoryComponent,
    TheoryComponentType,
    TheoryEvaluation,
)
from .literature.search import (
    LiteratureSearch,
    SearchQuery,
    SearchResult,
    SearchSource,
)
from .literature.reader import (
    PaperReader,
    PaperContent,
    ExtractedInsight,
)
from .literature.validator import (
    EvidenceValidator,
    EvidenceItem,
    EvidenceType,
    EvidenceQuality,
)
from .orchestrator import AIScientist, ResearchSession
from .research_state import ResearchState
from .hypothesis import Hypothesis, HypothesisEvolver
from .experiment import ExperimentSpec, ExperimentResult, ExperimentRunner, ExperimentEvaluator
from .autonomous_loop import AutonomousResearchLoop
from .ablation import AblationPlan, AblationPlanner
from .review_loop import ReviewIssue, ReviewActionRouter

__version__ = "0.1.0"

__all__ = [
    # Gateway
    "BaseGateway",
    "ClaudeGateway",
    "ClaudeRelayGateway",
    "MockGateway",
    "create_gateway",
    # Domain Models
    "ResearchPhenomenon",
    "ResearchPuzzle",
    "ResearchQuestion",
    "ResearchMethod",
    "Theory",
    "Construct",
    "Mechanism",
    "AlternativeExplanation",
    "PhenomenonType",
    "PuzzleType",
    "MechanismType",
    "QuestionClarity",
    "QuestionFeasibility",
    "MethodType",
    "TheoryLevel",
    # Database
    "Database",
    "Repository",
    # Debate
    "MultiAgentDebateSystem",
    "AgentRole",
    "DebateStatus",
    "DebateResult",
    # Theory
    "TheoryEngine",
    "TheoryDraft",
    "TheoryComponent",
    "TheoryComponentType",
    "TheoryEvaluation",
    # Literature
    "LiteratureSearch",
    "SearchQuery",
    "SearchResult",
    "SearchSource",
    "PaperReader",
    "PaperContent",
    "ExtractedInsight",
    "EvidenceValidator",
    "EvidenceItem",
    "EvidenceType",
    "EvidenceQuality",
    # Orchestrator
    "AIScientist",
    "ResearchSession",
    "ResearchState",
    "Hypothesis",
    "HypothesisEvolver",
    "ExperimentSpec",
    "ExperimentResult",
    "ExperimentRunner",
    "ExperimentEvaluator",
    "AutonomousResearchLoop",
    "AblationPlan",
    "AblationPlanner",
    "ReviewIssue",
    "ReviewActionRouter",
]
