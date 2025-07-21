import logging
from typing import List, Optional, Tuple

from repositories.base_repository import BaseRepository
from models.rss_feed import RSSFeed

logger = logging.getLogger(__name__)

class RSSRepository(BaseRepository):
    """Repository for RSS feed operations."""
    
    async def add_feed(self, url: str, group_id: int) -> bool:
        """
        Add a new RSS feed for a group.
        
        Args:
            url: The RSS feed URL
            group_id: The group ID
            
        Returns:
            bool: True if added successfully, False otherwise
        """
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
        """
        Remove an RSS feed from a group.
        
        Args:
            url: The RSS feed URL
            group_id: The group ID
            
        Returns:
            bool: True if removed successfully, False otherwise
        """
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
        """
        Get all RSS feeds for a group.
        
        Args:
            group_id: The group ID
            
        Returns:
            List[str]: List of feed URLs
        """
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
        """
        Get all RSS feeds with their group chat IDs.
        
        Returns:
            List[Tuple[int, str, int]]: List of (feed_id, url, chat_id) tuples
        """
        try:
            cursor = await self.execute(
                "SELECT rf.id, rf.url, g.chat_id FROM rss_feeds rf JOIN groups g ON rf.group_id = g.id"
            )
            return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get all RSS feeds: {e}")
            return []
    
    async def is_post_sent(self, post_guid: str, feed_id: int) -> bool:
        """
        Check if a post has already been sent.
        
        Args:
            post_guid: The post GUID
            feed_id: The feed ID
            
        Returns:
            bool: True if the post has been sent, False otherwise
        """
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
        """
        Mark a post as sent.
        
        Args:
            post_guid: The post GUID
            feed_id: The feed ID
            
        Returns:
            bool: True if marked successfully, False otherwise
        """
        try:
            await self.execute_and_commit(
                "INSERT INTO sent_posts (post_guid, feed_id) VALUES (?, ?)",
                (post_guid, feed_id)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to mark post {post_guid} as sent: {e}")
            return False 