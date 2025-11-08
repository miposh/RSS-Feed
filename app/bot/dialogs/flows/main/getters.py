from aiogram import Bot
from aiogram_dialog import DialogManager

from app.infrastructure.database.db import DB
from app.services.chat_service import ChatService


async def get_rss_parser_data(dialog_manager: DialogManager, db: DB, bot: Bot, **kwargs) -> dict:
    """Get data for RSS parser dialog including list of groups."""
    channels = await db.channels.get_all_channels()
    
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
    
    # Get feeds for this channel
    chat_service = ChatService(db)
    feeds = await chat_service.get_chat_feeds(channel_id=int(selected_channel_id))
    
    # Sort feeds by creation date (newest first)
    if feeds:
        feeds = sorted(feeds, key=lambda f: f.created_at, reverse=True)
    
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
    
    # Get feeds for this channel
    chat_service = ChatService(db)
    feeds = await chat_service.get_chat_feeds(channel_id=int(selected_channel_id))
    
    # Sort feeds by creation date (newest first)
    if feeds:
        feeds = sorted(feeds, key=lambda f: f.created_at, reverse=True)
    
    # Format sources as buttons (title, url)
    source_buttons = []
    if feeds:
        for feed in feeds:
            title = feed.title or feed.url[:50] + "..."
            source_buttons.append((title, feed.url))
    
    return {
        "group_name": channel.title,
        "source_buttons": source_buttons,
    }
