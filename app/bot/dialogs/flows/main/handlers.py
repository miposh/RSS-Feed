from typing import Any

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import MessageInput

from app.bot.dialogs.flows.main.states import MainSG
from app.infrastructure.database.db import DB
from app.services.chat_service import ChatService


async def on_group_selected(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    """Handle group selection."""
    # Store selected channel_id in dialog data for future use
    dialog_manager.dialog_data["selected_channel_id"] = item_id
    
    # Navigate to group menu
    await dialog_manager.switch_to(MainSG.group_menu)


async def on_add_group_clicked(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Handle 'Add Group' button click - navigate to instruction window."""
    await dialog_manager.switch_to(MainSG.add_group_instruction)


async def on_toggle_group(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Handle toggle group enabled/disabled."""
    db: DB = dialog_manager.middleware_data.get("db")
    selected_channel_id = dialog_manager.dialog_data.get("selected_channel_id")
    
    if not selected_channel_id:
        await callback.answer("❌ Ошибка: группа не выбрана")
        return
    
    try:
        # Toggle parsing status
        channel = await db.channels.toggle_parsing(channel_id=int(selected_channel_id))
        
        if channel:
            status = "включен" if channel.parsing_is_enabled else "выключен"
            await callback.answer(f"✅ Парсинг {status}")
            # Refresh the window to update button text
            await dialog_manager.show()
        else:
            await callback.answer("❌ Не удалось изменить статус")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}")


async def on_list_sources(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Handle list sources button."""
    await dialog_manager.switch_to(MainSG.sources_list)


async def on_add_source(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Handle add source button."""
    await dialog_manager.switch_to(MainSG.add_source)


async def on_remove_source(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Handle remove source button."""
    await dialog_manager.switch_to(MainSG.remove_source)


async def on_delete_group(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Handle delete group button."""
    # TODO: Implement group deletion with confirmation
    await callback.answer("Удаление группы в разработке")


async def on_source_url_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
) -> None:
    """Handle RSS feed URL input."""
    db: DB = dialog_manager.middleware_data.get("db")
    selected_channel_id = dialog_manager.dialog_data.get("selected_channel_id")
    
    if not selected_channel_id:
        await message.answer("❌ Ошибка: группа не выбрана")
        return
    
    feed_url = message.text.strip()
    
    # Validate URL format
    if not feed_url.startswith(("http://", "https://")):
        await message.answer("❌ Неверный формат URL. URL должен начинаться с http:// или https://")
        return
    
    try:
        chat_service = ChatService(db)
        success = await chat_service.add_feed_to_chat(
            channel_id=int(selected_channel_id),
            feed_url=feed_url
        )
        
        if success:
            await message.answer(f"✅ Источник успешно добавлен:\n{feed_url}")
            await dialog_manager.switch_to(MainSG.group_menu)
        else:
            await message.answer("❌ Не удалось добавить источник. Возможно, он уже существует.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при добавлении источника: {str(e)}")


async def on_source_selected(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    """Handle source selection for deletion."""
    db: DB = dialog_manager.middleware_data.get("db")
    selected_channel_id = dialog_manager.dialog_data.get("selected_channel_id")
    
    if not selected_channel_id:
        await callback.answer("❌ Ошибка: группа не выбрана")
        return
    
    try:
        # item_id is the feed URL
        chat_service = ChatService(db)
        success = await chat_service.remove_feed_from_chat(
            channel_id=int(selected_channel_id),
            feed_url=item_id
        )
        
        if success:
            await callback.answer("✅ Источник удален")
            await dialog_manager.switch_to(MainSG.group_menu)
        else:
            await callback.answer("❌ Не удалось удалить источник")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}")
