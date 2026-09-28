from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse
import uuid

from .artifact_store import ArtifactStore
from .db import create_research_engine, initialize_database
from .repository import ResearchRepository
from .sqlite_import import SQLiteImporter


def _json(value) -> None:
    print(json.dumps(value, sort_keys=True, default=str))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-scientist")
    groups = parser.add_subparsers(dest="group", required=True)
    db = groups.add_parser("db")
    db_commands = db.add_subparsers(dest="command", required=True)
    db_commands.add_parser("init")
    migrate = db_commands.add_parser("migrate")
    migrate.add_argument("--sqlite")
    import_sqlite = db_commands.add_parser("import-sqlite")
    import_sqlite.add_argument("path")

    literature = groups.add_parser("literature")
    literature_commands = literature.add_subparsers(dest="command", required=True)
    sync = literature_commands.add_parser("sync")
    sync.add_argument("schedule", choices=("daily", "weekly", "monthly", "on-demand"))
    sync.add_argument("--source", default="file")
    sync.add_argument("--scope", default="external")
    sync.add_argument("--idempotency-key", required=True)
    sync.add_argument("--input", required=True)
    ingest_core = literature_commands.add_parser("ingest-core")
    ingest_core.add_argument("--input", default="benchmarks/literature/core_bootstrap_v1.json")
    production_sync = literature_commands.add_parser("sync-production")
    production_sync.add_argument("--max-per-edition", type=int, default=0)
    production_sync.add_argument("--venues", nargs="*")
    production_sync.add_argument("--years", nargs="*", type=int)
    production_embed = literature_commands.add_parser("embed-production")
    production_embed.add_argument("--embedding-provider", choices=("bge-m3", "hashing"), default="bge-m3")
    production_embed.add_argument("--batch-size", type=int, default=64)
    production_embed.add_argument("--max-chunks", type=int, default=0)
    production_embed.add_argument("--shard-index", type=int, default=0)
    production_embed.add_argument("--shard-count", type=int, default=1)
    production_embed.add_argument("--output")
    literature_commands.add_parser("corpus-status")
    build_benchmark = literature_commands.add_parser("build-benchmark")
    build_benchmark.add_argument("--count", type=int, default=100)
    build_benchmark.add_argument("--output", default="benchmarks/literature/known_prior_production_v1.json")
    run_benchmark = literature_commands.add_parser("run-benchmark")
    run_benchmark.add_argument("--input", default="benchmarks/literature/known_prior_production_v1.json")
    run_benchmark.add_argument("--embedding-provider", choices=("bge-m3", "hashing"), default="bge-m3")
    run_benchmark.add_argument("--output")
    for name in ("search", "novelty-audit"):
        search = literature_commands.add_parser(name)
        search.add_argument("query")
        search.add_argument("--idea-ref")
        search.add_argument("--role", default="scout" if name == "search" else "reviewer")
        search.add_argument("--embedding-provider", choices=("bge-m3", "hashing"), default="bge-m3")

    opportunities = groups.add_parser("opportunities")
    opportunity_commands = opportunities.add_subparsers(dest="command", required=True)
    opportunity_commands.add_parser("sync")
    opportunity_commands.add_parser("list")
    show_opportunity = opportunity_commands.add_parser("show")
    show_opportunity.add_argument("opportunity_id")
    opportunity_commands.add_parser("workshops")
    opportunity_commands.add_parser("upcoming")
    opportunity_commands.add_parser("schedules")

    topic = groups.add_parser("topic")
    topic_commands = topic.add_subparsers(dest="command", required=True)
    for name in ("discover", "run-until-ready"):
        discovery = topic_commands.add_parser(name)
        discovery.add_argument("--embedding-provider", choices=("bge-m3", "hashing"), default="bge-m3")
        discovery.add_argument("--max-waves", type=int, default=0)
        discovery.add_argument("--no-live-sync", action="store_true")
        discovery.add_argument("--candidate-file", required=True)
    topic_commands.add_parser("status")
    topic_commands.add_parser("list")
    reaudit = topic_commands.add_parser("re-audit-current")
    reaudit.add_argument("--embedding-provider", choices=("bge-m3", "hashing"), default="bge-m3")
    topic_reports = topic_commands.add_parser("reports")
    topic_reports.add_argument("--benchmark-result")
    for name in ("show", "audit", "lineage", "dossier"):
        command = topic_commands.add_parser(name)
        command.add_argument("idea_id")

    research = groups.add_parser("research")
    research_commands = research.add_subparsers(dest="command", required=True)
    create = research_commands.add_parser("create")
    create.add_argument("--name", required=True)
    create.add_argument("--domain", default="")
    create.add_argument("--seed-question", default="")
    run = research_commands.add_parser("run")
    run.add_argument("project_id")
    run.add_argument("--thread-id", required=True)
    run.add_argument("--decision-id")
    run.add_argument("--hypothesis-id")
    run.add_argument("--protocol-version-id")
    run.add_argument("--experiment-spec-id")
    run.add_argument("--executor", choices=("codex", "human", "mock"), default="codex")
    resume = research_commands.add_parser("resume")
    resume.add_argument("project_id")
    resume.add_argument("--thread-id", required=True)
    resume.add_argument("--response", required=True)
    resume.add_argument("--executor", choices=("codex", "human", "mock"), default="codex")
    status = research_commands.add_parser("status")
    status.add_argument("project_id")
    for name in ("approve", "reject"):
        approval = research_commands.add_parser(name)
        approval.add_argument("approval_id")
        approval.add_argument("--by", required=True)

    export = groups.add_parser("export")
    export_commands = export.add_subparsers(dest="command", required=True)
    package = export_commands.add_parser("package")
    package.add_argument("project_id")
    package.add_argument("destination")
    package.add_argument("--workspace", default=".")
    return parser


