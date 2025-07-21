import logging
from typing import List, Tuple

from repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)

class RSSRepository(BaseRepository):    
    async def add_feed(self, url: str, group_id: int) -> bool:
        try:
            await self.execute_and_commit(
                "INSERT INTO rss_feeds (url, group_id) VALUES (?, ?)",
                (url, group_id)
            )
            logger.info(f"RSS feed {url} added to group {group_id}")
            return True
        except Exception as e:
            logger.info(f"Failed to add RSS feed {url} to group {group_id}: {e}")
            return False
    
    async def remove_feed(self, url: str, group_id: int) -> bool:
        try:
            await self.execute_and_commit(
                "DELETE FROM rss_feeds WHERE url = ? AND group_id = ?",
                (url, group_id)
            )
            logger.info(f"RSS feed {url} removed from group {group_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to remove RSS feed {url} from group {group_id}: {e}")
            return False
    
    async def get_feeds_for_group(self, group_id: int) -> List[str]:
        try:
            cursor = await self.execute(
                "SELECT url FROM rss_feeds WHERE group_id = ?",
                (group_id,)
            )
            return [row[0] for row in await cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get RSS feeds for group {group_id}: {e}")
            return []
    
    async def get_all_feeds(self) -> List[Tuple[int, str, int]]:
        try:
            cursor = await self.execute(
                "SELECT rf.id, rf.url, g.chat_id FROM rss_feeds rf JOIN groups g ON rf.group_id = g.id"
            )
            return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get all RSS feeds: {e}")
            return []
    
    async def is_post_sent(self, post_guid: str, feed_id: int) -> bool:
        try:
            cursor = await self.execute(
                "SELECT 1 FROM sent_posts WHERE post_guid = ? AND feed_id = ?",
                (post_guid, feed_id)
            )
            return await cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Failed to check if post {post_guid} was sent: {e}")
            return False
    
    async def mark_post_as_sent(self, post_guid: str, feed_id: int) -> bool:
        try:
            await self.execute_and_commit(
                "INSERT INTO sent_posts (post_guid, feed_id, sent_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (post_guid, feed_id)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to mark post {post_guid} as sent: {e}")
            return False
            
    async def cleanup_old_sent_posts(self, days: int = 30) -> int:
        try:
            cursor = await self.execute_and_commit(
                "DELETE FROM sent_posts WHERE sent_at < datetime('now', ?)",
                (f"-{days} days",)
            )
            deleted_count = cursor.rowcount
            logger.info(f"Cleaned up {deleted_count} old sent posts (older than {days} days)")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to clean up old sent posts: {e}")
            return 0 