"""Feed management dialog using aiogram-dialog"""
import logging
from typing import Any, Dict

from aiogram import Bot
from aiogram.types import CallbackQuery, Message, ChatMemberOwner, ChatMemberAdministrator
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.widgets.kbd import Button, Select, Row, Back, Cancel
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import MessageInput

from states.feed_management import FeedManagementSG
from repositories.chat_repository import ChatRepository
from repositories.feed_repository import FeedRepository
from repositories.subscription_repository import SubscriptionRepository
from config.config import config

logger = logging.getLogger(__name__)


# ============================================================================
# Data Getters
# ============================================================================

async def get_user_admin_chats(dialog_manager: DialogManager, event_from_user, **kwargs) -> Dict[str, Any]:
    """Get chats where user is admin and bot is present"""
    bot: Bot = dialog_manager.middleware_data.get("bot")
    user_id = event_from_user.id
    
    admin_chats = []
    
    # Get all chats from database
    chat_repo = ChatRepository(config.db_path)
    all_chats = await chat_repo.get_all_chats()
    
    for chat_db in all_chats:
        chat_internal_id, telegram_chat_id, title, username, chat_type, ai_enabled = chat_db
        
        try:
            # Check if user is admin
            member = await bot.get_chat_member(telegram_chat_id, user_id)
            if isinstance(member, (ChatMemberOwner, ChatMemberAdministrator)):
                admin_chats.append({
                    'id': telegram_chat_id,
                    'internal_id': chat_internal_id,
                    'title': title or f"Chat {telegram_chat_id}",
                    'username': username,
                    'type': chat_type,
                    'ai_enabled': ai_enabled
                })
        except Exception as e:
            logger.debug(f"Cannot check admin status for chat {telegram_chat_id}: {e}")
            continue
    
    return {
        'chats': admin_chats,
        'has_chats': len(admin_chats) > 0
    }


async def get_chat_info(dialog_manager: DialogManager, **kwargs) -> Dict[str, Any]:
    """Get selected chat info and feeds"""
    chat_data = dialog_manager.dialog_data.get('selected_chat')
    
    if not chat_data:
        return {'error': 'No chat selected'}
    
    chat_repo = ChatRepository(config.db_path)
    feed_repo = FeedRepository(config.db_path)
    sub_repo = SubscriptionRepository(config.db_path)
    
    # Get chat info
    chat_internal_id = chat_data['internal_id']
    telegram_chat_id = chat_data['id']
    
    # Get feeds for this chat
    feeds = await feed_repo.get_feeds_for_chat(chat_internal_id)
    subscriptions = await sub_repo.get_subscriptions_for_chat(chat_internal_id)
    
    feed_list = []
    for feed in feeds:
        feed_id, url, title, active, sub_active = feed
        feed_list.append({
            'id': feed_id,
            'url': url,
            'title': title or url[:50],
            'active': active,
            'sub_active': sub_active
        })
    
    return {
        'chat_title': chat_data['title'],
        'chat_id': telegram_chat_id,
        'ai_enabled': chat_data.get('ai_enabled', 0),
        'feeds': feed_list,
        'feed_count': len(feed_list)
    }


# ============================================================================
# Button Handlers
# ============================================================================

async def on_chat_selected(
    callback: CallbackQuery, 
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str
):
    """Handler when chat is selected"""
    chats = dialog_manager.dialog_data.get('chats', [])
    selected_chat = None
    
    # Find selected chat by telegram_chat_id
    for chat in chats:
        if str(chat['id']) == item_id:
            selected_chat = chat
            break
    
    if selected_chat:
        dialog_manager.dialog_data['selected_chat'] = selected_chat
        await dialog_manager.switch_to(FeedManagementSG.chat_menu)


async def on_start_feed_processing(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager
):
    """Start RSS feed processing for selected chat"""
    chat_data = dialog_manager.dialog_data.get('selected_chat')
    if not chat_data:
        await callback.answer("Ошибка: чат не выбран")
        return
    
    chat_repo = ChatRepository(config.db_path)
    success = await chat_repo.set_ai_enabled(chat_data['id'], True)
    
    if success:
        await callback.answer("✅ RSS-рассылка запущена!")
        dialog_manager.dialog_data['selected_chat']['ai_enabled'] = 1
    else:
        await callback.answer("❌ Ошибка при запуске")


async def on_stop_feed_processing(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager
):
    """Stop RSS feed processing for selected chat"""
    chat_data = dialog_manager.dialog_data.get('selected_chat')
    if not chat_data:
        await callback.answer("Ошибка: чат не выбран")
        return
    
    chat_repo = ChatRepository(config.db_path)
    success = await chat_repo.set_ai_enabled(chat_data['id'], False)
    
    if success:
        await callback.answer("⏸ RSS-рассылка остановлена")
        dialog_manager.dialog_data['selected_chat']['ai_enabled'] = 0
    else:
        await callback.answer("❌ Ошибка при остановке")


async def on_delete_chat(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager
):
    """Delete chat and all subscriptions"""
    await dialog_manager.switch_to(FeedManagementSG.confirm_delete)


async def on_confirm_delete(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager
):
    """Confirm deletion"""
    chat_data = dialog_manager.dialog_data.get('selected_chat')
    if not chat_data:
        await callback.answer("Ошибка: чат не выбран")
        return
    
    chat_repo = ChatRepository(config.db_path)
    success = await chat_repo.delete_chat(chat_data['id'])
    
    if success:
        await callback.answer("🗑 Чат удалён из базы")
        await dialog_manager.switch_to(FeedManagementSG.select_chat)
    else:
        await callback.answer("❌ Ошибка при удалении")


