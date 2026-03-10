import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram_dialog import setup_dialogs

from config.config import get_config, LogsConfig
from app.infrastructure.database.connection.connect_to_pg import get_pg_pool
from app.bot.middlewares.chat_type_middleware import ChatTypeMiddleware
from app.bot.middlewares.error_middleware import ErrorHandlingMiddleware
from app.bot.middlewares.user_tracking import UserTrackingMiddleware
from app.bot.middlewares.database import DataBaseMiddleware
from app.bot.dialogs.flows import dialogs
from app.bot.handlers import routers
from app.services.channel_rss_worker import ChannelRSSWorkerService
from app.services.cleanup_service import CleanupService
from app.services.message_queue import start_message_queue, stop_message_queue


def setup_logging(logs_config: LogsConfig) -> None:
    """Configure logging based on config settings."""
    level = getattr(logging, logs_config.level_name.upper(), logging.INFO)
    
    logging.basicConfig(
        level=level,
        format=logs_config.format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    
    logging.getLogger("aiogram").setLevel(level)
    logging.getLogger("aiogram_dialog").setLevel(level)
    logging.getLogger("psycopg").setLevel(logging.WARNING)
    logging.getLogger("psycopg_pool").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)

async def on_startup(bot: Bot, db_pool) -> tuple[ChannelRSSWorkerService, CleanupService]:
    logger.info("Bot is starting...")

    # Start the message queue (must start before workers)
    await start_message_queue()
    logger.info("Message queue started")

    # Start the channel-based RSS worker service (new)
    channel_worker_service = ChannelRSSWorkerService(bot, db_pool)
    await channel_worker_service.start()

    # Start cleanup service
    cleanup_service = CleanupService(db_pool)
    await cleanup_service.start()

    logger.info("Bot started successfully")
    return channel_worker_service, cleanup_service


async def on_shutdown(bot: Bot, channel_worker_service=None, cleanup_service=None, db_pool=None) -> None:
    logger.info("Bot is shutting down...")

    if channel_worker_service:
        await channel_worker_service.stop()

    if cleanup_service:
        await cleanup_service.stop()

    # Stop message queue (after workers)
    await stop_message_queue()
    logger.info("Message queue stopped")

    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed")

async def start_polling(dp: Dispatcher, bot: Bot) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    allowed_updates = dp.resolve_used_update_types()
    logger.info(f"Starting polling with allowed_updates: {allowed_updates}")
    await dp.start_polling(bot, allowed_updates=allowed_updates)

async def main() -> None:
    config = get_config()
    
    setup_logging(config.logs)
    logger.info(f"Logging configured: level={config.logs.level_name}")
    
    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    db_pool = await get_pg_pool(
        db_name=config.postgres.name,
        host=config.postgres.host,
        port=config.postgres.port,
        user=config.postgres.user,
        password=config.postgres.password,
    )
    
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    dp.update.outer_middleware(ErrorHandlingMiddleware())
    dp.update.middleware(DataBaseMiddleware())
    dp.message.middleware(ChatTypeMiddleware())
    dp.message.middleware(UserTrackingMiddleware())
    dp.callback_query.middleware(UserTrackingMiddleware())
    
    # Register handlers
    dp.include_routers(*routers)
    
    # Register dialogs
    dp.include_routers(*dialogs)
    
    setup_dialogs(dp)
    
    channel_worker_service = None
    cleanup_service = None

    try:
        dp["db_pool"] = db_pool
        channel_worker_service, cleanup_service = await on_startup(bot, db_pool)
        dp["channel_worker_service"] = channel_worker_service 
        await start_polling(dp, bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}", exc_info=True)
    finally:
        await on_shutdown(bot, channel_worker_service, cleanup_service, db_pool)
        await bot.session.close()