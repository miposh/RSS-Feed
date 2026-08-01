import logging

from app.infrastructure.database.connection.base import BaseConnection
from app.infrastructure.database.models.feed_subscription import FeedSubscriptionModel
from app.infrastructure.database.query.results import SingleQueryResult
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
