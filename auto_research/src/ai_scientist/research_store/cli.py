from __future__ import annotations

import argparse
import json
from pathlib import Path

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
    for name in ("search", "novelty-audit"):
        search = literature_commands.add_parser(name)
        search.add_argument("query")
        search.add_argument("--idea-ref")
        search.add_argument("--role", default="scout" if name == "search" else "reviewer")
        search.add_argument("--embedding-provider", choices=("bge-m3", "hashing"), default="bge-m3")

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

    if args.group == "literature":
        from ai_scientist.literature_intelligence import BGEEmbeddingProvider, HashingEmbeddingProvider, HybridSearch, LiteratureRepository, LiteratureService, NoveltyService, initialize_literature_database
        initialize_literature_database(engine)
        repository = LiteratureRepository(engine)
        service = LiteratureService(repository)
        if args.command == "sync":
            records = json.loads(Path(args.input).read_text(encoding="utf-8"))
            _json(service.ingest_records(records, job_type=args.schedule, idempotency_key=args.idempotency_key, source=args.source, scope=args.scope, cursor={"records": len(records)}))
        elif args.command == "ingest-core":
            service.bootstrap_core_venues()
            _json(service.bootstrap_core_records(json.loads(Path(args.input).read_text(encoding="utf-8"))))
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
