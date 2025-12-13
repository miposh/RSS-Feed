import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from psycopg import errors as pg_errors

from app.infrastructure.database.db import DB

logger = logging.getLogger(__name__)


class UserTrackingMiddleware(BaseMiddleware):
    """Automatically track and save users to database."""
    
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
            db: DB = data.get("db")
            if db:
                try:
                    await db.users.add(
                        user_id=user.id,
                        username=user.username
                    )
                    logger.debug(f"User tracked: {user.id} (@{user.username})")
                except pg_errors.UndefinedTable:
                    logger.warning(
                        f"Cannot track user {user.id}: users table missing. "
                        "Run migrations: python apply_migrations.py"
                    )
                except Exception as e:
                    logger.error(f"Failed to track user {user.id}: {e}")
            else:
                logger.debug("DB not available in middleware data")
        
        return await handler(event, data)
