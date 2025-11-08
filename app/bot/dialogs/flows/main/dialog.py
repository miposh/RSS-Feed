from aiogram.enums import ParseMode
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Back, Button, Group, Select, Url
from aiogram_dialog.widgets.text import Const, Format


from app.bot.dialogs.flows.main.getters import get_rss_parser_data
from app.bot.dialogs.flows.main.handlers import on_add_group_clicked, on_group_selected
from app.bot.dialogs.flows.main.states import MainSG


rss_parser_dialog = Dialog(
    Window(
        Const(
            "<b>RSS-Парсер</b>\n\n"
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
)
