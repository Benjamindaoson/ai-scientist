from __future__ import annotations

import os
from dataclasses import dataclass

from sqlalchemy import Engine, create_engine, text

from .models import metadata


DEFAULT_DATABASE_URL = "postgresql+psycopg://research:research@localhost:55432/research_os"


@dataclass(frozen=True)
class ResearchStoreConfig:
    database_url: str
    artifact_root: str = "research_output/artifacts"

    @classmethod
    def from_env(cls) -> "ResearchStoreConfig":
        return cls(
            database_url=os.getenv("RESEARCH_DATABASE_URL", DEFAULT_DATABASE_URL),
            artifact_root=os.getenv("RESEARCH_ARTIFACT_ROOT", "research_output/artifacts"),
        )


def create_research_engine(database_url: str | None = None) -> Engine:
    return create_engine(database_url or ResearchStoreConfig.from_env().database_url, pool_pre_ping=True)


def initialize_database(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS research"))
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    metadata.create_all(engine)
