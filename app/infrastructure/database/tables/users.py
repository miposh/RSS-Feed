import logging
from typing import Optional

from app.infrastructure.database.connection.base import BaseConnection
from app.infrastructure.database.models.user import UserModel
from app.infrastructure.database.query.results import SingleQueryResult, MultipleQueryResult
from app.infrastructure.database.tables.base import BaseTable
from app.infrastructure.database.tables.enums.users import UsersTableAction

logger = logging.getLogger(__name__)


class UsersTable(BaseTable):
    __tablename__ = "users"

    def __init__(self, connection: BaseConnection):
        self.connection = connection

    async def add(
        self,
        *,
        user_id: int,
        username: Optional[str] = None,
    ) -> UserModel | None:
        data: SingleQueryResult = await self.connection.insert_and_fetchone(
            sql="""
                INSERT INTO users(user_id, username)
                VALUES(%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username
                RETURNING *;
            """,
            params=(user_id, username),
        )
        user_model = data.to_model(model=UserModel)
        self._log(
            UsersTableAction.ADD,
            user_id=user_id,
            username=username,
        )
        return user_model

    async def add_many(self, *, users: list[tuple[int, str | None]]) -> list[int]:
        """Upsert several users at once.

        Args:
            users: ``(telegram_user_id, username)`` pairs

        Returns:
            Internal ``users.id`` values for the given users.
        """
        deduplicated = dict(users)

        if not deduplicated:
            return []

        data: MultipleQueryResult = await self.connection.fetchmany(
            sql="""
                INSERT INTO users(user_id, username)
                SELECT * FROM UNNEST(%s::bigint[], %s::varchar[])
                ON CONFLICT (user_id) DO UPDATE SET username = EXCLUDED.username
                RETURNING id;
            """,
            params=(list(deduplicated.keys()), list(deduplicated.values())),
        )
        user_ids = [row["id"] for row in data.data]
        self._log(UsersTableAction.ADD, count=len(user_ids))
        return user_ids
