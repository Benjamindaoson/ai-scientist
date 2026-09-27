from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ResearchOSConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    database_url: str
    artifact_root: Path = Path("artifacts")
    codex_executable: str = "codex"
    codex_timeout_seconds: int = 900
    latex_compiler: str | None = None
    browser_enabled: bool = False
    rpa_enabled: bool = False
    paid_api_enabled: bool = False
    resource_budget: dict = Field(default_factory=lambda: {"max_experiment_minutes": 60, "max_agent_tasks": 50})
    literature_artifact_root: Path = Path("artifacts/literature")
    embedding_model: str = "BAAI/bge-m3"
    conference_years: tuple[int, ...] = tuple(range(2022, 2027))
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "ResearchOSConfig":
        return cls(
            database_url=os.getenv("RESEARCH_DATABASE_URL", "postgresql+psycopg://research:research@localhost:55432/research_os"),
            artifact_root=Path(os.getenv("RESEARCH_ARTIFACT_ROOT", "artifacts")),
            codex_executable=os.getenv("RESEARCH_CODEX_EXECUTABLE", "codex"),
            codex_timeout_seconds=int(os.getenv("RESEARCH_CODEX_TIMEOUT_SECONDS", "900")),
            latex_compiler=os.getenv("RESEARCH_LATEX_COMPILER") or None,
            browser_enabled=os.getenv("RESEARCH_BROWSER_ENABLED", "false").lower() == "true",
            rpa_enabled=os.getenv("RESEARCH_RPA_ENABLED", "false").lower() == "true",
            paid_api_enabled=os.getenv("RESEARCH_PAID_API_ENABLED", "false").lower() == "true",
            literature_artifact_root=Path(os.getenv("RESEARCH_LITERATURE_ROOT", "artifacts/literature")),
            embedding_model=os.getenv("RESEARCH_EMBEDDING_MODEL", "BAAI/bge-m3"),
            conference_years=tuple(int(year) for year in os.getenv("RESEARCH_CONFERENCE_YEARS", "2022,2023,2024,2025,2026").split(",")),
            resource_budget=json.loads(os.getenv("RESEARCH_RESOURCE_BUDGET_JSON", '{"max_experiment_minutes":60,"max_agent_tasks":50}')),
            log_level=os.getenv("RESEARCH_LOG_LEVEL", "INFO"),
        )
