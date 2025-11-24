from aiogram.enums import ParseMode
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Group, Select, Url
from aiogram_dialog.widgets.text import Const, Format


from app.bot.dialogs.flows.main.getters import (
    get_channel_settings_data,
    get_global_settings_data,
    get_group_menu_data,
    get_remove_source_data,
    get_rss_parser_data,
    get_sources_list_data,
)
from app.bot.dialogs.flows.main.handlers import (
    on_add_group_clicked,
    on_add_source,
    on_api_key_input,
    on_back_to_settings,
    on_custom_interval_clicked,
    on_delete_group,
    on_delete_group_confirmed,
    on_global_api_key_input,
    on_global_disable_parsing,
    on_global_enable_parsing,
    on_global_set_api_key_clicked,
    on_global_settings_clicked,
    on_group_selected,
    on_interval_input,
    on_interval_preset_selected,
    on_list_sources,
    on_remove_source,
    on_set_api_key_clicked,
    on_set_interval_clicked,
    on_settings_clicked,
    on_source_selected,
    on_source_url_input,
    on_toggle_group,
    on_toggle_scraper,
)
from app.bot.dialogs.flows.main.states import MainSG


rss_parser_dialog = Dialog(
    Window(
        Const(
            "⚒️ <b>RSS-Парсер</b>\n\n"
            "Здесь вы можете подключить и настроить источники для парсинга.\n\n"
            "Выберите группу, в которой хотите настроить парсинг."
        ),
        Group(
            Select(
                Format("{item[0]}"),
                id="group_select",
                item_id_getter=lambda x: x[1],
                items="group_buttons",
                on_click=on_group_selected,
            ),
            width=2,
        ),
        Button(
            text=Const("➕ Добавить группу"),
            id="add_group_btn",
            on_click=on_add_group_clicked,
        ),
        Button(
            text=Const("Все группы"),
            id="global_settings_btn",
            on_click=on_global_settings_clicked,
        ),
        getter=get_rss_parser_data,
        state=MainSG.rss_parser,
        parse_mode=ParseMode.HTML,
    ),
    Window(
        Format(
            "<b>Подключение группы</b>\n\n"
            "Чтобы подключить группу, сделайте @{bot_username} его администратором, выдав следующие права:\n\n"
            "➕ Отправка сообщений\n"
            "➕ Редактирование сообщений\n"
            "➕ Удаление сообщений"
        ),
        Url(
            text=Const("➕ Добавить бота в группу"),
            url=Format("{add_group_url}"),
            id="add_bot_url",
        ),
        Button(
            text=Const("← Назад"),
            id="back_to_rss_parser_btn",
            on_click=lambda c, w, m: m.switch_to(MainSG.rss_parser),
        ),
        getter=get_rss_parser_data,
        state=MainSG.add_group_instruction,
        parse_mode=ParseMode.HTML,
    ),
    Window(
        Format(
            "<b>📱 Группа: {group_name}</b>\n\n"
            "Выберите действие:"
        ),
        Button(
            text=Format("{toggle_text}"),
            id="toggle_group_btn",
            on_click=on_toggle_group,
        ),
        Button(
            text=Const("📄 Список источников"),
            id="list_sources_btn",
            on_click=on_list_sources,
        ),
        Group(
            Button(
                text=Const("➕ Добавить источник"),
                id="add_source_btn",
                on_click=on_add_source,
            ),
            Button(
                text=Const("➖ Удалить источник"),
                id="remove_source_btn",
                on_click=on_remove_source,
            ),
            width=2,
        ),
        Button(
            text=Const("⚙️ Настройки"),
            id="settings_btn",
            on_click=on_settings_clicked,
        ),
        Button(
            text=Const("🗑️ Удалить группу"),
            id="delete_group_btn",
            on_click=on_delete_group,
        ),
        Button(
            text=Const("← Назад"),
            id="back_to_rss_parser_btn2",
            on_click=lambda c, w, m: m.switch_to(MainSG.rss_parser),
        ),
        getter=get_group_menu_data,
        state=MainSG.group_menu,
        parse_mode=ParseMode.HTML,
    ),
    Window(
        Format(
            "<b>📄 Список источников</b>\n\n"
            "<b>Количество источников:</b> {sources_count}\n\n"
            "{sources}"
        ),
        Button(
            text=Const("← Назад"),
            id="back_to_group_menu_btn2",
            on_click=lambda c, w, m: m.switch_to(MainSG.group_menu),
        ),
        getter=get_sources_list_data,
        state=MainSG.sources_list,
        parse_mode=ParseMode.HTML,
    ),
    Window(
        Format(
            "<b>➕ Добавить источник</b>\n\n"
            "Отправьте URL RSS-ленты, которую хотите добавить.\n\n"
            "Пример:\n"
            "<code>https://example.com/feed.xml</code>"
        ),
        MessageInput(
            func=on_source_url_input,
        ),
        Button(
            text=Const("← Назад"),
            id="back_to_group_menu_btn",
            on_click=lambda c, w, m: m.switch_to(MainSG.group_menu),
        ),
        getter=get_group_menu_data,
        state=MainSG.add_source,
        parse_mode=ParseMode.HTML,
    ),
    Window(
        Format(
            "<b>➖ Удалить источник</b>\n\n"
            "<b>Группа:</b> {group_name}\n\n"
            "Выберите источник для удаления:"
        ),
        Select(
            Format("{item[0]}"),
            id="source_select",
            item_id_getter=lambda x: x[1],
            items="source_buttons",
            on_click=on_source_selected,
        ),
        Button(
            text=Const("← Назад"),
            id="back_to_group_menu_btn3",
            on_click=lambda c, w, m: m.switch_to(MainSG.group_menu),
        ),
        getter=get_remove_source_data,
        state=MainSG.remove_source,
        parse_mode=ParseMode.HTML,
    ),
    Window(
        Format(
            "<b>⚙️ Настройки группы</b>\n\n"
            "<b>⏱ Интервал проверки:</b> {interval_time} сек ({interval_minutes} мин)\n"
            "<b>🔧 Скрапер:</b> {scraper_status}\n"
            "<b>🔑 API ключ:</b> {api_key_status}\n\n"
            "Выберите действие:"
        ),
        Button(
            text=Format("{scraper_toggle_text}"),
            id="toggle_scraper_btn",
            on_click=on_toggle_scraper,
        ),
        Button(
            text=Const("⏱ Изменить интервал"),
            id="set_interval_btn",
            on_click=on_set_interval_clicked,
        ),
        Button(
            text=Const("🔑 Установить API ключ"),
            id="set_api_key_btn",
            on_click=on_set_api_key_clicked,
        ),
        Button(
            text=Const("← Назад"),
            id="back_to_group_menu_btn4",
            on_click=lambda c, w, m: m.switch_to(MainSG.group_menu),
        ),
        getter=get_channel_settings_data,
        state=MainSG.channel_settings,
        parse_mode=ParseMode.HTML,
    ),
    Window(
        Format(
            "<b>🗑️ Удаление группы</b>\n"
            "<b>Группа:</b> {group_name}\n"
            "⚠️ Вы уверены, что хотите удалить эту группу?\n"
            "Это действие удалит:\n"
            "• Все подписки на RSS-ленты\n"
            "• Все настройки группы\n\n"
            "<b>Это действие нельзя отменить.</b>"
        ),
        Button(
            text=Const("✅ Да, удалить"),
            id="confirm_delete_btn",
            on_click=on_delete_group_confirmed,
        ),
        Button(
            text=Const("❌ Отмена"),
            id="cancel_delete_btn",
            on_click=lambda c, w, m: m.switch_to(MainSG.channel_settings),
        ),
        getter=get_group_menu_data,
        state=MainSG.delete_group_confirm,
        parse_mode=ParseMode.HTML,
    ),
    Window(
        Format(
            "<b>⏱ Интервал проверки RSS</b>\n\n"
            "<b>Текущий интервал:</b> {interval_time} секунд ({interval_minutes} минут)\n\n"
            "Выберите интервал проверки:"
        ),
        Group(
            Select(
                Format("{item[0]}"),
                id="interval_preset_select",
                item_id_getter=lambda x: x[1],
                items=[
                    ("⏱ 5 минут", "300"),
                    ("⏱ 10 минут", "600"),
                    ("⏱ 15 минут", "900"),
                    ("⏱ 20 минут", "1200"),
                    ("⏱ 30 минут", "1800"),
                    ("⏱ 45 минут", "2700"),
                    ("⏱ 1 час", "3600"),
                ],
                on_click=on_interval_preset_selected,
            ),
            width=3,
        ),
        Button(
            text=Const("✏️ Своё значение"),
            id="custom_interval_btn",
            on_click=on_custom_interval_clicked,
        ),
        Button(
            text=Const("← Назад"),
            id="back_to_settings_btn",
            on_click=on_back_to_settings,
        ),
        getter=get_channel_settings_data,
        state=MainSG.set_interval,
        parse_mode=ParseMode.HTML,
    ),
    Window(
        Format(
            "<b>⏱ Свой интервал проверки RSS</b>\n"
            "<b>Текущий интервал:</b> {interval_time} секунд ({interval_minutes} минут)\n"
            "Введите новый интервал в секундах (минимум 60, максимум 86400):\n\n"
            "Примеры:\n"
            "• 60 = 1 минута\n"
            "• 300 = 5 минут\n"
            "• 600 = 10 минут\n"
            "• 3600 = 1 час"
        ),
        MessageInput(
            func=on_interval_input,
        ),
        Button(
            text=Const("← Назад"),
            id="back_to_interval_btn",
            on_click=on_set_interval_clicked,
        ),
        getter=get_channel_settings_data,
        state=MainSG.set_interval_custom,
        parse_mode=ParseMode.HTML,
    ),
    Window(
        Format(
            "<b>🔑 API ключ ScraperAPI</b>\n"
            "ℹ️ API ключ используется для извлечения полного текста статей."
        ),
        MessageInput(
            func=on_api_key_input,
        ),
        Button(
            text=Const("← Назад"),
            id="back_to_settings_btn2",
            on_click=on_back_to_settings,
        ),
        getter=get_channel_settings_data,
        state=MainSG.set_scraper_api_key,
        parse_mode=ParseMode.HTML,
    ),
    # ============ Global Settings Windows ============
    Window(
        Format(
            "<b>🌐 Глобальные настройки</b>\n\n"
            "Настройки применяются ко всем каналам сразу.\n\n"
            "<b>📊 Статистика:</b>\n"
            "• Всего каналов: {total_channels}\n"
            "• Парсинг включен: {enabled_count}\n"
            "• Парсинг выключен: {disabled_count}"
        ),
        Button(
            text=Const("✅ Включить парсинг для всех"),
            id="global_enable_parsing_btn",
            on_click=on_global_enable_parsing,
        ),
        Button(
            text=Const("❌ Выключить парсинг для всех"),
            id="global_disable_parsing_btn",
            on_click=on_global_disable_parsing,
        ),
        Button(
            text=Const("🔑 Установить API ключ для всех"),
            id="global_set_api_key_btn",
            on_click=on_global_set_api_key_clicked,
        ),
        Button(
            text=Const("← Назад"),
            id="back_to_main_btn",
            on_click=lambda c, w, m: m.switch_to(MainSG.rss_parser),
        ),
        getter=get_global_settings_data,
        state=MainSG.global_settings,
        parse_mode=ParseMode.HTML,
    ),
    Window(
        Const(
            "<b>🔑 Установить API ключ для всех каналов</b>\n\n"
            "Отправьте API ключ ScraperAPI, который будет установлен для всех каналов.\n\n"
            "Отправьте пустое сообщение или пробел, чтобы удалить API ключ у всех каналов."
        ),
        MessageInput(
            func=on_global_api_key_input,
        ),
        Button(
            text=Const("← Назад"),
            id="back_to_global_settings_btn",
            on_click=lambda c, w, m: m.switch_to(MainSG.global_settings),
        ),
        state=MainSG.global_set_api_key,
        parse_mode=ParseMode.HTML,
    ),
)
