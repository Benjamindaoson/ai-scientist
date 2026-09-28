from __future__ import annotations

from datetime import datetime, timezone
import os
import uuid

import pytest
from sqlalchemy import create_engine, inspect, text

from ai_scientist.opportunity_intelligence import (
    OFFICIAL_SOURCES,
    MONITORING_JOBS,
    OpportunityRepository,
    OpportunityService,
    OfficialOpportunitySource,
    initialize_opportunity_database,
    normalize_deadline,
)
from ai_scientist.topic_discovery import (
    CandidateIdea,
    DiscoveryLoop,
    GateEvidence,
    GapDecision,
    IdeaDeduplicator,
    NoveltyJudge,
    ResearchProgram,
    TopicReadinessGate,
)
from ai_scientist.topic_discovery.service import ExternalPriorExpander, ProductionTopicPipeline
from ai_scientist.literature_intelligence import HashingEmbeddingProvider, LiteratureRepository, LiteratureService, OpenAlexProductionCorpus, ResumableEmbeddingIndexer, build_real_known_prior_benchmark, initialize_literature_database


DATABASE_URL = os.getenv("RESEARCH_DATABASE_URL", "postgresql+psycopg://research:research@localhost:55432/research_os")


@pytest.fixture
def opportunity_repository():
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    initialize_opportunity_database(engine)
    topic_tables = {
        "opportunity_topics", "opportunity_snapshots", "research_signals", "idea_lineage",
        "topic_candidates", "novelty_audits", "feasibility_audits", "topic_dossiers", "discovery_runs",
        "opportunities",
    }
    with engine.begin() as connection:
        existing = set(inspect(connection).get_table_names(schema="research"))
        for table in topic_tables & existing:
            connection.execute(text(f'TRUNCATE TABLE research."{table}" CASCADE'))
    return OpportunityRepository(engine)


def _html(deadline="September 25, 2026 11:59 PM AOE"):
    return f"""
    <html><body><h1>ICLR 2027 Call for Papers</h1>
    <p>We welcome machine learning, robotics, reinforcement learning, and uncertainty quantification.</p>
    <h2>Key dates</h2><p>Full paper submission deadline: {deadline}</p>
    <h2>Workshops</h2><a href='/workshops/world-model-reliability'>World Model Reliability Workshop</a>
    </body></html>
    """


def _source():
    return OfficialOpportunitySource(
        venue_name="ICLR", venue_year=2027, opportunity_type="MAIN_CONFERENCE_CFP",
        title="ICLR 2027 Call for Papers", official_url="https://iclr.cc/Conferences/2027/CallForPapers",
        source_priority=100,
    )


def test_official_opportunity_registry_covers_all_core_venues():
    assert {source.venue_name for source in OFFICIAL_SOURCES} >= {
        "ICLR", "NeurIPS", "ICML", "AISTATS", "AAAI", "CVPR", "ICCV", "ECCV",
        "ACL", "EMNLP", "CoRL", "RSS", "ICRA", "IROS",
    }


def test_required_monitoring_jobs_are_schedulable_commands():
    assert set(MONITORING_JOBS) == {
        "daily_cfp_watch", "weekly_workshop_watch", "weekly_recent_paper_watch", "monthly_topic_trend_refresh",
    }
    assert all(job["command"].startswith("ai-scientist ") for job in MONITORING_JOBS.values())


def test_cfp_official_page_workshop_deadline_and_provenance(opportunity_repository):
    service = OpportunityService(opportunity_repository, static_fetch=lambda _: _html())
    result = service.sync_source(_source(), now=datetime(2026, 9, 1, tzinfo=timezone.utc))
    assert result["official_verified"] is True
    assert result["submission_deadline_raw"] == "September 25, 2026 11:59 PM AOE"
    assert result["submission_deadline_utc"].isoformat() == "2026-09-26T11:59:00+00:00"
    assert result["status"] == "OPEN"
    assert "robotics" in result["topic_text"].lower()
    assert opportunity_repository.count("opportunity_snapshots") == 1
    workshops = service.workshops()
    assert workshops and workshops[0]["parent_event"] == "ICLR 2027"
    assert workshops[0]["official_url"].startswith("https://iclr.cc/")


