from __future__ import annotations

import os
from urllib.parse import urlsplit


DEFAULT_TEST_DATABASE_URL = (
    "postgresql+psycopg://research:research@localhost:55432/research_os_test"
)


def assert_test_database_url(database_url: str) -> None:
    database_name = urlsplit(database_url).path.rsplit("/", 1)[-1]
    if not database_name.endswith("_test"):
        raise RuntimeError(
            f"refusing to run pytest against non-test database {database_name!r}"
        )


def pytest_sessionstart(session) -> None:
    database_url = os.environ.setdefault(
        "RESEARCH_DATABASE_URL", DEFAULT_TEST_DATABASE_URL
    )
    assert_test_database_url(database_url)
