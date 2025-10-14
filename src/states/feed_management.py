from aiogram.fsm.state import State, StatesGroup


class FeedManagementSG(StatesGroup):
    select_chat = State()
    chat_menu = State()
    add_feed = State()
    manage_feeds = State()
    confirm_delete = State()