def test_deadline_normalization_and_change_versioning(opportunity_repository):
    assert normalize_deadline("May 6, 2026 AOE").isoformat() == "2026-05-07T11:59:59+00:00"
    assert normalize_deadline("Sep 25, 2026 11:59 PM AOE").isoformat() == "2026-09-26T11:59:00+00:00"
    assert normalize_deadline("Sep 16, 2026 11:59 PM PST").isoformat() == "2026-09-17T07:59:00+00:00"
    pages = iter([_html(), _html("September 20, 2026 11:59 PM AOE")])
    service = OpportunityService(opportunity_repository, static_fetch=lambda _: next(pages))
    before = opportunity_repository.count("opportunity_snapshots")
    first = service.sync_source(_source(), now=datetime(2026, 9, 1, tzinfo=timezone.utc))
    second = service.sync_source(_source(), now=datetime(2026, 9, 1, tzinfo=timezone.utc))
    assert first["opportunity_id"] == second["opportunity_id"]
    assert second["submission_deadline_utc"] < first["submission_deadline_utc"]
    assert opportunity_repository.count("opportunity_snapshots") >= before + 1


def test_submission_deadline_wins_over_open_and_notification_dates(opportunity_repository):
    page = "Submission site open April 15, 2026. Full paper submission deadline May 6, 2026 AOE. Acceptance notification September 24, 2026."
    source = OfficialOpportunitySource("NeurIPS", 2026, "POSITION_PAPER_CALL", "Position papers", "https://official.example/position")
    result = OpportunityService(opportunity_repository, static_fetch=lambda _: page).sync_source(source, now=datetime(2026, 4, 1, tzinfo=timezone.utc))
    assert result["submission_deadline_raw"] == "May 6, 2026 AOE"


def test_deadline_parser_handles_labels_after_dates_and_rejects_video_deadlines():
    aaai = """All deadlines are anywhere on earth (UTC-12). June 17, 2026 OpenReview submission site opens for author registration. July 28, 2026 Full papers due at 11:59 PM UTC-12. November 30, 2026 Notification of final acceptance."""
    raw, normalized, zone = OpportunityService._deadline(aaai)
    assert raw == "July 28, 2026 11:59 PM UTC-12"
    assert normalized.isoformat() == "2026-07-29T11:59:00+00:00"
    assert zone == "AOE"

    iros = "March 2, 2026 Deadline for Paper submissions. March 7, 2026 Deadline for Paper Video submissions."
    assert OpportunityService._deadline(iros)[0] == "March 2, 2026"

    icra = "Sep 16, 2026 (23:59 PST): Contributed paper submission deadline."
    raw, normalized, zone = OpportunityService._deadline(icra)
    assert raw == "Sep 16, 2026 23:59 PST"
    assert normalized.isoformat() == "2026-09-17T07:59:00+00:00"
    assert zone == "PST"

    cvpr = """Abstract Submission Deadline:\nPaper Submission Deadline:\nSupplementary Materials Deadline:\nReviews Released:\nRebuttal Period:\nFinal Decisions:\nNov 07, 2025 AOE\nNov 13, 2025 AOE\nNov 20, 2025 AOE\nJanuary 22, 2026\nJanuary 23, 2026\nFebruary 20, 2026"""
    assert OpportunityService._deadline(cvpr)[0] == "Nov 13, 2025 AOE"

    eccv = """Paper Registration Deadline:\nSubmission Deadline:\nSupplementary Materials Deadline:\nReviews Released to authors:\nRebuttal Deadline:\nFinal Decisions:\nCamera ready deadline:\nFeb 26, 2026 11:00 PM CET\nMar 05, 2026 11:00 PM CET\nMar 12, 2026 11:00 PM CET\nMay 02, 2026\nMay 11, 2026 11:00 PM CEST\nJun 17, 2026\nJun 30, 2026 AOE"""
    assert OpportunityService._deadline(eccv)[0] == "Mar 05, 2026 11:00 PM CET"

    extended_video = """Sep 16, 2026 (23:59 PST): Contributed paper submission deadline. Submission Deadline Extended Open (1) Aug 5-Sept 9, 2026, and (2) Sep 18-22, 2026 (23:59 PST): Submission of accompanying videos."""
    assert OpportunityService._deadline(extended_video)[0] == "Sep 16, 2026 23:59 PST"

    abstract_then_full = "Abstract submission deadline: May 4, 2026 AoE. Full paper submission deadline: May 6, 2026 AoE."
    assert OpportunityService._deadline(abstract_then_full)[0] == "May 6, 2026 AoE"


