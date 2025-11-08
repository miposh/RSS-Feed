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

    async def get_feed(self, *, feed_id: int) -> RSSFeedModel | None:
        """Get feed by id."""
        data: SingleQueryResult = await self.connection.fetchone(
            sql="""
                SELECT * FROM rss_feeds WHERE id = %s
            """,
            params=(feed_id,),
        )
        feed_model = data.to_model(model=RSSFeedModel)
        self._log(RSSFeedsTableAction.GET_FEED, feed_id=feed_id)
        return feed_model

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

    async def update_feed_metadata(
        self,
        *,
        feed_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        site_url: Optional[str] = None,
        language: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> RSSFeedModel | None:
        """Update feed metadata."""
        data: SingleQueryResult = await self.connection.update_and_fetchone(
            sql="""
                UPDATE rss_feeds
                SET title = COALESCE(%s, title),
                    description = COALESCE(%s, description),
                    site_url = COALESCE(%s, site_url),
                    language = COALESCE(%s, language),
                    image_url = COALESCE(%s, image_url)
                WHERE id = %s
                RETURNING *;
            """,
            params=(title, description, site_url, language, image_url, feed_id),
        )
        feed_model = data.to_model(model=RSSFeedModel, raise_if_empty=True)
        self._log(RSSFeedsTableAction.UPDATE_FEED_METADATA, feed_id=feed_id)
        return feed_model

    async def update_fetch_status(
        self,
        *,
        feed_id: int,
        last_status: int,
        etag: Optional[str] = None,
        last_modified: Optional[datetime] = None,
    ) -> RSSFeedModel | None:
        """Update feed fetch status."""
        data: SingleQueryResult = await self.connection.update_and_fetchone(
            sql="""
                UPDATE rss_feeds
                SET last_fetched_at = NOW(),
                    last_status = %s,
                    etag = %s,
                    last_modified = %s
                WHERE id = %s
                RETURNING *;
            """,
            params=(last_status, etag, last_modified, feed_id),
        )
        feed_model = data.to_model(model=RSSFeedModel, raise_if_empty=True)
        self._log(RSSFeedsTableAction.UPDATE_FETCH_STATUS, feed_id=feed_id, last_status=last_status)
        return feed_model

    async def update_error_count(self, *, feed_id: int) -> RSSFeedModel | None:
        """Increment error count."""
        data: SingleQueryResult = await self.connection.update_and_fetchone(
            sql="""
                UPDATE rss_feeds
                SET error_count = error_count + 1
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

    async def set_backoff(self, *, feed_id: int, backoff_until: datetime) -> RSSFeedModel | None:
        """Set backoff timestamp."""
        data: SingleQueryResult = await self.connection.update_and_fetchone(
            sql="""
                UPDATE rss_feeds
                SET backoff_until = %s
                WHERE id = %s
                RETURNING *;
            """,
            params=(backoff_until, feed_id),
        )
        feed_model = data.to_model(model=RSSFeedModel, raise_if_empty=True)
        self._log(RSSFeedsTableAction.SET_BACKOFF, feed_id=feed_id, backoff_until=backoff_until)
        return feed_model

    async def enable_feed(self, *, feed_id: int) -> RSSFeedModel | None:
        """Enable feed."""
        data: SingleQueryResult = await self.connection.update_and_fetchone(
            sql="""
                UPDATE rss_feeds
                SET enabled = TRUE
                WHERE id = %s
                RETURNING *;
            """,
            params=(feed_id,),
        )
        feed_model = data.to_model(model=RSSFeedModel, raise_if_empty=True)
        self._log(RSSFeedsTableAction.ENABLE_FEED, feed_id=feed_id)
        return feed_model

    async def disable_feed(self, *, feed_id: int) -> RSSFeedModel | None:
        """Disable feed."""
        data: SingleQueryResult = await self.connection.update_and_fetchone(
            sql="""
                UPDATE rss_feeds
                SET enabled = FALSE
                WHERE id = %s
                RETURNING *;
            """,
            params=(feed_id,),
        )
        feed_model = data.to_model(model=RSSFeedModel, raise_if_empty=True)
        self._log(RSSFeedsTableAction.DISABLE_FEED, feed_id=feed_id)
        return feed_model

    async def get_feeds_to_fetch(self) -> list[RSSFeedModel] | None:
        """Get feeds that need to be fetched."""
        data: MultipleQueryResult = await self.connection.fetchmany(
            sql="""
                SELECT * FROM rss_feeds
                WHERE enabled = TRUE
                AND (backoff_until IS NULL OR backoff_until < NOW())
                AND (last_fetched_at IS NULL 
                     OR last_fetched_at < NOW() - (fetch_interval_sec || ' seconds')::INTERVAL)
                ORDER BY last_fetched_at NULLS FIRST
            """,
        )
        feeds = data.to_models(model=RSSFeedModel)
        self._log(RSSFeedsTableAction.GET_FEEDS_TO_FETCH, count=len(data) if data else 0)
        return feeds

    async def get_all_feeds(self) -> list[RSSFeedModel] | None:
        """Get all feeds."""
        data: MultipleQueryResult = await self.connection.fetchmany(
            sql="""
                SELECT * FROM rss_feeds
                ORDER BY created_at DESC
            """,
        )
        feeds = data.to_models(model=RSSFeedModel)
        self._log(RSSFeedsTableAction.GET_ALL_FEEDS, count=len(data) if data else 0)
        return feeds
