import logging
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from states.feed_management import FeedManagementSG

logger = logging.getLogger(__name__)

private_router = Router()
private_router.message.filter(F.chat.type == "private")


@private_router.message(CommandStart())
async def cmd_start(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(
        FeedManagementSG.select_chat,
        mode=StartMode.RESET_STACK
    )


@private_router.message(Command("manage"))
async def cmd_manage(message: Message, dialog_manager: DialogManager):
    await dialog_manager.start(
        FeedManagementSG.select_chat,
        mode=StartMode.RESET_STACK
    )


@private_router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = """
🤖 <b>RSS Feed Bot - Помощь</b>

<b>Команды:</b>
/start - Открыть меню управления
/manage - Управление RSS-фидами
/help - Показать эту справку

<b>Как пользоваться:</b>
1. Добавьте бота в группу/канал где вы админ
2. Используйте /start для открытия меню
3. Выберите чат из списка
4. Управляйте фидами (добавить/удалить/запустить/остановить)

<b>Возможности:</b>
• Парсинг RSS-лент
• Автоматическая отправка новостей в Telegram
• AI-рерайт новостей (опционально)
• Управление подписками для каждого чата
"""
    await message.answer(help_text, parse_mode="HTML")