def test_cfp_parser_ignores_script_and_style_content(opportunity_repository):
    page = """<html><head><style>.x{content:'paper deadline December 30, 2026'}</style><script>const paper_deadline='December 31, 2026';</script></head><body><p>Full paper submission deadline May 6, 2026 AOE.</p></body></html>"""
    result = OpportunityService(opportunity_repository, static_fetch=lambda _: page).sync_source(
        OfficialOpportunitySource("Clean", 2026, "MAIN_CONFERENCE_CFP", "Clean CFP", "https://official.example/clean"),
        now=datetime(2026, 4, 1, tzinfo=timezone.utc),
    )
    assert result["submission_deadline_raw"] == "May 6, 2026 AOE"
    assert "const paper_deadline" not in result["cfp_text"]


def test_closed_call_is_not_open_target_but_remains_signal(opportunity_repository):
    service = OpportunityService(opportunity_repository, static_fetch=lambda _: _html("May 6, 2026 AOE"))
    call = service.sync_source(_source(), now=datetime(2026, 9, 28, tzinfo=timezone.utc))
    assert call["status"] == "CLOSED"
    assert call not in service.upcoming(now=datetime(2026, 9, 28, tzinfo=timezone.utc))
    signals = service.generate_signals(domain="robotics")
    assert any(signal["source_id"] == call["opportunity_id"] for signal in signals)


def test_duplicate_opportunity_and_signal_provenance_are_idempotent(opportunity_repository):
    service = OpportunityService(opportunity_repository, static_fetch=lambda _: _html())
    service.sync_source(_source())
    service.sync_source(_source())
    first = service.generate_signals(domain="robotics")
    second = service.generate_signals(domain="robotics")
    assert opportunity_repository.count("opportunities") == 2  # parent CFP plus extracted workshop
    assert len(first) == len(second)
    assert all(item["evidence_refs"] and item["source_type"] == "OPPORTUNITY" for item in first)


def test_http_failure_uses_browser_fallback_and_unavailable_source_never_fabricates_deadline(opportunity_repository):
    def fail(_):
        raise RuntimeError("layout changed")
    service = OpportunityService(opportunity_repository, static_fetch=fail, browser_fetch=lambda _: _html())
    assert service.sync_source(_source())["retrieval_method"] == "PLAYWRIGHT"
    unavailable = OpportunityService(opportunity_repository, static_fetch=fail, browser_fetch=fail)
    missing_source = OfficialOpportunitySource(
        venue_name="Missing", venue_year=2027, opportunity_type="WORKSHOP_CFP", title="Unavailable source",
        official_url="https://official.example.invalid/unavailable", source_priority=100,
    )
    result = unavailable.sync_source(missing_source)
    assert result["status"] == "UNKNOWN"
    assert result["submission_deadline_utc"] is None
    assert result["stale"] is True


def _candidate(idea_id="idea-1", question="Does action-conditioned world-model uncertainty identify closed-loop VLA intervention failure before task failure?"):
    return CandidateIdea(
        idea_id=idea_id,
        title="Action-conditioned uncertainty for VLA intervention failure",
        current_belief="Open-loop world-model accuracy is a sufficient reliability proxy.",
        proposed_challenge="Closed-loop intervention ordering may disagree with open-loop accuracy.",
        scientific_question=question,
        falsifiable_claim="Action-conditioned uncertainty predicts intervention failure better than open-loop likelihood under matched task success.",
        why_now="Public robot trajectories and world-model checkpoints make the relation testable.",
        origin_signal_ids=("signal-1",), expected_contribution_type="MEASUREMENT",
        possible_target_venues=("ICLR", "CoRL"), cheap_falsifier="Replay 200 public trajectories.",
        main_risk="A strong calibration baseline explains the effect.",
    )


def test_idea_lineage_killed_memory_and_renamed_semantic_duplicate(opportunity_repository):
    dedup = IdeaDeduplicator(opportunity_repository)
    original = _candidate()
    dedup.remember_killed(original, kill_reason="covered", killing_papers=["paper-1"], failed_gate="SCOUT_GAP_AUDIT")
    renamed = _candidate("idea-2", "Can closed loop VLA intervention failures be identified by action conditioned world model uncertainty before tasks fail?")
    assert dedup.is_duplicate(renamed) is True
    lineage = dedup.record_reframe(original, _candidate("idea-3", "Does uncertainty rank policy interventions under distribution shift?"), "Changed the scientific relation to intervention ranking under shift")
    assert lineage["parent_idea_id"] == original.idea_id
    assert lineage["generation"] == 1


