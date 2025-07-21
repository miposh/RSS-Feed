from aiogram.types import ChatMemberUpdated
from aiogram import Bot
import logging
from typing import Optional

from aiogram.exceptions import TelegramForbiddenError

from repositories.group_repository import GroupRepository
from config.config import config

logger = logging.getLogger(__name__)

# Create repository
group_repo = GroupRepository(config.db_path)

async def bot_added_to_group(event: ChatMemberUpdated, bot: Optional[Bot] = None) -> None:
    try:
        logger.info(f"Bot added handler: new status = {event.new_chat_member.status}")

        if not bot:
            logger.error("Bot instance is not available")
            return
        
        # Add group to database - this will now handle duplicates
        success = await group_repo.add_group(event.chat.id)
        if not success:
            logger.error(f"Failed to add group {event.chat.id} to database")
        
        if event.new_chat_member.status == "administrator":
            await bot.send_message(
                chat_id=event.chat.id,
                text="👋 Привет! Я бот для работы с RSS-лентами.\n\n"
                "Доступные команды:\n"
                "• /add - добавить RSS-ленту\n"
                "• /remove - удалить RSS-ленту\n"
                "• /list - показать список RSS-лент"
            )
            logger.info(f"Bot added as admin to {event.chat.title} (ID: {event.chat.id})")
        elif event.new_chat_member.status == "member":
            await bot.send_message(
                chat_id=event.chat.id,
                text="❗️ Добавьте бота @RSSFeedFetcher_Bot в администраторы с доступом к сообщениям"
            )
            logger.info(f"Bot added as member to {event.chat.title} (ID: {event.chat.id}), requested admin rights")
        else:
            await bot.send_message(
                chat_id=event.chat.id,
                text="❗️ Добавьте бота @RSSFeedFetcher_Bot в администраторы с доступом к сообщениям"
            )
            logger.info(f"Requested admin rights in {event.chat.title} (ID: {event.chat.id})")
    except TelegramForbiddenError:
        logger.warning(f"Bot added to {event.chat.title} (ID: {event.chat.id}) but can't send messages")
    except Exception as e:
        logger.error(f"Error processing bot addition to group: {e}", exc_info=True)


async def handle_bot_status_change(event: ChatMemberUpdated, bot: Optional[Bot] = None) -> None:
    logger.info(f"Status change detected: old={event.old_chat_member.status}, new={event.new_chat_member.status}")
    
    if event.old_chat_member.status in ["left", "kicked"] and event.new_chat_member.status in ["member", "administrator"]:
        logger.info(f"Bot was added to group or promoted to {event.chat.title} (ID: {event.chat.id})")
        return await bot_added_to_group(event, bot)
    elif event.old_chat_member.status in ["member", "administrator"] and event.new_chat_member.status in ["left", "kicked"]:
        logger.info(f"Bot was removed from group from {event.chat.title} (ID: {event.chat.id})")
        # Remove group from database
        await group_repo.remove_group(event.chat.id)
    elif event.old_chat_member.status == "member" and event.new_chat_member.status == "administrator":
        logger.info(f"Bot was promoted to administrator from {event.chat.title} (ID: {event.chat.id})")
        return await bot_added_to_group(event, bot)
    else:
        logger.info(f"Unhandled status change: {event.old_chat_member.status} -> {event.new_chat_member.status}") 