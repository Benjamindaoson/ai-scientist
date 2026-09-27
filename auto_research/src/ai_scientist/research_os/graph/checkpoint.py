from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg import Connection
from psycopg.rows import dict_row


def _psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


@contextmanager
def postgres_checkpointer(database_url: str) -> Iterator[PostgresSaver]:
    os.environ.setdefault("LANGGRAPH_STRICT_MSGPACK", "true")
    base_url = _psycopg_url(database_url)
    with Connection.connect(base_url, autocommit=True) as setup_connection:
        setup_connection.execute("CREATE SCHEMA IF NOT EXISTS orchestration")
    with Connection.connect(
        base_url, autocommit=True, prepare_threshold=0, row_factory=dict_row,
        options="-c search_path=orchestration,public",
    ) as connection:
        saver = PostgresSaver(connection)
        saver.setup()
        yield saver
