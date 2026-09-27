from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential


@dataclass(frozen=True)
class StructuredSourceAdapter:
    name: str
    base_url: str

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
    def fetch_json(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        response = httpx.get(f"{self.base_url.rstrip('/')}/{path.lstrip('/')}", params=params, timeout=30, follow_redirects=True)
        response.raise_for_status()
        return response.json()


SOURCE_ADAPTERS = {
    "openreview": StructuredSourceAdapter("openreview", "https://api2.openreview.net"),
    "pmlr": StructuredSourceAdapter("pmlr", "https://proceedings.mlr.press"),
    "cvf": StructuredSourceAdapter("cvf", "https://openaccess.thecvf.com"),
    "acl": StructuredSourceAdapter("acl", "https://aclanthology.org"),
    "neurips": StructuredSourceAdapter("neurips", "https://proceedings.neurips.cc"),
    "crossref": StructuredSourceAdapter("crossref", "https://api.crossref.org"),
    "openalex": StructuredSourceAdapter("openalex", "https://api.openalex.org"),
    "semantic_scholar": StructuredSourceAdapter("semantic_scholar", "https://api.semanticscholar.org/graph/v1"),
}
