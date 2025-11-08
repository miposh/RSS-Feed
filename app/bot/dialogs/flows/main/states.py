from aiogram.fsm.state import State, StatesGroup


class MainSG(StatesGroup):
    rss_parser = State()
    add_group_instruction = State()
