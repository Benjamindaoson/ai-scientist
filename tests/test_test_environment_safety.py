from pathlib import Path

import pytest


def test_database_safety_guard_rejects_non_test_database():
    from conftest import assert_test_database_url

    with pytest.raises(RuntimeError, match="refusing to run pytest"):
        assert_test_database_url(
            "postgresql+psycopg://research:research@postgres:5432/research_os"
        )


def test_database_safety_guard_accepts_dedicated_test_database():
    from conftest import assert_test_database_url

    assert_test_database_url(
        "postgresql+psycopg://research:research@postgres-test:5432/research_os_test"
    )


def test_compose_test_service_uses_dedicated_database():
    compose = (Path(__file__).parents[1] / "compose.yaml").read_text(encoding="utf-8")

    assert "postgres-test:" in compose
    assert "@postgres-test:5432/research_os_test" in compose
