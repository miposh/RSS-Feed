import logging
from typing import Any
from app.infrastructure.database.connection.base import BaseConnection
from app.infrastructure.database.tables.enums.base import BaseTableActionEnum

logger = logging.getLogger(__name__)


class BaseTable:
    __tablename__: str

    def __init__(self, connection: BaseConnection):
        self.connection = connection

    def _log(self, action: str | BaseTableActionEnum, **kwargs: Any):
        # DEBUG: this fires on every single query, which floods INFO logs.
        if not logger.isEnabledFor(logging.DEBUG):
            return

        logger.debug(
            "Table='%s', Action='%s', Details: %s",
            self.__tablename__,
            action,
            ", ".join(f"{k}={v}" for k, v in kwargs.items()),
        )
