import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, Update
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger(__name__)

class ErrorHandlingMiddleware(BaseMiddleware):
    """Middleware for handling errors in handlers."""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Process the event and handle any errors.
        
        Args:
            handler: The next handler in the chain
            event: The event to process
            data: Additional data
            
        Returns:
            Any: The result of the handler
        """
        try:
            return await handler(event, data)
        except TelegramAPIError as e:
            # Handle Telegram API errors
            logger.error(f"Telegram API error: {e}", exc_info=True)
            
            # Try to notify the user if possible
            if isinstance(event, Message):
                try:
                    await event.answer("Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.")
                except Exception:
                    pass
            elif isinstance(event, Update) and event.message:
                try:
                    await event.message.answer("Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.")
                except Exception:
                    pass
                    
            return None
        except Exception as e:
            # Handle other errors
            logger.error(f"Unhandled exception: {e}", exc_info=True)
            
            # Try to notify the user if possible
            if isinstance(event, Message):
                try:
                    await event.answer("Произошла внутренняя ошибка. Администраторы уведомлены.")
                except Exception:
                    pass
            elif isinstance(event, Update) and event.message:
                try:
                    await event.message.answer("Произошла внутренняя ошибка. Администраторы уведомлены.")
                except Exception:
                    pass
                    
            return None 