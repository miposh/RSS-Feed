from typing import Any

from psycopg import AsyncConnection
from psycopg.rows import dict_row

from app.infrastructure.database.connection.base import BaseConnection
from app.infrastructure.database.query.results import (
    MultipleQueryResult,
    SingleQueryResult,
)


class PsycopgConnection(BaseConnection):
    def __init__(self, connection: AsyncConnection) -> None:
        connection.row_factory = dict_row
        self._connection = connection

    def transaction(self):
        """Open a nested transaction (savepoint) that can fail on its own.

        Without this, one failing statement aborts the whole surrounding
        transaction and every later query fails with ``InFailedSqlTransaction``.
        """
        return self._connection.transaction()

    async def execute(
        self,
        sql: str,
        params: tuple[Any, ...] | None = None,
    ) -> int:
        """Execute SQL and return number of affected rows."""
        async with self._connection.cursor() as cur:
            await cur.execute(sql, params)
            return cur.rowcount

    async def fetchone(
        self,
        sql: str,
        params: tuple[Any, ...] | None = None,
    ) -> SingleQueryResult:
        async with self._connection.cursor() as cur:
            await cur.execute(sql, params)
            row = await cur.fetchone()
            return SingleQueryResult(row)

    async def fetchmany(
        self,
        sql: str,
        params: tuple[Any, ...] | None = None,
    ) -> MultipleQueryResult:
        async with self._connection.cursor() as cur:
            await cur.execute(sql, params)
            rows = await cur.fetchall()
            return MultipleQueryResult(rows)

    async def insert_and_fetchone(
        self,
        sql: str,
        params: tuple[Any, ...],
    ) -> SingleQueryResult:
        return await self.fetchone(sql, params)

    async def update_and_fetchone(
        self,
        sql: str,
        params: tuple[Any, ...],
    ) -> SingleQueryResult:
        return await self.fetchone(sql, params)
