import logging
from typing import Any

from aiogram import Bot
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import MessageInput

from app.bot.dialogs.flows.main.states import MainSG
from app.infrastructure.database.db import DB
from app.services.admin_service import SYNC_FAILED, sync_group_admins
from app.services.chat_service import ChatService
from app.services.channel_rss_worker import ChannelRSSWorkerService

logger = logging.getLogger(__name__)


async def _check_admin_permission(
    dialog_manager: DialogManager,
    user_id: int,
    channel_id: int,
) -> bool:
    """Check if a Telegram user is admin for a Telegram channel."""
    db: DB = dialog_manager.middleware_data.get("db")
    return await db.channel_admins.is_admin(
        telegram_user_id=user_id,
        telegram_channel_id=channel_id,
    )


async def _require_admin(
    callback_or_message: CallbackQuery | Message,
    dialog_manager: DialogManager,
) -> int | None:
    """Verify admin permission on the selected channel.

    Returns the telegram channel_id if allowed, or None after sending an error.
    """
    selected_channel_id = dialog_manager.dialog_data.get("selected_channel_id")
    if not selected_channel_id:
        await callback_or_message.answer("❌ Ошибка: группа не выбрана")
        return None

    channel_id = int(selected_channel_id)
    user_id = callback_or_message.from_user.id
    is_admin = await _check_admin_permission(dialog_manager, user_id, channel_id)
    if not is_admin:
        await callback_or_message.answer("❌ У вас нет прав на эту группу")
        return None

    return channel_id


async def _reload_channel_worker(
    dialog_manager: DialogManager,
    channel_id: int,
) -> None:
    """Reload channel worker after settings change."""
    try:
        worker_service: ChannelRSSWorkerService = dialog_manager.middleware_data.get("channel_worker_service")
        if worker_service:
            logger.info(f"Reloading worker for channel {channel_id}")
            await worker_service.reload_channel(channel_id=channel_id)
            logger.info(f"Worker reloaded for channel {channel_id}. Active workers: {list(worker_service.workers.keys())}")
        else:
            logger.warning("channel_worker_service not found in middleware_data")
    except Exception as e:
        logger.error(f"Error reloading worker for channel {channel_id}: {e}", exc_info=True)


