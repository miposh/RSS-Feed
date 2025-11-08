from aiogram import Bot
from aiogram_dialog import DialogManager

from app.infrastructure.database.db import DB


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
    }
