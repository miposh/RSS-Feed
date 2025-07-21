from aiogram import Router, F, Bot
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import Command
import logging

from handlers.group_events import handle_bot_status_change
from services.rss_management_service import RSSManagementService
from repositories.group_repository import GroupRepository
from repositories.rss_repository import RSSRepository
from utils.validators import is_valid_url
from config.config import config

logger = logging.getLogger(__name__)

# Create router for group messages
group_router = Router()
group_router.message.filter(F.chat.type.in_({"group", "supergroup"}))

# Create repositories and services
group_repo = GroupRepository(config.db_path)
rss_repo = RSSRepository(config.db_path)
rss_service = RSSManagementService(rss_repo, group_repo)

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
async def cmd_add_rss(message: Message) -> None:
    # Extract URL from the message
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Пожалуйста, укажите URL RSS-ленты.\nПример: /add https://kod.ru/rss")
        return
    
    url = parts[1].strip()
    
    # Validate URL format
    if not is_valid_url(url):
        await message.answer("❌ Неверный формат URL. Пожалуйста, укажите корректный URL.")
        return
    
    # Add RSS feed to the database
    success, error_message = await rss_service.add_feed(url, message.chat.id)
    
    if success:
        await message.answer(f"✅ RSS-лента {url} успешно добавлена!")
    else:
        error_text = f"❌ Не удалось добавить RSS-ленту: {error_message}" if error_message else "❌ Не удалось добавить RSS-ленту или она уже была добавлена."
        await message.answer(error_text)

@group_router.message(Command("list"))
async def cmd_list_rss(message: Message) -> None:
    # Get list of RSS feeds for this group
    feeds = await rss_service.get_feeds_for_chat(message.chat.id)
    
    if feeds:
        # Format the list with numbers
        feeds_text = "\n".join(f"{i+1}. {feed}" for i, feed in enumerate(feeds))
        await message.answer(f"📋 Список добавленных RSS-лент:\n\n{feeds_text}")
    else:
        await message.answer("ℹ️ В этой группе нет добавленных RSS-лент.")

@group_router.message(Command("remove"))
async def cmd_remove_rss(message: Message) -> None:
    # Extract URL from the message
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❌ Пожалуйста, укажите URL RSS-ленты для удаления.\nПример: /remove https://kod.ru/rss")
        return
    
    url = parts[1].strip()
    
    # Remove RSS feed from the database
    success = await rss_service.remove_feed(url, message.chat.id)
    if success:
        await message.answer(f"✅ RSS-лента {url} удалена.")
    else:
        await message.answer(f"❌ Не удалось удалить RSS-ленту. Проверьте, что она была добавлена.")

@group_router.my_chat_member()
async def bot_status_handler(event: ChatMemberUpdated, bot: Bot) -> None:
    return await handle_bot_status_change(event, bot)