async def on_manage_feeds(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager
):
    """Go to feed management"""
    await dialog_manager.switch_to(FeedManagementSG.manage_feeds)


async def on_add_feed_clicked(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager
):
    """Go to add feed state"""
    await dialog_manager.switch_to(FeedManagementSG.add_feed)


async def on_feed_url_received(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager
):
    """Handler for receiving feed URL"""
    url = message.text.strip()
    
    # Basic URL validation
    if not url.startswith(('http://', 'https://')):
        await message.answer("❌ Некорректный URL. Должен начинаться с http:// или https://")
        return
    
    chat_data = dialog_manager.dialog_data.get('selected_chat')
    if not chat_data:
        await message.answer("❌ Ошибка: чат не выбран")
        return
    
    feed_repo = FeedRepository(config.db_path)
    sub_repo = SubscriptionRepository(config.db_path)
    
    # Add feed
    feed_id = await feed_repo.add_feed(url)
    if not feed_id:
        await message.answer("❌ Ошибка при добавлении фида")
        return
    
    # Subscribe chat to feed
    chat_internal_id = chat_data['internal_id']
    success = await sub_repo.subscribe(chat_internal_id, feed_id)
    
    if success:
        await message.answer(f"✅ RSS-фид добавлен:\n{url}")
        await dialog_manager.switch_to(FeedManagementSG.manage_feeds)
    else:
        await message.answer("❌ Ошибка при подписке на фид")


async def on_toggle_feed(
    callback: CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str
):
    """Toggle feed active status"""
    feed_id = int(item_id)
    sub_repo = SubscriptionRepository(config.db_path)
    
    chat_data = dialog_manager.dialog_data.get('selected_chat')
    if not chat_data:
        await callback.answer("❌ Ошибка: чат не выбран")
        return
    
    chat_internal_id = chat_data['internal_id']
    success = await sub_repo.toggle_subscription(chat_internal_id, feed_id)
    
    if success:
        await callback.answer("✅ Статус подписки изменён")
    else:
        await callback.answer("❌ Ошибка")


# ============================================================================
# Dialog Windows
# ============================================================================

select_chat_window = Window(
    Const("🤖 <b>Управление RSS-фидами</b>\n\n"
          "Выберите чат/канал для управления:"),
    Select(
        Format("{item[title]}"),
        id="chat_select",
        item_id_getter=lambda x: str(x['id']),
        items="chats",
        on_click=on_chat_selected
    ),
    Cancel(Const("❌ Отмена")),
    state=FeedManagementSG.select_chat,
    getter=get_user_admin_chats
)

chat_menu_window = Window(
    Format("<b>📱 {chat_title}</b>\n\n"
           "ID: <code>{chat_id}</code>\n"
           "AI-рерайт: {'✅ Включен' if ai_enabled else '❌ Выключен'}\n"
           "RSS-фидов: {feed_count}"),
    Row(
        Button(
            Const("▶️ Запустить"),
            id="start_btn",
            on_click=on_start_feed_processing
        ),
        Button(
            Const("⏸ Остановить"),
            id="stop_btn",
            on_click=on_stop_feed_processing
        ),
    ),
    Button(
        Const("📋 Управление фидами"),
        id="manage_feeds_btn",
        on_click=on_manage_feeds
    ),
    Button(
        Const("🗑 Удалить из базы"),
        id="delete_btn",
        on_click=on_delete_chat
    ),
    Back(Const("🔙 Назад")),
    state=FeedManagementSG.chat_menu,
    getter=get_chat_info
)

manage_feeds_window = Window(
    Format("<b>📋 RSS-фиды для {chat_title}</b>\n\n"
           "Фидов: {feed_count}"),
    Select(
        Format("{'✅' if item['sub_active'] else '❌'} {item['title'][:40]}"),
        id="feed_toggle",
        item_id_getter=lambda x: str(x['id']),
        items="feeds",
        on_click=on_toggle_feed
    ),
    Button(
        Const("➕ Добавить новый фид"),
        id="add_feed_btn",
        on_click=on_add_feed_clicked
    ),
    Back(Const("🔙 Назад")),
    state=FeedManagementSG.manage_feeds,
    getter=get_chat_info
)

add_feed_window = Window(
    Const("<b>➕ Добавление RSS-фида</b>\n\n"
          "Отправьте URL RSS-ленты:"),
    MessageInput(on_feed_url_received),
    Back(Const("🔙 Отмена")),
    state=FeedManagementSG.add_feed
)

confirm_delete_window = Window(
    Format("<b>⚠️ Подтверждение удаления</b>\n\n"
           "Вы уверены, что хотите удалить чат <b>{chat_title}</b> из базы?\n\n"
           "Это удалит все подписки и историю доставок."),
    Row(
        Button(
            Const("✅ Да, удалить"),
            id="confirm_delete_btn",
            on_click=on_confirm_delete
        ),
        Back(Const("❌ Отмена")),
    ),
    state=FeedManagementSG.confirm_delete,
    getter=get_chat_info
)

# Create dialog
feed_management_dialog = Dialog(
    select_chat_window,
    chat_menu_window,
    manage_feeds_window,
    add_feed_window,
    confirm_delete_window
)
