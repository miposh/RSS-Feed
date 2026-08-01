import logging
from typing import Optional

from app.infrastructure.database.db import DB
from app.infrastructure.database.models.channel import ChannelModel
from app.infrastructure.database.models.rss_feed import RSSFeedModel

logger = logging.getLogger(__name__)


class ChatService:
    """Service for managing chats/channels and their feed subscriptions."""

    def __init__(self, db: DB):
        self.db = db

    async def add_feed_to_chat(self, channel_id: int, feed_url: str) -> bool:
        """Add a feed subscription to a channel."""
        try:
            # Get or create feed
            feed = await self.db.rss_feeds.get_feed_by_url(url=feed_url)
            if not feed:
                feed = await self.db.rss_feeds.add(url=feed_url)

            if not feed:
                logger.error(f"Failed to create feed {feed_url}")
                return False

            # Get channel internal id
            channel = await self.db.channels.get_channel(channel_id=channel_id)
            if not channel:
                logger.error(f"Channel {channel_id} not found in database")
                return False

            # Create subscription
            subscription = await self.db.feed_subscriptions.add(
                feed_id=feed.id,
                channel_id=channel.id
            )
            return subscription is not None
        except Exception as e:
            logger.error(f"Error adding feed to chat: {e}", exc_info=True)
            return False

    async def remove_feed_by_id(self, channel_id: int, feed_id: int) -> bool:
        """Remove a feed subscription by feed ID and delete the feed source."""
        try:
            # Get channel
            channel = await self.db.channels.get_channel(channel_id=channel_id)
            if not channel:
                logger.warning(f"Channel {channel_id} not found")
                return False

            # Delete subscription
            await self.db.feed_subscriptions.delete(
                feed_id=feed_id,
                channel_id=channel.id
            )

            # Delete the feed source completely
            await self.db.rss_feeds.delete(feed_id=feed_id)
            logger.info(f"Deleted feed id={feed_id} from channel {channel_id}")

            return True
        except Exception as e:
            logger.error(f"Error removing feed by id: {e}", exc_info=True)
            return False

    async def get_chat_feeds(self, channel_id: int) -> list[RSSFeedModel]:
        """Get all feeds subscribed by a channel, newest first."""
        try:
            channel = await self.db.channels.get_channel(channel_id=channel_id)
            if not channel:
                logger.warning(f"Channel {channel_id} not found")
                return []

            return await self.db.rss_feeds.get_feeds_by_channel(channel_id=channel.id)
        except Exception as e:
            logger.error(f"Error getting chat feeds: {e}", exc_info=True)
            return []

    async def get_channel(self, channel_id: int) -> Optional[ChannelModel]:
        """Get channel by Telegram channel_id."""
        try:
            return await self.db.channels.get_channel(channel_id=channel_id)
        except Exception as e:
            logger.error(f"Error getting channel {channel_id}: {e}", exc_info=True)
            return None
