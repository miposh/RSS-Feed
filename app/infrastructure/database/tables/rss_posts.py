import logging
import json
from datetime import datetime
from typing import Optional, Any

from app.infrastructure.database.connection.base import BaseConnection
from app.infrastructure.database.models.rss_post import RSSPostModel
from app.infrastructure.database.query.results import SingleQueryResult, MultipleQueryResult
from app.infrastructure.database.tables.base import BaseTable
from app.infrastructure.database.tables.enums.rss_posts import RSSPostsTableAction

logger = logging.getLogger(__name__)


class RSSPostsTable(BaseTable):
    __tablename__ = "rss_posts"

    def __init__(self, connection: BaseConnection):
        self.connection = connection

    async def add(
        self,
        *,
        feed_id: int,
        guid: str,
        link: str,
        title: Optional[str] = None,
        summary: Optional[str] = None,
        content_html: Optional[str] = None,
        author: Optional[str] = None,
        published_at: Optional[datetime] = None,
        content_hash: Optional[str] = None,
        media_urls: Optional[dict[str, Any]] = None,
        tags: Optional[dict[str, Any]] = None,
    ) -> RSSPostModel | None:
        
        media_json = json.dumps(media_urls) if media_urls else None
        tags_json = json.dumps(tags) if tags else None
        
        data: SingleQueryResult = await self.connection.insert_and_fetchone(
            sql="""
                INSERT INTO rss_posts(
                    feed_id, guid, link, title, summary, content_html, 
                    author, published_at, content_hash, media_urls, tags
                )
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                ON CONFLICT (feed_id, guid) DO NOTHING
                RETURNING *;
            """,
            params=(feed_id, guid, link, title, summary, content_html, author, published_at, content_hash, media_json, tags_json),
        )
        post_model = data.to_model(model=RSSPostModel)
        self._log(RSSPostsTableAction.ADD, feed_id=feed_id, guid=guid)
        return post_model

    async def get_post(self, *, post_id: int) -> RSSPostModel | None:
        data: SingleQueryResult = await self.connection.fetchone(
            sql="""
                SELECT * FROM rss_posts WHERE id = %s
            """,
            params=(post_id,),
        )
        post_model = data.to_model(model=RSSPostModel)
        self._log(RSSPostsTableAction.GET_POST, post_id=post_id)
        return post_model

    async def get_post_by_guid(self, *, feed_id: int, guid: str) -> RSSPostModel | None:
        data: SingleQueryResult = await self.connection.fetchone(
            sql="""
                SELECT * FROM rss_posts WHERE feed_id = %s AND guid = %s
            """,
            params=(feed_id, guid),
        )
        post_model = data.to_model(model=RSSPostModel)
        self._log(RSSPostsTableAction.GET_POST_BY_GUID, feed_id=feed_id, guid=guid)
        return post_model

    async def get_unsent_posts(self, *, limit: int = 100) -> list[RSSPostModel] | None:
        data: MultipleQueryResult = await self.connection.fetchmany(
            sql="""
                SELECT * FROM rss_posts
                WHERE is_sent = FALSE
                ORDER BY published_at DESC NULLS LAST, created_at DESC
                LIMIT %s
            """,
            params=(limit,),
        )
        posts = data.to_models(model=RSSPostModel)
        self._log(RSSPostsTableAction.GET_UNSENT_POSTS, count=len(data) if data else 0)
        return posts

    async def mark_as_sent(self, *, post_id: int) -> RSSPostModel | None:
        data: SingleQueryResult = await self.connection.update_and_fetchone(
            sql="""
                UPDATE rss_posts
                SET is_sent = TRUE, sent_at = NOW()
                WHERE id = %s
                RETURNING *;
            """,
            params=(post_id,),
        )
        post_model = data.to_model(model=RSSPostModel, raise_if_empty=True)
        self._log(RSSPostsTableAction.MARK_AS_SENT, post_id=post_id)
        return post_model

    async def get_posts_by_feed(self, *, feed_id: int, limit: int = 50) -> list[RSSPostModel] | None:
        data: MultipleQueryResult = await self.connection.fetchmany(
            sql="""
                SELECT * FROM rss_posts
                WHERE feed_id = %s
                ORDER BY published_at DESC NULLS LAST, created_at DESC
                LIMIT %s
            """,
            params=(feed_id, limit),
        )
        posts = data.to_models(model=RSSPostModel)
        self._log(RSSPostsTableAction.GET_POSTS_BY_FEED, feed_id=feed_id, count=len(data) if data else 0)
        return posts

    async def delete_older_than(self, *, days: int) -> int:
        data: SingleQueryResult = await self.connection.fetchone(
            sql="""
                WITH deleted AS (
                    DELETE FROM rss_posts
                    WHERE created_at < NOW() - make_interval(days := %s)
                    RETURNING id
                )
                SELECT count(*) as count FROM deleted;
            """,
            params=(days,),
        )
        count = data.result["count"] if data.result else 0
        logger.info(f"Deleted {count} old posts (older than {days} days)")
        return count
