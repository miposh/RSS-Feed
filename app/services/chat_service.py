import logging
from typing import List, Tuple
from aiogram.types import Chat

from repositories.chat_repository import ChatRepository
from repositories.feed_repository import FeedRepository
from repositories.subscription_repository import SubscriptionRepository
from config.config import config

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self):
        self.chat_repo = ChatRepository(config.db_path)
        self.feed_repo = FeedRepository(config.db_path)
        self.sub_repo = SubscriptionRepository(config.db_path)
    
    async def register_chat(self, chat: Chat) -> bool:
        try:
            result = await self.chat_repo.add_or_update_chat(
                chat_id=chat.id,
                title=chat.title,
                username=chat.username,
                chat_type=chat.type
            )
            return result is not None
        except Exception as e:
            logger.error(f"Error registering chat {chat.id}: {e}", exc_info=True)
            return False
    
    async def add_feed_to_chat(self, chat_telegram_id: int, feed_url: str) -> bool:
        try:
            feed_id = await self.feed_repo.add_feed(feed_url)
            if not feed_id:
                return False
            
            # Get chat internal id
            chat_internal_id = await self.chat_repo.get_chat_id(chat_telegram_id)
            if not chat_internal_id:
                logger.error(f"Chat {chat_telegram_id} not found in database")
                return False
            
            # Subscribe
            return await self.sub_repo.subscribe(chat_internal_id, feed_id)
        except Exception as e:
            logger.error(f"Error adding feed to chat: {e}", exc_info=True)
            return False
    
    async def remove_feed_from_chat(self, chat_telegram_id: int, feed_url: str) -> bool:
        try:
            feed = await self.feed_repo.get_feed_by_url(feed_url)
            if not feed:
                return False
            
            feed_id = feed[0]
            
            chat_internal_id = await self.chat_repo.get_chat_id(chat_telegram_id)
            if not chat_internal_id:
                return False
            
            return await self.sub_repo.unsubscribe(chat_internal_id, feed_id)
        except Exception as e:
            logger.error(f"Error removing feed from chat: {e}", exc_info=True)
            return False
    
    async def get_chat_feeds(self, chat_telegram_id: int) -> List[Tuple]:
        try:
            chat_internal_id = await self.chat_repo.get_chat_id(chat_telegram_id)
            if not chat_internal_id:
                return []
            
            return await self.feed_repo.get_feeds_for_chat(chat_internal_id)
        except Exception as e:
            logger.error(f"Error getting chat feeds: {e}", exc_info=True)
            return []
    
    async def get_all_active_subscriptions(self) -> List[Tuple]:
        return await self.sub_repo.get_active_subscriptions()
    
    async def toggle_ai_for_chat(self, chat_telegram_id: int) -> bool:
        return await self.chat_repo.toggle_ai(chat_telegram_id)
