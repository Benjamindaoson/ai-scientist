"""Core package."""

from .models import (
    PhenomenonType,
    ResearchPhenomenon,
    PuzzleType,
    ResearchPuzzle,
    PaperType,
    PaperAnalysis,
    NearestNeighborType,
    NearestNeighborPaper,
    TheoryLevel,
    Theory,
    Construct,
    MechanismType,
    Mechanism,
    AlternativeExplanation,
    QuestionClarity,
    QuestionFeasibility,
    ResearchQuestion,
    MethodType,
    ResearchMethod,
    DataSource,
    Measurement,
    IdentificationStrategy,
    StateSnapshot,
    ContractVersion,
)

from .gateway import (
    BaseGateway,
    ClaudeGateway,
    ClaudeRelayGateway,
    MockGateway,
    ModelResponse,
    create_gateway,
)

__all__ = [
    # Phenomenon & Puzzle
    "PhenomenonType",
    "ResearchPhenomenon",
    "PuzzleType",
    "ResearchPuzzle",
    # Paper & Analysis
    "PaperType",
    "PaperAnalysis",
    "NearestNeighborType",
    "NearestNeighborPaper",
    # Theory, Construct, Mechanism
    "TheoryLevel",
    "Theory",
    "Construct",
    "MechanismType",
    "Mechanism",
    "AlternativeExplanation",
    # Research Question
    "QuestionClarity",
    "QuestionFeasibility",
    "ResearchQuestion",
    # Method, Data, Measurement
    "MethodType",
    "ResearchMethod",
    "DataSource",
    "Measurement",
    "IdentificationStrategy",
    # State & Contract
    "StateSnapshot",
    "ContractVersion",
    # Gateway
    "BaseGateway",
    "ClaudeGateway",
    "ClaudeRelayGateway",
    "MockGateway",
    "ModelResponse",
    "create_gateway",
]
