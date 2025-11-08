from aiogram.enums import ParseMode
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Back, Button, Group, Select, Url
from aiogram_dialog.widgets.text import Const, Format


from app.bot.dialogs.flows.main.getters import (
    get_group_menu_data,
    get_remove_source_data,
    get_rss_parser_data,
    get_sources_list_data,
)
from app.bot.dialogs.flows.main.handlers import (
    on_add_group_clicked,
    on_add_source,
    on_delete_group,
    on_group_selected,
    on_list_sources,
    on_remove_source,
    on_source_selected,
    on_source_url_input,
    on_toggle_group,
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
        Back(Const("← Назад")),
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
            text=Const("🗑️ Удалить группу"),
            id="delete_group_btn",
            on_click=on_delete_group,
        ),
        Back(Const("← Назад")),
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
        Back(Const("← Назад")),
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
        Back(Const("← Назад")),
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
        Back(Const("← Назад")),
        getter=get_remove_source_data,
        state=MainSG.remove_source,
        parse_mode=ParseMode.HTML,
    ),
)
