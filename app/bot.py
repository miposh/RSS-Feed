import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeAllPrivateChats
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_dialog import setup_dialogs

from app.config.config import get_config
from handlers.group_handlers import group_router
from handlers.private_handlers import private_router
from dialogs.feed_management_dialog import feed_management_dialog
from middlewares.chat_type_middleware import ChatTypeMiddleware
from middlewares.error_middleware import ErrorHandlingMiddleware
from middlewares.user_tracking import UserTrackingMiddleware
from database.database import init_db
from services.new_rss_service import NewRSSService
from services.chat_service import ChatService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)

async def set_bot_commands(bot: Bot) -> None:
    # Commands for groups
    group_commands = [
        BotCommand(command="start", description="информация о боте"),
        BotCommand(command="add", description="добавить RSS-канал"),
        BotCommand(command="list", description="показать список RSS-каналов"),
        BotCommand(command="remove", description="удалить RSS-канал"),
    ]
    
    # Commands for private chats
    private_commands = [
        BotCommand(command="start", description="открыть меню управления"),
        BotCommand(command="manage", description="управление фидами"),
        BotCommand(command="help", description="помощь"),
    ]

    await bot.set_my_commands(group_commands, scope=BotCommandScopeDefault())
    await bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
    logger.info("Bot commands have been set successfully")

async def on_startup(bot: Bot) -> NewRSSService:
    logger.info("Bot is starting...")
    await set_bot_commands(bot)
    await init_db()
    
    chat_service = ChatService()
    
    rss_service = NewRSSService(bot, chat_service)
    await rss_service.start()
    
    logger.info("Bot started successfully with new schema")
    return rss_service


async def on_shutdown(bot: Bot, rss_service=None) -> None:
    logger.info("Bot is shutting down...")
    if rss_service:
        await rss_service.stop()
    
    from repositories.base_repository import BaseRepository
    await BaseRepository.close_connection()

async def start_polling(dp: Dispatcher, bot: Bot) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

async def main() -> None:
    config = get_config()
    
    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    dp.update.outer_middleware(ErrorHandlingMiddleware())
    dp.message.middleware(ChatTypeMiddleware())
    dp.message.middleware(UserTrackingMiddleware())
    dp.callback_query.middleware(UserTrackingMiddleware())
    
    dp.include_router(private_router)
    dp.include_router(group_router)
    dp.include_router(feed_management_dialog)
    
    setup_dialogs(dp)
    
    rss_service = None
    try:
        rss_service = await on_startup(bot)
        await start_polling(dp, bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}", exc_info=True)
    finally:
        await on_shutdown(bot, rss_service)
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)