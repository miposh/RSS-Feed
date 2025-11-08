"""
Post deduplication service.
Currently uses SQLite, will be extended to support Redis.
"""
import logging
from typing import Protocol, Set

logger = logging.getLogger(__name__)


class DeduplicatorBackend(Protocol):
    async def is_post_seen(self, feed_id: int, guid: str) -> bool:
        ...
    
    async def mark_post_seen(self, feed_id: int, guid: str) -> bool:
        ...
    
    async def has_any_posts(self, feed_id: int) -> bool:
        ...


class SQLiteDeduplicator:
    def __init__(self, rss_repository):
        self.rss_repository = rss_repository
    
    async def is_post_seen(self, feed_id: int, guid: str) -> bool:
        return await self.rss_repository.is_post_sent(guid, feed_id)
    
    async def mark_post_seen(self, feed_id: int, guid: str) -> bool:
        return await self.rss_repository.mark_post_as_sent(guid, feed_id)
    
    async def has_any_posts(self, feed_id: int) -> bool:
        return await self.rss_repository.has_sent_posts_for_feed(feed_id)


class InMemoryDeduplicator:
    def __init__(self):
        self._seen_posts: Set[tuple] = set()
        self._feeds_with_posts: Set[int] = set()
    
    async def is_post_seen(self, feed_id: int, guid: str) -> bool:
        return (feed_id, guid) in self._seen_posts
    
    async def mark_post_seen(self, feed_id: int, guid: str) -> bool:
        self._seen_posts.add((feed_id, guid))
        self._feeds_with_posts.add(feed_id)
        return True
    
    async def has_any_posts(self, feed_id: int) -> bool:
        return feed_id in self._feeds_with_posts