def _agent_lab(kind: str, config):
    from ai_scientist.research_os.agents import AgentLab, CodexExecutor, HumanAssistedExecutor, MockExecutor, ResearchRole
    executor = {
        "codex": CodexExecutor(config.codex_executable, timeout_seconds=config.codex_timeout_seconds),
        "human": HumanAssistedExecutor(),
        "mock": MockExecutor(),
    }[kind]
    return AgentLab({role: executor for role in ResearchRole})


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    engine = create_research_engine()
    if args.group == "db":
        initialize_database(engine)
        if args.command == "migrate" and args.sqlite:
            _json(SQLiteImporter(ResearchRepository(engine)).import_database(args.sqlite))
        elif args.command == "import-sqlite":
            _json(SQLiteImporter(ResearchRepository(engine)).import_database(args.path))
        return 0

    if args.group == "opportunities":
        from ai_scientist.opportunity_intelligence import MONITORING_JOBS, OpportunityRepository, OpportunityService, initialize_opportunity_database
        initialize_opportunity_database(engine)
        browser_fetch = None
        if args.command == "sync":
            from ai_scientist.research_os.actions import ActionBroker, PlaywrightActionHandler
            from ai_scientist.research_os.agents import ActionRequest
            broker = ActionBroker("artifacts/opportunity_actions", handlers={"playwright": PlaywrightActionHandler()})

            def browser_fetch(url: str) -> str:
                fingerprint = hashlib.sha256(url.encode()).hexdigest()
                attempt_id = str(uuid.uuid4())
                result = broker.execute(ActionRequest(
                    action_id=f"opportunity-{attempt_id}", operation="fetch_official_page", target=url,
                    domain=urlparse(url).hostname, allowed_channels=["playwright"],
                    idempotency_key=f"opportunity:{fingerprint}:{attempt_id}", payload={"wait_until": "domcontentloaded"},
                ))
                return result["content"]

        service = OpportunityService(OpportunityRepository(engine), browser_fetch=browser_fetch)
        if args.command == "sync":
            _json(service.sync())
        elif args.command == "list":
            _json(service.list())
        elif args.command == "show":
            result = service.show(args.opportunity_id)
            if not result:
                raise KeyError(args.opportunity_id)
            _json(result)
        elif args.command == "workshops":
            _json(service.workshops())
        elif args.command == "upcoming":
            _json(service.upcoming())
        elif args.command == "schedules":
            _json(MONITORING_JOBS)
        return 0

    if args.group == "topic":
        from ai_scientist.literature_intelligence import BGEEmbeddingProvider, HashingEmbeddingProvider, LiteratureRepository, initialize_literature_database
        from ai_scientist.opportunity_intelligence import OpportunityRepository, initialize_opportunity_database
        from ai_scientist.topic_discovery import ProductionTopicPipeline, RecordedCodexCandidateGenerator, TopicDiscoveryService, TopicReportWriter
        initialize_opportunity_database(engine)
        initialize_literature_database(engine)
        provider = BGEEmbeddingProvider() if getattr(args, "embedding_provider", "hashing") == "bge-m3" else HashingEmbeddingProvider()
        generator = RecordedCodexCandidateGenerator(args.candidate_file) if getattr(args, "candidate_file", None) else None
        service = TopicDiscoveryService(ProductionTopicPipeline(OpportunityRepository(engine), LiteratureRepository(engine), provider, candidate_generator=generator, live_sync=not getattr(args, "no_live_sync", False)))
        if args.command in {"discover", "run-until-ready"}:
            max_waves = args.max_waves or (1 if args.command == "discover" else None)
            _json(service.run_until_ready(max_waves=max_waves))
        elif args.command == "status":
            _json(service.status())
        elif args.command == "re-audit-current":
            _json(service.reaudit_current())
        elif args.command == "list":
            _json(service.list())
        elif args.command == "show":
            _json(service.show(args.idea_id))
        elif args.command == "audit":
            _json(service.audits(args.idea_id))
        elif args.command == "lineage":
            _json(service.lineage(args.idea_id))
        elif args.command == "dossier":
            _json(service.dossier(args.idea_id))
        elif args.command == "reports":
            metrics = json.loads(Path(args.benchmark_result).read_text(encoding="utf-8")) if args.benchmark_result else None
            _json({"reports": TopicReportWriter(engine).write(benchmark_result=metrics)})
        return 0

    if args.group == "literature":
        from ai_scientist.literature_intelligence import BGEEmbeddingProvider, CORE_VENUES, CORE_YEARS, HashingEmbeddingProvider, HybridSearch, LiteratureRepository, LiteratureService, NoveltyService, OpenAlexProductionCorpus, ResumableEmbeddingIndexer, build_real_known_prior_benchmark, corpus_counts, initialize_literature_database
        initialize_literature_database(engine)
        repository = LiteratureRepository(engine)
        service = LiteratureService(repository)
        if args.command == "sync":
            records = json.loads(Path(args.input).read_text(encoding="utf-8"))
            _json(service.ingest_records(records, job_type=args.schedule, idempotency_key=args.idempotency_key, source=args.source, scope=args.scope, cursor={"records": len(records)}))
        elif args.command == "ingest-core":
            service.bootstrap_core_venues()
            _json(service.bootstrap_core_records(json.loads(Path(args.input).read_text(encoding="utf-8"))))
        elif args.command == "sync-production":
            result = OpenAlexProductionCorpus(service).sync(
                venues=tuple(args.venues or CORE_VENUES), years=tuple(args.years or CORE_YEARS),
                max_per_edition=args.max_per_edition,
            )
            _json({"started_at": result.started_at, "completed_at": result.completed_at, "papers": result.papers, "venue_year": result.venue_year, "errors": result.errors})
        elif args.command == "embed-production":
            provider = BGEEmbeddingProvider() if args.embedding_provider == "bge-m3" else HashingEmbeddingProvider()
            result = ResumableEmbeddingIndexer(repository, service, provider).run(
                batch_size=args.batch_size, max_chunks=args.max_chunks,
                shard_index=args.shard_index, shard_count=args.shard_count,
            )
            if args.output:
                output = Path(args.output)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
            _json(result)
        elif args.command == "corpus-status":
            _json(corpus_counts(repository))
        elif args.command == "build-benchmark":
            _json({"output": args.output, "questions": len(build_real_known_prior_benchmark(
                repository, args.output, count=args.count, embedding_model="BAAI/bge-m3"
            ))})
        elif args.command == "run-benchmark":
            provider = BGEEmbeddingProvider() if args.embedding_provider == "bge-m3" else HashingEmbeddingProvider()
            benchmark = service.load_known_prior_benchmark(args.input)
            result = service.run_known_prior_benchmark(benchmark, HybridSearch(repository, provider))
            if args.output:
                output = Path(args.output)
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
            _json(result)
        else:
            provider = BGEEmbeddingProvider() if args.embedding_provider == "bge-m3" else HashingEmbeddingProvider()
            search = HybridSearch(repository, provider)
            result = search.search(args.query, actor_role=args.role, idea_ref=args.idea_ref) if args.command == "search" else NoveltyService(search).audit(args.idea_ref or args.query, args.query, actor_role=args.role, external=True)
            _json(result)
        return 0

    repository = ResearchRepository(engine)
    initialize_database(engine)
    if args.group == "research":
        if args.command == "create":
            _json(repository.create_project(args.name, args.domain, args.seed_question))
            return 0
        if args.command == "status":
            project = repository.get_project(args.project_id)
            if not project:
                raise KeyError(args.project_id)
            _json({"project": project, "latest_decisions": {kind: repository.get_latest_decision(args.project_id, kind) for kind in ("IDEA_GATE", "PROTOCOL_GATE", "KILLER_GATE", "PROGRESS_GATE", "AUDIT_GATE")}})
            return 0
        if args.command in {"approve", "reject"}:
            _json(repository.update_approval(args.approval_id, status="APPROVED" if args.command == "approve" else "REJECTED", approved_by=args.by))
            return 0

        from langgraph.types import Command
        from ai_scientist.experiment.runner import ExperimentRunner
        from ai_scientist.research_os.config import ResearchOSConfig
        from ai_scientist.research_os.graph import ResearchOSRuntime, build_research_graph, default_state, postgres_checkpointer
        config = ResearchOSConfig.from_env()
        runtime = ResearchOSRuntime(repository, ExperimentRunner(), agent_lab=_agent_lab(args.executor, config), task_workspace=str(Path.cwd()))
        graph_config = {"configurable": {"thread_id": args.thread_id}}
        with postgres_checkpointer(config.database_url) as checkpointer:
            graph = build_research_graph(runtime, checkpointer)
            result = graph.invoke(default_state(args.project_id, args.hypothesis_id, args.protocol_version_id, args.experiment_spec_id, args.decision_id), graph_config) if args.command == "run" else graph.invoke(Command(resume=json.loads(args.response)), graph_config)
        _json(result)
        return 0

    if args.group == "export" and args.command == "package":
        from ai_scientist.research_os.config import ResearchOSConfig
        from ai_scientist.research_os.package_export import ResearchPackageExporter
        config = ResearchOSConfig.from_env()
        path = ResearchPackageExporter(repository, ArtifactStore(config.artifact_root, repository)).export(args.project_id, args.destination, workspace=args.workspace)
        _json({"package": str(path)})
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
