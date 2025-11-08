from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager

from app.bot.dialogs.flows.main.states import MainSG


async def on_group_selected(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    """Handle group selection."""
    # Store selected channel_id in dialog data for future use
    dialog_manager.dialog_data["selected_channel_id"] = item_id
    
    # TODO: Navigate to RSS feed management for this group
    await callback.answer(f"Выбрана группа с ID: {item_id}")


async def on_add_group_clicked(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Handle 'Add Group' button click - navigate to instruction window."""
    await dialog_manager.switch_to(MainSG.add_group_instruction)
