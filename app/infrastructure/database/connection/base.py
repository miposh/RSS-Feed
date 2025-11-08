from abc import ABC, abstractmethod
from typing import Any

from app.infrastructure.database.query.results import (
    SingleQueryResult,
    MultipleQueryResult,
)


class BaseConnection(ABC):
    @abstractmethod
    async def execute(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
        connection: Any | None = None,
    ) -> None:
        pass

    @abstractmethod
    async def fetchone(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
        connection: Any | None = None,
    ) -> SingleQueryResult:
        pass

    @abstractmethod
    async def fetchmany(
        self,
        sql: str,
        params: dict[str, Any] | None = None,
        connection: Any | None = None,
    ) -> MultipleQueryResult:
        pass

    @abstractmethod
    async def insert_and_fetchone(
        self,
        sql: str,
        params: dict[str, Any],
        connection: Any | None = None,
    ) -> SingleQueryResult:
        pass

    @abstractmethod
    async def insert_and_fetchmany(
        self,
        sql: str,
        params: list[dict[str, Any]],
        connection: Any | None = None,
    ) -> MultipleQueryResult:
        pass

    @abstractmethod
    async def update_and_fetchone(
        self,
        sql: str,
        params: dict[str, Any],
        connection: Any | None = None,
    ) -> SingleQueryResult:
        pass

    @abstractmethod
    async def update_and_fetchmany(
        self,
        sql: str,
        params: list[dict[str, Any]],
        connection: Any | None = None,
    ) -> MultipleQueryResult:
        pass
