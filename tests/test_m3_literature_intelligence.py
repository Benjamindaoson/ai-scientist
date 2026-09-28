from __future__ import annotations

import json
import os

import pytest
from sqlalchemy import create_engine, inspect, text

from ai_scientist.literature_intelligence import (
    CORE_VENUES,
    HashingEmbeddingProvider,
    HybridSearch,
    LiteratureRepository,
    LiteratureService,
    NoveltyService,
    initialize_literature_database,
)
from ai_scientist.literature_intelligence.claims import add_lazy_claim
from ai_scientist.research_store.cli import main as cli_main


DATABASE_URL = os.getenv("RESEARCH_DATABASE_URL", "postgresql+psycopg://research:research@localhost:55432/research_os")


@pytest.fixture(scope="module")
def literature():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    initialize_literature_database(engine)
    with engine.begin() as connection:
        for table in reversed(inspect(connection).get_table_names(schema="literature")):
            connection.execute(text(f'TRUNCATE TABLE literature."{table}" CASCADE'))
    repository = LiteratureRepository(engine)
    service = LiteratureService(repository)
    service.bootstrap_core_venues()
    return repository, service


def _record(identifier="2401.00001", title="Section Aware Retrieval for Science", source="openreview"):
    return {
        "source": source,
        "source_record_id": f"{source}:{identifier}",
        "title": title,
        "abstract": "A hybrid retrieval method combines lexical and dense scientific evidence.",
        "identifiers": {"arxiv": identifier},
        "authors": [{"name": "Ada Researcher", "position": 1}],
        "version": {"version_label": "v1", "source_url": f"https://arxiv.org/abs/{identifier}"},
    }


def test_literature_schema_and_core_registry(literature):
    repository, _ = literature
    expected = {"venues", "venue_editions", "papers", "paper_versions", "paper_appearances", "citations", "chunks", "embeddings", "retrieval_runs", "retrieval_results", "merge_events"}
    assert expected <= set(inspect(repository.engine).get_table_names(schema="literature"))
    assert len(CORE_VENUES) == 14
    assert repository.count("venue_editions") == 70


def test_real_multi_venue_bootstrap_uses_official_acceptance_snapshot(literature):
    repository, service = literature
    records = json.loads(open("benchmarks/literature/core_bootstrap_v1.json", encoding="utf-8").read())
    first = service.bootstrap_core_records(records)
    second = service.bootstrap_core_records(records)
    assert first == second == {"papers": 2, "venues": 2}
    assert repository.count("paper_appearances") == 2


def test_exact_identifier_is_idempotent_and_fuzzy_only_creates_candidate(literature):
    repository, service = literature
    paper_count = repository.count("papers")
    merge_count = repository.count("merge_events")
    first = service.ingest_record(_record())
    second = service.ingest_record(_record(source="openalex"))
    fuzzy = service.ingest_record(_record("2401.99999", "Section-Aware Retrieval for Science", "crossref"))
    assert first["paper_id"] == second["paper_id"]
    assert fuzzy["paper_id"] != first["paper_id"]
    assert repository.count("papers") == paper_count + 2
    assert repository.count("merge_events") == merge_count + 1


def test_paper_version_appearance_and_official_core_evidence_are_distinct(literature):
    repository, service = literature
    paper = service.ingest_record(_record("2402.00002", "Official Core Paper"))
    appearance = service.add_official_appearance(paper["paper_id"], "ICLR", 2024, "main", official_source_url="https://openreview.net/group?id=ICLR.cc/2024/Conference")
    repeated = service.add_official_appearance(paper["paper_id"], "ICLR", 2024, "main", official_source_url="https://openreview.net/group?id=ICLR.cc/2024/Conference")
    unverified = service.ingest_record(_record("2402.00003", "Claimed Accepted Paper", "arxiv"))
    assert paper["paper_id"] != paper["paper_version_id"]
    assert appearance["is_core_accepted"] is True
    assert repeated["paper_appearance_id"] == appearance["paper_appearance_id"]
    assert repository.list_appearances(unverified["paper_id"]) == []


def test_fulltext_chunks_keep_provenance_and_embeddings_are_content_addressed(literature):
    repository, service = literature
    paper = service.ingest_record(_record("2403.00003", "Full Text Prior"))
    text_content = "Abstract\nHybrid retrieval is evaluated.\n\nIntroduction\nPrior systems lose section provenance.\n\nMethods\nWe combine keyword and dense ranks.\n\nLimitations\nThe corpus is bounded."
    first = service.ingest_full_text(paper["paper_version_id"], text_content, source_url="https://example.org/legal.txt", license_name="CC-BY-4.0")
    second = service.ingest_full_text(paper["paper_version_id"], text_content, source_url="https://example.org/legal.txt", license_name="CC-BY-4.0")
    provider = HashingEmbeddingProvider(dimension=1024, model_name="test/hashing-1024")
    embedded_once = service.embed_document(first["document_id"], provider)
    embedded_twice = service.embed_document(first["document_id"], provider)
    chunks = repository.list_document_chunks(first["document_id"])
    assert first["content_hash"] == second["content_hash"]
    assert chunks and all(chunk["section_id"] and chunk["char_start"] < chunk["char_end"] for chunk in chunks)
    assert embedded_once == embedded_twice == len(chunks)
    assert repository.count("embeddings") >= len(chunks)