def test_prior_equivalence_kills_despite_title_or_corpus_source():
    idea = _candidate()
    judge = NoveltyJudge()
    prior = {
        "paper_id": "external-1", "title": "Reliable Decisions from Latent Dynamics",
        "abstract": "Action conditioned world model uncertainty predicts closed loop intervention failure before task failure in vision language action policies better than open loop likelihood under matched task success.",
        "source_scope": "EXTERNAL", "source_chunk_ids": ["chunk-1"],
    }
    result = judge.decide(idea, [prior], search_complete=True)
    assert result.decision == GapDecision.KILLED_BY_PRIOR
    assert result.killing_paper_id == "external-1"
    assert result.overlap["same_question"] and result.overlap["same_claim"]


def test_uncertain_expands_search_and_independent_runs_required():
    idea = _candidate()
    judge = NoveltyJudge(minimum_candidates=20)
    result = judge.decide(idea, [], search_complete=False)
    assert result.decision == GapDecision.NOVELTY_UNCERTAIN
    assert result.required_expansion
    gate = TopicReadinessGate()
    evidence = GateEvidence.complete()
    evidence.scout_retrieval_run_id = "same"
    evidence.reviewer_retrieval_run_id = "same"
    verdict = gate.evaluate(evidence)
    assert verdict.ready is False
    assert "independent_retrieval_runs" in verdict.missing


@pytest.mark.parametrize("field", ["data", "method", "compute", "killer_experiment"])
def test_missing_feasibility_element_blocks_topic_ready(field):
    evidence = GateEvidence.complete()
    setattr(evidence, field, None)
    verdict = TopicReadinessGate().evaluate(evidence)
    assert verdict.ready is False
    assert field in verdict.missing


def test_deadline_fit_recalculates_and_fatal_blocks():
    evidence = GateEvidence.complete()
    evidence.deadline = datetime(2026, 10, 20, tzinfo=timezone.utc)
    evidence.p90_completion_days = 18
    evidence.safety_buffer_days = 7
    evidence.future_cycle_target = False
    verdict = TopicReadinessGate(now=lambda: datetime(2026, 9, 28, tzinfo=timezone.utc)).evaluate(evidence)
    assert verdict.ready is False
    assert "deadline_fit" in verdict.missing
    evidence.future_cycle_target = True
    evidence.unresolved_fatal_objections = ("Data license prohibits redistribution",)
    verdict = TopicReadinessGate(now=lambda: datetime(2026, 9, 28, tzinfo=timezone.utc)).evaluate(evidence)
    assert "no_unresolved_fatal" in verdict.missing


def test_topic_ready_only_after_every_mandatory_gate():
    verdict = TopicReadinessGate().evaluate(GateEvidence.complete())
    assert verdict.ready is True
    assert verdict.status == "TOPIC_READY"
    assert verdict.missing == ()


class _ScriptedPipeline:
    def __init__(self, killed_waves=1):
        self.wave = 0
        self.killed_waves = killed_waves
        self.strategies = []

    def sync(self): return None
    def signals(self): return ["signal"]
    def candidates(self, minimum, strategy):
        self.wave += 1
        self.strategies.append(strategy)
        return [_candidate(f"idea-{self.wave}-{i}") for i in range(minimum)]
    def evaluate(self, candidate):
        return GateEvidence.complete()
    def cheap_screen(self, candidate): return self.wave > self.killed_waves
    def rank_survivors(self, candidates): return candidates
    def select(self, ready): return ready[0]


def test_candidate_and_whole_wave_failure_continue_until_ready():
    pipeline = _ScriptedPipeline(killed_waves=1)
    result = DiscoveryLoop(pipeline, ResearchProgram.production_default(), max_waves=3).run_until_topic_ready()
    assert result.status == "TOPIC_READY"
    assert result.waves_run == 2
    assert result.ideas_generated == 40
    assert result.ideas_killed == 20
    assert pipeline.strategies[0] != pipeline.strategies[1]


def test_twenty_killed_candidates_trigger_next_wave():
    pipeline = _ScriptedPipeline(killed_waves=2)
    result = DiscoveryLoop(pipeline, ResearchProgram.production_default(), max_waves=3).run_until_topic_ready()
    assert result.waves_run == 3
    assert result.ideas_killed == 40
    assert result.status == "TOPIC_READY"


