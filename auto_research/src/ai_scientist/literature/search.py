"""Literature search module.

Provides functionality for searching academic literature.
"""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class SearchSource(str, Enum):
    ARXIV = "ARXIV"
    SEMANTIC_SCHOLAR = "SEMANTIC_SCHOLAR"
    GOOGLE_SCHOLAR = "GOOGLE_SCHOLAR"
    CROSSREF = "CROSSREF"


@dataclass
class SearchQuery:
    """A literature search query."""
    query_text: str
    sources: list[SearchSource] = field(default_factory=lambda: [SearchSource.ARXIV])
    max_results: int = 20
    domains: list[str] = field(default_factory=list)  # e.g., ["cs.AI", "cs.LG"]
    year_from: int | None = None
    year_to: int | None = None


@dataclass
class SearchResult:
    """A literature search result."""
    paper_id: str
    title: str
    authors: list[str]
    abstract: str
    source: SearchSource
    url: str
    arxiv_id: str = ""
    published_date: str = ""
    categories: list[str] = field(default_factory=list)
    citation_count: int = 0
    relevance_score: float = 0.0
    matched_terms: list[str] = field(default_factory=list)


class LiteratureSearch:
    """Literature search system.

    Searches multiple academic sources for relevant papers.
    """

    def __init__(self, gateway=None):
        """Initialize literature search.

        Args:
            gateway: LLM gateway for query enhancement
        """
        self.gateway = gateway

    async def search(self, query: SearchQuery) -> list[SearchResult]:
        """Search for relevant literature.

        Args:
            query: Search query specification

        Returns:
            List of search results ranked by relevance
        """
        results: list[SearchResult] = []

        # Enhance query with LLM if available
        enhanced_query = query.query_text
        if self.gateway:
            enhanced_query = await self._enhance_query(query.query_text)

        # Search each source
        for source in query.sources:
            if source == SearchSource.ARXIV:
                source_results = await self._search_arxiv(
                    enhanced_query,
                    query.max_results,
                    query.domains,
                    query.year_from,
                    query.year_to,
                )
                results.extend(source_results)
            elif source == SearchSource.SEMANTIC_SCHOLAR:
                source_results = await self._search_semantic_scholar(
                    enhanced_query,
                    query.max_results,
                )
                results.extend(source_results)

        # Deduplicate by title similarity
        results = self._deduplicate_results(results)

        # Re-rank by relevance
        results.sort(key=lambda x: x.relevance_score, reverse=True)

        return results[: query.max_results]

    async def _enhance_query(self, query: str) -> str:
        """Enhance search query with LLM."""
        if not self.gateway:
            return query

        prompt = f"""Given the research topic: "{query}"

Generate an optimized search query for academic literature search.
Return only the optimized query, nothing else.
Focus on key concepts and their relationships."""

        try:
            response = self.gateway.generate(prompt)
            return response.strip() if response else query
        except Exception:
            return query

    async def _search_arxiv(
        self,
        query: str,
        max_results: int,
        categories: list[str],
        year_from: int | None,
        year_to: int | None,
    ) -> list[SearchResult]:
        """Search arXiv for papers."""
        results: list[SearchResult] = []

        # Build arXiv API query
        search_query = self._build_arxiv_query(query, categories, year_from, year_to)
        encoded_query = urllib.parse.quote(search_query)
        url = f"http://export.arxiv.org/api/query?search_query={encoded_query}&start=0&max_results={max_results}&sortBy=relevance"

        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                xml_content = response.read().decode("utf-8")

            root = ET.fromstring(xml_content)
            ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

            for entry in root.findall("atom:entry", ns):
                title = entry.find("atom:title", ns)
                abstract = entry.find("atom:summary", ns)
                authors = entry.findall("atom:author/atom:name", ns)
                published = entry.find("atom:published", ns)
                categories_elem = entry.findall("arxiv:category", ns)
                link = entry.find("atom:id", ns)

                title_text = title.text.strip() if title is not None else ""
                abstract_text = abstract.text.strip() if abstract is not None else ""
                author_names = [a.text for a in authors if a.text]
                categories_list = [c.get("term", "") for c in categories_elem if c.get("term")]
                published_text = published.text[:10] if published is not None else ""
                url_text = link.text if link is not None else ""

                # Extract arXiv ID
                arxiv_id = ""
                if url_text:
                    match = re.search(r'(\d+\.\d+)', url_text)
                    if match:
                        arxiv_id = match.group(1)

                # Calculate relevance
                relevance = self._calculate_relevance(query, title_text, abstract_text)

                results.append(SearchResult(
                    paper_id=f"arxiv_{arxiv_id}" if arxiv_id else f"paper_{hash(title_text) % 100000}",
                    title=title_text,
                    authors=author_names,
                    abstract=abstract_text,
                    source=SearchSource.ARXIV,
                    url=url_text,
                    arxiv_id=arxiv_id,
                    published_date=published_text,
                    categories=categories_list,
                    relevance_score=relevance,
                ))

        except Exception as e:
            # Return empty results on error
            pass

        return results

    def _build_arxiv_query(
        self,
        query: str,
        categories: list[str],
        year_from: int | None,
        year_to: int | None,
    ) -> str:
        """Build arXiv API query string."""
        parts = [f"all:{query}"]

        for cat in categories:
            parts.append(f"cat:{cat}")

        if year_from:
            parts.append(f"submittedDate:[{year_from} TO *]")
        if year_to:
            parts.append(f"submittedDate:[* TO {year_to}]")

        return " AND ".join(parts)

    async def _search_semantic_scholar(
        self,
        query: str,
        max_results: int,
    ) -> list[SearchResult]:
        """Search Semantic Scholar for papers."""
        # Placeholder - would need API key for real implementation
        return []

    def _calculate_relevance(
        self,
        query: str,
        title: str,
        abstract: str,
    ) -> float:
        """Calculate relevance score for a paper."""
        query_terms = set(query.lower().split())
        title_terms = set(title.lower().split())
        abstract_terms = set(abstract.lower().split())

        # Title matches are worth more
        title_matches = len(query_terms & title_terms)
        abstract_matches = len(query_terms & abstract_terms)

        # Score based on matches
        score = (title_matches * 3 + abstract_matches) / (len(query_terms) * 4)
        return min(1.0, score)

    def _deduplicate_results(
        self,
        results: list[SearchResult],
    ) -> list[SearchResult]:
        """Remove duplicate papers based on title similarity."""
        seen_titles: set[str] = set()
        unique_results: list[SearchResult] = []

        for result in results:
            # Normalize title for comparison
            normalized_title = re.sub(r'[^\w\s]', '', result.title.lower())
            title_words = set(normalized_title.split())

            # Check if we have a very similar title
            is_duplicate = False
            for seen_title in seen_titles:
                seen_words = set(re.sub(r'[^\w\s]', '', seen_title).split())
                overlap = len(title_words & seen_words)
                if overlap >= min(len(title_words), len(seen_words)) * 0.8:
                    is_duplicate = True
                    break

            if not is_duplicate:
                seen_titles.add(normalized_title)
                unique_results.append(result)

        return unique_results
