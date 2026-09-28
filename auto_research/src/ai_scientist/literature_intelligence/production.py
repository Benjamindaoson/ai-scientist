from __future__ import annotations

import time
import html as html_module
import re
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import func, select

from . import models
from .repository import LiteratureRepository
from .service import CORE_VENUES, CORE_YEARS, LiteratureService


OFFICIAL_PROCEEDINGS = {
    "ICLR": "https://openreview.net/group?id=ICLR.cc",
    "ICML": "https://proceedings.mlr.press/",
    "NeurIPS": "https://proceedings.neurips.cc/",
    "AISTATS": "https://proceedings.mlr.press/",
    "AAAI": "https://ojs.aaai.org/index.php/AAAI",
    "CVPR": "https://openaccess.thecvf.com/CVPR.html",
    "ICCV": "https://openaccess.thecvf.com/ICCV.html",
    "ECCV": "https://www.ecva.net/papers.php",
    "ACL": "https://aclanthology.org/venues/acl/",
    "EMNLP": "https://aclanthology.org/venues/emnlp/",
    "CoRL": "https://proceedings.mlr.press/",
    "RSS": "https://www.roboticsproceedings.org/",
    "ICRA": "https://ieeexplore.ieee.org/xpl/conhome/1000639/all-proceedings",
    "IROS": "https://ieeexplore.ieee.org/xpl/conhome/1000393/all-proceedings",
}

SOURCE_NAMES = {
    "ICLR": "International Conference on Learning Representations",
    "ICML": "International Conference on Machine Learning",
    "NeurIPS": "Neural Information Processing Systems",
    "AISTATS": "International Conference on Artificial Intelligence and Statistics",
    "AAAI": "AAAI Conference on Artificial Intelligence",
    "CVPR": "Computer Vision and Pattern Recognition",
    "ICCV": "International Conference on Computer Vision",
    "ECCV": "European Conference on Computer Vision",
    "ACL": "Annual Meeting of the Association for Computational Linguistics",
    "EMNLP": "Empirical Methods in Natural Language Processing",
    "CoRL": "Conference on Robot Learning",
    "RSS": "Robotics Science and Systems",
    "ICRA": "International Conference on Robotics and Automation",
    "IROS": "Intelligent Robots and Systems",
}

PMLR_VOLUMES = {
    ("ICML", 2022): 162, ("ICML", 2023): 202, ("ICML", 2024): 235, ("ICML", 2025): 267,
    ("AISTATS", 2022): 151, ("AISTATS", 2023): 206, ("AISTATS", 2024): 238, ("AISTATS", 2025): 258,
    ("CoRL", 2022): 205, ("CoRL", 2023): 229, ("CoRL", 2024): 270,
}


def _abstract(inverted: dict[str, list[int]] | None) -> str:
    if not inverted:
        return ""
    positions = [(position, word) for word, indexes in inverted.items() for position in indexes]
    return " ".join(word for _, word in sorted(positions))


def _clean_html(value: str) -> str:
    return " ".join(html_module.unescape(re.sub(r"<[^>]+>", " ", value)).split())


@dataclass
class ProductionSyncResult:
    started_at: str
    completed_at: str
    venue_year: dict[str, dict[str, int]]
    errors: list[dict[str, str]]

    @property
    def papers(self) -> int:
        return sum(item["accepted"] for item in self.venue_year.values())


