"""Repository for managing RSS feeds"""
import logging
from typing import List, Optional, Tuple
from repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class FeedRepository(BaseRepository):
    """Repository for feed operations"""

    async def add_feed(
        self, 
        url: str, 
        title: str = None,
        pull_interval: int = 300,
        active: bool = True
    ) -> Optional[int]:
        """Add or update RSS feed"""
        try:
            cursor = await self.execute_and_commit(
                """
                INSERT INTO feeds (url, title, pull_interval, active)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(url) DO UPDATE SET
                    title = COALESCE(excluded.title, feeds.title),
                    pull_interval = excluded.pull_interval,
                    active = excluded.active,
                    updated_at = datetime('now', 'utc')
                """,
                (url, title, pull_interval, 1 if active else 0)
            )
            
            # Get feed id
            conn = await self.get_connection()
            cursor = await conn.execute("SELECT id FROM feeds WHERE url = ?", (url,))
            result = await cursor.fetchone()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error adding feed {url}: {e}", exc_info=True)
            return None

    async def get_feed_by_url(self, url: str) -> Optional[Tuple]:
        """Get feed by URL"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                "SELECT id, url, title, last_modified, etag, pull_interval, active FROM feeds WHERE url = ?",
                (url,)
            )
            return await cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting feed {url}: {e}", exc_info=True)
            return None

    async def get_feed_by_id(self, feed_id: int) -> Optional[Tuple]:
        """Get feed by ID"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                "SELECT id, url, title, last_modified, etag, pull_interval, active FROM feeds WHERE id = ?",
                (feed_id,)
            )
            return await cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting feed {feed_id}: {e}", exc_info=True)
            return None

    async def get_all_feeds(self) -> List[Tuple]:
        """Get all feeds"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                """
                SELECT id, url, title, last_modified, etag, pull_interval, active
                FROM feeds
                ORDER BY created_at DESC
                """
            )
            return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting all feeds: {e}", exc_info=True)
            return []

    async def get_active_feeds(self) -> List[Tuple]:
        """Get all active feeds"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                """
                SELECT id, url, title, last_modified, etag, pull_interval
                FROM feeds
                WHERE active = 1
                ORDER BY updated_at ASC
                """
            )
            return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting active feeds: {e}", exc_info=True)
            return []

    async def update_feed_metadata(
        self,
        feed_id: int,
        title: str = None,
        last_modified: str = None,
        etag: str = None
    ) -> bool:
        """Update feed metadata after fetch"""
        try:
            await self.execute_and_commit(
                """
                UPDATE feeds 
                SET title = COALESCE(?, title),
                    last_modified = COALESCE(?, last_modified),
                    etag = COALESCE(?, etag),
                    updated_at = datetime('now', 'utc')
                WHERE id = ?
                """,
                (title, last_modified, etag, feed_id)
            )
            return True
        except Exception as e:
            logger.error(f"Error updating feed metadata {feed_id}: {e}", exc_info=True)
            return False

    async def toggle_feed(self, feed_id: int) -> bool:
        """Toggle feed active status"""
        try:
            await self.execute_and_commit(
                """
                UPDATE feeds 
                SET active = CASE WHEN active = 1 THEN 0 ELSE 1 END,
                    updated_at = datetime('now', 'utc')
                WHERE id = ?
                """,
                (feed_id,)
            )
            return True
        except Exception as e:
            logger.error(f"Error toggling feed {feed_id}: {e}", exc_info=True)
            return False

    async def set_feed_active(self, feed_id: int, active: bool) -> bool:
        """Set feed active status"""
        try:
            await self.execute_and_commit(
                """
                UPDATE feeds 
                SET active = ?,
                    updated_at = datetime('now', 'utc')
                WHERE id = ?
                """,
                (1 if active else 0, feed_id)
            )
            return True
        except Exception as e:
            logger.error(f"Error setting feed active status {feed_id}: {e}", exc_info=True)
            return False

    async def delete_feed(self, feed_id: int) -> bool:
        """Delete feed (cascades to items, subscriptions, etc.)"""
        try:
            await self.execute_and_commit(
                "DELETE FROM feeds WHERE id = ?",
                (feed_id,)
            )
            return True
        except Exception as e:
            logger.error(f"Error deleting feed {feed_id}: {e}", exc_info=True)
            return False

    async def get_feeds_for_chat(self, chat_internal_id: int) -> List[Tuple]:
        """Get all feeds subscribed by a chat"""
        try:
            conn = await self.get_connection()
            cursor = await conn.execute(
                """
                SELECT f.id, f.url, f.title, f.active, s.active as subscription_active
                FROM feeds f
                JOIN subscriptions s ON s.feed_id = f.id
                WHERE s.chat_id = ?
                ORDER BY f.title, f.url
                """,
                (chat_internal_id,)
            )
            return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting feeds for chat {chat_internal_id}: {e}", exc_info=True)
            return []