async def on_group_selected(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    """Handle group selection with admin permission check."""
    user_id = callback.from_user.id
    is_admin = await _check_admin_permission(dialog_manager, user_id, int(item_id))
    if not is_admin:
        await callback.answer("❌ У вас нет прав на эту группу")
        return

    dialog_manager.dialog_data["selected_channel_id"] = item_id
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
    channel_id = await _require_admin(callback, dialog_manager)
    if channel_id is None:
        return

    db: DB = dialog_manager.middleware_data.get("db")

    try:
        channel = await db.channels.toggle_parsing(channel_id=channel_id)

        if channel:
            status = "включен" if channel.parsing_is_enabled else "выключен"
            await callback.answer(f"✅ Парсинг {status}")
            await _reload_channel_worker(dialog_manager, channel_id)
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
    """Handle delete group button - show confirmation."""
    await dialog_manager.switch_to(MainSG.delete_group_confirm)


async def on_delete_group_confirmed(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Handle confirmed group deletion."""
    channel_id = await _require_admin(callback, dialog_manager)
    if channel_id is None:
        return

    db: DB = dialog_manager.middleware_data.get("db")

    try:
        # Stop worker first
        worker_service: ChannelRSSWorkerService = dialog_manager.middleware_data.get("channel_worker_service")
        if worker_service and channel_id in worker_service.workers:
            worker = worker_service.workers.pop(channel_id)
            await worker.stop()
            logger.info(f"Stopped worker for channel {channel_id} before deletion")

        # Delete channel from database (cascades to subscriptions and channel_admins)
        await db.channels.delete(channel_id=channel_id)

        await callback.answer("✅ Группа удалена")
        logger.info(f"Channel {channel_id} deleted")

        await dialog_manager.switch_to(MainSG.rss_parser)

    except Exception as e:
        logger.error(f"Error deleting channel {channel_id}: {e}", exc_info=True)
        await callback.answer(f"❌ Ошибка: {str(e)}")


async def on_source_url_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
) -> None:
    """Handle RSS feed URL input."""
    channel_id = await _require_admin(message, dialog_manager)
    if channel_id is None:
        return

    db: DB = dialog_manager.middleware_data.get("db")
    feed_url = message.text.strip()

    if not feed_url.startswith(("http://", "https://")):
        await message.answer("❌ Неверный формат URL. URL должен начинаться с http:// или https://")
        return

    try:
        chat_service = ChatService(db)
        success = await chat_service.add_feed_to_chat(
            channel_id=channel_id,
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
    channel_id = await _require_admin(callback, dialog_manager)
    if channel_id is None:
        return

    db: DB = dialog_manager.middleware_data.get("db")

    try:
        chat_service = ChatService(db)
        success = await chat_service.remove_feed_by_id(
            channel_id=channel_id,
            feed_id=int(item_id)
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
    channel_id = await _require_admin(callback, dialog_manager)
    if channel_id is None:
        return

    db: DB = dialog_manager.middleware_data.get("db")

    try:
        channel = await db.channels.toggle_scraper(channel_id=channel_id)

        if channel:
            status = "включен" if channel.scraper_is_enabled else "выключен"
            await callback.answer(f"✅ Скрапер {status}")
            await _reload_channel_worker(dialog_manager, channel_id)
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


async def on_set_scraper_type_clicked(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Handle set scraper type button click."""
    await dialog_manager.switch_to(MainSG.set_scraper_type)


async def on_scraper_type_selected(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
    item_id: str,
) -> None:
    """Handle scraper type selection."""
    channel_id = await _require_admin(callback, dialog_manager)
    if channel_id is None:
        return

    db: DB = dialog_manager.middleware_data.get("db")

    try:
        if item_id == "scraperapi":
            channel = await db.channels.get_channel(channel_id=channel_id)
            if channel and not channel.scraper_api_key:
                dialog_manager.dialog_data["pending_scraper_type"] = item_id
                await callback.answer("⚠️ Для ScraperAPI требуется API ключ")
                await dialog_manager.switch_to(MainSG.set_scraper_api_key)
                return

        channel = await db.channels.update_scraper_type(
            channel_id=channel_id,
            scraper_type=item_id
        )

        if channel:
            type_names = {
                "scraperapi": "ScraperAPI",
                "botasaurus": "Botasaurus",
            }
            type_name = type_names.get(item_id, item_id)
            await callback.answer(f"✅ Тип скрапера: {type_name}")
            await _reload_channel_worker(dialog_manager, channel_id)
            await dialog_manager.switch_to(MainSG.channel_settings)
        else:
            await callback.answer("❌ Не удалось изменить тип скрапера")
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}")


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
    channel_id = await _require_admin(callback, dialog_manager)
    if channel_id is None:
        return

    db: DB = dialog_manager.middleware_data.get("db")

    try:
        interval = int(item_id)

        channel = await db.channels.update_interval_time(
            channel_id=channel_id,
            interval_time=interval
        )

        if channel:
            minutes = interval // 60
            await callback.answer(f"✅ Интервал установлен: {minutes} минут")
            await _reload_channel_worker(dialog_manager, channel_id)
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
    channel_id = await _require_admin(message, dialog_manager)
    if channel_id is None:
        return

    db: DB = dialog_manager.middleware_data.get("db")

    try:
        interval = int(message.text.strip())

        if interval < 60:
            await message.answer("❌ Интервал не может быть меньше 60 секунд")
            return

        if interval > 86400:
            await message.answer("❌ Интервал не может быть больше 24 часов (86400 секунд)")
            return

        channel = await db.channels.update_interval_time(
            channel_id=channel_id,
            interval_time=interval
        )

        if channel:
            minutes = interval // 60
            await message.answer(f"✅ Интервал обновлен: {interval} секунд ({minutes} минут)")
            await _reload_channel_worker(dialog_manager, channel_id)
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
    channel_id = await _require_admin(message, dialog_manager)
    if channel_id is None:
        return

    db: DB = dialog_manager.middleware_data.get("db")
    api_key = message.text.strip()

    if not api_key:
        api_key = None

    pending_scraper_type = dialog_manager.dialog_data.get("pending_scraper_type")
    if pending_scraper_type == "scraperapi" and not api_key:
        await message.answer("❌ Для ScraperAPI требуется API ключ. Введите ключ или выберите другой тип скрапера.")
        return

    try:
        channel = await db.channels.update_scraper_api_key(
            channel_id=channel_id,
            api_key=api_key
        )

        if channel:
            if pending_scraper_type and api_key:
                await db.channels.update_scraper_type(
                    channel_id=channel_id,
                    scraper_type=pending_scraper_type
                )
                dialog_manager.dialog_data.pop("pending_scraper_type", None)
                await message.answer("✅ API ключ установлен, тип скрапера: ScraperAPI")
            elif api_key:
                await message.answer("✅ API ключ успешно обновлен")
            else:
                await message.answer("✅ API ключ удален")

            await _reload_channel_worker(dialog_manager, channel_id)
            await dialog_manager.switch_to(MainSG.channel_settings)
        else:
            await message.answer("❌ Не удалось обновить API ключ")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


# ============ Refresh Admins ============

async def on_refresh_admins(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Refresh admin list for the selected group from Telegram API."""
    channel_id = await _require_admin(callback, dialog_manager)
    if channel_id is None:
        return

    db: DB = dialog_manager.middleware_data.get("db")
    bot: Bot = dialog_manager.middleware_data.get("bot")

    channel = await db.channels.get_channel(channel_id=channel_id)
    if not channel:
        await callback.answer("❌ Группа не найдена")
        return

    synced_count = await sync_group_admins(
        bot=bot, db=db, chat_id=channel_id, internal_channel_id=channel.id,
    )

    if synced_count != SYNC_FAILED:
        # Verify calling user is still admin after sync
        user_id = callback.from_user.id
        still_admin = await _check_admin_permission(dialog_manager, user_id, channel_id)
        if not still_admin:
            await callback.answer("⚠️ Вы больше не админ этой группы в Telegram")
            await dialog_manager.switch_to(MainSG.rss_parser)
            return
        await callback.answer(f"✅ Синхронизировано админов: {synced_count}")
    else:
        await callback.answer("❌ Не удалось получить список админов")

    await dialog_manager.show()


# ============ Global Settings Handlers ============

async def on_global_settings_clicked(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Handle global settings button click."""
    await dialog_manager.switch_to(MainSG.global_settings)


async def _set_global_parsing(
    callback: CallbackQuery,
    dialog_manager: DialogManager,
    enabled: bool,
) -> None:
    """Enable or disable parsing across every group the caller administers."""
    db: DB = dialog_manager.middleware_data.get("db")

    try:
        count = await db.channels.set_parsing_for_admin(
            telegram_user_id=callback.from_user.id,
            enabled=enabled,
        )

        action = "включен" if enabled else "выключен"
        await callback.answer(f"✅ Парсинг {action} для {count} групп")

        worker_service: ChannelRSSWorkerService = dialog_manager.middleware_data.get("channel_worker_service")
        if worker_service:
            await worker_service.sync_workers()

        await dialog_manager.show()
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)}")


async def on_global_enable_parsing(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Enable parsing for user's admin groups."""
    await _set_global_parsing(callback, dialog_manager, enabled=True)


async def on_global_disable_parsing(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Disable parsing for user's admin groups."""
    await _set_global_parsing(callback, dialog_manager, enabled=False)


async def on_global_set_api_key_clicked(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
) -> None:
    """Handle global set API key button click."""
    await dialog_manager.switch_to(MainSG.global_set_api_key)


async def on_global_api_key_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
) -> None:
    """Handle global scraper API key input (scoped to user's admin groups)."""
    db: DB = dialog_manager.middleware_data.get("db")

    api_key = message.text.strip() or None

    try:
        count = await db.channels.set_api_key_for_admin(
            telegram_user_id=message.from_user.id,
            api_key=api_key,
        )

        if api_key:
            await message.answer(f"✅ API ключ установлен для {count} групп")
        else:
            await message.answer(f"✅ API ключ удален для {count} групп")

        worker_service: ChannelRSSWorkerService = dialog_manager.middleware_data.get("channel_worker_service")
        if worker_service:
            await worker_service.sync_workers()

        await dialog_manager.switch_to(MainSG.global_settings)
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
