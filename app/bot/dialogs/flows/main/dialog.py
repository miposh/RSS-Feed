from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.kbd import Group, Select, Url
from aiogram_dialog.widgets.text import Const, Format

from app.bot.dialogs.flows.main.getters import get_rss_parser_data
from app.bot.dialogs.flows.main.handlers import on_group_selected
from app.bot.dialogs.flows.main.states import MainSG


rss_parser_dialog = Dialog(
    Window(
        Const(
            "RSS-Парсер\n\n"
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
        Url(
            text=Const("➕ Добавить группу"),
            url=Format("{add_group_url}"),
            id="add_group_btn",
        ),
        getter=get_rss_parser_data,
        state=MainSG.rss_parser,
    ),
)
