from aiogram import Bot
from aiogram_dialog import DialogManager

from app.infrastructure.database.db import DB
from app.services.chat_service import ChatService


async def get_rss_parser_data(dialog_manager: DialogManager, db: DB, bot: Bot, **kwargs) -> dict:
    """Get data for RSS parser dialog including list of groups where user is admin."""
    user_id = dialog_manager.event.from_user.id
    channels = await db.channels.get_channels_for_admin(telegram_user_id=user_id)
    
    group_buttons = []
    if channels:
        for channel in channels:
            group_buttons.append((channel.title, str(channel.channel_id)))
    
    bot_me = await bot.get_me()
    bot_username = bot_me.username
    
    add_group_url = f"https://t.me/{bot_username}?startgroup&admin=post_messages+edit_messages+delete_messages+manage_chat"
    
    return {
        "group_buttons": group_buttons,
        "add_group_url": add_group_url,
        "bot_username": bot_username,
    }


async def get_group_menu_data(dialog_manager: DialogManager, db: DB, **kwargs) -> dict:
    """Get data for group menu window."""
    selected_channel_id = dialog_manager.dialog_data.get("selected_channel_id")
    
    if not selected_channel_id:
        return {
            "group_name": "Неизвестная группа",
            "is_enabled": False,
        }
    
    # Get channel info from database
    channel = await db.channels.get_channel(channel_id=int(selected_channel_id))
    
    if not channel:
        return {
            "group_name": "Группа не найдена",
            "is_enabled": False,
        }
    
    return {
        "group_name": channel.title,
        "is_enabled": channel.parsing_is_enabled,
        "toggle_text": "🔘 Выключить" if channel.parsing_is_enabled else "⭕️ Включить",
    }


async def get_sources_list_data(dialog_manager: DialogManager, db: DB, **kwargs) -> dict:
    """Get data for sources list window."""
    selected_channel_id = dialog_manager.dialog_data.get("selected_channel_id")
    
    if not selected_channel_id:
        return {
            "group_name": "Неизвестная группа",
            "sources": [],
            "sources_count": 0,
        }
    
    # Get channel info
    channel = await db.channels.get_channel(channel_id=int(selected_channel_id))
    if not channel:
        return {
            "group_name": "Группа не найдена",
            "sources": [],
            "sources_count": 0,
        }
    
    # Get feeds for this channel (already newest first)
    chat_service = ChatService(db)
    feeds = await chat_service.get_chat_feeds(channel_id=int(selected_channel_id))

    # Format sources for display
    sources_list = []
    if feeds:
        for idx, feed in enumerate(feeds, 1):
            title = feed.title or "Без названия"
            sources_list.append(f"{idx}. {title}\n   {feed.url}")
    
    return {
        "group_name": channel.title,
        "sources": "\n\n".join(sources_list) if sources_list else "Нет источников",
        "sources_count": len(feeds) if feeds else 0,
    }


async def get_remove_source_data(dialog_manager: DialogManager, db: DB, **kwargs) -> dict:
    """Get data for remove source window."""
    selected_channel_id = dialog_manager.dialog_data.get("selected_channel_id")
    
    if not selected_channel_id:
        return {
            "group_name": "Неизвестная группа",
            "source_buttons": [],
        }
    
    # Get channel info
    channel = await db.channels.get_channel(channel_id=int(selected_channel_id))
    if not channel:
        return {
            "group_name": "Группа не найдена",
            "source_buttons": [],
        }
    
    # Get feeds for this channel (already newest first)
    chat_service = ChatService(db)
    feeds = await chat_service.get_chat_feeds(channel_id=int(selected_channel_id))

    # Format sources as buttons (title, feed_id)
    # Use feed.id instead of URL to avoid BUTTON_DATA_INVALID error
    # (Telegram limits callback_data to 64 bytes)
    source_buttons = []
    if feeds:
        for feed in feeds:
            title = feed.title or feed.url[:50] + "..."
            source_buttons.append((title, str(feed.id)))
    
    return {
        "group_name": channel.title,
        "source_buttons": source_buttons,
    }


SCRAPER_TYPE_NAMES = {
    "scraperapi": "ScraperAPI",
    "botasaurus": "Botasaurus",
}


async def get_channel_settings_data(dialog_manager: DialogManager, db: DB, **kwargs) -> dict:
    """Get data for channel settings window."""
    selected_channel_id = dialog_manager.dialog_data.get("selected_channel_id")
    
    if not selected_channel_id:
        return {
            "group_name": "Неизвестная группа",
            "interval_time": 300,
            "interval_minutes": 5,
            "scraper_is_enabled": False,
            "scraper_status": "❌ Выключен",
            "scraper_toggle_text": "⭕️ Включить скрапер",
            "scraper_type": "botasaurus",
            "scraper_type_name": "Botasaurus",
            "api_key_status": "Не установлен",
        }
    
    # Get channel info from database
    channel = await db.channels.get_channel(channel_id=int(selected_channel_id))
    
    if not channel:
        return {
            "group_name": "Группа не найдена",
            "interval_time": 300,
            "interval_minutes": 5,
            "scraper_is_enabled": False,
            "scraper_status": "❌ Выключен",
            "scraper_toggle_text": "⭕️ Включить скрапер",
            "scraper_type": "botasaurus",
            "scraper_type_name": "Botasaurus",
            "api_key_status": "Не установлен",
        }
    
    interval_minutes = channel.interval_time // 60
    scraper_toggle_text = "🔘 Выключить скрапер" if channel.scraper_is_enabled else "⭕️ Включить скрапер"
    scraper_status = "✅ Включен" if channel.scraper_is_enabled else "❌ Выключен"
    scraper_type_name = SCRAPER_TYPE_NAMES.get(channel.scraper_type, channel.scraper_type)
    
    if channel.scraper_api_key:
        # Show masked API key
        masked_key = channel.scraper_api_key[:8] + "..." + channel.scraper_api_key[-4:] if len(channel.scraper_api_key) > 12 else "***"
        api_key_status = f"{masked_key}"
    else:
        api_key_status = "Не установлен"
    
    return {
        "group_name": channel.title,
        "interval_time": channel.interval_time,
        "interval_minutes": interval_minutes,
        "scraper_is_enabled": channel.scraper_is_enabled,
        "scraper_status": scraper_status,
        "scraper_toggle_text": scraper_toggle_text,
        "scraper_type": channel.scraper_type,
        "scraper_type_name": scraper_type_name,
        "api_key_status": api_key_status,
    }


async def get_global_settings_data(dialog_manager: DialogManager, db: DB, **kwargs) -> dict:
    """Get data for global settings window (scoped to user's admin groups)."""
    user_id = dialog_manager.event.from_user.id
    channels = await db.channels.get_channels_for_admin(telegram_user_id=user_id)
    
    if not channels:
        return {
            "total_channels": 0,
            "enabled_count": 0,
            "disabled_count": 0,
        }
    
    enabled_count = sum(1 for c in channels if c.parsing_is_enabled)
    disabled_count = len(channels) - enabled_count
    
    return {
        "total_channels": len(channels),
        "enabled_count": enabled_count,
        "disabled_count": disabled_count,
    }