class OpenAlexProductionCorpus:
    """Resumable metadata/abstract ingestion; official proceeding URLs remain acceptance provenance."""

    def __init__(self, service: LiteratureService, *, client: httpx.Client | None = None):
        self.service = service
        self.repository = service.repository
        self.client = client or httpx.Client(timeout=45, follow_redirects=True, headers={"User-Agent": "ai-scientist/0.1 topic-discovery (mailto:research@example.invalid)"})

    def _get(self, path: str, params: dict[str, Any]) -> dict:
        last: Exception | None = None
        for attempt in range(5):
            try:
                response = self.client.get(f"https://api.openalex.org/{path}", params=params)
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last = exc
                time.sleep(min(8, 2 ** attempt))
        raise RuntimeError(f"OpenAlex request failed after retries: {last}")

    def _get_text(self, url: str) -> str:
        last: Exception | None = None
        for attempt in range(5):
            try:
                response = self.client.get(url)
                if response.status_code == 404:
                    raise RuntimeError(f"source fetch failed: {url}: 404 Not Found")
                response.raise_for_status()
                return response.text
            except RuntimeError:
                raise
            except Exception as exc:
                last = exc
                time.sleep(min(8, 2 ** attempt))
        raise RuntimeError(f"source fetch failed after retries: {url}: {last}")

    def _source_id(self, venue: str) -> str:
        payload = self._get("sources", {"search": SOURCE_NAMES[venue], "per-page": 10})
        results = payload.get("results", [])
        if not results:
            raise LookupError(f"OpenAlex source not found: {venue}")
        terms = set(SOURCE_NAMES[venue].lower().split())
        chosen = max(results, key=lambda row: len(terms & set(row.get("display_name", "").lower().split())))
        return chosen["id"].rsplit("/", 1)[-1]

    @staticmethod
    def _record(work: dict) -> dict:
        identifiers = {"openalex": work["id"].rsplit("/", 1)[-1]}
        ids = work.get("ids") or {}
        if ids.get("doi"):
            identifiers["doi"] = ids["doi"]
        if ids.get("pmid"):
            identifiers["pmid"] = ids["pmid"]
        return {
            "source": "openalex", "source_record_id": work["id"], "title": work.get("title") or "Untitled",
            "abstract": _abstract(work.get("abstract_inverted_index")), "publication_year": work.get("publication_year"),
            "identifiers": identifiers,
            "authors": [{"name": author["author"]["display_name"], "position": index + 1} for index, author in enumerate(work.get("authorships", [])) if author.get("author")],
            "version": {"version_label": "openalex-current", "source_url": (work.get("primary_location") or {}).get("landing_page_url") or work["id"]},
            "openalex_referenced_works": work.get("referenced_works", []),
        }

    def _pmlr_records(self, venue: str, year: int, limit: int) -> list[dict]:
        volume = PMLR_VOLUMES.get((venue, year))
        if not volume:
            return []
        base = f"https://proceedings.mlr.press/v{volume}/"
        index_text = self._get_text(base)
        links = list(dict.fromkeys(re.findall(r'href="(https://proceedings\.mlr\.press/v\d+/[^"/]+\.html)"', index_text)))
        if limit:
            links = links[:limit]
        def fetch_record(link: str) -> dict | None:
            page_text = self._get_text(link)
            meta: dict[str, list[str]] = {}
            for name, content in re.findall(r'<meta\s+name="([^"]+)"\s+content="([^"]*)"\s*/?>', page_text, re.I):
                meta.setdefault(name.lower(), []).append(html_module.unescape(content))
            title = (meta.get("citation_title") or [""])[0]
            authors = meta.get("citation_author") or []
            abstract = (meta.get("description") or meta.get("twitter:description") or meta.get("og:description") or [""])[0]
            pdf = (meta.get("citation_pdf_url") or [link])[0]
            if not title:
                return None
            return {
                "source": "pmlr", "source_record_id": link, "title": title, "abstract": abstract,
                "publication_year": year, "identifiers": {"proceedings": link},
                "authors": [{"name": name, "position": index + 1} for index, name in enumerate(authors)],
                "version": {"version_label": f"pmlr-v{volume}", "source_url": link}, "pdf_url": pdf,
            }
        with ThreadPoolExecutor(max_workers=16) as executor:
            return [record for record in executor.map(fetch_record, links) if record]

    def _cvf_records(self, venue: str, year: int, limit: int) -> list[dict]:
        if venue == "ICCV" and year % 2 == 0:
            return []
        base = f"https://openaccess.thecvf.com/{venue}{year}?day=all"
        try:
            index_text = self._get_text(base)
        except RuntimeError as exc:
            if "404" in str(exc):
                return []
            raise
        paths = list(dict.fromkeys(re.findall(r'href="(/content/(?:CVPR|ICCV)\d+/html/[^"/]+\.html)"', index_text)))
        links = [f"https://openaccess.thecvf.com{path}" for path in paths]
        if limit:
            links = links[:limit]

        def fetch_record(link: str) -> dict | None:
            page_text = self._get_text(link)
            meta: dict[str, list[str]] = {}
            for name, content in re.findall(r'<meta\s+name="([^"]+)"\s+content="([^"]*)"\s*/?>', page_text, re.I):
                meta.setdefault(name.lower(), []).append(html_module.unescape(content))
            title = (meta.get("citation_title") or [""])[0]
            authors = meta.get("citation_author") or []
            match = re.search(r'<div\s+id="abstract"[^>]*>(.*?)</div>', page_text, re.I | re.S)
            abstract = " ".join(html_module.unescape(re.sub(r"<[^>]+>", " ", match.group(1))).split()) if match else ""
            if not title:
                return None
            return {
                "source": "cvf", "source_record_id": link, "title": title, "abstract": abstract,
                "publication_year": year, "identifiers": {"proceedings": link},
                "authors": [{"name": name, "position": index + 1} for index, name in enumerate(authors)],
                "version": {"version_label": f"{venue.lower()}-{year}", "source_url": link},
                "pdf_url": (meta.get("citation_pdf_url") or [link])[0],
            }
        with ThreadPoolExecutor(max_workers=16) as executor:
            return [record for record in executor.map(fetch_record, links) if record]

    def _acl_anthology_records(self, venue: str, year: int, limit: int) -> list[dict]:
        event_url = f"https://aclanthology.org/events/{venue.lower()}-{year}/"
        try:
            page = self._get_text(event_url)
        except RuntimeError as exc:
            if "404" in str(exc):
                return []
            raise
        paper_pattern = rf"{year}\.(?:acl-(?:long|short)|emnlp-main)\.\d+"
        paper_ids = list(dict.fromkeys(re.findall(rf"href=/(?:{paper_pattern})/", page)))
        # The full match includes the href prefix; extracting again keeps the parser
        # tolerant of ACL Anthology's unquoted HTML attributes.
        paper_ids = [re.search(paper_pattern, value).group(0) for value in paper_ids]
        paper_ids = [paper_id for paper_id in paper_ids if not paper_id.endswith(".0")]
        if limit:
            paper_ids = paper_ids[:limit]
        records = []
        for paper_id in paper_ids:
            start = page.find(f"href=/{paper_id}/")
            end = page.find('<div class="d-sm-flex align-items-stretch mb-3">', start + 1)
            segment = page[start:end if end >= 0 else None]
            title_match = re.search(r"href=/[^>]+/>(.*?)</a></strong><br>", segment, re.S)
            if not title_match:
                continue
            author_block = segment[title_match.end():segment.find("</span>", title_match.end())]
            authors = [_clean_html(value) for value in re.findall(r"href=/people/[^>]+>(.*?)</a>", author_block, re.S)]
            abstract_match = re.search(r'class="card-body p-3 small">(.*?)</div>', segment, re.S)
            abstract = _clean_html(abstract_match.group(1)) if abstract_match else ""
            source_url = f"https://aclanthology.org/{paper_id}/"
            records.append({
                "source": "acl_anthology", "source_record_id": paper_id,
                "title": _clean_html(title_match.group(1)), "abstract": abstract,
                "publication_year": year, "identifiers": {"proceedings": source_url},
                "authors": [{"name": name, "position": index + 1} for index, name in enumerate(authors)],
                "version": {"version_label": f"acl-anthology-{year}", "source_url": source_url},
            })
        return records

    def _eccv_records(self, year: int, limit: int) -> list[dict]:
        if year % 2:
            return []
        page = self._get_text("https://www.ecva.net/papers.php")
        marker = f"<!-- ECCV {year} -->"
        start = page.find(marker)
        if start < 0:
            return []
        end = page.find("<!-- ECCV ", start + len(marker))
        section = page[start:end if end >= 0 else None]
        entry_pattern = re.compile(
            rf'<dt[^>]*>\s*<br>\s*<a href=([^>]*eccv_{year}[^>]*)>\s*(.*?)</a>\s*</dt><dd>\s*(.*?)</dd>\s*<dd>(.*?)</dd>',
            re.I | re.S,
        )
        records = []
        for match in entry_pattern.finditer(section):
            relative_url, title, author_text, links = match.groups()
            source_url = f"https://www.ecva.net/{relative_url.strip().strip(chr(39) + chr(34))}"
            doi_match = re.search(r"https://link\.springer\.com/chapter/(10\.1007/[^\"']+)", links)
            identifiers = {"proceedings": source_url}
            if doi_match:
                identifiers["doi"] = doi_match.group(1)
            authors = [part.strip().rstrip("*") for part in _clean_html(author_text).split(",") if part.strip()]
            records.append({
                "source": "ecva", "source_record_id": source_url, "title": _clean_html(title),
                "abstract": "", "publication_year": year, "identifiers": identifiers,
                "authors": [{"name": name, "position": index + 1} for index, name in enumerate(authors)],
                "version": {"version_label": f"eccv-{year}", "source_url": source_url},
            })
            if limit and len(records) >= limit:
                break
        return records

    def _rss_records(self, year: int, limit: int) -> list[dict]:
        volume = year - 2004
        base = f"https://roboticsproceedings.org/rss{volume}/"
        index = self._get_text(f"{base}index.html")
        links = [f"{base}{path}" for path in dict.fromkeys(re.findall(r'href="(p\d+\.html)"', index, re.I))]
        if limit:
            links = links[:limit]

        def fetch_record(link: str) -> dict | None:
            page = self._get_text(link)
            title_match = re.search(r'<meta name="citation_title" content="(.*?)"', page, re.I | re.S)
            if not title_match:
                return None
            authors = [_clean_html(value) for value in re.findall(r'<meta name="citation_author" content="(.*?)"', page, re.I | re.S)]
            abstract_match = re.search(r"<b>Abstract:</b>\s*</p>\s*<p[^>]*>(.*?)</p>", page, re.I | re.S)
            abstract = _clean_html(abstract_match.group(1)) if abstract_match else ""
            return {
                "source": "rss", "source_record_id": link, "title": _clean_html(title_match.group(1)),
                "abstract": abstract, "publication_year": year, "identifiers": {"proceedings": link},
                "authors": [{"name": name, "position": index + 1} for index, name in enumerate(authors)],
                "version": {"version_label": f"rss-{volume}", "source_url": link},
            }

        with ThreadPoolExecutor(max_workers=16) as executor:
            return [record for record in executor.map(fetch_record, links) if record]

    def _crossref_conference_records(self, venue: str, year: int, limit: int) -> list[dict]:
        queries = {
            "ICRA": "IEEE International Conference on Robotics and Automation ICRA",
            "IROS": "IEEE RSJ International Conference on Intelligent Robots and Systems IROS",
        }
        expected = {
            "ICRA": "international conference on robotics and automation",
            "IROS": "international conference on intelligent robots and systems",
        }
        response = self.client.get("https://api.crossref.org/works", params={
            "query.container-title": f"{year} {queries[venue]}",
            "filter": f"from-pub-date:{year}-01-01,until-pub-date:{year}-12-31",
            "rows": limit or 1000,
            "select": "DOI,title,container-title,published,author,abstract,URL",
        })
        response.raise_for_status()
        records = []
        for item in response.json().get("message", {}).get("items", []):
            containers = " ".join(item.get("container-title") or []).lower()
            if expected[venue] not in containers:
                continue
            doi = item.get("DOI")
            title = " ".join(item.get("title") or [])
            if not doi or not title:
                continue
            source_url = item.get("URL") or f"https://doi.org/{doi}"
            authors = [" ".join(part for part in (author.get("given"), author.get("family")) if part) for author in item.get("author") or []]
            records.append({
                "source": "crossref", "source_record_id": doi, "title": title,
                "abstract": _clean_html(item.get("abstract") or ""), "publication_year": year,
                "identifiers": {"doi": doi},
                "authors": [{"name": name, "position": index + 1} for index, name in enumerate(authors) if name],
                "version": {"version_label": f"crossref-{year}", "source_url": source_url},
            })
        return records

    def _sync_records(self, venue: str, year: int, records: list[dict], counts: dict[str, int]) -> None:
        counts["found"] = len(records)
        for record in records:
            paper = self.service.ingest_record(record)
            self.service.add_official_appearance(paper["paper_id"], venue, year, "main", official_source_url=OFFICIAL_PROCEEDINGS[venue])
            counts["accepted"] += 1
            counts["metadata"] += int(bool(record["title"] and record["authors"]))
            if record["abstract"]:
                self.service.ingest_full_text(paper["paper_version_id"], f"Abstract\n{record['abstract']}", source_url=record["version"]["source_url"], license_name=f"{venue} public abstract")
                counts["documents"] += 1

    def sync(self, *, venues: tuple[str, ...] = tuple(CORE_VENUES), years: tuple[int, ...] = CORE_YEARS, max_per_edition: int = 0) -> ProductionSyncResult:
        self.service.bootstrap_core_venues()
        started = datetime.now(timezone.utc)
        coverage: dict[str, dict[str, int]] = {}
        errors: list[dict[str, str]] = []
        for venue in venues:
            adapter = None
            if venue in {"ACL", "EMNLP"}:
                adapter = lambda year: self._acl_anthology_records(venue, year, max_per_edition)
            elif venue == "ECCV":
                adapter = lambda year: self._eccv_records(year, max_per_edition)
            elif venue == "RSS":
                adapter = lambda year: self._rss_records(year, max_per_edition)
            elif venue in {"ICRA", "IROS"}:
                adapter = lambda year: self._crossref_conference_records(venue, year, max_per_edition)
            if adapter:
                for year in years:
                    key = f"{venue}:{year}"
                    counts = {"found": 0, "accepted": 0, "metadata": 0, "documents": 0, "citations": 0, "embeddings": 0}
                    coverage[key] = counts
                    try:
                        self._sync_records(venue, year, adapter(year), counts)
                    except Exception as exc:
                        errors.append({"scope": key, "error": str(exc)})
                continue
            if venue in {"CVPR", "ICCV"}:
                for year in years:
                    key = f"{venue}:{year}"
                    counts = {"found": 0, "accepted": 0, "metadata": 0, "documents": 0, "citations": 0, "embeddings": 0}
                    coverage[key] = counts
                    try:
                        self._sync_records(venue, year, self._cvf_records(venue, year, max_per_edition), counts)
                    except Exception as exc:
                        errors.append({"scope": key, "error": str(exc)})
                continue
            if any((venue, year) in PMLR_VOLUMES for year in years):
                for year in years:
                    key = f"{venue}:{year}"
                    counts = {"found": 0, "accepted": 0, "metadata": 0, "documents": 0, "citations": 0, "embeddings": 0}
                    coverage[key] = counts
                    try:
                        self._sync_records(venue, year, self._pmlr_records(venue, year, max_per_edition), counts)
                    except Exception as exc:
                        errors.append({"scope": key, "error": str(exc)})
                continue
            try:
                source_id = self._source_id(venue)
            except Exception as exc:
                for year in years:
                    coverage[f"{venue}:{year}"] = {"found": 0, "accepted": 0, "metadata": 0, "documents": 0, "citations": 0, "embeddings": 0}
                errors.append({"scope": venue, "error": str(exc)})
                continue
            for year in years:
                key = f"{venue}:{year}"
                counts = {"found": 0, "accepted": 0, "metadata": 0, "documents": 0, "citations": 0, "embeddings": 0}
                coverage[key] = counts
                cursor = "*"
                saved: dict[str, tuple[dict, dict]] = {}
                try:
                    while cursor:
                        payload = self._get("works", {
                            # Conference papers often have arXiv as the primary location; the
                            # official proceedings appears in another indexed location.
                            "filter": f"locations.source.id:{source_id},publication_year:{year}",
                            "per-page": 200, "cursor": cursor,
                            "select": "id,doi,title,publication_year,abstract_inverted_index,authorships,ids,primary_location,referenced_works",
                        })
                        works = payload.get("results", [])
                        if not works:
                            break
                        for work in works:
                            counts["found"] += 1
                            if max_per_edition and counts["accepted"] >= max_per_edition:
                                break
                            record = self._record(work)
                            paper = self.service.ingest_record(record)
                            self.service.add_official_appearance(paper["paper_id"], venue, year, "main", official_source_url=OFFICIAL_PROCEEDINGS[venue])
                            counts["accepted"] += 1
                            counts["metadata"] += int(bool(record["title"] and record["authors"]))
                            if record["abstract"]:
                                document = self.service.ingest_full_text(
                                    paper["paper_version_id"], f"Abstract\n{record['abstract']}",
                                    source_url=record["version"]["source_url"] if record["version"]["source_url"].startswith("https://") else work["id"],
                                    license_name="OpenAlex abstract metadata",
                                )
                                counts["documents"] += 1
                            saved[work["id"]] = (paper, record)
                        if max_per_edition and counts["accepted"] >= max_per_edition:
                            break
                        cursor = (payload.get("meta") or {}).get("next_cursor")
                    for _, (paper, record) in saved.items():
                        for referenced in record.get("openalex_referenced_works", []):
                            if referenced in saved:
                                self.service.add_citation(paper["paper_id"], saved[referenced][0]["paper_id"], source="openalex", source_record_id=f"{paper['paper_id']}:{saved[referenced][0]['paper_id']}")
                                counts["citations"] += 1
                except Exception as exc:
                    errors.append({"scope": key, "error": str(exc)})
        return ProductionSyncResult(started.isoformat(), datetime.now(timezone.utc).isoformat(), coverage, errors)


