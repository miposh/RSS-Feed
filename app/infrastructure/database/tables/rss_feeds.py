import logging
from datetime import datetime
from typing import Optional

from app.infrastructure.database.connection.base import BaseConnection
from app.infrastructure.database.models.rss_feed import RSSFeedModel
from app.infrastructure.database.query.results import SingleQueryResult, MultipleQueryResult
from app.infrastructure.database.tables.base import BaseTable
from app.infrastructure.database.tables.enums.rss_feeds import RSSFeedsTableAction

logger = logging.getLogger(__name__)


class RSSFeedsTable(BaseTable):
    __tablename__ = "rss_feeds"

    def __init__(self, connection: BaseConnection):
        self.connection = connection

    async def add(
        self,
        *,
        url: str,
        owner_user_id: Optional[int] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        site_url: Optional[str] = None,
        language: Optional[str] = None,
        image_url: Optional[str] = None,
        fetch_interval_sec: int = 900,
        enabled: bool = True,
    ) -> RSSFeedModel | None:
        """Add a new RSS feed."""
        data: SingleQueryResult = await self.connection.insert_and_fetchone(
            sql="""
                INSERT INTO rss_feeds(
                    url, owner_user_id, title, description, site_url,
                    language, image_url, fetch_interval_sec, enabled
                )
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO UPDATE
                SET title = COALESCE(EXCLUDED.title, rss_feeds.title),
                    description = COALESCE(EXCLUDED.description, rss_feeds.description),
                    site_url = COALESCE(EXCLUDED.site_url, rss_feeds.site_url),
                    language = COALESCE(EXCLUDED.language, rss_feeds.language),
                    image_url = COALESCE(EXCLUDED.image_url, rss_feeds.image_url)
                RETURNING *;
            """,
            params=(url, owner_user_id, title, description, site_url, language, image_url, fetch_interval_sec, enabled),
        )
        feed_model = data.to_model(model=RSSFeedModel)
        self._log(RSSFeedsTableAction.ADD, url=url, owner_user_id=owner_user_id)
        return feed_model

    async def delete(self, *, feed_id: int) -> None:
        """Delete an RSS feed."""
        await self.connection.execute(
            sql="""
                DELETE FROM rss_feeds WHERE id = %s;
            """,
            params=(feed_id,),
        )
        self._log(RSSFeedsTableAction.DELETE, feed_id=feed_id)

    async def get_feed_by_url(self, *, url: str) -> RSSFeedModel | None:
        """Get feed by URL."""
        data: SingleQueryResult = await self.connection.fetchone(
            sql="""
                SELECT * FROM rss_feeds WHERE url = %s
            """,
            params=(url,),
        )
        feed_model = data.to_model(model=RSSFeedModel)
        self._log(RSSFeedsTableAction.GET_FEED_BY_URL, url=url)
        return feed_model

    async def get_feeds_by_channel(
        self,
        *,
        channel_id: int,
        enabled_only: bool = False,
    ) -> list[RSSFeedModel]:
        """Get every feed a channel is subscribed to, in one query.

        Args:
            channel_id: Internal ``channels.id``
            enabled_only: Skip feeds that are disabled or still in error backoff

        Returns:
            Feeds ordered newest first.
        """
        data: MultipleQueryResult = await self.connection.fetchmany(
            sql=f"""
                SELECT f.*
                FROM rss_feeds f
                JOIN feed_subscriptions fs ON fs.feed_id = f.id
                WHERE fs.channel_id = %s
                {"AND f.enabled = TRUE AND (f.backoff_until IS NULL OR f.backoff_until <= now())" if enabled_only else ""}
                ORDER BY f.created_at DESC
            """,
            params=(channel_id,),
        )
        feeds = data.to_models(model=RSSFeedModel) or []
        self._log(
            RSSFeedsTableAction.GET_FEEDS_BY_CHANNEL,
            channel_id=channel_id,
            enabled_only=enabled_only,
            count=len(feeds),
        )
        return feeds

    async def update_fetch_status(
        self,
        *,
        feed_id: int,
        last_status: int,
        etag: Optional[str] = None,
        last_modified: Optional[datetime] = None,
    ) -> RSSFeedModel | None:
        """Update feed fetch status.

        ``etag`` and ``last_modified`` are only overwritten when the server sent
        them, so a response without validators does not discard the cached ones.
        """
        data: SingleQueryResult = await self.connection.update_and_fetchone(
            sql="""
                UPDATE rss_feeds
                SET last_fetched_at = NOW(),
                    last_status = %s,
                    etag = COALESCE(%s, etag),
                    last_modified = COALESCE(%s, last_modified)
                WHERE id = %s
                RETURNING *;
            """,
            params=(last_status, etag, last_modified, feed_id),
        )
        feed_model = data.to_model(model=RSSFeedModel, raise_if_empty=True)
        self._log(RSSFeedsTableAction.UPDATE_FETCH_STATUS, feed_id=feed_id, last_status=last_status)
        return feed_model

    async def update_error_count(self, *, feed_id: int) -> RSSFeedModel | None:
        """Increment error count and push the feed into exponential backoff.

        ``error_count`` on the right-hand side is the pre-update value, so the
        first failure waits one fetch interval and each further one doubles it,
        capped at 6 hours. Without this a permanently dead feed (expired domain,
        dropped DNS) is refetched every cycle forever.
        """
        data: SingleQueryResult = await self.connection.update_and_fetchone(
            sql="""
                UPDATE rss_feeds
                SET error_count = error_count + 1,
                    backoff_until = now() + LEAST(
                        INTERVAL '6 hours',
                        (fetch_interval_sec * POWER(2, LEAST(error_count, 10)))
                            * INTERVAL '1 second'
                    )
                WHERE id = %s
                RETURNING *;
            """,
            params=(feed_id,),
        )
        feed_model = data.to_model(model=RSSFeedModel, raise_if_empty=True)
        self._log(RSSFeedsTableAction.UPDATE_ERROR_COUNT, feed_id=feed_id)
        return feed_model

    async def reset_error_count(self, *, feed_id: int) -> RSSFeedModel | None:
        """Reset error count to 0."""
        data: SingleQueryResult = await self.connection.update_and_fetchone(
            sql="""
                UPDATE rss_feeds
                SET error_count = 0, backoff_until = NULL
                WHERE id = %s
                RETURNING *;
            """,
            params=(feed_id,),
        )
        feed_model = data.to_model(model=RSSFeedModel, raise_if_empty=True)
        self._log(RSSFeedsTableAction.RESET_ERROR_COUNT, feed_id=feed_id)
        return feed_model
