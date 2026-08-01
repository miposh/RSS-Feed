from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from typing import Any

from app.infrastructure.database.query.results import (
    SingleQueryResult,
    MultipleQueryResult,
)


class BaseConnection(ABC):
    @abstractmethod
    def transaction(self) -> AbstractAsyncContextManager[Any]:
        """Open a nested transaction (savepoint) that can fail on its own."""

    @abstractmethod
    async def execute(
        self,
        sql: str,
        params: tuple[Any, ...] | None = None,
    ) -> int:
        pass

    @abstractmethod
    async def fetchone(
        self,
        sql: str,
        params: tuple[Any, ...] | None = None,
    ) -> SingleQueryResult:
        pass

    @abstractmethod
    async def fetchmany(
        self,
        sql: str,
        params: tuple[Any, ...] | None = None,
    ) -> MultipleQueryResult:
        pass

    @abstractmethod
    async def insert_and_fetchone(
        self,
        sql: str,
        params: tuple[Any, ...],
    ) -> SingleQueryResult:
        pass

    @abstractmethod
    async def update_and_fetchone(
        self,
        sql: str,
        params: tuple[Any, ...],
    ) -> SingleQueryResult:
        pass