class ResumableEmbeddingIndexer:
    def __init__(self, repository: LiteratureRepository, service: LiteratureService, provider):
        self.repository = repository
        self.service = service
        self.provider = provider

    def run(self, *, batch_size: int = 64, max_chunks: int = 0, shard_index: int = 0, shard_count: int = 1) -> dict[str, Any]:
        if shard_count < 1 or not 0 <= shard_index < shard_count:
            raise ValueError("shard_index must be within shard_count")
        started = time.monotonic()
        model = self.repository.get_or_create_embedding_model(self.provider.model_name, self.provider.dimension, self.provider.config)
        statement = select(models.chunks).outerjoin(models.embeddings, (
            (models.embeddings.c.chunk_id == models.chunks.c.chunk_id)
            & (models.embeddings.c.embedding_model_id == model["embedding_model_id"])
            & (models.embeddings.c.content_hash == models.chunks.c.content_hash)
        )).where(models.embeddings.c.embedding_id.is_(None))
        if shard_count > 1:
            statement = statement.where(func.mod(func.get_byte(func.uuid_send(models.chunks.c.chunk_id), 0), shard_count) == shard_index)
        with self.repository.engine.connect() as connection:
            rows = connection.execute(statement.order_by(models.chunks.c.token_count, models.chunks.c.chunk_id)).mappings().all()
        if max_chunks:
            rows = rows[:max_chunks]
        embedded = errors = 0
        for start in range(0, len(rows), batch_size):
            batch = rows[start:start + batch_size]
            try:
                vectors = self.provider.embed_many([chunk["content"] for chunk in batch]) if hasattr(self.provider, "embed_many") else None
            except Exception:
                vectors = None
            for index, chunk in enumerate(batch):
                try:
                    vector = vectors[index] if vectors is not None else self.provider.embed(chunk["content"])
                    self.repository.ensure_embedding(dict(chunk), model, vector)
                    embedded += 1
                except Exception:
                    errors += 1
        return {"model": self.provider.model_name, "shard": f"{shard_index + 1}/{shard_count}", "pending_at_start": len(rows), "embedded": embedded, "errors": errors, "runtime_seconds": round(time.monotonic() - started, 3)}


