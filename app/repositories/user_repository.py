import logging
from typing import Optional, Tuple, List
from repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):

    async def add_or_update_user(
        self,
        user_id: int,
        username: str = None
    ) -> bool:
        try:
            await self.execute_and_commit(
                """
                INSERT INTO users (id, username)
                VALUES (?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    username = excluded.username
                """,
                (user_id, username)
            )
            return True
        except Exception as e:
            logger.error(f"Error adding/updating user {user_id}: {e}", exc_info=True)
            return False

    async def get_user_by_id(self, user_id: int) -> Optional[Tuple]:
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                "SELECT id, username FROM users WHERE id = ?",
                (user_id,)
            )
            return await cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}", exc_info=True)
            return None

    async def get_user_by_username(self, username: str) -> Optional[Tuple]:
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                "SELECT id, username FROM users WHERE username = ?",
                (username,)
            )
            return await cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}", exc_info=True)
            return None

    async def get_all_users(self) -> List[Tuple]:
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                """
                SELECT id, username 
                FROM users
                """
            )
            return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting all users: {e}", exc_info=True)
            return []

    async def delete_user(self, user_id: int) -> bool:
        try:
            await self.execute_and_commit(
                "DELETE FROM users WHERE id = ?",
                (user_id,)
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting user {user_id}: {e}", exc_info=True)
            return False

    async def user_exists(self, user_id: int) -> bool:
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                "SELECT 1 FROM users WHERE id = ? LIMIT 1",
                (user_id,)
            )
            result = await cursor.fetchone()
            return result is not None
        except Exception as e:
            logger.error(f"Error checking user exists {user_id}: {e}", exc_info=True)
            return False
