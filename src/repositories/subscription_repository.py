"""Repository for managing chat-feed subscriptions"""
import logging
from typing import List, Optional, Tuple
from repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class SubscriptionRepository(BaseRepository):
    """Repository for subscription operations"""

    async def subscribe(self, chat_internal_id: int, feed_id: int, filters_json: str = None) -> bool:
        """Subscribe chat to feed"""
        try:
            await self.execute_and_commit(
                """
                INSERT INTO subscriptions (chat_id, feed_id, filters_json, active)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(chat_id, feed_id) DO UPDATE SET
                    active = 1,
                    filters_json = excluded.filters_json
                """,
                (chat_internal_id, feed_id, filters_json)
            )
            return True
        except Exception as e:
            logger.error(f"Error subscribing chat {chat_internal_id} to feed {feed_id}: {e}", exc_info=True)
            return False

    async def unsubscribe(self, chat_internal_id: int, feed_id: int) -> bool:
        """Unsubscribe chat from feed (delete subscription)"""
        try:
            await self.execute_and_commit(
                "DELETE FROM subscriptions WHERE chat_id = ? AND feed_id = ?",
                (chat_internal_id, feed_id)
            )
            return True
        except Exception as e:
            logger.error(f"Error unsubscribing chat {chat_internal_id} from feed {feed_id}: {e}", exc_info=True)
            return False

    async def toggle_subscription(self, chat_internal_id: int, feed_id: int) -> bool:
        """Toggle subscription active status"""
        try:
            await self.execute_and_commit(
                """
                UPDATE subscriptions 
                SET active = CASE WHEN active = 1 THEN 0 ELSE 1 END
                WHERE chat_id = ? AND feed_id = ?
                """,
                (chat_internal_id, feed_id)
            )
            return True
        except Exception as e:
            logger.error(f"Error toggling subscription: {e}", exc_info=True)
            return False

    async def get_subscriptions_for_chat(self, chat_internal_id: int) -> List[Tuple]:
        """Get all subscriptions for a chat"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                """
                SELECT s.id, s.feed_id, s.active, f.url, f.title, f.active as feed_active
                FROM subscriptions s
                JOIN feeds f ON f.id = s.feed_id
                WHERE s.chat_id = ?
                ORDER BY s.created_at DESC
                """,
                (chat_internal_id,)
            )
            return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting subscriptions for chat {chat_internal_id}: {e}", exc_info=True)
            return []

    async def get_active_subscriptions(self) -> List[Tuple]:
        """Get all active subscriptions (chat_id, feed_id, telegram_chat_id, feed_url)"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                """
                SELECT s.chat_id, s.feed_id, c.chat_id as telegram_chat_id, f.url, f.id as feed_id
                FROM subscriptions s
                JOIN chats c ON c.id = s.chat_id
                JOIN feeds f ON f.id = s.feed_id
                WHERE s.active = 1 AND f.active = 1
                """
            )
            return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting active subscriptions: {e}", exc_info=True)
            return []

    async def is_subscribed(self, chat_internal_id: int, feed_id: int) -> bool:
        """Check if chat is subscribed to feed"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                "SELECT 1 FROM subscriptions WHERE chat_id = ? AND feed_id = ? AND active = 1",
                (chat_internal_id, feed_id)
            )
            result = await cursor.fetchone()
            return result is not None
        except Exception as e:
            logger.error(f"Error checking subscription: {e}", exc_info=True)
            return False

    async def get_chats_for_feed(self, feed_id: int) -> List[int]:
        """Get all chat IDs subscribed to a feed"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                """
                SELECT c.chat_id 
                FROM subscriptions s
                JOIN chats c ON c.id = s.chat_id
                WHERE s.feed_id = ? AND s.active = 1
                """,
                (feed_id,)
            )
            results = await cursor.fetchall()
            return [row[0] for row in results]
        except Exception as e:
            logger.error(f"Error getting chats for feed {feed_id}: {e}", exc_info=True)
            return []
