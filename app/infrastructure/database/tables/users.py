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

    async def delete(self, *, user_id: int) -> None:
        await self.connection.execute(
            sql="""
                DELETE FROM users WHERE user_id = %s;
            """,
            params=(user_id,),
        )
        self._log(UsersTableAction.DELETE, user_id=user_id)

    async def get_user(self, *, user_id: int) -> UserModel | None:
        data: SingleQueryResult = await self.connection.fetchone(
            sql="""
                SELECT id, user_id, username, created_at, updated_at
                FROM users
                WHERE user_id = %s
            """,
            params=(user_id,),
        )
        user_model = data.to_model(model=UserModel)
        self._log(UsersTableAction.GET_USER, user_id=user_id)
        return user_model

    async def get_user_by_username(self, *, username: str) -> UserModel | None:
        data: SingleQueryResult = await self.connection.fetchone(
            sql="""
                SELECT id, user_id, username, created_at, updated_at
                FROM users
                WHERE username = %s
            """,
            params=(username,),
        )
        user_model = data.to_model(model=UserModel)
        self._log(UsersTableAction.GET_USER_BY_USERNAME, username=username)
        return user_model

    async def update_username(self, *, user_id: int, username: str) -> UserModel | None:
        data: SingleQueryResult = await self.connection.update_and_fetchone(
            sql="""
                UPDATE users
                SET username = %s
                WHERE user_id = %s
                RETURNING *;
            """,
            params=(username, user_id),
        )
        user_model = data.to_model(model=UserModel, raise_if_empty=True)
        self._log(UsersTableAction.UPDATE_USERNAME, user_id=user_id, username=username)
        return user_model

    async def get_all_users(self) -> list[UserModel] | None:
        data: MultipleQueryResult = await self.connection.fetchmany(
            sql="""
                SELECT id, user_id, username, created_at, updated_at
                FROM users
                ORDER BY created_at DESC
            """,
        )
        users = data.to_models(model=UserModel)
        self._log(UsersTableAction.GET_ALL_USERS, count=len(data) if data else 0)
        return users
