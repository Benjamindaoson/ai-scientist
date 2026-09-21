"""Core models package."""

from .domain import (
    # Phenomenon & Puzzle
    PhenomenonType,
    ResearchPhenomenon,
    PuzzleType,
    ResearchPuzzle,
    # Paper & Analysis
    PaperType,
    PaperAnalysis,
    NearestNeighborType,
    NearestNeighborPaper,
    # Theory, Construct, Mechanism
    TheoryLevel,
    Theory,
    Construct,
    MechanismType,
    Mechanism,
    AlternativeExplanation,
    # Research Question
    QuestionClarity,
    QuestionFeasibility,
    ResearchQuestion,
    # Method, Data, Measurement
    MethodType,
    ResearchMethod,
    DataSource,
    Measurement,
    IdentificationStrategy,
    # State & Contract
    StateSnapshot,
    ContractVersion,
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
]
