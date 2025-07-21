import asyncio
import logging
import urllib3

# Disable SSL verification warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault

from config.config import config
from handlers.group_handlers import group_router
from middlewares.chat_type_middleware import ChatTypeMiddleware
from middlewares.error_middleware import ErrorHandlingMiddleware
from database.database import init_db
from services.rss_service import RSSService
from repositories.group_repository import GroupRepository
from repositories.rss_repository import RSSRepository
from services.rss_management_service import RSSManagementService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)

# Register bot commands
async def set_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description="перезапуск бота"),
        BotCommand(command="add", description="добавить RSS-канал"),
        BotCommand(command="list", description="показать список RSS-каналов"),
        BotCommand(command="remove", description="удалить RSS-канал"),
    ]

    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    logger.info("Bot commands have been set successfully")

# Startup function
async def on_startup(bot: Bot) -> RSSService:
    logger.info("Bot is starting...")
    await set_bot_commands(bot)
    await init_db()

    # Create repositories and services
    group_repo = GroupRepository(config.db_path)
    rss_repo = RSSRepository(config.db_path)
    rss_management_service = RSSManagementService(rss_repo, group_repo)
    
    # Start RSS service
    rss_service = RSSService(bot, rss_management_service)
    await rss_service.start()
    return rss_service

# Shutdown function
async def on_shutdown(bot: Bot, rss_service=None) -> None:
    logger.info("Bot is shutting down...")
    if rss_service:
        await rss_service.stop()
    
    # Close database connections
    from repositories.base_repository import BaseRepository
    await BaseRepository.close_connection()

# Start polling
async def start_polling(dp: Dispatcher, bot: Bot) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

# Main function
async def main() -> None:
    # Create bot instance
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Create dispatcher
    dp = Dispatcher()
    
    # Register middlewares
    dp.update.outer_middleware(ErrorHandlingMiddleware())
    dp.message.middleware(ChatTypeMiddleware())
    
    # Register routers
    dp.include_router(group_router)
    
    # Start the bot
    rss_service = None
    try:
        rss_service = await on_startup(bot)
        await start_polling(dp, bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}", exc_info=True)
    finally:
        await on_shutdown(bot, rss_service)
        await bot.session.close()

# Entry point
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)