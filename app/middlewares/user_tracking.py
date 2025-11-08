import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from repositories.user_repository import UserRepository
from config.config import config

logger = logging.getLogger(__name__)


class UserTrackingMiddleware(BaseMiddleware):
    """Automatically track and save users to database"""
    
    def __init__(self):
        super().__init__()
        self.user_repo = UserRepository(config.db_path)
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = None
        
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        
        if user and not user.is_bot:
            try:
                await self.user_repo.add_or_update_user(
                    user_id=user.id,
                    username=user.username
                )
                logger.debug(f"User tracked: {user.id} (@{user.username})")
            except Exception as e:
                logger.error(f"Failed to track user {user.id}: {e}")
        
        return await handler(event, data)
