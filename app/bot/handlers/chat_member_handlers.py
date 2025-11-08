import logging
from aiogram import Bot, Router
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_ADMIN, MEMBER
from aiogram.types import ChatMemberUpdated

from app.infrastructure.database.db import DB

logger = logging.getLogger(__name__)

chat_member_router = Router()


@chat_member_router.my_chat_member(
    ChatMemberUpdatedFilter(IS_NOT_MEMBER >> (IS_ADMIN | MEMBER))
)
async def on_bot_added_to_group(event: ChatMemberUpdated, bot: Bot, db: DB) -> None:
    chat = event.chat
    
    # Debug logging
    logger.info(f"my_chat_member event: chat_type={chat.type}, chat_id={chat.id}, from_user={event.from_user.id}")
    
    if chat.type not in ["group", "supergroup"]:
        return
    
    new_status = event.new_chat_member
    
    # Check if bot has admin rights
    if new_status.status in ["administrator", "creator"]:
        logger.info(f"Bot added as admin to chat: {chat.id} ({chat.title})")
        
        channel = await db.channels.add(
            channel_id=chat.id,
            username=chat.username,
            title=chat.title,
        )
        
        if channel:
            success_message = (
                f"✅ Группа <b>{chat.title}</b>успешно подключена к боту.\n\n"
            )
            
            try:
                await bot.send_message(
                    chat_id=event.from_user.id,
                    text=success_message,
                    parse_mode="HTML"
                )
                logger.info(f"Successfully sent notification to user: {event.from_user.id}")
            except Exception as e:
                logger.error(f"Failed to send notification to user {event.from_user.id}: {e}")
                
            logger.info(f"Successfully connected group: {chat.title} (ID: {chat.id})")
        else:
            logger.error(f"Failed to save channel {chat.id} to database")
    else:
        logger.warning(f"Bot added without admin rights to chat: {chat.id} ({chat.title})")
        
        warning_message = (
            "⚠️ <b>Недостаточно прав</b>\n\n"
            "Для корректной работы бота необходимо назначить его администратором группы "
            "со следующими правами:\n\n"
            "➕ Отправка сообщений\n"
            "➕ Редактирование сообщений\n"
            "➕ Удаление сообщений\n\n"
            "Пожалуйста, выдайте боту права администратора в настройках группы."
        )
        
        try:
            await bot.send_message(
                chat_id=chat.id,
                text=warning_message,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to send warning message to chat {chat.id}: {e}")
