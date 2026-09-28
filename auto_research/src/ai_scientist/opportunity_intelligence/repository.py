from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Engine, func, insert, select, update

from . import models


def new_id() -> str:
    return str(uuid.uuid4())


class OpportunityRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def insert(self, table, **values: Any) -> dict[str, Any]:
        with self.engine.begin() as connection:
            return dict(connection.execute(insert(table).values(**values).returning(table)).one()._mapping)

    def count(self, table_name: str) -> int:
        with self.engine.connect() as connection:
            return int(connection.execute(select(func.count()).select_from(models.TABLES[table_name])).scalar_one())

    def get_opportunity_by_url(self, url: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = connection.execute(select(models.opportunities).where(models.opportunities.c.official_url == url)).first()
        return dict(row._mapping) if row else None

    def save_opportunity(self, values: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_opportunity_by_url(values["official_url"])
        if not existing:
            return self.insert(models.opportunities, opportunity_id=new_id(), **values)
        with self.engine.begin() as connection:
            row = connection.execute(update(models.opportunities).where(
                models.opportunities.c.opportunity_id == existing["opportunity_id"]
            ).values(**values).returning(models.opportunities)).one()
        return dict(row._mapping)

    def list_opportunities(self, *, status: str | None = None, kind: str | None = None) -> list[dict[str, Any]]:
        statement = select(models.opportunities)
        if status:
            statement = statement.where(models.opportunities.c.status == status)
        if kind:
            statement = statement.where(models.opportunities.c.opportunity_type == kind)
        with self.engine.connect() as connection:
            return [dict(row._mapping) for row in connection.execute(statement.order_by(models.opportunities.c.submission_deadline_utc.nulls_last()))]

    def get_opportunity(self, opportunity_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = connection.execute(select(models.opportunities).where(models.opportunities.c.opportunity_id == opportunity_id)).first()
        return dict(row._mapping) if row else None

    def get_lineage(self, idea_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = connection.execute(select(models.idea_lineage).where(models.idea_lineage.c.idea_id == idea_id)).first()
        return dict(row._mapping) if row else None

    def list_killed_lineage(self) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            return [dict(row._mapping) for row in connection.execute(select(models.idea_lineage).where(models.idea_lineage.c.status == "KILLED"))]
