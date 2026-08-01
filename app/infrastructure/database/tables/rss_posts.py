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

    async def add_sent(
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
        """Store a post and mark it as sent, in a single statement.

        Re-seeing a post the bot already stored just refreshes the sent flag, so
        no separate SELECT/UPDATE round trips are needed.
        """
        media_json = json.dumps(media_urls) if media_urls else None
        tags_json = json.dumps(tags) if tags else None

        data: SingleQueryResult = await self.connection.insert_and_fetchone(
            sql="""
                INSERT INTO rss_posts(
                    feed_id, guid, link, title, summary, content_html,
                    author, published_at, content_hash, media_urls, tags,
                    is_sent, sent_at
                )
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, TRUE, NOW())
                ON CONFLICT (feed_id, guid) DO UPDATE
                SET is_sent = TRUE,
                    sent_at = COALESCE(rss_posts.sent_at, NOW())
                RETURNING *;
            """,
            params=(feed_id, guid, link, title, summary, content_html, author, published_at, content_hash, media_json, tags_json),
        )
        post_model = data.to_model(model=RSSPostModel)
        self._log(RSSPostsTableAction.ADD, feed_id=feed_id, guid=guid)
        return post_model

    async def get_sent_guids(self, *, feed_id: int, guids: list[str]) -> set[str]:
        """
        Batch check: return set of GUIDs that are already sent for given feed.

        This is more efficient than checking each GUID individually in a loop.
        Uses a single query with ANY() for all GUIDs.
        """
        if not guids:
            return set()

        data: MultipleQueryResult = await self.connection.fetchmany(
            sql="""
                SELECT guid FROM rss_posts
                WHERE feed_id = %s AND guid = ANY(%s) AND is_sent = TRUE
            """,
            params=(feed_id, guids),
        )

        sent_guids = {row["guid"] for row in data.data}
        self._log(RSSPostsTableAction.GET_SENT_GUIDS, feed_id=feed_id, count=len(sent_guids))
        return sent_guids

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
        count = data.data.get("count", 0) if data.data else 0
        logger.info(f"Deleted {count} old posts (older than {days} days)")
        return count