def corpus_counts(repository: LiteratureRepository) -> dict[str, int]:
    return {name: repository.count(name) for name in ("papers", "paper_versions", "documents", "chunks", "embeddings", "citations")}


def build_real_known_prior_benchmark(repository: LiteratureRepository, output: str | Path, *, count: int = 100, embedding_model: str | None = None) -> list[dict[str, Any]]:
    with repository.engine.connect() as connection:
        statement = (
            select(models.papers, models.paper_versions.c.paper_version_id, models.chunks.c.chunk_id, models.chunks.c.content)
            .join(models.paper_versions, models.paper_versions.c.paper_id == models.papers.c.paper_id)
            .join(models.chunks, models.chunks.c.paper_version_id == models.paper_versions.c.paper_version_id)
            .where(models.papers.c.abstract != "", models.papers.c.publication_year.is_not(None))
        )
        if embedding_model:
            statement = statement.join(models.embeddings, models.embeddings.c.chunk_id == models.chunks.c.chunk_id).join(
                models.embedding_models, models.embedding_models.c.embedding_model_id == models.embeddings.c.embedding_model_id
            ).where(models.embedding_models.c.model_name == embedding_model)
        source_rows = connection.execute(statement.order_by(
            models.papers.c.publication_year.desc().nulls_last(), models.papers.c.paper_id, models.chunks.c.ordinal
        )).mappings().all()
        rows = []
        seen_papers: set[str] = set()
        seen_questions: set[str] = set()
        for row in source_rows:
            paper_id = str(row["paper_id"])
            question_signature = " ".join(re.findall(r"[A-Za-z][A-Za-z-]+", row["abstract"])[:32]).lower()
            if paper_id in seen_papers or not question_signature or question_signature in seen_questions:
                continue
            seen_papers.add(paper_id)
            seen_questions.add(question_signature)
            rows.append(row)
            if len(rows) == count:
                break
        paper_ids = [row["paper_id"] for row in rows]
        identifiers = connection.execute(
            select(models.paper_identifiers.c.paper_id, models.paper_identifiers.c.identifier_type, models.paper_identifiers.c.identifier_value)
            .where(models.paper_identifiers.c.paper_id.in_(paper_ids))
        ).mappings().all()
        source_records = connection.execute(
            select(models.source_records.c.paper_id, models.source_records.c.source, models.source_records.c.native_id)
            .where(models.source_records.c.paper_id.in_(paper_ids))
        ).mappings().all()
        official_paper_ids = {
            str(row.paper_id) for row in connection.execute(
                select(models.paper_appearances.c.paper_id).where(models.paper_appearances.c.paper_id.in_(paper_ids))
            )
        }
    if len(rows) < count:
        raise ValueError(f"only {len(rows)} source-backed papers available; {count} required")
    identifier_rank = {"doi": 0, "arxiv": 1, "openalex": 2}
    designated_identifiers: dict[str, str] = {}
    for item in sorted(identifiers, key=lambda item: identifier_rank.get(item["identifier_type"], 100)):
        designated_identifiers.setdefault(str(item["paper_id"]), f"{item['identifier_type']}:{item['identifier_value']}")
    for item in source_records:
        designated_identifiers.setdefault(str(item["paper_id"]), f"{item['source']}:{item['native_id']}")
    benchmark = []
    abstract_tokens = [set(re.findall(r"[a-z][a-z-]+", row["abstract"].lower())) for row in rows]
    for index, row in enumerate(rows):
        concepts = " ".join(re.findall(r"[A-Za-z][A-Za-z-]+", row["abstract"])[:32])
        neighbours = sorted(
            (
                (len(abstract_tokens[index] & tokens) / max(1, len(abstract_tokens[index] | tokens)), other)
                for other, tokens in enumerate(abstract_tokens) if other != index
            ),
            reverse=True,
        )[:2]
        false_friends = [str(rows[other]["paper_id"]) for _, other in neighbours]
        benchmark.append({
            "question_id": f"real-prior-{index + 1:03d}",
            "question": f"Which source-backed work investigates this relation: {concepts}?",
            "designated_identifier": designated_identifiers.get(str(row["paper_id"]), f"internal:{row['paper_id']}"),
            "designated_paper_id": str(row["paper_id"]), "dangerous_prior_paper_id": str(row["paper_id"]),
            "closest_prior_paper_id": str(row["paper_id"]), "false_friend_paper_ids": false_friends,
            "source_scope": "CORE_OFFICIAL" if str(row["paper_id"]) in official_paper_ids else "EXTERNAL",
            "source_chunk_id": str(row["chunk_id"]), "verification_status": "SOURCE_DERIVED_AND_DETERMINISTICALLY_VERIFIED",
            "verification_rule": "question concepts are extracted from the designated source abstract; false friends are the two lexically closest distinct frozen benchmark papers",
        })
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(benchmark, indent=2), encoding="utf-8")
    return benchmark
