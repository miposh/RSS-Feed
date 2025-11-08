import logging
from typing import List, Tuple, Optional

from repositories.rss_repository import RSSRepository
from repositories.group_repository import GroupRepository
from utils.validators import validate_rss_feed

logger = logging.getLogger(__name__)

class RSSManagementService:
    def __init__(self, rss_repository: RSSRepository, group_repository: GroupRepository):
        self.rss_repository = rss_repository
        self.group_repository = group_repository
    
    async def add_feed(self, url: str, chat_id: int) -> Tuple[bool, Optional[str]]:
        is_valid, error_message = await validate_rss_feed(url)
        if not is_valid:
            return False, error_message
        
        group_id = await self.group_repository.get_group_id(chat_id)
        if group_id is None:
            success = await self.group_repository.add_group(chat_id)
            if not success:
                return False, "Failed to register group"
            group_id = await self.group_repository.get_group_id(chat_id)
            if group_id is None:
                return False, "Group registration failed"
        
        success = await self.rss_repository.add_feed(url, group_id)
        return success, None if success else "Failed to add feed"
    
    async def remove_feed(self, url: str, chat_id: int) -> bool:
        group_id = await self.group_repository.get_group_id(chat_id)
        if group_id is None:
            logger.warning(f"Attempted to remove feed from non-existent group {chat_id}")
            return False
        
        return await self.rss_repository.remove_feed(url, group_id)
    
    async def get_feeds_for_chat(self, chat_id: int) -> List[str]:
        group_id = await self.group_repository.get_group_id(chat_id)
        if group_id is None:
            logger.warning(f"Attempted to get feeds for non-existent group {chat_id}")
            return []
        
        return await self.rss_repository.get_feeds_for_group(group_id)
    
    async def get_all_feeds(self) -> List[Tuple[int, str, int]]:
        return await self.rss_repository.get_all_feeds()
    
    async def is_post_sent(self, post_guid: str, feed_id: int) -> bool:
        return await self.rss_repository.is_post_sent(post_guid, feed_id)
    
    async def mark_post_as_sent(self, post_guid: str, feed_id: int) -> bool:
        return await self.rss_repository.mark_post_as_sent(post_guid, feed_id)
    
    async def has_sent_posts_for_feed(self, feed_id: int) -> bool:
        return await self.rss_repository.has_sent_posts_for_feed(feed_id)
        
    async def cleanup_old_sent_posts(self, days: int = 90) -> int:
        return await self.rss_repository.cleanup_old_sent_posts(days) 