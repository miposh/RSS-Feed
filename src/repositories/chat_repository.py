"""Repository for managing Telegram chats"""
import logging
from typing import List, Optional, Tuple
from repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ChatRepository(BaseRepository):
    """Repository for chat operations"""

    async def add_or_update_chat(
        self, 
        chat_id: int, 
        title: str = None, 
        username: str = None,
        chat_type: str = 'group'
    ) -> Optional[int]:
        """Add or update chat information"""
        try:
            cursor = await self.execute_and_commit(
                """
                INSERT INTO chats (chat_id, title, username, chat_type)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    title = excluded.title,
                    username = excluded.username,
                    chat_type = excluded.chat_type,
                    updated_at = datetime('now', 'utc')
                """,
                (chat_id, title, username, chat_type)
            )
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error adding/updating chat {chat_id}: {e}", exc_info=True)
            return None

    async def get_chat_by_telegram_id(self, chat_id: int) -> Optional[Tuple]:
        """Get chat by Telegram chat_id"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                "SELECT id, chat_id, title, username, chat_type, ai_enabled FROM chats WHERE chat_id = ?",
                (chat_id,)
            )
            return await cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting chat {chat_id}: {e}", exc_info=True)
            return None

    async def get_chat_id(self, telegram_chat_id: int) -> Optional[int]:
        """Get internal chat id by Telegram chat_id"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                "SELECT id FROM chats WHERE chat_id = ?",
                (telegram_chat_id,)
            )
            result = await cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting chat id for {telegram_chat_id}: {e}", exc_info=True)
            return None

    async def get_all_chats(self) -> List[Tuple]:
        """Get all chats"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                """
                SELECT id, chat_id, title, username, chat_type, ai_enabled 
                FROM chats 
                ORDER BY created_at DESC
                """
            )
            return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting all chats: {e}", exc_info=True)
            return []

    async def toggle_ai(self, chat_id: int) -> bool:
        """Toggle AI rewrite for chat"""
        try:
            await self.execute_and_commit(
                """
                UPDATE chats 
                SET ai_enabled = CASE WHEN ai_enabled = 1 THEN 0 ELSE 1 END,
                    updated_at = datetime('now', 'utc')
                WHERE chat_id = ?
                """,
                (chat_id,)
            )
            return True
        except Exception as e:
            logger.error(f"Error toggling AI for chat {chat_id}: {e}", exc_info=True)
            return False

    async def set_ai_enabled(self, chat_id: int, enabled: bool) -> bool:
        """Set AI rewrite status for chat"""
        try:
            await self.execute_and_commit(
                """
                UPDATE chats 
                SET ai_enabled = ?,
                    updated_at = datetime('now', 'utc')
                WHERE chat_id = ?
                """,
                (1 if enabled else 0, chat_id)
            )
            return True
        except Exception as e:
            logger.error(f"Error setting AI status for chat {chat_id}: {e}", exc_info=True)
            return False

    async def delete_chat(self, chat_id: int) -> bool:
        """Delete chat (cascades to subscriptions and deliveries)"""
        try:
            await self.execute_and_commit(
                "DELETE FROM chats WHERE chat_id = ?",
                (chat_id,)
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting chat {chat_id}: {e}", exc_info=True)
            return False
