from aiogram.fsm.state import State, StatesGroup


class MainSG(StatesGroup):
    rss_parser = State()
    add_group_instruction = State()
    group_menu = State()
    sources_list = State()
    add_source = State()
    remove_source = State()
    channel_settings = State()
    set_interval = State()
    set_interval_custom = State()
    set_scraper_api_key = State()
    # Delete group confirmation
    delete_group_confirm = State()
    # Global settings for all channels
    global_settings = State()
    global_set_api_key = State()