def test_embedding_batch_crash_resumes_without_duplicates(opportunity_repository):
    initialize_literature_database(opportunity_repository.engine)
    repository = LiteratureRepository(opportunity_repository.engine)
    service = LiteratureService(repository)
    paper = service.ingest_record({
        "source": "test", "source_record_id": "resume-paper", "title": "Resume indexing",
        "abstract": "A deterministic document for crash recovery.", "publication_year": 2026,
        "identifiers": {}, "authors": [],
        "version": {"version_label": "v1", "source_url": "https://example.test/resume"},
    })
    service.ingest_full_text(paper["paper_version_id"], "Abstract\nCrash recovery must resume without duplicate embeddings.", source_url="https://example.test/resume", license_name="test fixture")
    before = repository.count("embeddings")
    model_name = f"test/resume-{uuid.uuid4()}"

    class CrashOnce(HashingEmbeddingProvider):
        def __init__(self):
            super().__init__(1024, model_name)
            object.__setattr__(self, "failed", False)

        def embed(self, value):
            if not self.failed:
                object.__setattr__(self, "failed", True)
                raise RuntimeError("injected batch crash")
            return super().embed(value)

    first = ResumableEmbeddingIndexer(repository, service, CrashOnce()).run(max_chunks=3)
    second = ResumableEmbeddingIndexer(repository, service, HashingEmbeddingProvider(1024, model_name)).run(max_chunks=3)
    assert first["errors"] == 1
    assert second["errors"] == 0
    assert repository.count("embeddings") - before == first["embedded"] + second["embedded"]


def test_embedding_shards_are_disjoint_and_complete(opportunity_repository):
    initialize_literature_database(opportunity_repository.engine)
    repository = LiteratureRepository(opportunity_repository.engine)
    service = LiteratureService(repository)
    provider = HashingEmbeddingProvider(1024, f"test/sharded-{uuid.uuid4()}")
    first = ResumableEmbeddingIndexer(repository, service, provider).run(shard_index=0, shard_count=2)
    second = ResumableEmbeddingIndexer(repository, service, provider).run(shard_index=1, shard_count=2)
    assert first["errors"] == second["errors"] == 0
    assert first["pending_at_start"] + second["pending_at_start"] == repository.count("chunks")
    assert first["embedded"] + second["embedded"] == repository.count("chunks")
    assert ResumableEmbeddingIndexer(repository, service, provider).run(shard_index=0, shard_count=2)["pending_at_start"] == 0


def test_known_prior_benchmark_preserves_real_source_identifier(opportunity_repository, tmp_path):
    initialize_literature_database(opportunity_repository.engine)
    with opportunity_repository.engine.begin() as connection:
        tables = inspect(connection).get_table_names(schema="literature")
        connection.execute(text("TRUNCATE " + ", ".join(f'literature.\"{table}\"' for table in tables) + " CASCADE"))
    repository = LiteratureRepository(opportunity_repository.engine)
    service = LiteratureService(repository)
    openalex_id = f"W{uuid.uuid4().hex}"
    paper = service.ingest_record({
        "source": "openalex", "source_record_id": openalex_id, "title": f"Verified prior {openalex_id}",
        "abstract": "A source backed study of robust robot learning under distribution shift.",
        "publication_year": 2147483647, "identifiers": {"openalex": openalex_id}, "authors": [],
        "version": {"version_label": "openalex", "source_url": f"https://openalex.org/{openalex_id}"},
    })
    service.ingest_full_text(
        paper["paper_version_id"], "Abstract\nRobust robot learning under distribution shift.",
        source_url=f"https://openalex.org/{openalex_id}", license_name="source fixture",
    )
    benchmark = build_real_known_prior_benchmark(repository, tmp_path / "known-prior.json", count=1)
    assert benchmark[0]["designated_identifier"] == f"openalex:{openalex_id.lower()}"


