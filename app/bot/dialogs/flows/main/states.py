from aiogram.fsm.state import State, StatesGroup


class MainSG(StatesGroup):
    rss_parser = State()
    add_group_instruction = State()
    group_menu = State()
    sources_list = State()
    add_source = State()
    remove_source = State()
