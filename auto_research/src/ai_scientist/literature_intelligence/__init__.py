from .db import initialize_literature_database
from .embeddings import BGEEmbeddingProvider, HashingEmbeddingProvider
from .repository import LiteratureRepository
from .search import HybridSearch, NoveltyService
from .service import CORE_VENUES, CORE_YEARS, LiteratureService
from .sources import SOURCE_ADAPTERS

__all__ = [
    "BGEEmbeddingProvider", "CORE_VENUES", "CORE_YEARS", "HashingEmbeddingProvider", "HybridSearch",
    "LiteratureRepository", "LiteratureService", "NoveltyService", "SOURCE_ADAPTERS", "initialize_literature_database",
]
