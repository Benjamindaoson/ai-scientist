from __future__ import annotations

import argparse
import json

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
    args = parser.parse_args(argv)
    engine = create_research_engine()
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
