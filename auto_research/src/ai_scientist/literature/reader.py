"""Paper reader module.

Provides functionality for reading and analyzing papers.
"""
from __future__ import annotations

import hashlib
import re
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


@dataclass
class PaperContent:
    """Full content of a paper."""
    paper_id: str
    arxiv_id: str
    title: str
    abstract: str
    authors: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    full_text: str = ""
    sections: dict[str, str] = field(default_factory=dict)  # section_name -> content
    references: list[dict] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)  # cited paper IDs
    key_findings: list[str] = field(default_factory=list)
    methodology: str = ""
    limitations: list[str] = field(default_factory=list)
    pdf_url: str = ""


@dataclass
class ExtractedInsight:
    """An insight extracted from a paper."""
    insight_type: str  # FINDING, METHOD, THEORY, GAP, LIMITATION
    content: str
    confidence: float = 0.5
    source_location: str = ""  # Where in the paper this was found
    supporting_text: str = ""


class PaperReader:
    """Paper reading and analysis system.

    Reads papers from arXiv and extracts structured information.
    """

    def __init__(self, gateway=None):
        """Initialize paper reader.

        Args:
            gateway: LLM gateway for analysis
        """
        self.gateway = gateway
        self._cache: dict[str, PaperContent] = {}

    async def read_paper(
        self,
        arxiv_id: str,
        project_id: str = "",
        fetch_full_text: bool = False,
    ) -> PaperContent | None:
        """Read and parse a paper.

        Args:
            arxiv_id: arXiv paper ID
            project_id: Project ID for caching
            fetch_full_text: Whether to fetch full text

        Returns:
            PaperContent with parsed paper data
        """
        cache_key = f"{project_id}:{arxiv_id}" if project_id else arxiv_id

        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            # Fetch metadata from arXiv API
            url = f"http://export.arxiv.org/api/query?id_list={arxiv_id}&max_results=1"
            import urllib.request

            with urllib.request.urlopen(url, timeout=30) as response:
                xml_content = response.read().decode("utf-8")

            paper = self._parse_arxiv_response(xml_content, arxiv_id)

            if paper and fetch_full_text:
                # Try to fetch full text (abstract is most reliable from API)
                pass  # Full PDF parsing would require additional libraries

            if paper:
                self._cache[cache_key] = paper
                return paper

        except Exception as e:
            pass

        return None

    def _parse_arxiv_response(self, xml_content: str, arxiv_id: str) -> PaperContent | None:
        """Parse arXiv API response."""
        import xml.etree.ElementTree as ET

        try:
            root = ET.fromstring(xml_content)
            ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

            entry = root.find("atom:entry", ns)
            if entry is None:
                return None

            title = entry.find("atom:title", ns)
            abstract = entry.find("atom:summary", ns)
            authors = entry.findall("atom:author/atom:name", ns)
            published = entry.find("atom:published", ns)
            categories = entry.findall("arxiv:category", ns)
            links = entry.findall("atom:link", ns)

            title_text = title.text.strip().replace("\n", " ") if title is not None else ""
            abstract_text = abstract.text.strip().replace("\n", " ") if abstract is not None else ""
            author_names = [a.text for a in authors if a.text]
            categories_list = [c.get("term", "") for c in categories if c.get("term")]
            published_text = published.text[:10] if published is not None else ""

            # Find PDF link
            pdf_url = ""
            for link in links:
                if link.get("title") == "pdf":
                    pdf_url = link.get("href", "")
                    break

            # Generate paper ID
            paper_id = f"paper_{hashlib.md5(arxiv_id.encode()).hexdigest()[:8]}"

            return PaperContent(
                paper_id=paper_id,
                arxiv_id=arxiv_id,
                title=title_text,
                abstract=abstract_text,
                full_text="",  # Would need PDF parsing for full text
                sections={"abstract": abstract_text},
                references=[],
                key_findings=[],
                pdf_url=pdf_url,
            )

        except Exception:
            return None

    async def analyze_paper(
        self,
        paper: PaperContent,
        research_question: str = "",
    ) -> list[ExtractedInsight]:
        """Analyze a paper and extract insights.

        Args:
            paper: Paper content to analyze
            research_question: Optional research question context

        Returns:
            List of extracted insights
        """
        insights: list[ExtractedInsight] = []

        if not self.gateway:
            # Basic keyword-based extraction
            insights.extend(self._basic_extraction(paper))
            return insights

        # LLM-powered analysis
        prompt = self._build_analysis_prompt(paper, research_question)

        try:
            response = self.gateway.generate(prompt)
            insights.extend(self._parse_analysis_response(response, paper))
        except Exception:
            # Fallback to basic extraction
            insights.extend(self._basic_extraction(paper))

        return insights

    def _build_analysis_prompt(
        self,
        paper: PaperContent,
        research_question: str,
    ) -> str:
        """Build analysis prompt for LLM."""
        rq_context = f"\n\nResearch question context: {research_question}" if research_question else ""

        return f"""Analyze the following academic paper and extract key insights.{rq_context}

# Paper Title
{paper.title}

# Authors
{', '.join(paper.authors)}

# Abstract
{paper.abstract}

# Categories
{', '.join(paper.categories)}

Extract the following types of insights:
1. KEY_FINDINGS: Main results and contributions
2. METHOD: Methodology and approach
3. THEORY: Theoretical foundations
4. GAP: Research gaps or limitations
5. LIMITATION: Explicit limitations mentioned

Format each insight as:
[INSIGHT_TYPE] Content of the insight | Confidence: 0.0-1.0 | Location: where found"""

    def _parse_analysis_response(
        self,
        response: str,
        paper: PaperContent,
    ) -> list[ExtractedInsight]:
        """Parse LLM analysis response."""
        insights: list[ExtractedInsight] = []

        for line in response.strip().split("\n"):
            line = line.strip()
            if not line or "[" not in line:
                continue

            try:
                # Parse [TYPE] Content | Confidence: X | Location: Y format
                if "]" in line:
                    type_part = line.split("]")[0] + "]"
                    rest = line[len(type_part):].strip()

                    insight_type = type_part.strip("[]").split()[0]
                    content = rest.split("|")[0].strip()

                    confidence = 0.5
                    location = "abstract"

                    if "Confidence:" in rest:
                        conf_str = rest.split("Confidence:")[1].split("|")[0].strip()
                        try:
                            confidence = float(conf_str)
                        except ValueError:
                            pass

                    if "Location:" in rest:
                        location = rest.split("Location:")[1].strip()

                    insights.append(ExtractedInsight(
                        insight_type=insight_type,
                        content=content,
                        confidence=confidence,
                        source_location=location,
                        supporting_text=content,
                    ))

            except Exception:
                continue

        return insights

    def _basic_extraction(self, paper: PaperContent) -> list[ExtractedInsight]:
        """Basic keyword-based extraction without LLM."""
        insights: list[ExtractedInsight] = []

        # Extract from abstract
        abstract_lower = paper.abstract.lower()

        # Look for methodology indicators
        method_keywords = ["method", "approach", "algorithm", "model", "framework"]
        for keyword in method_keywords:
            if keyword in abstract_lower:
                # Find sentence containing keyword
                for sentence in paper.abstract.split("."):
                    if keyword in sentence.lower():
                        insights.append(ExtractedInsight(
                            insight_type="METHOD",
                            content=sentence.strip(),
                            confidence=0.6,
                            source_location="abstract",
                        ))
                        break

        # Look for limitation indicators
        if "limit" in abstract_lower or "challenge" in abstract_lower:
            for sentence in paper.abstract.split("."):
                if "limit" in sentence.lower() or "challenge" in sentence.lower():
                    insights.append(ExtractedInsight(
                        insight_type="LIMITATION",
                        content=sentence.strip(),
                        confidence=0.5,
                        source_location="abstract",
                    ))
                    break

        # Look for contribution indicators
        contribution_keywords = ["propose", "introduce", "present", "demonstrate", "show"]
        for keyword in contribution_keywords:
            if keyword in abstract_lower:
                for sentence in paper.abstract.split("."):
                    if keyword in sentence.lower():
                        insights.append(ExtractedInsight(
                            insight_type="FINDING",
                            content=sentence.strip(),
                            confidence=0.6,
                            source_location="abstract",
                        ))
                        break

        return insights

    async def extract_research_question(self, paper: PaperContent) -> str:
        """Extract the main research question from a paper."""
        if not self.gateway:
            # Basic extraction from abstract
            return self._basic_rq_extraction(paper)

        prompt = f"""Given the following paper abstract, identify the main research question being addressed.

# Title
{paper.title}

# Abstract
{paper.abstract}

Return only the research question, phrased as a specific, answerable question."""

        try:
            response = self.gateway.generate(prompt)
            return response.strip()
        except Exception:
            return self._basic_rq_extraction(paper)

    def _basic_rq_extraction(self, paper: PaperContent) -> str:
        """Basic RQ extraction without LLM."""
        abstract = paper.abstract

        # Look for "we study", "we investigate", "we propose", etc.
        patterns = [
            r"we (?:study|investigate|examine|explore|analyze)\s+([^.]+)",
            r"this paper (?:studies|investigates|examines|explores|proposes)\s+([^.]+)",
            r"the goal of (?:this paper|this work|this study)\s+is\s+([^.]+)",
            r"we (?:aim to|seek to|attempt to)\s+([^.]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, abstract, re.IGNORECASE)
            if match:
                return f"How {match.group(1).strip()}?"

        # Fallback: use title
        return f"How can we {paper.title.lower().replace(':', '?')}"