def test_citation_edges_and_sources_are_idempotent(literature):
    repository, service = literature
    citing = service.ingest_record(_record("2404.00004", "Citing Work"))
    cited = service.ingest_record(_record("2404.00005", "Cited Work"))
    service.add_citation(citing["paper_id"], cited["paper_id"], source="openalex", source_record_id="edge-1")
    service.add_citation(citing["paper_id"], cited["paper_id"], source="openalex", source_record_id="edge-1")
    assert repository.count("citations") == 1
    assert repository.count("citation_sources") == 1
    assert cited["paper_id"] in service.expand_citations(citing["paper_id"], hops=1)


def test_graph_expansion_and_lazy_claims_keep_source_provenance(literature):
    repository, service = literature
    target = service.ingest_record(_record("2404.10001", "Graph Target"))
    related = service.ingest_record(_record("2404.10002", "Graph Related"))
    citer_a = service.ingest_record(_record("2404.10003", "Citer A"))
    citer_b = service.ingest_record(_record("2404.10004", "Citer B"))
    service.add_citation(citer_a["paper_id"], target["paper_id"], source="openalex", source_record_id="g1")
    service.add_citation(citer_a["paper_id"], related["paper_id"], source="openalex", source_record_id="g2")
    service.add_citation(citer_b["paper_id"], target["paper_id"], source="openalex", source_record_id="g3")
    service.add_topic(target["paper_id"], "causal retrieval")
    service.add_topic(related["paper_id"], "causal retrieval")
    assert related["paper_id"] in service.co_citations(target["paper_id"])
    assert citer_b["paper_id"] in service.bibliographic_coupling(citer_a["paper_id"])
    assert related["paper_id"] in service.same_author_papers(target["paper_id"])
    assert related["paper_id"] in service.topic_expansion(target["paper_id"])
    document = service.ingest_full_text(
        target["paper_version_id"], "Results\nThe graph improves recall.",
        source_url="https://example.org/graph.txt", license_name="CC-BY-4.0",
    )
    chunk = repository.list_document_chunks(document["document_id"])[0]
    claim = add_lazy_claim(repository, target["paper_version_id"], chunk["chunk_id"], "finding", "The graph improves recall.")
    assert claim["source_chunk_id"] == chunk["chunk_id"]
    assert claim["review_status"] == "unverified"


def test_resumable_ingestion_and_all_schedule_cli_paths(literature, tmp_path, monkeypatch, capsys):
    repository, service = literature
    record = _record("2404.20001", "Scheduled Ingestion", "openalex")
    first = service.ingest_records([record], job_type="daily", idempotency_key="daily:2026-09-28", source="openalex", scope="external", cursor={"page": 1})
    second = service.ingest_records([record], job_type="daily", idempotency_key="daily:2026-09-28", source="openalex", scope="external", cursor={"page": 2})
    assert first["ingestion_run_id"] == second["ingestion_run_id"]
    assert first["status"] == second["status"] == "COMPLETE"
    payload = tmp_path / "records.json"
    payload.write_text("[]", encoding="utf-8")
    monkeypatch.setenv("RESEARCH_DATABASE_URL", DATABASE_URL)
    for schedule in ("daily", "weekly", "monthly", "on-demand"):
        assert cli_main(["literature", "sync", schedule, "--idempotency-key", f"cli:{schedule}", "--input", str(payload)]) == 0
    assert repository.count("ingestion_runs") >= 5
    assert '"status": "COMPLETE"' in capsys.readouterr().out


def test_hybrid_search_external_expansion_and_independent_runs(literature):
    repository, service = literature
    external = service.ingest_record(_record("2405.00006", "Dangerous External Novelty Prior", "arxiv"))
    fulltext = service.ingest_full_text(external["paper_version_id"], "Abstract\nDangerous external novelty prior uses a unique causal mechanism.", source_url="https://arxiv.org/abs/2405.00006", license_name="arXiv")
    service.embed_document(fulltext["document_id"], HashingEmbeddingProvider(1024, "test/hashing-1024"))
    novelty = NoveltyService(HybridSearch(repository, HashingEmbeddingProvider(1024, "test/hashing-1024")))
    scout = novelty.audit("idea-external", "unique causal mechanism", actor_role="scout", external=True)
    reviewer = novelty.audit("idea-external", "unique causal mechanism", actor_role="reviewer", external=True)
    assert scout["retrieval_run_id"] != reviewer["retrieval_run_id"]
    assert external["paper_id"] in [item["paper_id"] for item in scout["results"]]
    assert scout["source_chunk_ids"]


def test_frozen_known_prior_benchmark_meets_quality_gate(literature):
    repository, service = literature
    benchmark = service.load_known_prior_benchmark("benchmarks/literature/known_prior_v1.json")
    for item in benchmark:
        service.ingest_record(item["paper"])
    result = service.run_known_prior_benchmark(benchmark, HybridSearch(repository, HashingEmbeddingProvider(1024, "test/hashing-1024")))
    assert result["queries"] == 20
    assert result["top_50_recall"] >= 0.90
    assert result["top_20_recall"] >= 0.80
    assert result["inspectable_source_rate"] == 1.0
    assert result["fabricated_ids"] == 0
