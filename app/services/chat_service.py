import logging
from typing import Optional
from aiogram.types import Chat

from psycopg import errors as pg_errors

from app.infrastructure.database.db import DB
from app.infrastructure.database.models.channel import ChannelModel
from app.infrastructure.database.models.rss_feed import RSSFeedModel

logger = logging.getLogger(__name__)


class ChatService:
    """Service for managing chats/channels and their feed subscriptions."""
    
    def __init__(self, db: DB):
        self.db = db
    
    async def register_chat(self, chat: Chat) -> bool:
        """Register or update a chat/channel in the database."""
        try:
            result = await self.db.channels.add(
                channel_id=chat.id,
                title=chat.title or "Unknown",
                username=chat.username
            )
            return result is not None
        except pg_errors.UndefinedTable as e:
            logger.warning(
                f"Cannot register chat {chat.id}: database table missing. "
                f"Run migrations: python apply_migrations.py. Error: {e}"
            )
            return False
        except Exception as e:
            logger.error(f"Error registering chat {chat.id}: {e}", exc_info=True)
            return False
    
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
        except pg_errors.UndefinedTable as e:
            logger.warning(
                f"Cannot add feed to chat: database table missing. "
                f"Run migrations: python apply_migrations.py. Error: {e}"
            )
            return False
        except Exception as e:
            logger.error(f"Error adding feed to chat: {e}", exc_info=True)
            return False
    
    async def remove_feed_from_chat(self, channel_id: int, feed_url: str) -> bool:
        """Remove a feed subscription from a channel and delete the feed source."""
        try:
            # Get feed
            feed = await self.db.rss_feeds.get_feed_by_url(url=feed_url)
            if not feed:
                logger.warning(f"Feed {feed_url} not found")
                return False

            # Get channel
            channel = await self.db.channels.get_channel(channel_id=channel_id)
            if not channel:
                logger.warning(f"Channel {channel_id} not found")
                return False

            # Delete subscription
            await self.db.feed_subscriptions.delete(
                feed_id=feed.id,
                channel_id=channel.id
            )

            # Delete the feed source completely
            await self.db.rss_feeds.delete(feed_id=feed.id)
            logger.info(f"Deleted feed {feed_url} (id={feed.id}) from channel {channel_id}")

            return True
        except pg_errors.UndefinedTable as e:
            logger.warning(
                f"Cannot remove feed from chat: database table missing. "
                f"Run migrations: python apply_migrations.py. Error: {e}"
            )
            return False
        except Exception as e:
            logger.error(f"Error removing feed from chat: {e}", exc_info=True)
            return False
    
    async def get_chat_feeds(self, channel_id: int) -> list[RSSFeedModel]:
        """Get all feeds subscribed by a channel."""
        try:
            # Get channel
            channel = await self.db.channels.get_channel(channel_id=channel_id)
            if not channel:
                logger.warning(f"Channel {channel_id} not found")
                return []
            
            # Get subscriptions
            subscriptions = await self.db.feed_subscriptions.get_subscriptions_by_channel(
                channel_id=channel.id
            )
            
            if not subscriptions:
                return []
            
            # Get feeds
            feeds = []
            for sub in subscriptions:
                feed = await self.db.rss_feeds.get_feed(feed_id=sub.feed_id)
                if feed:
                    feeds.append(feed)
            
            return feeds
        except pg_errors.UndefinedTable as e:
            logger.warning(
                f"Cannot get chat feeds: database table missing. "
                f"Run migrations: python apply_migrations.py. Error: {e}"
            )
            return []
        except Exception as e:
            logger.error(f"Error getting chat feeds: {e}", exc_info=True)
            return []
    
    async def get_channel(self, channel_id: int) -> Optional[ChannelModel]:
        """Get channel by Telegram channel_id."""
        try:
            return await self.db.channels.get_channel(channel_id=channel_id)
        except pg_errors.UndefinedTable as e:
            logger.warning(
                f"Cannot get channel {channel_id}: database table missing. "
                f"Run migrations: python apply_migrations.py. Error: {e}"
            )
            return None
        except Exception as e:
            logger.error(f"Error getting channel {channel_id}: {e}", exc_info=True)
            return None
