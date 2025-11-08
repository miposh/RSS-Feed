from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode

from app.bot.dialogs.flows.main.states import MainSG

commands_router = Router()


@commands_router.message(CommandStart())
async def process_rss_command(
    message: Message,
    dialog_manager: DialogManager,
) -> None:
    await dialog_manager.start(state=MainSG.rss_parser, mode=StartMode.RESET_STACK)
