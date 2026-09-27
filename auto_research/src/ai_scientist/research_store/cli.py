from __future__ import annotations

import argparse
import json
from pathlib import Path

from .db import ResearchStoreConfig, create_research_engine, initialize_database
from .repository import ResearchRepository
from .sqlite_import import SQLiteImporter


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ai-scientist")
    subcommands = parser.add_subparsers(dest="group", required=True)
    db = subcommands.add_parser("db")
    db_commands = db.add_subparsers(dest="command", required=True)
    db_commands.add_parser("init")
    migrate = db_commands.add_parser("migrate")
    migrate.add_argument("--sqlite")
    import_sqlite = db_commands.add_parser("import-sqlite")
    import_sqlite.add_argument("path")
    literature = subcommands.add_parser("literature")
    literature_commands = literature.add_subparsers(dest="command", required=True)
    sync = literature_commands.add_parser("sync")
    sync.add_argument("schedule", choices=("daily", "weekly", "monthly", "on-demand"))
    sync.add_argument("--source", default="file")
    sync.add_argument("--scope", default="external")
    sync.add_argument("--idempotency-key", required=True)
    sync.add_argument("--input", required=True)
    args = parser.parse_args(argv)
    engine = create_research_engine()
    if args.group == "literature":
        from ai_scientist.literature_intelligence import LiteratureRepository, LiteratureService, initialize_literature_database

        initialize_literature_database(engine)
        records = json.loads(Path(args.input).read_text(encoding="utf-8"))
        result = LiteratureService(LiteratureRepository(engine)).ingest_records(
            records, job_type=args.schedule, idempotency_key=args.idempotency_key,
            source=args.source, scope=args.scope, cursor={"records": len(records)},
        )
        print(json.dumps(result, sort_keys=True, default=str))
        return 0
    if args.command in {"init", "migrate"}:
        initialize_database(engine)
        if args.command == "migrate" and args.sqlite:
            print(json.dumps(SQLiteImporter(ResearchRepository(engine)).import_database(args.sqlite), sort_keys=True))
        return 0
    if args.command == "import-sqlite":
        initialize_database(engine)
        print(json.dumps(SQLiteImporter(ResearchRepository(engine)).import_database(args.path), sort_keys=True))
        return 0
    return 2
