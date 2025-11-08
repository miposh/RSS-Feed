import logging

from app.infrastructure.database.connection.base import BaseConnection
from app.infrastructure.database.models.feed_subscription import FeedSubscriptionModel
from app.infrastructure.database.query.results import SingleQueryResult, MultipleQueryResult
from app.infrastructure.database.tables.base import BaseTable
from app.infrastructure.database.tables.enums.feed_subscriptions import FeedSubscriptionsTableAction

logger = logging.getLogger(__name__)


class FeedSubscriptionsTable(BaseTable):
    __tablename__ = "feed_subscriptions"

    def __init__(self, connection: BaseConnection):
        self.connection = connection

    async def add(
        self,
        *,
        feed_id: int,
        channel_id: int,
    ) -> FeedSubscriptionModel | None:
        """Add a new feed subscription."""
        data: SingleQueryResult = await self.connection.insert_and_fetchone(
            sql="""
                INSERT INTO feed_subscriptions(feed_id, channel_id)
                VALUES(%s, %s)
                ON CONFLICT (feed_id, channel_id) DO NOTHING
                RETURNING *;
            """,
            params=(feed_id, channel_id),
        )
        subscription_model = data.to_model(model=FeedSubscriptionModel)
        self._log(FeedSubscriptionsTableAction.ADD, feed_id=feed_id, channel_id=channel_id)
        return subscription_model

    async def delete(self, *, feed_id: int, channel_id: int) -> None:
        """Delete a feed subscription."""
        await self.connection.execute(
            sql="""
                DELETE FROM feed_subscriptions 
                WHERE feed_id = %s AND channel_id = %s;
            """,
            params=(feed_id, channel_id),
        )
        self._log(FeedSubscriptionsTableAction.DELETE, feed_id=feed_id, channel_id=channel_id)

    async def get_subscription(self, *, feed_id: int, channel_id: int) -> FeedSubscriptionModel | None:
        """Get subscription by feed_id and channel_id."""
        data: SingleQueryResult = await self.connection.fetchone(
            sql="""
                SELECT * FROM feed_subscriptions 
                WHERE feed_id = %s AND channel_id = %s
            """,
            params=(feed_id, channel_id),
        )
        subscription_model = data.to_model(model=FeedSubscriptionModel)
        self._log(FeedSubscriptionsTableAction.GET_SUBSCRIPTION, feed_id=feed_id, channel_id=channel_id)
        return subscription_model

    async def get_subscriptions_by_feed(self, *, feed_id: int) -> list[FeedSubscriptionModel] | None:
        """Get all subscriptions for a feed."""
        data: MultipleQueryResult = await self.connection.fetchmany(
            sql="""
                SELECT * FROM feed_subscriptions 
                WHERE feed_id = %s
                ORDER BY created_at DESC
            """,
            params=(feed_id,),
        )
        subscriptions = data.to_models(model=FeedSubscriptionModel)
        self._log(FeedSubscriptionsTableAction.GET_SUBSCRIPTIONS_BY_FEED, feed_id=feed_id, count=len(data) if data else 0)
        return subscriptions

    async def get_subscriptions_by_channel(self, *, channel_id: int) -> list[FeedSubscriptionModel] | None:
        """Get all subscriptions for a channel."""
        data: MultipleQueryResult = await self.connection.fetchmany(
            sql="""
                SELECT * FROM feed_subscriptions 
                WHERE channel_id = %s
                ORDER BY created_at DESC
            """,
            params=(channel_id,),
        )
        subscriptions = data.to_models(model=FeedSubscriptionModel)
        self._log(FeedSubscriptionsTableAction.GET_SUBSCRIPTIONS_BY_CHANNEL, channel_id=channel_id, count=len(data) if data else 0)
        return subscriptions

    async def get_channels_for_feed(self, *, feed_id: int) -> list[int]:
        """Get all channel IDs subscribed to a feed (only enabled channels)."""
        data: MultipleQueryResult = await self.connection.fetchmany(
            sql="""
                SELECT c.channel_id
                FROM feed_subscriptions fs
                JOIN channels c ON fs.channel_id = c.id
                WHERE fs.feed_id = %s AND c.parsing_is_enabled = TRUE
            """,
            params=(feed_id,),
        )
        channel_ids = [row['channel_id'] for row in data.data] if data and not data.is_empty() else []
        self._log(FeedSubscriptionsTableAction.GET_CHANNELS_FOR_FEED, feed_id=feed_id, count=len(channel_ids))
        return channel_ids
