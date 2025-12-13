import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, Update, CallbackQuery
from aiogram.exceptions import TelegramAPIError
from psycopg import errors as pg_errors, OperationalError

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            return await handler(event, data)
        except TelegramAPIError as e:
            logger.error(f"Telegram API error: {e}", exc_info=True)
            await self._send_error_message(
                event, 
                "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже."
            )
            return None
            
        except pg_errors.UndefinedTable as e:
            logger.error(
                f"Database table missing: {e}. "
                "Please run migrations: python apply_migrations.py"
            )
            await self._send_error_message(
                event, 
                "Ошибка базы данных: таблица не найдена. Обратитесь к администратору."
            )
            return None
            
        except (OperationalError, pg_errors.ConnectionException) as e:
            logger.error(f"Database connection error: {e}", exc_info=True)
            await self._send_error_message(
                event, 
                "Ошибка подключения к базе данных. Попробуйте позже."
            )
            return None
            
        except pg_errors.Error as e:
            logger.error(f"Database error: {e}", exc_info=True)
            await self._send_error_message(
                event, 
                "Ошибка базы данных. Попробуйте позже."
            )
            return None
            
        except Exception as e:
            logger.error(f"Unhandled exception: {e}", exc_info=True)
            await self._send_error_message(
                event, 
                "Произошла внутренняя ошибка. Администраторы уведомлены."
            )
            return None
    
    async def _send_error_message(self, event: TelegramObject, message: str) -> None:
        """Send error message to user based on event type."""
        try:
            if isinstance(event, Message):
                await event.answer(message)
            elif isinstance(event, CallbackQuery):
                await event.answer(message, show_alert=True)
            elif isinstance(event, Update):
                if event.message:
                    await event.message.answer(message)
                elif event.callback_query:
                    await event.callback_query.answer(message, show_alert=True)
        except Exception:
            pass 