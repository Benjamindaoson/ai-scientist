from __future__ import annotations

import uuid

from . import models
from .repository import LiteratureRepository


ALLOWED_CLAIM_TYPES = {"research_question", "assumption", "contribution", "finding", "mechanism", "limitation", "negative_result"}


def add_lazy_claim(repository: LiteratureRepository, paper_version_id: str, source_chunk_id: str, claim_type: str, claim_text: str) -> dict:
    if claim_type not in ALLOWED_CLAIM_TYPES:
        raise ValueError(f"unsupported paper claim type: {claim_type}")
    return repository.insert(
        models.paper_claims, paper_claim_id=str(uuid.uuid4()), paper_version_id=paper_version_id,
        source_chunk_id=source_chunk_id, claim_type=claim_type, claim_text=claim_text, review_status="unverified",
    )