def test_official_proceedings_adapters_extract_real_records_without_network():
    corpus = object.__new__(OpenAlexProductionCorpus)
    acl_page = '''
    href=/2024.acl-long.1/>A Verified ACL Paper</a></strong><br>
    <a href=/people/a/>Ada Author</a></span></div>
    <div class="card bg-light mb-2 mb-lg-3 collapse abstract-collapse"><div class="card-body p-3 small">Source-backed abstract.</div></div>
    <div class="d-sm-flex align-items-stretch mb-3">
    '''
    eccv_page = '''<!-- ECCV 2024 --><dt class="ptitle"><br>
    <a href=papers/eccv_2024/papers_ECCV/html/4_ECCV_2024_paper.php>A Verified ECCV Paper</a>
    </dt><dd>Ada Author*, Bob Author</dd><dd><a href="https://link.springer.com/chapter/10.1007/example_1">DOI</a></dd>
    <!-- ECCV 2022 -->'''
    rss_index = '<a href="p001.html">paper</a>'
    rss_paper = '''<meta name="citation_title" content="A Verified RSS Paper" />
    <meta name="citation_author" content="Ada Author" /><b>Abstract:</b></p>
    <p style="text-align: justify;">Robot source-backed abstract.</p>'''

    def fetch(url):
        if "aclanthology" in url: return acl_page
        if "ecva" in url: return eccv_page
        if url.endswith("index.html"): return rss_index
        return rss_paper

    corpus._get_text = fetch
    acl = corpus._acl_anthology_records("ACL", 2024, 10)
    eccv = corpus._eccv_records(2024, 10)
    rss = corpus._rss_records(2024, 10)
    assert acl[0]["source_record_id"] == "2024.acl-long.1"
    assert acl[0]["abstract"] == "Source-backed abstract."
    assert eccv[0]["identifiers"]["doi"] == "10.1007/example_1"
    assert rss[0]["abstract"] == "Robot source-backed abstract."


def test_crossref_conference_adapter_rejects_wrong_container():
    class Response:
        def raise_for_status(self): return None
        def json(self):
            return {"message": {"items": [
                {"DOI": "10.1109/icra.real", "title": ["Real ICRA"], "container-title": ["2024 IEEE International Conference on Robotics and Automation (ICRA)"], "author": [], "URL": "https://doi.org/10.1109/icra.real"},
                {"DOI": "10.1/wrong", "title": ["Wrong venue"], "container-title": ["International Conference on Automation Quality and Testing Robotics"], "author": []},
            ]}}

    class Client:
        def get(self, *args, **kwargs): return Response()

    corpus = object.__new__(OpenAlexProductionCorpus)
    corpus.client = Client()
    records = corpus._crossref_conference_records("ICRA", 2024, 120)
    assert [record["source_record_id"] for record in records] == ["10.1109/icra.real"]


def test_dataset_url_unavailable_is_data_blocked(monkeypatch):
    monkeypatch.setattr("ai_scientist.topic_discovery.service.httpx.get", lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("offline")))
    result = ProductionTopicPipeline._data_preflight(object())
    assert result["status"] == "DATA_BLOCKED"
    assert "offline" in result["preflight"]


def test_external_search_timeout_retries_then_resumes(monkeypatch, opportunity_repository):
    initialize_literature_database(opportunity_repository.engine)

    class Response:
        headers = {"content-type": "application/json"}
        def raise_for_status(self): return None
        def json(self): return {"message": {"items": []}, "results": [], "data": [], "notes": []}

    class Client:
        calls = 0
        def get(self, *args, **kwargs):
            self.calls += 1
            if self.calls < 3:
                raise TimeoutError("injected timeout")
            return Response()

    monkeypatch.setattr("ai_scientist.topic_discovery.service.time.sleep", lambda _: None)
    client = Client()
    service = LiteratureService(LiteratureRepository(opportunity_repository.engine))
    result = ExternalPriorExpander(service, client=client).expand("robot learning reliability")
    assert result["status"] == "COMPLETE"
    assert set(result["sources"]) == {"crossref", "openalex", "semantic_scholar", "arxiv", "openreview"}
    assert client.calls >= 5


def test_novelty_audit_performs_real_citation_and_author_expansion():
    class Literature:
        def expand_citations(self, paper_id, hops=2):
            assert hops == 2
            return {f"citation-of-{paper_id}"}

        def co_citations(self, paper_id):
            return {f"co-citation-of-{paper_id}"}

        def bibliographic_coupling(self, paper_id):
            return {f"coupled-to-{paper_id}"}

        def same_author_papers(self, paper_id):
            return {f"same-author-as-{paper_id}"}

    pipeline = object.__new__(ProductionTopicPipeline)
    pipeline.literature = Literature()
    coverage = pipeline._expand_evidence_graph([{"paper_id": "prior-1"}])
    assert coverage["performed"] is True
    assert coverage["seed_papers"] == 1
    assert set(coverage["expanded_paper_ids"]) == {
        "citation-of-prior-1", "co-citation-of-prior-1", "coupled-to-prior-1", "same-author-as-prior-1"
    }
