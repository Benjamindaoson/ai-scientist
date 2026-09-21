"""Literature package.

Provides literature search, paper reading, and evidence validation.
"""

from .search import LiteratureSearch, SearchQuery, SearchResult, SearchSource
from .reader import PaperReader, PaperContent, ExtractedInsight
from .validator import (
    EvidenceValidator,
    EvidenceItem,
    EvidenceType,
    EvidenceQuality,
    EvidenceValidationResult,
    ValidityThreat,
)

__all__ = [
    # Search
    "LiteratureSearch",
    "SearchQuery",
    "SearchResult",
    "SearchSource",
    # Reader
    "PaperReader",
    "PaperContent",
    "ExtractedInsight",
    # Validator
    "EvidenceValidator",
    "EvidenceItem",
    "EvidenceType",
    "EvidenceQuality",
    "EvidenceValidationResult",
    "ValidityThreat",
]
