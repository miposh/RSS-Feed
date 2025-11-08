from aiogram import Router, F, Bot
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import Command
import logging

from handlers.group_events import handle_bot_status_change
from services.chat_service import ChatService
from utils.validators import is_valid_url
from app.infrastructure.database.db import DB

logger = logging.getLogger(__name__)

group_router = Router()
group_router.message.filter(F.chat.type.in_({"group", "supergroup"}))

@group_router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "👋 Привет! Я бот для работы с RSS-лентами.\n\n"
        "Доступные команды:\n"
        "• /add - добавить RSS-ленту\n"
        "• /remove - удалить RSS-ленту\n"
        "• /list - показать список RSS-лент"
    )

@group_router.message(Command("add"))
async def cmd_add_rss(message: Message, db: DB) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Пожалуйста, укажите URL RSS-ленты.\nПример: /add https://kod.ru/rss")
        return
    
    url = parts[1].strip()
    
    if not is_valid_url(url):
        await message.answer("❌ Неверный формат URL. Пожалуйста, укажите корректный URL.")
        return
    
    chat_service = ChatService(db)
    await chat_service.register_chat(message.chat)
    
    success = await chat_service.add_feed_to_chat(message.chat.id, url)
    
    if success:
        await message.answer(f"✅ RSS-лента {url} успешно добавлена!")
    else:
        await message.answer("❌ Не удалось добавить RSS-ленту или она уже была добавлена.")

@group_router.message(Command("list"))
async def cmd_list_rss(message: Message, db: DB) -> None:
    chat_service = ChatService(db)
    feeds = await chat_service.get_chat_feeds(message.chat.id)
    
    if feeds:
        feeds_text = "\n".join(
            f"{i+1}. {feed.title or feed.url} {'✅' if feed.enabled else '❌'}" 
            for i, feed in enumerate(feeds)
        )
        await message.answer(f"📋 Список добавленных RSS-лент:\n\n{feeds_text}\n\n✅ - активна, ❌ - приостановлена")
    else:
        await message.answer("ℹ️ В этой группе нет добавленных RSS-лент.")

@group_router.message(Command("remove"))
async def cmd_remove_rss(message: Message, db: DB) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Пожалуйста, укажите URL RSS-ленты для удаления.\nПример: /remove https://kod.ru/rss")
        return
    
    url = parts[1].strip()
    
    chat_service = ChatService(db)
    success = await chat_service.remove_feed_from_chat(message.chat.id, url)
    if success:
        await message.answer(f"✅ RSS-лента {url} удалена.")
    else:
        await message.answer("❌ Не удалось удалить RSS-ленту. Проверьте, что она была добавлена.")

@group_router.my_chat_member()
async def bot_status_handler(event: ChatMemberUpdated, bot: Bot) -> None:
    return await handle_bot_status_change(event, bot)