from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message

class ChatTypeMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message):
            data["chat_type"] = event.chat.type
            data["is_private"] = event.chat.type == "private"
            data["is_group"] = event.chat.type in ("group", "supergroup")
            data["is_channel"] = event.chat.type == "channel"
        
        return await handler(event, data) 