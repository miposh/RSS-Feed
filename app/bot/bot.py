import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeAllPrivateChats
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_dialog import setup_dialogs

from config.config import get_config
from app.infrastructure.database.connection.connect_to_pg import get_pg_pool
from app.infrastructure.database.schema import DatabaseSchema
from app.infrastructure.database.connection.psycopg_connection import PsycopgConnection
from app.bot.middlewares.chat_type_middleware import ChatTypeMiddleware
from app.bot.middlewares.error_middleware import ErrorHandlingMiddleware
from app.bot.middlewares.user_tracking import UserTrackingMiddleware
from app.bot.middlewares.database import DataBaseMiddleware
from app.services.new_rss_service import NewRSSService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)

# async def set_bot_commands(bot: Bot) -> None:
#     group_commands = [
#         BotCommand(command="start", description="информация о боте"),
#         BotCommand(command="add", description="добавить RSS-канал"),
#         BotCommand(command="list", description="показать список RSS-каналов"),
#         BotCommand(command="remove", description="удалить RSS-канал"),
#     ]
    
#     private_commands = [
#         BotCommand(command="start", description="открыть меню управления"),
#         BotCommand(command="manage", description="управление фидами"),
#         BotCommand(command="help", description="помощь"),
#     ]

#     await bot.set_my_commands(group_commands, scope=BotCommandScopeDefault())
#     await bot.set_my_commands(private_commands, scope=BotCommandScopeAllPrivateChats())
#     logger.info("Bot commands have been set successfully")

async def on_startup(bot: Bot, db_pool) -> NewRSSService:
    logger.info("Bot is starting...")
    # await set_bot_commands(bot)
    
    async with db_pool.connection() as raw_connection:
        connection = PsycopgConnection(raw_connection)
        schema = DatabaseSchema(connection)
        await schema.create_tables()
    
    rss_service = NewRSSService(bot, db_pool)
    await rss_service.start()
    
    logger.info("Bot started successfully")
    return rss_service


async def on_shutdown(bot: Bot, rss_service=None, db_pool=None) -> None:
    logger.info("Bot is shutting down...")
    if rss_service:
        await rss_service.stop()
    
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed")

async def start_polling(dp: Dispatcher, bot: Bot) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

async def main() -> None:
    config = get_config()
    
    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    db_pool = await get_pg_pool(config.database)
    
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    dp.update.outer_middleware(ErrorHandlingMiddleware())
    dp.update.middleware(DataBaseMiddleware())
    dp.message.middleware(ChatTypeMiddleware())
    dp.message.middleware(UserTrackingMiddleware())
    dp.callback_query.middleware(UserTrackingMiddleware())
    
    setup_dialogs(dp)
    
    rss_service = None
    try:
        dp["db_pool"] = db_pool
        rss_service = await on_startup(bot, db_pool)
        await start_polling(dp, bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}", exc_info=True)
    finally:
        await on_shutdown(bot, rss_service, db_pool)
        await bot.session.close()