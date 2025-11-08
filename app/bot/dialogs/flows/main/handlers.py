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


async def on_settings_clicked(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Handle settings button click."""
    await dialog_manager.switch_to(MainSG.channel_settings)


async def on_toggle_scraper(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Handle toggle scraper enabled/disabled."""
    db: DB = dialog_manager.middleware_data.get("db")
    selected_channel_id = dialog_manager.dialog_data.get("selected_channel_id")
    
    if not selected_channel_id:
        await callback.answer("❌ Ошибка: группа не выбрана")
        return
    
    try:
        channel = await db.channels.toggle_scraper(channel_id=int(selected_channel_id))
        
        if channel:
            status = "включен" if channel.scraper_is_enabled else "выключен"
            await callback.answer(f"✅ Скрапер {status}")
            await dialog_manager.show()
        else:
            await callback.answer("❌ Не удалось изменить статус")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}")


async def on_set_interval_clicked(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Handle set interval button click."""
    await dialog_manager.switch_to(MainSG.set_interval)


async def on_set_api_key_clicked(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Handle set API key button click."""
    await dialog_manager.switch_to(MainSG.set_scraper_api_key)


async def on_back_to_settings(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Handle back to settings button click."""
    await dialog_manager.switch_to(MainSG.channel_settings)


async def on_interval_preset_selected(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    """Handle preset interval selection."""
    db: DB = dialog_manager.middleware_data.get("db")
    selected_channel_id = dialog_manager.dialog_data.get("selected_channel_id")
    
    if not selected_channel_id:
        await callback.answer("❌ Ошибка: группа не выбрана")
        return
    
    try:
        interval = int(item_id)
        
        channel = await db.channels.update_interval_time(
            channel_id=int(selected_channel_id),
            interval_time=interval
        )
        
        if channel:
            minutes = interval // 60
            await callback.answer(f"✅ Интервал установлен: {minutes} минут")
            await dialog_manager.switch_to(MainSG.channel_settings)
        else:
            await callback.answer("❌ Не удалось обновить интервал")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}")


async def on_custom_interval_clicked(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Handle custom interval button click."""
    await dialog_manager.switch_to(MainSG.set_interval_custom)


async def on_interval_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
) -> None:
    """Handle interval time input."""
    db: DB = dialog_manager.middleware_data.get("db")
    selected_channel_id = dialog_manager.dialog_data.get("selected_channel_id")
    
    if not selected_channel_id:
        await message.answer("❌ Ошибка: группа не выбрана")
        return
    
    try:
        interval = int(message.text.strip())
        
        if interval < 60:
            await message.answer("❌ Интервал не может быть меньше 60 секунд")
            return
        
        if interval > 86400:
            await message.answer("❌ Интервал не может быть больше 24 часов (86400 секунд)")
            return
        
        channel = await db.channels.update_interval_time(
            channel_id=int(selected_channel_id),
            interval_time=interval
        )
        
        if channel:
            minutes = interval // 60
            await message.answer(f"✅ Интервал обновлен: {interval} секунд ({minutes} минут)")
            await dialog_manager.switch_to(MainSG.channel_settings)
        else:
            await message.answer("❌ Не удалось обновить интервал")
    except ValueError:
        await message.answer("❌ Введите целое число секунд")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


async def on_api_key_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
) -> None:
    """Handle scraper API key input."""
    db: DB = dialog_manager.middleware_data.get("db")
    selected_channel_id = dialog_manager.dialog_data.get("selected_channel_id")
    
    if not selected_channel_id:
        await message.answer("❌ Ошибка: группа не выбрана")
        return
    
    api_key = message.text.strip()
    
    # Allow empty string to clear the API key
    if not api_key:
        api_key = None
    
    try:
        channel = await db.channels.update_scraper_api_key(
            channel_id=int(selected_channel_id),
            api_key=api_key
        )
        
        if channel:
            if api_key:
                await message.answer("✅ API ключ успешно обновлен")
            else:
                await message.answer("✅ API ключ удален (будет использоваться глобальный)")
            await dialog_manager.switch_to(MainSG.channel_settings)
        else:
            await message.answer("❌ Не удалось обновить API ключ")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
